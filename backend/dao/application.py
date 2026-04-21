"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import Optional
from sqlalchemy import insert, select, update, exists, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta


from backend.database import get_db
from backend.dbmodels.application import (
    ApplicationComment,
    ApplicationActionLog,
    InspectionReport,
    VehicleEntry,
    VehicleMaterial,
    VehicleEntryDumpingPhoto,
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
    selectinload(Application.materials).selectinload(ApplicationMaterial.material),
    selectinload(Application.comments).selectinload(ApplicationComment.commenter),
    selectinload(Application.phases),
    selectinload(Application.phase_materials).selectinload(ApplicationPhaseMaterial.material),
    selectinload(Application.inspections).selectinload(InspectionReport.inspector),
    selectinload(Application.vehicle_entries).selectinload(VehicleEntry.materials).selectinload(VehicleMaterial.material),
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
                flags.append(
                    ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION
                )

            elif st == ApplicationStatus.APPROVED:
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(
                        ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_INSPECTION
                    )
                elif not application.materials:
                    flags.append(
                        ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_MATERIAL_ENTRY
                    )
                else:
                    flags.append(
                        ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION
                    )

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
                        a
                        for a in application.action_logs
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
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION
                    )

            elif st == ApplicationStatus.APPROVED:
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION
                    )
                elif not application.materials:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY
                    )
                else:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION
                    )

            elif st == ApplicationStatus.TOKEN_GENERATED:
                self._add_phase_flags(application, flags)

        return flags

    @staticmethod
    def _add_phase_flags(application: Application, flags: list[ApplicationFlags]):
        """Append phase-level and naka flags for TOKEN_GENERATED applications."""
        active_phases = [
            p for p in application.phases if p.status == ApplicationPhaseStatus.ACTIVE
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
            material_ids = [
                m.material_id for m in material_requirements if m.material_id is not None
            ]

            if material_ids:
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
                        custom_name=material.custom_name,
                        custom_unit=material.custom_unit,
                        quantity=material.material_qty,
                    )
                )

        await self.session.commit()

        # Re-fetch the application with all relationships loaded
        stmt = (
            select(Application)
            .where(Application.id == new_application_id)
            .options(*_APPLICATION_LOAD_OPTIONS)
        )
        result = await self.session.execute(stmt)
        new_application = result.scalar_one()

        return ApplicationResponse.model_validate(new_application)

    async def get_application(
        self, application_id: int
    ) -> Optional[ApplicationResponse]:
        """Get application."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(*_APPLICATION_LOAD_OPTIONS)
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()

        if not application:
            return None  # Handle outside

        response = ApplicationResponse.model_validate(application)

        # Attach token details if phases exist
        if application.phases:
            from backend.schemas.response.application import TokenResponse

            token_dicts = await self._build_token_list_dicts(application.phases)
            response.tokens = [TokenResponse.model_validate(t) for t in token_dicts]

        return response

    async def get_applications(
        self,
        flag: Optional[ApplicationFlags] = None,
        offset: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> list[ApplicationResponse]:
        """Get applications, optionally filtered by flag."""
        query = select(Application).options(*_APPLICATION_LOAD_OPTIONS)
        if user_id:
            query = query.where(Application.user_id == user_id)

        if flag is None:
            # No flag filter — return paginated results directly (citizen path)
            applications = list(
                await self.session.scalars(query.offset(offset).limit(limit))
            )
            responses = [
                ApplicationResponse.model_validate(app) for app in applications
            ]
            # Attach tokens for applications that have phases
            apps_with_phases = [app for app in applications if app.phases]
            if apps_with_phases:
                from backend.schemas.response.application import TokenResponse

                all_phases = [p for app in apps_with_phases for p in app.phases]
                token_dicts = await self._build_token_list_dicts(all_phases)
                # Group by application_id — get app_id from transport_code decode
                # Since list dicts don't have app_id, use phase objects to map
                # Build phase_id -> app_id mapping
                # Build transport_code -> app_id from phases
                from backend.core.transport_code import encode_transport_code

                tc_to_app: dict[str, int] = {}
                for app in apps_with_phases:
                    for p in app.phases:
                        tc = encode_transport_code(p.application_id, p.phase)
                        tc_to_app[tc] = p.application_id
                tokens_by_app: dict[int, list] = {}
                for td in token_dicts:
                    app_id = tc_to_app.get(td["transport_code"])
                    if app_id:
                        tokens_by_app.setdefault(app_id, []).append(td)
                for resp in responses:
                    if resp.id in tokens_by_app:
                        resp.tokens = [
                            TokenResponse.model_validate(t)
                            for t in tokens_by_app[resp.id]
                        ]
            return responses

        # Flag filter — load all matching apps, compute flags, then paginate in Python
        all_applications = list((await self.session.scalars(query)).all())
        matched_apps = [
            app for app in all_applications if flag in self.get_required_flags(app)
        ]
        paginated = matched_apps[offset : offset + limit]
        responses = [ApplicationResponse.model_validate(app) for app in paginated]
        # Attach tokens
        apps_with_phases = [app for app in paginated if app.phases]
        if apps_with_phases:
            from backend.schemas.response.application import TokenResponse
            from backend.core.transport_code import encode_transport_code as _enc

            all_phases = [p for app in apps_with_phases for p in app.phases]
            token_dicts = await self._build_token_list_dicts(all_phases)
            tc_to_app: dict[str, int] = {}
            for app in apps_with_phases:
                for p in app.phases:
                    tc_to_app[_enc(p.application_id, p.phase)] = p.application_id
            tokens_by_app: dict[int, list] = {}
            for td in token_dicts:
                app_id = tc_to_app.get(td["transport_code"])
                if app_id:
                    tokens_by_app.setdefault(app_id, []).append(td)
            for resp in responses:
                if resp.id in tokens_by_app:
                    resp.tokens = [
                        TokenResponse.model_validate(t) for t in tokens_by_app[resp.id]
                    ]
        return responses

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

    async def withdraw_application(
        self, application_id: int, user_id: int
    ) -> SuccessResponse:
        """Withdraw an application by the applicant."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if application.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="You can only withdraw your own applications"
            )

        # Allow withdrawal only if PENDING or SUBMITTED
        if application.status not in (
            ApplicationStatus.PENDING,
            ApplicationStatus.SUBMITTED,
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot withdraw application in '{application.status.value}' status. Only PENDING or SUBMITTED applications can be withdrawn.",
            )

        old_status = application.status
        print(
            f"DEBUG: old_status={old_status}, user_id={user_id}, application_id={application_id}"
        )
        application.status = ApplicationStatus.WITHDRAWN

        # Log the action
        self.session.add(
            ApplicationActionLog(
                application_id=application_id,
                action=WorkflowAction.WITHDRAW,
                from_status=old_status,
                to_status=ApplicationStatus.WITHDRAWN,
                performed_by=user_id,
                performed_at=datetime.now(),
                remarks="Withdrawn by applicant",
            )
        )

        await self.session.commit()
        return SuccessResponse(message="Application withdrawn successfully")

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
        material_ids = [
            m.material_id for m in material_requirements if m.material_id is not None
        ]

        if material_ids:
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
                    custom_name=material.custom_name,
                    custom_unit=material.custom_unit,
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
                selectinload(Application.comments).selectinload(ApplicationComment.commenter),
            )
        )
        result = await self.session.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # ── RENOVATION flow validation: check department comments ────────────────
        if (
            application.type == ApplicationType.RENOVATION
            and application.status == ApplicationStatus.FORWARDED
            and action == WorkflowAction.APPROVE
        ):
            # A department review is any comment from a required role, 
            # ideally of type DEPT_REVIEW but we accept GENERAL too for robustness.
            dept_review_roles = {
                c.commenter.role
                for c in application.comments
                if c.commenter.role in RENOVATION_DEPT_ROLES
            }
            
            missing_depts = RENOVATION_DEPT_ROLES - dept_review_roles
            if missing_depts:
                missing_names = [r.value for r in sorted(list(missing_depts))]
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot approve: missing department reviews from: {', '.join(missing_names)}",
                )

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
            # Require JEN inspection for NEW and RENOVATION flow
            if application.type in (ApplicationType.NEW, ApplicationType.RENOVATION) and not application.inspections:
                raise HTTPException(
                    status_code=400,
                    detail="JEN inspection must be completed before generating tokens",
                )
            application.num_stages = num_stages

            # Create phases
            for phase_num in range(1, num_stages + 1):
                phase_status = (
                    ApplicationPhaseStatus.ACTIVE
                    if phase_num == 1
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
                existing_pm_rows = existing_pm_result.scalars().all()
                
                # Composite key: (phase, material_id, custom_name)
                existing_keys = {
                    (pm.phase, pm.material_id, pm.custom_name)
                    for pm in existing_pm_rows
                }
                for pm in phase_materials:
                    key = (pm.phase, pm.material_id, pm.custom_name)
                    if key in existing_keys:
                        continue  # already created by JEN inspection
                    self.session.add(
                        ApplicationPhaseMaterial(
                            application_id=application_id,
                            phase=pm.phase,
                            material_id=pm.material_id,
                            custom_name=pm.custom_name,
                            custom_unit=pm.custom_unit,
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

    async def update_phase_materials(
        self, application_id: int, phase_materials: list
    ) -> SuccessResponse:
        """Update or add phase materials for an application.

        Used by JEN to add/update materials if they were forgotten during inspection.
        """
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Check for existing materials to avoid duplicates
        existing_stmt = select(ApplicationPhaseMaterial).where(
            ApplicationPhaseMaterial.application_id == application_id
        )
        existing_result = await self.session.execute(existing_stmt)
        existing_materials = {
            (pm.phase, pm.material_id, pm.custom_name): pm
            for pm in existing_result.scalars().all()
        }

        for pm_data in phase_materials:
            key = (pm_data.phase, pm_data.material_id, pm_data.custom_name)
            if key in existing_materials:
                # Update quantity
                existing_materials[key].quantity = pm_data.quantity
            else:
                # Insert new
                self.session.add(
                    ApplicationPhaseMaterial(
                        application_id=application_id,
                        phase=pm_data.phase,
                        material_id=pm_data.material_id,
                        custom_name=pm_data.custom_name,
                        custom_unit=pm_data.custom_unit,
                        quantity=pm_data.quantity,
                    )
                )

        await self.session.commit()
        return SuccessResponse(message="Phase materials updated successfully")

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
            # Upsert logic: check existing materials for this application
            existing_stmt = select(ApplicationPhaseMaterial).where(
                ApplicationPhaseMaterial.application_id == application_id
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_materials = {
                (pm.phase, pm.material_id, pm.custom_name): pm
                for pm in existing_result.scalars().all()
            }

            for pm in phase_materials:
                key = (pm.phase, pm.material_id, pm.custom_name)
                if key in existing_materials:
                    # Update quantity
                    existing_materials[key].quantity = pm.quantity
                else:
                    # Insert new
                    self.session.add(
                        ApplicationPhaseMaterial(
                            application_id=application_id,
                            phase=pm.phase,
                            material_id=pm.material_id,
                            custom_name=pm.custom_name,
                            custom_unit=pm.custom_unit,
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
        materials: list[dict],
        vehicle_number: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        remarks: Optional[str] = None,
        media: Optional[dict] = None,
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

        # Validate each material against phase allocation and quantity limits
        for mat in materials:
            mid = mat.get("material_id")
            cname = mat.get("custom_name")
            cunit = mat.get("custom_unit")
            qty = mat["quantity_brought"]

            pm_stmt = select(ApplicationPhaseMaterial).where(
                ApplicationPhaseMaterial.application_id == application_id,
                ApplicationPhaseMaterial.phase == phase,
                ApplicationPhaseMaterial.material_id == mid,
                ApplicationPhaseMaterial.custom_name == cname,
            )
            pm_result = await self.session.execute(pm_stmt)
            phase_mat = pm_result.scalar_one_or_none()
            if not phase_mat:
                label = f"Material {mid}" if mid else f"Custom Material '{cname}'"
                raise HTTPException(
                    status_code=400,
                    detail=f"{label} is not allocated for phase {phase}",
                )

            # Sum existing naka entries for this material in this phase
            used_stmt = (
                select(func.coalesce(func.sum(VehicleMaterial.quantity), 0))
                .select_from(VehicleEntry)
                .join(VehicleMaterial)
                .where(
                    VehicleEntry.application_id == application_id,
                    VehicleEntry.phase == phase,
                    VehicleMaterial.material_id == mid,
                    VehicleMaterial.custom_name == cname,
                )
            )
            used_result = await self.session.execute(used_stmt)
            already_brought = used_result.scalar() or 0

            if already_brought + qty > phase_mat.quantity:
                remaining = phase_mat.quantity - already_brought
                label = mid if mid else cname
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Quantity exceeds limit. Phase {phase} allows {phase_mat.quantity} "
                        f"of material {label}, already brought {already_brought}, "
                        f"remaining {remaining}. Requested: {qty}."
                    ),
                )

        # Create 1 vehicle entry
        vehicle_entry = VehicleEntry(
            application_id=application_id,
            phase=phase,
            entry_by=user_id,
            entry_at=datetime.now(),
            vehicle_number=vehicle_number or "UNKNOWN",
            vehicle_type=vehicle_type,
            latitude=latitude,
            longitude=longitude,
            remarks=remarks,
            media=media,
        )
        self.session.add(vehicle_entry)
        await self.session.flush()  # Get ID

        # Create N vehicle materials
        for mat in materials:
            vm = VehicleMaterial(
                vehicle_entry_id=vehicle_entry.id,
                material_id=mat.get("material_id"),
                custom_name=mat.get("custom_name"),
                custom_unit=mat.get("custom_unit"),
                quantity=float(mat["quantity_brought"]),
            )
            self.session.add(vm)

        await self.session.commit()
        return SuccessResponse(message="Naka entry recorded successfully")

    async def add_dumping_photo(
        self, application_id: int, entry_id: int, photo_path: str, user_id: int
    ) -> SuccessResponse:
        """Add a dumping photo to a vehicle entry with a limit of 5 photos."""
        # 1. Verify application ownership (CITIZEN must own it, or be SUPERADMIN)
        app_stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(selectinload(Application.documents))
        )
        app_result = await self.session.execute(app_stmt)
        application = app_result.scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Get user details for role check
        from backend.dbmodels.user import User

        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.role != UserRole.SUPERADMIN and application.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only upload photos for your own applications",
            )

        # 2. Verify VehicleEntry exists and belongs to this application
        entry_stmt = select(VehicleEntry).where(
            VehicleEntry.id == entry_id, VehicleEntry.application_id == application_id
        )
        entry_result = await self.session.execute(entry_stmt)
        entry = entry_result.scalar_one_or_none()

        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle entry {entry_id} not found for application {application_id}",
            )

        # 3. Check existing photo count (Limit 5)
        count_stmt = select(func.count(VehicleEntryDumpingPhoto.id)).where(
            VehicleEntryDumpingPhoto.vehicle_entry_id == entry_id
        )
        count_result = await self.session.execute(count_stmt)
        photo_count = count_result.scalar() or 0

        if photo_count >= 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum of 5 dumping photos allowed per vehicle entry",
            )

        # 4. Save the record
        self.session.add(
            VehicleEntryDumpingPhoto(
                vehicle_entry_id=entry_id,
                photo_path=photo_path,
                uploaded_at=datetime.now(),
            )
        )
        await self.session.commit()
        return SuccessResponse(message="Dumping photo uploaded successfully")

    async def get_naka_entries(self, application_id: int) -> list[VehicleEntry]:
        """Get all naka entries for an application."""
        stmt = (
            select(VehicleEntry)
            .where(VehicleEntry.application_id == application_id)
            .options(selectinload(VehicleEntry.materials))
            .order_by(VehicleEntry.entry_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_vehicle_entry_detail(self, entry_id: int) -> dict:
        """Get full details for a single vehicle entry."""
        from backend.dbmodels.user import User
        from backend.dbmodels.application import (
            ApprovedApplicationPhase,
            Material,
            ApplicationApproval,
            ApplicationPhaseMaterial,
            TOKEN_VALIDITY_DAYS,
        )
        from backend.services.storage import generate_signed_file_url

        # 1. Fetch main vehicle entry with its relations
        stmt = (
            select(VehicleEntry, Application, User, ApprovedApplicationPhase)
            .join(Application, VehicleEntry.application_id == Application.id)
            .join(User, VehicleEntry.entry_by == User.id)
            .outerjoin(
                ApprovedApplicationPhase,
                and_(
                    ApprovedApplicationPhase.application_id == VehicleEntry.application_id,
                    ApprovedApplicationPhase.phase == VehicleEntry.phase,
                ),
            )
            .where(VehicleEntry.id == entry_id)
            .options(
                selectinload(VehicleEntry.materials).selectinload(
                    VehicleMaterial.material
                ),
                selectinload(VehicleEntry.dumping_photos),
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Vehicle entry not found")

        ve, app, incharge, phase_rec = row

        # 2. Get "issued_by" (The Nodal officer who approved the most recent GENERATE_TOKENS action)
        issued_by = "Authority"
        issued_stmt = (
            select(User.name)
            .join(ApplicationApproval, User.id == ApplicationApproval.approved_by)
            .where(
                ApplicationApproval.application_id == ve.application_id,
                ApplicationApproval.action == WorkflowAction.GENERATE_TOKENS,
            )
            .order_by(ApplicationApproval.approved_at.desc())
            .limit(1)
        )
        issued_result = await self.session.execute(issued_stmt)
        issued_name = issued_result.scalar()
        if issued_name:
            issued_by = issued_name

        # 3. Compute derived fields
        year = (
            phase_rec.activated_at.year
            if (phase_rec and phase_rec.activated_at)
            else datetime.now().year
        )
        token_number = (
            f"TKN-{year}-{phase_rec.id:03d}" if phase_rec else f"APP-{app.id}-P{ve.phase}"
        )
        app_number = f"APP-{year}-{app.id:05d}"
        valid_till = None
        if phase_rec and phase_rec.activated_at:
            valid_till = phase_rec.activated_at + timedelta(days=TOKEN_VALIDITY_DAYS)

        # 4. Material entry details (flattened list for schema)
        material_details = []
        for vm in ve.materials:
            m_name = vm.material.name if vm.material else (vm.custom_name or "Unknown")
            material_details.append(
                {
                    "material_name": m_name,
                    "approved_quantity": 0,  # Not strictly requested to be precise here
                    "consumed_quantity": vm.quantity,
                    "remaining_quantity": 0,
                }
            )

        # 5. Media signed URLs
        vehicle_image = None
        entry_proof = []
        if ve.media:
            plate = ve.media.get("vehicle_plate")
            if plate:
                vehicle_image = generate_signed_file_url(plate)
            proofs = ve.media.get("entry_proofs", [])
            if proofs and isinstance(proofs, list):
                entry_proof = [generate_signed_file_url(p) for p in proofs if p]

        # 6. Dumping photos
        dumping_photos = []
        for dp in ve.dumping_photos:
            dumping_photos.append(
                {
                    "id": dp.id,
                    "photo_path": dp.photo_path,
                    "uploaded_at": dp.uploaded_at,
                    "access_url": generate_signed_file_url(dp.photo_path),
                }
            )

        return {
            "id": ve.id,
            "token_number": token_number,
            "issued_by": issued_by,
            "application_number": app_number,
            "token_validity": valid_till,
            "vehicle_number": ve.vehicle_number,
            "vehicle_type": ve.vehicle_type,
            "latitude": ve.latitude,
            "longitude": ve.longitude,
            "entry_at": ve.entry_at,
            "naka_incharge_name": incharge.name,
            "material_entry_details": material_details,
            "vehicle_image": vehicle_image,
            "entry_proof": entry_proof,
            "dumping_photos": dumping_photos,
            "application_user_id": app.user_id,  # For authorization check
        }

    async def get_all_vehicle_entries(self) -> list[dict]:
        """Get all vehicle entries for authority view, flattened by material."""
        from backend.dbmodels.user import User
        from backend.dbmodels.application import ApprovedApplicationPhase, Material

        # Query all VehicleMaterial rows with their entry, application, user, and material details
        # Also check for dumping photos existence
        stmt = (
            select(
                VehicleMaterial,
                VehicleEntry,
                Application,
                User,
                Material,
                ApprovedApplicationPhase,
                exists().where(VehicleEntryDumpingPhoto.vehicle_entry_id == VehicleEntry.id).label("has_dumping_photos")
            )
            .join(VehicleEntry, VehicleMaterial.vehicle_entry_id == VehicleEntry.id)
            .join(Application, VehicleEntry.application_id == Application.id)
            .join(User, VehicleEntry.entry_by == User.id)
            .outerjoin(Material, VehicleMaterial.material_id == Material.id)
            .outerjoin(ApprovedApplicationPhase, and_(
                ApprovedApplicationPhase.application_id == VehicleEntry.application_id,
                ApprovedApplicationPhase.phase == VehicleEntry.phase
            ))
            .order_by(VehicleEntry.entry_at.desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        flattened = []
        for vm, ve, app, incharge, m_catalog, phase_rec, has_photos in rows:
            # Use custom name if catalog material is not linked
            m_name = m_catalog.name if m_catalog else (vm.custom_name or "Unknown")
            
            # Generate token_number like the system does
            if phase_rec:
                year = (
                    phase_rec.activated_at.year
                    if phase_rec.activated_at
                    else datetime.now().year
                )
                token_number = f"TKN-{year}-{phase_rec.id:03d}"
            else:
                token_number = f"APP-{app.id}-P{ve.phase}"

            flattened.append({
                "id": vm.id,
                "vehicle_entry_id": ve.id,
                "application_id": ve.application_id,
                "token_number": token_number,
                "vehicle_number": ve.vehicle_number,
                "material_name": m_name,
                "material_quantity": vm.quantity,
                "entry_at": ve.entry_at,
                "naka_incharge_name": incharge.name,
                "has_dumping_photos": has_photos,
                "media": ve.media
            })
            
        return flattened

    async def get_phase_material_summary(self, application_id: int, phase: int) -> dict:
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

        # Get phase materials with material details (outer join for custom)
        pm_stmt = (
            select(ApplicationPhaseMaterial, Material)
            .outerjoin(Material, ApplicationPhaseMaterial.material_id == Material.id)
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
                VehicleMaterial.material_id,
                VehicleMaterial.custom_name,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label(
                    "total_brought"
                ),
            )
            .select_from(VehicleEntry)
            .join(VehicleMaterial)
            .where(
                VehicleEntry.application_id == application_id,
                VehicleEntry.phase == phase,
            )
            .group_by(VehicleMaterial.material_id, VehicleMaterial.custom_name)
        )
        brought_result = await self.session.execute(brought_stmt)
        # Map using (material_id, custom_name) as key
        brought_map = {
            (row.material_id, row.custom_name): row.total_brought
            for row in brought_result
        }

        materials = []
        for pm, mat in phase_materials:
            key = (pm.material_id, pm.custom_name)
            brought = brought_map.get(key, 0)
            
            m_id = pm.material_id
            m_name = mat.name if mat else pm.custom_name
            m_unit = mat.unit if mat else pm.custom_unit
            
            materials.append(
                {
                    "material_id": m_id,
                    "custom_name": pm.custom_name,
                    "material_name": m_name,
                    "unit": m_unit,
                    "allowed_qty": pm.quantity,
                    "brought_qty": brought,
                    "remaining_qty": pm.quantity - brought,
                }
            )

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

    # ── Token queries ─────────────────────────────────────────────────────
    async def _build_token_list_dicts(
        self, phases: list[ApprovedApplicationPhase]
    ) -> list[dict]:
        """Build lightweight token dicts for the listing table.

        Returns only the 5 columns shown in the token list screen:
        transport_code, token_number, application_number,
        remaining_quantity_pct, valid_till, status.
        """
        from backend.core.transport_code import encode_transport_code
        from backend.schemas.response.application import TOKEN_VALIDITY_DAYS

        if not phases:
            return []

        # Gather all application_ids
        app_ids = list({p.application_id for p in phases})

        # Bulk-fetch phase materials
        pm_stmt = select(ApplicationPhaseMaterial).where(
            ApplicationPhaseMaterial.application_id.in_(app_ids)
        )
        pm_result = await self.session.execute(pm_stmt)
        pm_rows = list(pm_result.scalars().all())

        # Index: (app_id, phase) -> total approved qty
        pm_map: dict[tuple[int, int], int] = {}
        for pm in pm_rows:
            key = (pm.application_id, pm.phase)
            pm_map[key] = pm_map.get(key, 0) + pm.quantity

        # Bulk-fetch consumed quantities from vehicle_entries
        brought_stmt = (
            select(
                VehicleEntry.application_id,
                VehicleEntry.phase,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label(
                    "total_brought"
                ),
            )
            .select_from(VehicleEntry)
            .join(VehicleMaterial)
            .where(VehicleEntry.application_id.in_(app_ids))
            .group_by(VehicleEntry.application_id, VehicleEntry.phase)
        )
        brought_result = await self.session.execute(brought_stmt)
        brought_map: dict[tuple[int, int], int] = {}
        for row in brought_result:
            brought_map[(row.application_id, row.phase)] = row.total_brought

        tokens: list[dict] = []
        for phase_rec in phases:
            key = (phase_rec.application_id, phase_rec.phase)
            year = (
                phase_rec.activated_at.year
                if phase_rec.activated_at
                else datetime.now().year
            )
            token_number = f"TKN-{year}-{phase_rec.id:03d}"
            application_number = f"APP-{year}-{phase_rec.application_id:05d}"

            valid_till = None
            if phase_rec.activated_at:
                valid_till = phase_rec.activated_at + timedelta(
                    days=TOKEN_VALIDITY_DAYS
                )

            total_approved = pm_map.get(key, 0)
            total_brought = brought_map.get(key, 0)
            remaining_pct = None
            if total_approved > 0:
                remaining_pct = round(
                    ((total_approved - total_brought) / total_approved) * 100, 1
                )

            transport_code = encode_transport_code(
                phase_rec.application_id, phase_rec.phase
            )

            tokens.append(
                {
                    "transport_code": transport_code,
                    "token_number": token_number,
                    "application_number": application_number,
                    "remaining_quantity_pct": remaining_pct,
                    "valid_till": valid_till,
                    "status": phase_rec.status,
                }
            )

        return tokens

    async def get_token_detail(self, application_id: int, phase: int) -> dict:
        """Build a full token-detail dict for a single phase.

        Includes application info, authority info, material summary,
        and vehicle (naka) entries — everything shown on the
        Token Detail screen.
        """
        from backend.core.transport_code import encode_transport_code
        from backend.schemas.response.application import TOKEN_VALIDITY_DAYS
        from backend.dbmodels.user import User
        from backend.dbmodels.master import Ward

        # ── Phase record ──────────────────────────────────────────────
        phase_stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase,
        )
        phase_result = await self.session.execute(phase_stmt)
        phase_rec = phase_result.scalar_one_or_none()
        if not phase_rec:
            raise HTTPException(status_code=404, detail="Token not found")

        # ── Application record ────────────────────────────────────────
        app_stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.approvals).selectinload(
                    ApplicationApproval.approver
                ),
            )
        )
        app_result = await self.session.execute(app_stmt)
        application = app_result.scalar_one_or_none()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # ── Formatted numbers ─────────────────────────────────────────
        year = (
            phase_rec.activated_at.year
            if phase_rec.activated_at
            else datetime.now().year
        )
        token_number = f"TKN-{year}-{phase_rec.id:03d}"
        application_number = f"APP-{year}-{application_id:05d}"

        valid_till = None
        if phase_rec.activated_at:
            valid_till = phase_rec.activated_at + timedelta(days=TOKEN_VALIDITY_DAYS)

        transport_code = encode_transport_code(application_id, phase)

        # ── Authority info ────────────────────────────────────────────
        # Find who generated the tokens (GENERATE_TOKENS action approval)
        issued_by = None
        issued_on = phase_rec.activated_at
        for approval in application.approvals:
            if approval.action == WorkflowAction.GENERATE_TOKENS:
                # Build label like "Nodal Officer (Ward 3)"
                approver_name = (
                    approval.approver.name if approval.approver else "Unknown"
                )
                ward_label = ""
                if application.ward_id:
                    ward_stmt = select(Ward).where(Ward.id == application.ward_id)
                    ward_res = await self.session.execute(ward_stmt)
                    ward = ward_res.scalar_one_or_none()
                    if ward:
                        ward_label = f" ({ward.name})"
                issued_by = f"{approver_name}{ward_label}"
                issued_on = approval.approved_at
                break

        token_generated_from = (
            f"Approved {application.type.value.capitalize()} Application"
        )

        # ── Phase materials with consumed quantities ──────────────────
        pm_stmt = (
            select(ApplicationPhaseMaterial, Material)
            .outerjoin(Material, ApplicationPhaseMaterial.material_id == Material.id)
            .where(
                ApplicationPhaseMaterial.application_id == application_id,
                ApplicationPhaseMaterial.phase == phase,
            )
        )
        pm_result = await self.session.execute(pm_stmt)
        phase_materials = pm_result.all()

        brought_stmt = (
            select(
                VehicleMaterial.material_id,
                VehicleMaterial.custom_name,
                func.coalesce(func.sum(VehicleMaterial.quantity), 0).label(
                    "total_brought"
                ),
            )
            .select_from(VehicleEntry)
            .join(VehicleMaterial)
            .where(
                VehicleEntry.application_id == application_id,
                VehicleEntry.phase == phase,
            )
            .group_by(VehicleMaterial.material_id, VehicleMaterial.custom_name)
        )
        brought_result = await self.session.execute(brought_stmt)
        # Map using (material_id, custom_name) as key
        brought_map = {
            (row.material_id, row.custom_name): row.total_brought
            for row in brought_result
        }

        materials_list = []
        total_approved = 0
        total_remaining = 0
        for pm, mat in phase_materials:
            key = (pm.material_id, pm.custom_name)
            brought = brought_map.get(key, 0)
            remaining = pm.quantity - brought
            total_approved += pm.quantity
            total_remaining += remaining

            m_id = pm.material_id
            m_name = mat.name if mat else pm.custom_name
            m_unit = mat.unit if mat else pm.custom_unit

            materials_list.append(
                {
                    "material_id": m_id,
                    "custom_name": pm.custom_name,
                    "custom_unit": pm.custom_unit,
                    "material_name": m_name,
                    "unit": m_unit,
                    "approved_quantity": pm.quantity,
                    "consumed_quantity": brought,
                    "remaining_quantity": remaining,
                }
            )

        remaining_pct = None
        if total_approved > 0:
            remaining_pct = round((total_remaining / total_approved) * 100, 1)

        # ── Vehicle entries (naka entries) ────────────────────────────
        from backend.services.storage import generate_signed_file_url

        naka_stmt = (
            select(VehicleEntry, Material, VehicleMaterial)
            .select_from(VehicleEntry)
            .join(VehicleMaterial)
            .outerjoin(Material, VehicleMaterial.material_id == Material.id)
            .where(
                VehicleEntry.application_id == application_id,
                VehicleEntry.phase == phase,
            )
            .order_by(VehicleEntry.entry_at.desc())
        )
        naka_result = await self.session.execute(naka_stmt)
        vehicle_entries = []
        for entry, mat, vmat in naka_result.all():
            access_urls = {}
            if entry.media:
                plate = entry.media.get("vehicle_plate")
                if plate:
                    access_urls["vehicle_plate"] = generate_signed_file_url(plate)

                proofs = entry.media.get("entry_proofs", [])
                if proofs:
                    access_urls["entry_proofs"] = [
                        generate_signed_file_url(p) for p in proofs if p
                    ]

            m_name = mat.name if mat else vmat.custom_name
            m_unit = mat.unit if mat else vmat.custom_unit

            vehicle_entries.append(
                {
                    "id": entry.id,
                    "vehicle_number": entry.vehicle_number,
                    "material_id": vmat.material_id,
                    "custom_name": vmat.custom_name,
                    "material_name": m_name,
                    "material_unit": m_unit,
                    "quantity_entered": vmat.quantity,
                    "entry_at": entry.entry_at,
                    "remarks": entry.remarks,
                    "media": entry.media,
                    "access_urls": access_urls,
                }
            )

        return {
            "transport_code": transport_code,
            "token_number": token_number,
            "status": phase_rec.status,
            "valid_from": phase_rec.activated_at,
            "valid_till": valid_till,
            "application_id": application_id,
            "application_number": application_number,
            "applicant_name": application.applicant_name,
            "property_address": application.property_address,
            "property_usage": application.property_usage,
            "application_type": application.type,
            "authority": {
                "issued_by": issued_by,
                "issued_on": issued_on,
                "token_generated_from": token_generated_from,
            },
            "materials": materials_list,
            "remaining_quantity_pct": remaining_pct,
            "vehicle_entries": vehicle_entries,
        }

    async def get_tokens(
        self,
        user_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[dict]:
        """Get all tokens (phases) with optional user_id filtering.

        Supports filtering by phase status and searching by token/application number.
        """
        # Fetch phases
        stmt = (
            select(ApprovedApplicationPhase)
            .join(
                Application, ApprovedApplicationPhase.application_id == Application.id
            )
            .order_by(ApprovedApplicationPhase.id.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Application.user_id == user_id)

        if status_filter:
            try:
                phase_status = ApplicationPhaseStatus(status_filter)
                stmt = stmt.where(ApprovedApplicationPhase.status == phase_status)
            except ValueError:
                pass  # ignore invalid status filter

        # Load all (Search happens in memory due to complex generated fields in build_token_list_dicts)
        result = await self.session.execute(stmt)
        phases = list(result.scalars().all())

        # Build lightweight token dicts for listing
        tokens = await self._build_token_list_dicts(phases)

        # Search filter (on token_number or application_number)
        if search:
            search_lower = search.lower()
            tokens = [
                t
                for t in tokens
                if search_lower in t["token_number"].lower()
                or search_lower in t["application_number"].lower()
            ]

        # Paginate
        return tokens[offset : offset + limit]

    async def get_application_tokens(self, application_id: int) -> list[dict]:
        """Get all tokens (phases) for a single application with material summaries."""
        stmt = (
            select(ApprovedApplicationPhase)
            .where(ApprovedApplicationPhase.application_id == application_id)
            .order_by(ApprovedApplicationPhase.phase)
        )
        result = await self.session.execute(stmt)
        phases = list(result.scalars().all())
        return await self._build_token_list_dicts(phases)


async def get_application_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationDAO:
    """..."""
    return ApplicationDAO(session)
