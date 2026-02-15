"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import Optional
from sqlalchemy import insert, select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta


from backend.database import get_db
from backend.dbmodels.application import (
    ApplicationComment,
    ApplicationActionLog,
    InspectionReport,
    NakaEntry,
)
from backend.dao.base import BaseDAO
from backend.meta import ApplicationStatus, CommentType, WorkflowAction
from backend.schemas.request.application import ApplicationCreate
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.response.meta import SuccessResponse
from backend.dbmodels.application import (
    Application,
    ApplicationDocument,
    ApplicationApproval,
    ApplicationMaterial,
    ApplicationPhaseMaterial,
    ApprovedApplicationPhase,
    Material,
)
from backend.meta import (
    ApplicationDocumentType,
    ApplicationFlags,
    UserRole,
    ApplicationType,
    ApplicationPhaseStatus,
)
from backend.core.workflow import validate_transition, RENOVATION_DEPT_ROLES


# ── Eager-loading options reused across queries ──────────────────────────
_APPLICATION_LOAD_OPTIONS = [
    selectinload(Application.documents),
    selectinload(Application.materials),
    selectinload(Application.comments).selectinload(ApplicationComment.commenter),
    selectinload(Application.approvals).selectinload(ApplicationApproval.approver),
    selectinload(Application.phases),
    selectinload(Application.phase_materials),
    selectinload(Application.inspections),
    selectinload(Application.naka_entries),
    selectinload(Application.action_logs),
]


class ApplicationDAO(BaseDAO):
    """Application DAO."""

    # ── Flag computation ──────────────────────────────────────────────────
    def get_required_flags(self, application: Application) -> list[ApplicationFlags]:
        """Compute which dashboard-flags an application should appear under."""
        flags: list[ApplicationFlags] = []
        st = application.status
        tp = application.type

        # ── OBJECTED (both flows) ─────────────────────────────────────
        if st == ApplicationStatus.OBJECTED:
            flags.append(ApplicationFlags.OBJECTED_CITIZEN_ACTION)
            return flags

        # ── NEW flow ──────────────────────────────────────────────────
        if tp == ApplicationType.NEW:
            if st == ApplicationStatus.SUBMITTED:
                flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION)

            elif st == ApplicationStatus.APPROVED:
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_INSPECTION)
                elif not application.materials:
                    flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_MATERIAL_ENTRY)
                else:
                    flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION)

            elif st == ApplicationStatus.TOKEN_GENERATED:
                self._add_phase_flags(application, flags)

        # ── RENOVATION flow ───────────────────────────────────────────
        elif tp == ApplicationType.RENOVATION:
            if st == ApplicationStatus.SUBMITTED:
                flags.append(ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_FORWARD)

            elif st == ApplicationStatus.FORWARDED:
                # Check which depts have commented with DEPT_REVIEW type
                dept_review_roles = {
                    c.commenter.role
                    for c in application.comments
                    if c.comment_type == CommentType.DEPT_REVIEW
                }
                missing_depts = RENOVATION_DEPT_ROLES - dept_review_roles
                if missing_depts:
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_DEPT_COMMENT)
                    # Check overdue (> 7 days since forward)
                    forward_actions = [
                        a for a in application.action_logs
                        if a.action == WorkflowAction.FORWARD
                    ]
                    if forward_actions:
                        latest = max(forward_actions, key=lambda a: a.performed_at)
                        if datetime.now() - latest.performed_at > timedelta(days=7):
                            flags.append(ApplicationFlags.RENOVATION_OVERDUE_COMMENTS)
                            for dept in missing_depts:
                                suffix = dept.value.split("_")[-1]
                                flag_name = f"RENOVATION_OVERDUE_COMMENTS_{suffix}"
                                if hasattr(ApplicationFlags, flag_name):
                                    flags.append(ApplicationFlags(flag_name))
                else:
                    # All depts commented → Commissioner can act
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION)

            elif st == ApplicationStatus.APPROVED:
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION)
                elif not application.materials:
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY)
                else:
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION)

            elif st == ApplicationStatus.TOKEN_GENERATED:
                self._add_phase_flags(application, flags)

        return flags

    @staticmethod
    def _add_phase_flags(application: Application, flags: list[ApplicationFlags]):
        """Append phase-level and naka flags for TOKEN_GENERATED applications."""
        active_phases = [
            p for p in application.phases
            if p.status == ApplicationPhaseStatus.ACTIVE
        ]
        if active_phases:
            flags.append(ApplicationFlags.PHASE_READY_FOR_NAKA)
            flags.append(ApplicationFlags.NAKA_INCHARGE_ACTION)

    async def update_application(
        self, application_id: int, application: ApplicationCreate
    ) -> Optional[ApplicationResponse]:
        """Update application."""
        # For simplicity, only allow updating the basic fields, not materials or documents here
        application_data = application.model_dump(exclude={"material_requirements"})
        await self.session.execute(
            update(Application)
            .where(Application.id == application_id)
            .values(**application_data)
        )
        await self.session.commit()
        return await self.get_application(application_id)

    async def create_application(
        self, application: ApplicationCreate, user_id: int, mobile: str
    ) -> ApplicationResponse:
        """Create application."""
        # Extract material requirements before creating application
        material_requirements = application.material_requirements
        application_data = application.model_dump(exclude={"material_requirements"})
        application_data["user_id"] = user_id
        application_data["mobile"] = mobile

        # Validate that all material IDs exist
        if material_requirements:
            material_ids = [m.material_id for m in material_requirements]

            # Query existing materials
            stmt = select(Material.id).where(Material.id.in_(material_ids))
            result = await self.session.execute(stmt)
            existing_ids = set(result.scalars().all())

            # Check for invalid material IDs
            invalid_ids = [mid for mid in material_ids if mid not in existing_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid material IDs: {invalid_ids}. These materials do not exist.",
                )

        # Create the application
        result = await self.session.execute(
            insert(Application).values(**application_data).returning(Application.id)
        )
        new_application_id = result.scalar_one()

        # Insert material requirements into ApplicationMaterial table
        if material_requirements:
            for material in material_requirements:
                await self.session.execute(
                    insert(ApplicationMaterial).values(
                        application_id=new_application_id,
                        material_id=material.material_id,
                        quantity=material.material_qty,
                    )
                )

        await self.session.commit()

        # Re-fetch the application with all relationships loaded
        stmt = (
            select(Application)
            .where(Application.id == new_application_id)
            .options(
                selectinload(Application.documents),
                selectinload(Application.materials),
                selectinload(Application.comments).selectinload(ApplicationComment.commenter),
                selectinload(Application.approvals).selectinload(ApplicationApproval.approver),
                selectinload(Application.phases),
            )
        )
        result = await self.session.execute(stmt)
        new_application = result.scalar_one()

        return ApplicationResponse.model_validate(new_application)

    async def get_application(self, application_id: int) -> Optional[ApplicationResponse]:
        """Get application."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.documents),
                selectinload(Application.materials),
                selectinload(Application.comments).selectinload(ApplicationComment.commenter),
                selectinload(Application.approvals).selectinload(ApplicationApproval.approver),
                selectinload(Application.phases),
            )
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()

        # application = await self.session.get(Application, application_id) # Old method
        if not application:
            return None  # Handle outside

        return ApplicationResponse.model_validate(application)

    async def get_applications(
        self,
        flag: Optional[ApplicationFlags] = None,
        offset: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> list[ApplicationResponse]:
        """Get applications, optionally filtered by flag."""
        query = select(Application).options(
            selectinload(Application.documents),
            selectinload(Application.materials),
            selectinload(Application.comments).selectinload(ApplicationComment.commenter),
            selectinload(Application.approvals).selectinload(ApplicationApproval.approver),
            selectinload(Application.phases),
        )
        if user_id:
            query = query.where(Application.user_id == user_id)

        if flag is None:
            # No flag filter — return paginated results directly (citizen path)
            applications = await self.session.scalars(query.offset(offset).limit(limit))
            return [
                ApplicationResponse.model_validate(app) for app in applications
            ]

        # Flag filter — load all matching apps, compute flags, then paginate in Python
        all_applications = (await self.session.scalars(query)).all()
        matched = [
            ApplicationResponse.model_validate(app)
            for app in all_applications
            if flag in self.get_required_flags(app)
        ]
        return matched[offset : offset + limit]

    async def approve_application(self, application_id: int) -> SuccessResponse:
        """Approve an Application (legacy simple path, use perform_workflow_action instead)."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        application.status = ApplicationStatus.APPROVED
        await self.session.commit()
        return SuccessResponse(message="Application approved successfully")

    async def delete_application(self, application_id: int) -> SuccessResponse:
        """Delete an Application."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        await self.session.delete(application)
        await self.session.commit()
        return SuccessResponse(message=None)

    async def add_document(
        self,
        application_id: int,
        document_path: str,
        document_type: ApplicationDocumentType,
        user_id: int,
        document_name: Optional[str] = None,
    ) -> SuccessResponse:
        """Add document record."""
        await self.session.execute(
            insert(ApplicationDocument).values(
                application_id=application_id,
                document_path=document_path,
                document_type=document_type,
                document_by=user_id,
                document_name=document_name,
            )
        )
        await self.session.commit()
        return SuccessResponse(message=None)

    async def add_materials(
        self, application_id: int, material_requirements: list
    ) -> SuccessResponse:
        """Add materials to an existing application."""
        material_ids = [m.material_id for m in material_requirements]

        # Query existing materials
        stmt = select(Material.id).where(Material.id.in_(material_ids))
        result = await self.session.execute(stmt)
        existing_ids = set(result.scalars().all())

        # Check for invalid material IDs
        invalid_ids = [mid for mid in material_ids if mid not in existing_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid material IDs: {invalid_ids}. These materials do not exist.",
            )

        # Insert material requirements into ApplicationMaterial table
        for material in material_requirements:
            await self.session.execute(
                insert(ApplicationMaterial).values(
                    application_id=application_id,
                    material_id=material.material_id,
                    quantity=material.material_qty,
                )
            )

        await self.session.commit()
        return SuccessResponse(message=None)

    async def submit_application(
        self, application_id: int, user_id: int
    ) -> SuccessResponse:
        """Submit an application (change status from PENDING to SUBMITTED).
        
        Validates that the application has the required document types:
        AADHAAR, PERMISSION_DOCUMENTS, and OWNERSHIP_DOCUMENTS.
        Only the owning CITIZEN can submit.
        """
        # Load application with documents
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(selectinload(Application.documents))
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if application.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="You can only submit your own applications"
            )

        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Application is in '{application.status.value}' status and cannot be submitted. Only PENDING applications can be submitted.",
            )

        # Validate required document types
        existing_doc_types = {doc.document_type for doc in application.documents}
        required_doc_types = {
            ApplicationDocumentType.AADHAAR,
            ApplicationDocumentType.PERMISSION_DOCUMENTS,
            ApplicationDocumentType.OWNERSHIP_DOCUMENTS,
        }
        missing = required_doc_types - existing_doc_types
        if missing:
            missing_names = [dt.value for dt in missing]
            raise HTTPException(
                status_code=400,
                detail=f"Cannot submit: missing required documents: {', '.join(sorted(missing_names))}. "
                       f"Please upload AADHAAR, PERMISSION_DOCUMENTS, and OWNERSHIP_DOCUMENTS before submitting.",
            )

        # Update status
        application.status = ApplicationStatus.SUBMITTED
        await self.session.commit()
        return SuccessResponse(message="Application submitted successfully")

    async def get_comments(self, application_id: int) -> list[ApplicationComment]:
        """Get all comments for an application."""
        stmt = (
            select(ApplicationComment)
            .where(ApplicationComment.application_id == application_id)
            .options(selectinload(ApplicationComment.commenter))
            .order_by(ApplicationComment.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Workflow action (approve / reject / object / forward / generate-tokens) ─
    async def perform_workflow_action(
        self,
        application_id: int,
        action: WorkflowAction,
        user_id: int,
        user_role: UserRole,
        remarks: Optional[str] = None,
        num_stages: Optional[int] = None,
        phase_materials: Optional[list] = None,
    ) -> SuccessResponse:
        """
        Execute a workflow action on an application.
        Uses the state machine to validate the transition and update status.
        For GENERATE_TOKENS also creates phases + phase materials.
        """
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.inspections),
                selectinload(Application.materials),
                selectinload(Application.phases),
                selectinload(Application.phase_materials),
            )
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Validate via state machine (raises ValueError on failure)
        try:
            next_status = validate_transition(
                application.status, action, application.type, user_role
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        old_status = application.status

        # ── GENERATE_TOKENS specific logic ────────────────────────────────
        if action == WorkflowAction.GENERATE_TOKENS:
            if not num_stages or num_stages < 1:
                raise HTTPException(
                    status_code=400,
                    detail="num_stages is required for GENERATE_TOKENS and must be >= 1",
                )
            # Require JEN inspection for NEW flow
            if application.type == ApplicationType.NEW and not application.inspections:
                raise HTTPException(
                    status_code=400,
                    detail="JEN inspection must be completed before generating tokens",
                )
            application.num_stages = num_stages

            # Create phases
            for phase_num in range(1, num_stages + 1):
                phase_status = (
                    ApplicationPhaseStatus.ACTIVE if phase_num == 1
                    else ApplicationPhaseStatus.PENDING
                )
                self.session.add(
                    ApprovedApplicationPhase(
                        application_id=application_id,
                        phase=phase_num,
                        name=f"Phase {phase_num}",
                        status=phase_status,
                        activated_at=datetime.now() if phase_num == 1 else None,
                    )
                )

            # Create phase materials if provided (skip duplicates from JEN inspection)
            if phase_materials:
                existing_pm_stmt = select(ApplicationPhaseMaterial).where(
                    ApplicationPhaseMaterial.application_id == application_id,
                )
                existing_pm_result = await self.session.execute(existing_pm_stmt)
                existing_keys = {
                    (pm.phase, pm.material_id)
                    for pm in existing_pm_result.scalars().all()
                }
                for pm in phase_materials:
                    key = (pm.phase, pm.material_id)
                    if key in existing_keys:
                        continue  # already created by JEN inspection
                    self.session.add(
                        ApplicationPhaseMaterial(
                            application_id=application_id,
                            phase=pm.phase,
                            material_id=pm.material_id,
                            quantity=pm.quantity,
                        )
                    )

        # Update application status
        application.status = next_status

        # Record approval row
        self.session.add(
            ApplicationApproval(
                application_id=application_id,
                action=action,
                remarks=remarks,
                approved_by=user_id,
                approved_at=datetime.now(),
            )
        )

        # Audit log
        self.session.add(
            ApplicationActionLog(
                application_id=application_id,
                action=action,
                from_status=old_status,
                to_status=next_status,
                performed_by=user_id,
                performed_at=datetime.now(),
                remarks=remarks,
            )
        )

        await self.session.commit()
        return SuccessResponse(
            message=f"Application {action.value.lower()}d successfully"
        )

    # ── JEN inspection ────────────────────────────────────────────────────
    async def create_inspection_report(
        self,
        application_id: int,
        user_id: int,
        latitude: Optional[float],
        longitude: Optional[float],
        remarks: str,
        media_paths: Optional[list] = None,
        recommended_phases: Optional[int] = None,
        phase_materials: Optional[list] = None,
    ) -> SuccessResponse:
        """Create a JEN inspection report for an application."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.status != ApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail="Inspection is only allowed on APPROVED applications",
            )

        self.session.add(
            InspectionReport(
                application_id=application_id,
                inspected_by=user_id,
                inspected_at=datetime.now(),
                latitude=latitude,
                longitude=longitude,
                remarks=remarks,
                media_paths=media_paths,
                recommended_phases=recommended_phases,
            )
        )

        # If JEN also provides phase material recommendations, save them
        if phase_materials:
            for pm in phase_materials:
                self.session.add(
                    ApplicationPhaseMaterial(
                        application_id=application_id,
                        phase=pm.phase,
                        material_id=pm.material_id,
                        quantity=pm.quantity,
                    )
                )

        await self.session.commit()
        return SuccessResponse(message="Inspection report created successfully")

    # ── Naka checkpoint entry ─────────────────────────────────────────────
    async def create_naka_entry(
        self,
        application_id: int,
        phase: int,
        user_id: int,
        material_id: int,
        quantity_brought: int,
        vehicle_number: Optional[str] = None,
        remarks: Optional[str] = None,
        media_path: Optional[str] = None,
    ) -> SuccessResponse:
        """Log a material checkpoint entry at Naka."""
        # Verify application status
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.status != ApplicationStatus.TOKEN_GENERATED:
            raise HTTPException(
                status_code=400,
                detail="Naka entries are only allowed on TOKEN_GENERATED applications",
            )

        # Verify phase is ACTIVE
        stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase,
        )
        result = await self.session.execute(stmt)
        phase_record = result.scalar_one_or_none()
        if not phase_record:
            raise HTTPException(status_code=404, detail=f"Phase {phase} not found")
        if phase_record.status != ApplicationPhaseStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail=f"Phase {phase} is '{phase_record.status.value}', must be ACTIVE for naka entry",
            )

        # Validate quantity against phase material limit
        pm_stmt = select(ApplicationPhaseMaterial).where(
            ApplicationPhaseMaterial.application_id == application_id,
            ApplicationPhaseMaterial.phase == phase,
            ApplicationPhaseMaterial.material_id == material_id,
        )
        pm_result = await self.session.execute(pm_stmt)
        phase_mat = pm_result.scalar_one_or_none()
        if not phase_mat:
            raise HTTPException(
                status_code=400,
                detail=f"Material {material_id} is not allocated for phase {phase}",
            )

        # Sum existing naka entries for this material in this phase
        used_stmt = select(func.coalesce(func.sum(NakaEntry.quantity_brought), 0)).where(
            NakaEntry.application_id == application_id,
            NakaEntry.phase == phase,
            NakaEntry.material_id == material_id,
        )
        used_result = await self.session.execute(used_stmt)
        already_brought: int = used_result.scalar() or 0

        if already_brought + quantity_brought > phase_mat.quantity:
            remaining: int = phase_mat.quantity - already_brought
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Quantity exceeds limit. Phase {phase} allows {phase_mat.quantity} "
                    f"of material {material_id}, already brought {already_brought}, "
                    f"remaining {remaining}. Requested: {quantity_brought}."
                ),
            )

        self.session.add(
            NakaEntry(
                application_id=application_id,
                phase=phase,
                material_id=material_id,
                quantity_brought=quantity_brought,
                entry_by=user_id,
                entry_at=datetime.now(),
                vehicle_number=vehicle_number,
                remarks=remarks,
                media_path=media_path,
            )
        )
        await self.session.commit()
        return SuccessResponse(message="Naka entry recorded successfully")

    async def get_naka_entries(self, application_id: int) -> list[NakaEntry]:
        """Get all naka entries for an application."""
        stmt = (
            select(NakaEntry)
            .where(NakaEntry.application_id == application_id)
            .order_by(NakaEntry.entry_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_phase_material_summary(
        self, application_id: int, phase: int
    ) -> dict:
        """Get material summary for a phase at the naka checkpoint.

        Returns dict with phase info and per-material allowed/brought/remaining.
        Validates application is TOKEN_GENERATED and phase exists.
        """
        # Verify application status
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.status != ApplicationStatus.TOKEN_GENERATED:
            raise HTTPException(
                status_code=400,
                detail="This transport code is not currently active",
            )

        # Get phase record
        phase_stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase,
        )
        phase_result = await self.session.execute(phase_stmt)
        phase_record = phase_result.scalar_one_or_none()
        if not phase_record:
            raise HTTPException(status_code=404, detail="Phase not found")

        # Get phase materials with material details
        pm_stmt = (
            select(ApplicationPhaseMaterial, Material)
            .join(Material, ApplicationPhaseMaterial.material_id == Material.id)
            .where(
                ApplicationPhaseMaterial.application_id == application_id,
                ApplicationPhaseMaterial.phase == phase,
            )
        )
        pm_result = await self.session.execute(pm_stmt)
        phase_materials = pm_result.all()

        # Sum brought quantities per material from naka entries
        brought_stmt = (
            select(
                NakaEntry.material_id,
                func.coalesce(func.sum(NakaEntry.quantity_brought), 0).label("total_brought"),
            )
            .where(
                NakaEntry.application_id == application_id,
                NakaEntry.phase == phase,
            )
            .group_by(NakaEntry.material_id)
        )
        brought_result = await self.session.execute(brought_stmt)
        brought_map = {row.material_id: row.total_brought for row in brought_result}

        materials = []
        for pm, mat in phase_materials:
            brought = brought_map.get(mat.id, 0)
            materials.append({
                "material_id": mat.id,
                "material_name": mat.name,
                "unit": mat.unit,
                "allowed_qty": pm.quantity,
                "brought_qty": brought,
                "remaining_qty": pm.quantity - brought,
            })

        return {
            "phase": phase_record.phase,
            "phase_status": phase_record.status,
            "materials": materials,
        }

    # ── Phase management ──────────────────────────────────────────────────
    async def get_phases(self, application_id: int) -> list[ApprovedApplicationPhase]:
        """Get all phases for an application."""
        stmt = (
            select(ApprovedApplicationPhase)
            .where(ApprovedApplicationPhase.application_id == application_id)
            .order_by(ApprovedApplicationPhase.phase)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def complete_phase(
        self, application_id: int, phase_num: int, user_id: int
    ) -> SuccessResponse:
        """Mark a phase as COMPLETED and activate the next one."""
        stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase_num,
        )
        result = await self.session.execute(stmt)
        phase_record = result.scalar_one_or_none()
        if not phase_record:
            raise HTTPException(status_code=404, detail=f"Phase {phase_num} not found")
        if phase_record.status != ApplicationPhaseStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail=f"Phase {phase_num} must be ACTIVE to complete, current status: {phase_record.status.value}",
            )

        phase_record.status = ApplicationPhaseStatus.COMPLETED
        phase_record.completed_at = datetime.now()

        # Activate next phase if exists
        next_stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase_num + 1,
        )
        next_result = await self.session.execute(next_stmt)
        next_phase = next_result.scalar_one_or_none()
        if next_phase and next_phase.status == ApplicationPhaseStatus.PENDING:
            next_phase.status = ApplicationPhaseStatus.ACTIVE
            next_phase.activated_at = datetime.now()

        # Audit log
        self.session.add(
            ApplicationActionLog(
                application_id=application_id,
                action=WorkflowAction.APPROVE,  # reuse APPROVE for phase completion
                from_status=ApplicationStatus.TOKEN_GENERATED,
                to_status=ApplicationStatus.TOKEN_GENERATED,
                performed_by=user_id,
                performed_at=datetime.now(),
                remarks=f"Phase {phase_num} completed",
                phase=phase_num,
            )
        )

        await self.session.commit()
        return SuccessResponse(message=f"Phase {phase_num} completed successfully")

    # ── Comment (enhanced) ────────────────────────────────────────────────
    async def comment_on_application(
        self,
        application_id: int,
        comment: str,
        user_id: int,
        comment_type: CommentType = CommentType.GENERAL,
        media_paths: Optional[list] = None,
    ) -> SuccessResponse:
        """Comment on application."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        self.session.add(
            ApplicationComment(
                application_id=application_id,
                comment=comment,
                comment_by=user_id,
                comment_type=comment_type,
                media_paths=media_paths,
                created_at=datetime.now(),
            )
        )
        await self.session.commit()
        return SuccessResponse(message="Comment added successfully")


async def get_application_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationDAO:
    """..."""
    return ApplicationDAO(session)
