"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import List, Optional
from sqlalchemy import insert, select, update, delete, exists, and_, or_, String
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta

from backend.database import get_db
from backend.services.sms import sms_service
from backend.dbmodels.application import (
    ApplicationComment,
    ApplicationActionLog,
    InspectionReport,
    VehicleEntry,
    VehicleMaterial,
    VehicleEntryDumpingPhoto,
)
from backend.dao.base import BaseDAO
from backend.meta import ApplicationStatus, CommentType, WorkflowAction, ObjectionStatus, UserRole, ApplicationFlags, ApplicationType, ApplicationPhaseStatus, PropertyUsageType
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
    ApplicationObjection,
)
from backend.meta import (
    ApplicationDocumentType,
    ApplicationFlags,
    UserRole,
    ApplicationType,
    ApplicationPhaseStatus,
    PropertyUsageType,
    JurisdictionZone,
)
from backend.core.workflow import validate_transition, RENOVATION_DEPT_ROLES


# ── Eager-loading options reused across queries ──────────────────────────
_APPLICATION_LOAD_OPTIONS = [
    joinedload(Application.ward_rel),
    joinedload(Application.department_rel),
    selectinload(Application.documents),
    selectinload(Application.materials).selectinload(ApplicationMaterial.material),
    selectinload(Application.comments).selectinload(ApplicationComment.commenter),
    selectinload(Application.phases),
    selectinload(Application.phase_materials).selectinload(ApplicationPhaseMaterial.material),
    selectinload(Application.inspections).selectinload(InspectionReport.inspector),
    selectinload(Application.vehicle_entries).selectinload(VehicleEntry.materials).selectinload(VehicleMaterial.material),
    selectinload(Application.action_logs).selectinload(ApplicationActionLog.performer),
    selectinload(Application.objections).selectinload(ApplicationObjection.objected_by_user),
    selectinload(Application.objections).selectinload(ApplicationObjection.resolved_by_user),
]


def _get_app_last_updated_at(app: Application) -> datetime:
    if hasattr(app, "action_logs") and app.action_logs:
        log_ts = [log.performed_at for log in app.action_logs if log.performed_at]
        if log_ts:
            return max(log_ts)
    return app.created_at


class ApplicationDAO(BaseDAO):
    """Application DAO."""

    # ── Flag computation ──────────────────────────────────────────────────
    def get_required_flags(self, application: Application, user_role: Optional[UserRole] = None) -> list[ApplicationFlags]:
        """Compute which dashboard-flags an application should appear under."""
        flags: list[ApplicationFlags] = []
        st = application.status
        tp = application.type

        # ── OBJECTED (both flows) ─────────────────────────────────────
        if st == ApplicationStatus.OBJECTED:
            if not application.objection_to_role or application.objection_to_role == UserRole.CITIZEN:
                flags.append(ApplicationFlags.OBJECTED_CITIZEN_ACTION)

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
                elif not application.phase_materials:
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
                # Inspection report satisfies the JEN review requirement
                if len(application.inspections) > 0:
                    dept_review_roles.add(UserRole.JEN)

                missing_depts = RENOVATION_DEPT_ROLES - dept_review_roles
                
                # Check for inspection requirement in FORWARDED state
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION
                    )
                elif not application.phase_materials:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY
                    )

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
                    # All depts commented (and JEN inspected/commented) → Commissioner can act
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION
                    )

            elif st == ApplicationStatus.APPROVED:
                has_inspection = len(application.inspections) > 0
                if not has_inspection:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_FIELD_INSPECTION
                    )
                elif not application.phase_materials:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY
                    )
                else:
                    flags.append(
                        ApplicationFlags.RENOVATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION
                    )

            elif st == ApplicationStatus.TOKEN_GENERATED:
                self._add_phase_flags(application, flags)

        # ── ALL_DEPT flag ──────────────────────────────────────────────
        # NEW application is visible forever under ALL_DEPT if it has ever been APPROVED or TOKEN_GENERATED.
        # RENOVATION application is visible forever under ALL_DEPT if it has ever been FORWARDED, APPROVED, or TOKEN_GENERATED.
        is_new_approved = (
            st in (ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED) or
            any(log.to_status in (ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED) for log in getattr(application, "action_logs", []))
        )
        is_renovation_forwarded = (
            st in (ApplicationStatus.FORWARDED, ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED) or
            any(log.to_status in (ApplicationStatus.FORWARDED, ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED) for log in getattr(application, "action_logs", []))
        )

        if st not in (ApplicationStatus.PENDING, ApplicationStatus.WITHDRAWN):
            if (tp == ApplicationType.NEW and is_new_approved) or \
               (tp == ApplicationType.RENOVATION and is_renovation_forwarded):
                flags.append(ApplicationFlags.ALL_DEPT)

        # ── PENDING_WITH_ME flag ─────────────────────────────────────────
        if user_role:
            is_pending_with_me = False
            if st == ApplicationStatus.OBJECTED:
                if application.objection_to_role == user_role:
                    is_pending_with_me = True
                elif not application.objection_to_role and user_role == UserRole.CITIZEN:
                    is_pending_with_me = True
            else:
                if user_role == UserRole.NODAL_OFFICER:
                    # 1. NEW in SUBMITTED (needing approval)
                    # 2. NEW in APPROVED (has inspection + phase materials, needs token generation)
                    # 3. RENOVATION in APPROVED (has inspection + phase materials, needs token generation)
                    if tp == ApplicationType.NEW and st == ApplicationStatus.SUBMITTED:
                        is_pending_with_me = True
                    elif st == ApplicationStatus.APPROVED and len(application.inspections) > 0 and application.phase_materials:
                        is_pending_with_me = True
                
                elif user_role == UserRole.COMMISSIONER:
                    # 1. RENOVATION in SUBMITTED (needing forwarding)
                    # 2. RENOVATION in FORWARDED where all depts commented and JEN inspected (needing approval)
                    if tp == ApplicationType.RENOVATION:
                        if st == ApplicationStatus.SUBMITTED:
                            is_pending_with_me = True
                        elif st == ApplicationStatus.FORWARDED:
                            dept_review_roles = {
                                c.commenter.role
                                for c in application.comments
                                if c.comment_type == CommentType.DEPT_REVIEW
                            }
                            if len(application.inspections) > 0:
                                dept_review_roles.add(UserRole.JEN)
                            
                            missing_depts = RENOVATION_DEPT_ROLES - dept_review_roles
                            if not missing_depts:
                                is_pending_with_me = True
                
                elif user_role == UserRole.JEN:
                    # 1. NEW in APPROVED and (no inspection or no phase materials)
                    # 2. RENOVATION in FORWARDED and (no inspection or no phase materials)
                    if tp == ApplicationType.NEW and st == ApplicationStatus.APPROVED:
                        if len(application.inspections) == 0 or not application.phase_materials:
                            is_pending_with_me = True
                    elif tp == ApplicationType.RENOVATION and st == ApplicationStatus.FORWARDED:
                        if len(application.inspections) == 0 or not application.phase_materials:
                            is_pending_with_me = True
                
                elif user_role in (UserRole.DEPT_ATP, UserRole.DEPT_LAND, UserRole.DEPT_LEGAL):
                    # RENOVATION in FORWARDED and has NOT commented yet with DEPT_REVIEW
                    if tp == ApplicationType.RENOVATION and st == ApplicationStatus.FORWARDED:
                        has_commented = any(
                            c.commenter.role == user_role and c.comment_type == CommentType.DEPT_REVIEW
                            for c in application.comments
                        )
                        if not has_commented:
                            is_pending_with_me = True

            if is_pending_with_me:
                flags.append(ApplicationFlags.PENDING_WITH_ME)

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
    async def _validate_materials_active(self, material_ids: list[int]):
        """Validate that all material IDs exist and are active."""
        if not material_ids:
            return

        stmt = select(Material.id, Material.name, Material.status).where(
            Material.id.in_(material_ids)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        existing_ids = {r[0] for r in rows}
        invalid_ids = [mid for mid in material_ids if mid not in existing_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid material IDs: {invalid_ids}. These materials do not exist.",
            )

        inactive_materials = [r[1] for r in rows if not r[2]]
        if inactive_materials:
            raise HTTPException(
                status_code=400,
                detail=f"The following materials are deactivated and cannot be used for new entries: {', '.join(inactive_materials)}",
            )

    async def create_application(
        self, application: ApplicationCreate, user_id: int, mobile: str
    ) -> ApplicationResponse:
        """Create application."""
        # Extract material requirements before creating application
        material_requirements = application.material_requirements
        application_data = application.model_dump(exclude={"material_requirements"})
        application_data["user_id"] = user_id
        application_data["mobile"] = mobile

        # Validate that all material IDs exist and are active
        if material_requirements:
            material_ids = [
                m.material_id for m in material_requirements if m.material_id is not None
            ]
            await self._validate_materials_active(material_ids)

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
        search: Optional[str] = None,
        ward_id: Optional[int] = None,
        ward_ids: Optional[list[int]] = None,
        property_usage: Optional[PropertyUsageType] = None,
        jurisdiction_zone: Optional[JurisdictionZone] = None,
        user_role: Optional[UserRole] = None,
        primary_tab: Optional[str] = None,  # "PENDING", "COMPLETED", "SUBMISSION_DAYS"
        authority_role: Optional[UserRole] = None,
        action_name: Optional[str] = None,
        pending_days: Optional[int] = None,
        submitted_days: Optional[int] = None,
        app_type: Optional[ApplicationType] = None,
        app_status: Optional[ApplicationStatus] = None,
    ) -> tuple[list[ApplicationResponse], int]:
        """Get applications with primary workflow filters, secondary filters, pagination, and total count."""
        query = select(Application).options(*_APPLICATION_LOAD_OPTIONS).order_by(Application.created_at.desc())
        
        # ── Global & Secondary filters ───────────────────────────────────
        if user_id:
            query = query.where(Application.user_id == user_id)
        if ward_ids and len(ward_ids) > 0:
            query = query.where(Application.ward_id.in_(ward_ids))
        elif ward_id:
            query = query.where(Application.ward_id == ward_id)
        if property_usage:
            query = query.where(Application.property_usage == property_usage)
        if jurisdiction_zone:
            query = query.where(Application.jurisdiction_zone == jurisdiction_zone)
        if app_type:
            query = query.where(Application.type == app_type)
        if app_status:
            query = query.where(Application.status == app_status)
            
        # ── Search logic ──────────────────────────────────────────────────
        if search:
            search_filters = []
            search_filters.append(Application.applicant_name.ilike(f"%{search}%"))
            search_filters.append(Application.mobile.ilike(f"%{search}%"))
            if search.isdigit():
                search_filters.append(Application.id == int(search))
            elif search.upper().startswith("APP-"):
                try:
                    parts = search.split("-")
                    app_id = int(parts[-1])
                    search_filters.append(Application.id == app_id)
                except (ValueError, IndexError):
                    pass
            query = query.where(or_(*search_filters))

        # ── Primary Tab C: SUBMISSION_DAYS ────────────────────────────────
        if primary_tab == "SUBMISSION_DAYS" and submitted_days is not None:
            cutoff = datetime.now() - timedelta(days=submitted_days)
            query = query.where(
                and_(
                    Application.created_at <= cutoff,
                    Application.status != ApplicationStatus.TOKEN_GENERATED,
                    Application.status != ApplicationStatus.WITHDRAWN,
                    Application.status != ApplicationStatus.REJECTED,
                )
            )

        # Execute base query to get all candidate applications
        all_applications = list((await self.session.scalars(query)).unique().all())

        # ── Primary Tab Filtering ─────────────────────────────────────────
        matched_apps = []
        now = datetime.now()

        for app in all_applications:
            # Legacy flag filter if present
            if flag and flag != ApplicationFlags.ALL and flag not in self.get_required_flags(app, user_role):
                continue

            # Primary Tab A: PENDING with Authority
            if primary_tab == "PENDING" and authority_role:
                is_pending_for_role = False
                pending_start_ts: Optional[datetime] = None

                # Rule 6.2/Workflow check for role
                if authority_role == UserRole.NODAL_OFFICER:
                    if app.type == ApplicationType.NEW and app.status == ApplicationStatus.SUBMITTED:
                        is_pending_for_role = True
                        pending_start_ts = app.created_at
                    elif app.status in (ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED):
                        # Pending token generation
                        is_pending_for_role = True
                        insp_ts = [i.inspected_at for i in app.inspections if i.inspected_at]
                        pending_start_ts = max(insp_ts) if insp_ts else _get_app_last_updated_at(app)
                    elif app.status == ApplicationStatus.OBJECTED:
                        pending_objs = [o for o in app.objections if o.status == ObjectionStatus.PENDING and o.objected_to_role in (UserRole.CITIZEN, UserRole.JEN)]
                        if pending_objs:
                            is_pending_for_role = True
                            pending_start_ts = min([o.created_at for o in pending_objs if o.created_at])

                elif authority_role == UserRole.COMMISSIONER:
                    if app.type == ApplicationType.RENOVATION:
                        if app.status == ApplicationStatus.SUBMITTED:
                            is_pending_for_role = True
                            pending_start_ts = app.created_at
                        elif app.status == ApplicationStatus.FORWARDED:
                            is_pending_for_role = True
                            pending_start_ts = _get_app_last_updated_at(app)
                        elif app.status == ApplicationStatus.OBJECTED:
                            is_pending_for_role = True
                            pending_start_ts = _get_app_last_updated_at(app)

                elif authority_role == UserRole.JEN:
                    if app.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.FORWARDED) and (not app.inspections or not app.phase_materials):
                        is_pending_for_role = True
                        pending_start_ts = _get_app_last_updated_at(app)
                    elif app.status == ApplicationStatus.OBJECTED:
                        pending_objs = [o for o in app.objections if o.status == ObjectionStatus.PENDING and o.objected_to_role == UserRole.JEN]
                        if pending_objs:
                            is_pending_for_role = True
                            pending_start_ts = min([o.created_at for o in pending_objs if o.created_at])

                elif authority_role in (UserRole.DEPT_LAND, UserRole.DEPT_LEGAL, UserRole.DEPT_ATP):
                    if app.type == ApplicationType.RENOVATION and app.status == ApplicationStatus.FORWARDED:
                        commented_roles = {c.commenter.role for c in app.comments if c.commenter and c.commenter.role}
                        if authority_role not in commented_roles:
                            is_pending_for_role = True
                            pending_start_ts = _get_app_last_updated_at(app)
                    elif app.status == ApplicationStatus.OBJECTED:
                        pending_objs = [o for o in app.objections if o.status == ObjectionStatus.PENDING and o.objected_to_role == authority_role]
                        if pending_objs:
                            is_pending_for_role = True
                            pending_start_ts = min([o.created_at for o in pending_objs if o.created_at])

                if not is_pending_for_role:
                    continue

                # Filter by pending_days if provided
                if pending_days is not None and pending_days > 0 and pending_start_ts:
                    days_elapsed = (now - pending_start_ts).days
                    if days_elapsed < pending_days:
                        continue

            # Primary Tab B: COMPLETED by Authority
            elif primary_tab == "COMPLETED" and authority_role:
                is_completed_by_role = False
                if authority_role in (UserRole.NODAL_OFFICER, UserRole.COMMISSIONER):
                    # Check action logs / approvals
                    if hasattr(app, "action_logs") and app.action_logs:
                        if any(log.performer and log.performer.role == authority_role for log in app.action_logs if hasattr(log, "performer")):
                            is_completed_by_role = True
                elif authority_role == UserRole.JEN:
                    if app.inspections and len(app.inspections) > 0 and app.phase_materials and len(app.phase_materials) > 0:
                        is_completed_by_role = True
                elif authority_role in (UserRole.DEPT_LAND, UserRole.DEPT_LEGAL, UserRole.DEPT_ATP):
                    if app.comments:
                        if any(c.commenter and c.commenter.role == authority_role for c in app.comments if hasattr(c, "commenter")):
                            is_completed_by_role = True

                if not is_completed_by_role:
                    continue

            matched_apps.append(app)

        total_count = len(matched_apps)
        paginated_apps = matched_apps[offset : offset + limit]

        responses = [ApplicationResponse.model_validate(app) for app in paginated_apps]

        # Attach tokens for applications that have phases
        apps_with_phases = [app for app in paginated_apps if app.phases]
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

        return responses, total_count

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

    async def get_organization_suggestions(self, property_usage: PropertyUsageType) -> list[str]:
        """Fetch unique list of organization names for property usage type (COMMERCIAL / GOVERNMENT)."""
        stmt = (
            select(Application.organization_name)
            .where(Application.property_usage == property_usage)
            .where(Application.organization_name.isnot(None))
            .distinct()
            .order_by(Application.organization_name.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
            await self._validate_materials_active(material_ids)

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

        # Trigger SMS notification
        try:
            year = application.created_at.year if application.created_at else datetime.now().year
            app_number = f"APP-{year}-{application_id:05d}"
            await sms_service.send_application_sms(
                mobile=application.mobile,
                app_id=app_number,
                status="successfully submitted"
            )
        except Exception as e:
            print(f"Error sending application submission SMS: {e}")

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
        phase: Optional[int] = None,
        phase_materials: Optional[list] = None,
        objection_to_role: Optional[UserRole] = None,
        objection_to_roles: Optional[list[UserRole]] = None,
        role_remarks: Optional[dict] = None,
        reverted_document_url: Optional[str] = None,
        clear_objection_role: Optional[UserRole] = None,
    ) -> SuccessResponse:
        """
        Execute a workflow action on an application.
        Uses the state machine to validate the transition and update status.
        For GENERATE_TOKENS also creates phases + phase materials.
        """
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(*_APPLICATION_LOAD_OPTIONS)
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
            if len(application.inspections) > 0:
                dept_review_roles.add(UserRole.JEN)
            
            missing_depts = RENOVATION_DEPT_ROLES - dept_review_roles
            if missing_depts:
                missing_names = [r.value for r in sorted(list(missing_depts))]
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot approve: missing department reviews from: {', '.join(missing_names)}",
                )

            # Require JEN inspection for RENOVATION flow before approval
            if len(application.inspections) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot approve: JEN field inspection is not completed.",
                )

            # Require phase materials for RENOVATION flow before approval
            if len(application.phase_materials) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot approve: phase materials have not been entered.",
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
            if not phase or phase < 1:
                raise HTTPException(
                    status_code=400,
                    detail="phase is required for GENERATE_TOKENS and must be >= 1",
                )
            # Require JEN inspection for NEW and RENOVATION flow
            if application.type in (ApplicationType.NEW, ApplicationType.RENOVATION) and not application.inspections:
                raise HTTPException(
                    status_code=400,
                    detail="JEN inspection must be completed before generating tokens",
                )

            if not phase:
                raise HTTPException(
                    status_code=400,
                    detail="phase is required for GENERATE_TOKENS action",
                )

            # Check duplicates
            existing_phase = next((p for p in application.phases if p.phase == phase), None)
            if existing_phase:
                raise HTTPException(
                    status_code=400,
                    detail=f"Phase {phase} has already been generated.",
                )

            # Validate sequential generation
            if phase > 1:
                prev_phase = next((p for p in application.phases if p.phase == phase - 1), None)
                if not prev_phase:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot generate Phase {phase}: Phase {phase - 1} has not been generated yet.",
                    )
                if prev_phase.status not in (ApplicationPhaseStatus.COMPLETED, ApplicationPhaseStatus.TERMINATED):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot generate Phase {phase}: Phase {phase - 1} is '{prev_phase.status.value}', must be COMPLETED or TERMINATED.",
                    )

            if not application.num_stages or phase > application.num_stages:
                application.num_stages = phase

            # Create the requested phase directly with ACTIVE status
            self.session.add(
                ApprovedApplicationPhase(
                    application_id=application_id,
                    phase=phase,
                    name=f"Phase {phase}",
                    status=ApplicationPhaseStatus.ACTIVE,
                    activated_at=datetime.now(),
                )
            )

            # Create phase materials if provided for this phase
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
                    if pm.phase != phase:
                        continue
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

        # Handle objection redirection validation and assignment
        if action == WorkflowAction.OBJECT:
            # Save the pre-objection status if not already saved
            if not application.objected_from_status:
                application.objected_from_status = application.status

            # Consolidate target roles
            target_roles: list[UserRole] = []
            if objection_to_roles:
                target_roles = [r for r in objection_to_roles if r]
            elif objection_to_role:
                target_roles = [objection_to_role]

            if not target_roles:
                raise HTTPException(
                    status_code=400,
                    detail="objection_to_roles is required when raising an objection",
                )

            # Rule 6.1: In New Construction at SUBMITTED state (before inspection), Nodal Officer can ONLY object to CITIZEN
            if application.type == ApplicationType.NEW and application.status == ApplicationStatus.SUBMITTED:
                for r in target_roles:
                    if r != UserRole.CITIZEN:
                        raise HTTPException(
                            status_code=400,
                            detail="For new construction in submitted state, objection can only be sent to CITIZEN before inspection.",
                        )

            # Rule 6.8 & 6.9: In Renovation workflow, Commissioner can only object to lower authorities who have commented or inspected
            if application.type == ApplicationType.RENOVATION and user_role == UserRole.COMMISSIONER:
                participated_roles = {
                    c.commenter.role for c in application.comments if c.commenter and c.commenter.role
                }
                for insp in application.inspections:
                    if hasattr(insp, "inspector") and insp.inspector and hasattr(insp.inspector, "role"):
                        participated_roles.add(insp.inspector.role)
                
                for r in target_roles:
                    if r != UserRole.CITIZEN and r not in participated_roles:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot object to {r.value} because they have not commented or inspected yet.",
                        )

            application.objection_to_role = target_roles[0]

            # Process each target role in application_objections table
            for role in target_roles:
                r_remark = (role_remarks or {}).get(role.value) or (role_remarks or {}).get(str(role)) or remarks
                
                # Check for existing pending objection for this role
                existing_obj = next(
                    (o for o in application.objections if o.objected_to_role == role and o.status == ObjectionStatus.PENDING),
                    None
                )
                if existing_obj:
                    existing_obj.remarks = r_remark
                    if role == UserRole.CITIZEN and reverted_document_url:
                        existing_obj.reverted_document_url = reverted_document_url
                else:
                    self.session.add(
                        ApplicationObjection(
                            application_id=application_id,
                            objected_by_id=user_id,
                            objected_by_role=user_role,
                            objected_to_role=role,
                            remarks=r_remark,
                            reverted_document_url=reverted_document_url if role == UserRole.CITIZEN else None,
                            status=ObjectionStatus.PENDING,
                            created_at=datetime.now(),
                        )
                    )

            # Rule 6.2 & 6.3: Log comment with proper privacy type
            if remarks:
                if UserRole.CITIZEN in target_roles:
                    c_type = CommentType.OBJECTION_COMMENT
                else:
                    c_type = CommentType.DEPT_REVIEW  # Hidden from CITIZEN

                self.session.add(
                    ApplicationComment(
                        application_id=application_id,
                        comment=f"Objection [{', '.join([r.value for r in target_roles])}]: {remarks}",
                        comment_by=user_id,
                        comment_type=c_type,
                        media_paths=[reverted_document_url] if (UserRole.CITIZEN in target_roles and reverted_document_url) else None,
                        created_at=datetime.now(),
                    )
                )

        elif action == WorkflowAction.CLEAR_OBJECTION:
            # Rule 6.13: Only Nodal Officer, Commissioner, and Superadmin can clear objections
            if user_role not in (UserRole.NODAL_OFFICER, UserRole.COMMISSIONER, UserRole.SUPERADMIN):
                raise HTTPException(
                    status_code=403,
                    detail="Only Nodal Officer, Commissioner, or Superadmin can verify and clear objections.",
                )

            # Mark matching pending objections as RESOLVED
            pending_objs = [o for o in application.objections if o.status == ObjectionStatus.PENDING]
            if clear_objection_role:
                pending_objs = [o for o in pending_objs if o.objected_to_role == clear_objection_role]

            for obj in pending_objs:
                obj.status = ObjectionStatus.RESOLVED
                obj.resolved_at = datetime.now()
                obj.resolved_by_id = user_id
                obj.resolved_by_role = user_role
                obj.resolution_remarks = remarks or f"Objection cleared by {user_role.value}"

            # Check if any pending objections remain
            remaining_pending = [o for o in application.objections if o.status == ObjectionStatus.PENDING and o not in pending_objs]
            if not remaining_pending:
                if application.objected_from_status:
                    next_status = application.objected_from_status
                else:
                    next_status = ApplicationStatus.FORWARDED if application.type == ApplicationType.RENOVATION else ApplicationStatus.SUBMITTED
                
                application.objected_from_status = None
                application.objection_to_role = None
            else:
                next_status = ApplicationStatus.OBJECTED
                application.objection_to_role = remaining_pending[0].objected_to_role
        else:
            # Clear target role for other actions
            application.objection_to_role = None

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

        # Trigger SMS notification
        try:
            year = application.created_at.year if application.created_at else datetime.now().year
            app_number = f"APP-{year}-{application_id:05d}"
            
            if action == WorkflowAction.APPROVE and next_status == ApplicationStatus.APPROVED:
                await sms_service.send_application_sms(application.mobile, app_number, "approved")
            elif action == WorkflowAction.REJECT:
                await sms_service.send_application_sms(application.mobile, app_number, "rejected")
            elif action == WorkflowAction.OBJECT:
                await sms_service.send_application_sms(application.mobile, app_number, "objected")
            elif action == WorkflowAction.GENERATE_TOKENS:
                # Notify that tokens are generated for the application
                await sms_service.send_token_sms(application.mobile, app_number, "generated")
        except Exception as e:
            print(f"Error sending workflow SMS: {e}")

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

        # Get all unique phases in the incoming payload
        phases_to_update = {pm_data.phase for pm_data in phase_materials}

        if phases_to_update:
            # Check if any of these phases have already been generated/approved
            generated_phases_stmt = select(ApprovedApplicationPhase.phase).where(
                ApprovedApplicationPhase.application_id == application_id,
                ApprovedApplicationPhase.phase.in_(list(phases_to_update))
            )
            generated_phases_result = await self.session.execute(generated_phases_stmt)
            generated_phases = generated_phases_result.scalars().all()
            if generated_phases:
                phases_str = ", ".join(map(str, sorted(generated_phases)))
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot update materials for Phase(s) {phases_str} because token(s) have already been generated.",
                )

            # Delete existing phase materials for these phases
            delete_stmt = delete(ApplicationPhaseMaterial).where(
                ApplicationPhaseMaterial.application_id == application_id,
                ApplicationPhaseMaterial.phase.in_(list(phases_to_update))
            )
            await self.session.execute(delete_stmt)

        # Insert new/edited phase materials
        for pm_data in phase_materials:
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
        if application.type == ApplicationType.RENOVATION:
            if application.status != ApplicationStatus.FORWARDED:
                raise HTTPException(
                    status_code=400,
                    detail="Inspection is only allowed on FORWARDED applications for renovation",
                )
        else:
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

    async def update_inspection_report(
        self,
        application_id: int,
        user_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        remarks: Optional[str] = None,
        media_paths: Optional[list] = None,
        recommended_phases: Optional[int] = None,
    ) -> SuccessResponse:
        """Update an existing site inspection report by JEN."""
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        if application.type == ApplicationType.RENOVATION:
            if application.status not in (ApplicationStatus.FORWARDED, ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED):
                raise HTTPException(
                    status_code=400,
                    detail="Inspection update is only allowed on FORWARDED, APPROVED, or TOKEN_GENERATED applications for renovation",
                )
        else:
            if application.status not in (ApplicationStatus.APPROVED, ApplicationStatus.TOKEN_GENERATED):
                raise HTTPException(
                    status_code=400,
                    detail="Inspection update is only allowed on APPROVED or TOKEN_GENERATED applications",
                )

        stmt = (
            select(InspectionReport)
            .where(InspectionReport.application_id == application_id)
            .order_by(InspectionReport.id.desc())
        )
        result = await self.session.execute(stmt)
        inspection = result.scalars().first()
        if not inspection:
            raise HTTPException(status_code=404, detail="Inspection report not found")

        if latitude is not None:
            inspection.latitude = latitude
        if longitude is not None:
            inspection.longitude = longitude
        if remarks is not None:
            inspection.remarks = remarks
        if media_paths is not None:
            inspection.media_paths = media_paths
        if recommended_phases is not None:
            inspection.recommended_phases = recommended_phases

        inspection.inspected_by = user_id
        inspection.inspected_at = datetime.now()

        await self.session.commit()
        return SuccessResponse(message="Inspection report updated successfully")

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

        await self.session.flush()

        # Check if all allocated materials for the current phase are fully completed (remaining is zero or less)
        pm_stmt = select(ApplicationPhaseMaterial).where(
            ApplicationPhaseMaterial.application_id == application_id,
            ApplicationPhaseMaterial.phase == phase,
        )
        pm_result = await self.session.execute(pm_stmt)
        allocated_materials = pm_result.scalars().all()

        phase_fully_utilized = True
        for pm in allocated_materials:
            used_stmt = (
                select(func.coalesce(func.sum(VehicleMaterial.quantity), 0))
                .select_from(VehicleEntry)
                .join(VehicleMaterial)
                .where(
                    VehicleEntry.application_id == application_id,
                    VehicleEntry.phase == phase,
                    VehicleMaterial.material_id == pm.material_id,
                    VehicleMaterial.custom_name == pm.custom_name,
                )
            )
            used_result = await self.session.execute(used_stmt)
            total_brought = used_result.scalar() or 0
            
            if total_brought < pm.quantity:
                phase_fully_utilized = False
                break

        if phase_fully_utilized:
            phase_record.status = ApplicationPhaseStatus.COMPLETED
            phase_record.completed_at = datetime.now()

            # Log the automatic completion log entry
            self.session.add(
                ApplicationActionLog(
                    application_id=application_id,
                    action=WorkflowAction.APPROVE,
                    from_status=ApplicationStatus.TOKEN_GENERATED,
                    to_status=ApplicationStatus.TOKEN_GENERATED,
                    performed_by=user_id,
                    performed_at=datetime.now(),
                    remarks=f"Phase {phase} auto-completed: all materials exhausted",
                    phase=phase,
                )
            )

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
        )
        from backend.schemas.response.application import TOKEN_VALIDITY_DAYS
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

        # 4. Fetch phase material limits and total brought quantities for this phase
        phase_limits = {}
        phase_units = {}
        brought_so_far = {}

        # 4.1. Get limits and units
        pm_stmt = (
            select(ApplicationPhaseMaterial, Material.unit)
            .outerjoin(Material, ApplicationPhaseMaterial.material_id == Material.id)
            .where(
                ApplicationPhaseMaterial.application_id == ve.application_id,
                ApplicationPhaseMaterial.phase == ve.phase,
            )
        )
        pm_results = await self.session.execute(pm_stmt)
        for pm, m_unit in pm_results.all():
            key = (pm.material_id, pm.custom_name)
            phase_limits[key] = pm.quantity
            phase_units[key] = m_unit or pm.custom_unit or ""

        # 4.2. Get total brought quantities for this phase
        brought_stmt = (
            select(
                VehicleMaterial.material_id,
                VehicleMaterial.custom_name,
                func.sum(VehicleMaterial.quantity).label("total"),
            )
            .join(VehicleEntry, VehicleMaterial.vehicle_entry_id == VehicleEntry.id)
            .where(
                VehicleEntry.application_id == ve.application_id,
                VehicleEntry.phase == ve.phase,
            )
            .group_by(VehicleMaterial.material_id, VehicleMaterial.custom_name)
        )
        brought_results = await self.session.execute(brought_stmt)
        for row in brought_results.all():
            key = (row.material_id, row.custom_name)
            brought_so_far[key] = row.total

        # 5. Material entry details (flattened list for schema)
        material_details = []
        for vm in ve.materials:
            m_name = vm.material.name if vm.material else (vm.custom_name or "Unknown")
            key = (vm.material_id, vm.custom_name)
            
            approved = phase_limits.get(key, 0.0)
            brought = brought_so_far.get(key, 0.0)
            unit = (vm.material.unit if vm.material else None) or vm.custom_unit or phase_units.get(key, "")

            material_details.append(
                {
                    "material_id": vm.material_id,
                    "custom_name": vm.custom_name,
                    "custom_unit": vm.custom_unit,
                    "material_name": m_name,
                    "unit": unit,
                    "approved_quantity": approved,
                    "consumed_quantity": vm.quantity,
                    "remaining_quantity": approved - brought,
                }
            )

        # 6. Media signed URLs
        vehicle_image = None
        entry_proof = []
        if ve.media:
            plate = ve.media.get("vehicle_plate")
            if plate:
                vehicle_image = generate_signed_file_url(plate)
            proofs = ve.media.get("entry_proofs", [])
            if proofs and isinstance(proofs, list):
                entry_proof = [generate_signed_file_url(p) for p in proofs if p]

        # 7. Dumping photos
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

    async def get_all_vehicle_entries(
        self,
        search: Optional[str] = None,
        vehicle_number: Optional[List[str]] = None,
        material_name: Optional[List[str]] = None,
        token_number: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Get all vehicle entries for authority view, grouped by trip with advanced filtering."""
        from backend.dbmodels.user import User
        from backend.dbmodels.application import (
            ApprovedApplicationPhase,
            Material,
            VehicleMaterial,
            ApplicationPhaseMaterial,
        )

        # Base query for VehicleEntry
        stmt = (
            select(
                VehicleEntry,
                Application,
                User,
                ApprovedApplicationPhase,
                exists()
                .where(VehicleEntryDumpingPhoto.vehicle_entry_id == VehicleEntry.id)
                .label("has_dumping_photos"),
            )
            .join(Application, VehicleEntry.application_id == Application.id)
            .join(User, VehicleEntry.entry_by == User.id)
            .outerjoin(
                ApprovedApplicationPhase,
                and_(
                    ApprovedApplicationPhase.application_id == VehicleEntry.application_id,
                    ApprovedApplicationPhase.phase == VehicleEntry.phase,
                ),
            )
        )

        # ── Explicit Filters ─────────────────────────────────────────────
        filters = []
        if vehicle_number:
            v_filters = [VehicleEntry.vehicle_number.ilike(f"%{vn}%") for vn in vehicle_number]
            filters.append(or_(*v_filters))

        if material_name:
            m_or_filters = []
            for mn in material_name:
                material_match_exists = exists().where(
                    and_(
                        VehicleMaterial.vehicle_entry_id == VehicleEntry.id,
                        or_(
                            VehicleMaterial.custom_name.ilike(f"%{mn}%"),
                            exists().where(
                                and_(
                                    Material.id == VehicleMaterial.material_id,
                                    Material.name.ilike(f"%{mn}%"),
                                )
                            ),
                        ),
                    )
                )
                m_or_filters.append(material_match_exists)
            filters.append(or_(*m_or_filters))

        if token_number:
            t_or_filters = []
            for tn in token_number:
                if tn.upper().startswith("TKN-"):
                    try:
                        parts = tn.split("-")
                        phase_id = int(parts[-1])
                        t_or_filters.append(ApprovedApplicationPhase.id == phase_id)
                    except (ValueError, IndexError):
                        pass
                elif tn.upper().startswith("APP-"):
                    try:
                        parts = tn.split("-")
                        app_id = int(parts[-1])
                        t_or_filters.append(Application.id == app_id)
                    except (ValueError, IndexError):
                        pass
                elif tn.isdigit():
                    val = int(tn)
                    t_or_filters.append(
                        or_(Application.id == val, ApprovedApplicationPhase.id == val)
                    )
            if t_or_filters:
                filters.append(or_(*t_or_filters))

        if start_date:
            filters.append(VehicleEntry.entry_at >= start_date)
        if end_date:
            filters.append(VehicleEntry.entry_at <= end_date)

        # ── Fuzzy Search Filters (Legacy) ─────────────────────────────────
        if search:
            search_filters = []
            search_filters.append(VehicleEntry.vehicle_number.ilike(f"%{search}%"))

            material_match_exists = exists().where(
                and_(
                    VehicleMaterial.vehicle_entry_id == VehicleEntry.id,
                    or_(
                        VehicleMaterial.custom_name.ilike(f"%{search}%"),
                        exists().where(
                            and_(
                                Material.id == VehicleMaterial.material_id,
                                Material.name.ilike(f"%{search}%"),
                            )
                        ),
                    ),
                )
            )
            search_filters.append(material_match_exists)
            search_filters.append(
                func.cast(VehicleEntry.entry_at, String).ilike(f"%{search}%")
            )

            if search.isdigit():
                val = int(search)
                search_filters.append(Application.id == val)
                search_filters.append(ApprovedApplicationPhase.id == val)
            elif search.upper().startswith("TKN-"):
                try:
                    parts = search.split("-")
                    phase_id = int(parts[-1])
                    search_filters.append(ApprovedApplicationPhase.id == phase_id)
                except (ValueError, IndexError):
                    pass
            elif search.upper().startswith("APP-"):
                try:
                    parts = search.split("-")
                    app_id = int(parts[-1])
                    search_filters.append(Application.id == app_id)
                except (ValueError, IndexError):
                    pass

            filters.append(or_(*search_filters))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(VehicleEntry.entry_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Batch fetch phase material limits and total brought quantities for efficiency
        app_phase_pairs = set((ve.application_id, ve.phase) for ve, _, _, _, _ in rows)
        phase_material_limits = {}  # (app_id, phase, material_id, custom_name) -> qty
        phase_material_units = {}   # (app_id, phase, material_id, custom_name) -> unit
        total_brought_so_far = {}   # (app_id, phase, material_id, custom_name) -> total_qty

        if app_phase_pairs:
            # 1. Get Phase Material Limits and Units
            pm_filters = [
                and_(
                    ApplicationPhaseMaterial.application_id == aid,
                    ApplicationPhaseMaterial.phase == ph,
                )
                for aid, ph in app_phase_pairs
            ]
            pm_stmt = (
                select(ApplicationPhaseMaterial, Material.unit)
                .outerjoin(Material, ApplicationPhaseMaterial.material_id == Material.id)
                .where(or_(*pm_filters))
            )
            pm_results = await self.session.execute(pm_stmt)
            for pm, m_unit in pm_results.all():
                key = (pm.application_id, pm.phase, pm.material_id, pm.custom_name)
                phase_material_limits[key] = pm.quantity
                phase_material_units[key] = m_unit or pm.custom_unit or ""

            # 2. Get Total Brought Quantities for these phases
            brought_stmt = (
                select(
                    VehicleEntry.application_id,
                    VehicleEntry.phase,
                    VehicleMaterial.material_id,
                    VehicleMaterial.custom_name,
                    func.sum(VehicleMaterial.quantity).label("total"),
                )
                .join(
                    VehicleMaterial, VehicleEntry.id == VehicleMaterial.vehicle_entry_id
                )
                .where(
                    or_(
                        *[
                            and_(
                                VehicleEntry.application_id == aid,
                                VehicleEntry.phase == ph,
                            )
                            for aid, ph in app_phase_pairs
                        ]
                    )
                )
                .group_by(
                    VehicleEntry.application_id,
                    VehicleEntry.phase,
                    VehicleMaterial.material_id,
                    VehicleMaterial.custom_name,
                )
            )
            brought_results = await self.session.execute(brought_stmt)
            for row in brought_results.all():
                key = (row.application_id, row.phase, row.material_id, row.custom_name)
                total_brought_so_far[key] = row.total

        grouped_results = []
        for ve, app, incharge, phase_rec, has_photos in rows:
            # Generate token_number
            if phase_rec:
                year = (
                    phase_rec.activated_at.year
                    if phase_rec.activated_at
                    else datetime.now().year
                )
                token_number = f"TKN-{year}-{phase_rec.id:03d}"
            else:
                token_number = f"APP-{app.id}-P{ve.phase}"

            # Fetch all materials for this vehicle entry
            mat_stmt = (
                select(VehicleMaterial, Material.name, Material.unit)
                .outerjoin(Material, VehicleMaterial.material_id == Material.id)
                .where(VehicleMaterial.vehicle_entry_id == ve.id)
            )
            mat_result = await self.session.execute(mat_stmt)
            mat_rows = mat_result.all()

            materials_list = []
            for vm, catalog_name, m_unit in mat_rows:
                key = (ve.application_id, ve.phase, vm.material_id, vm.custom_name)
                permitted = phase_material_limits.get(key, 0.0)
                brought = total_brought_so_far.get(key, 0.0)
                unit = m_unit or vm.custom_unit or phase_material_units.get(key, "")

                materials_list.append(
                    {
                        "id": vm.id,
                        "material_name": catalog_name or vm.custom_name or "Unknown",
                        "quantity": vm.quantity,
                        "unit": unit,
                        "permitted_material_quantity": permitted,
                        "remaining_material_quantity": permitted - brought,
                    }
                )

            grouped_results.append(
                {
                    "id": ve.id,
                    "application_id": ve.application_id,
                    "token_number": token_number,
                    "vehicle_number": ve.vehicle_number,
                    "vehicle_type": ve.vehicle_type,
                    "entry_at": ve.entry_at,
                    "naka_incharge_name": incharge.name,
                    "has_dumping_photos": has_photos,
                    "materials": materials_list,
                    "media": ve.media,
                }
            )

        return grouped_results

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

    async def update_phase_status(
        self,
        application_id: int,
        phase_num: int,
        status: ApplicationPhaseStatus,
        user_id: int,
    ) -> SuccessResponse:
        """Manually update a phase's status (HOLD/TERMINATE/ACTIVATE)."""
        stmt = select(ApprovedApplicationPhase).where(
            ApprovedApplicationPhase.application_id == application_id,
            ApprovedApplicationPhase.phase == phase_num,
        )
        result = await self.session.execute(stmt)
        phase_record = result.scalar_one_or_none()
        if not phase_record:
            raise HTTPException(status_code=404, detail=f"Phase {phase_num} not found")

        if phase_record.status in (ApplicationPhaseStatus.TERMINATED, ApplicationPhaseStatus.COMPLETED):
            raise HTTPException(
                status_code=400,
                detail=f"Phase {phase_num} is {phase_record.status.value} and cannot be changed.",
            )

        old_status = phase_record.status
        phase_record.status = status

        if status == ApplicationPhaseStatus.ACTIVE and old_status != ApplicationPhaseStatus.ACTIVE:
            if not phase_record.activated_at:
                phase_record.activated_at = datetime.now()

        if status == ApplicationPhaseStatus.COMPLETED and old_status != ApplicationPhaseStatus.COMPLETED:
            if not phase_record.completed_at:
                phase_record.completed_at = datetime.now()

        # Audit log using a generic changed action
        self.session.add(
            ApplicationActionLog(
                application_id=application_id,
                action=WorkflowAction.APPROVE, # Generic action for log
                from_status=ApplicationStatus.TOKEN_GENERATED,
                to_status=ApplicationStatus.TOKEN_GENERATED,
                performed_by=user_id,
                performed_at=datetime.now(),
                remarks=f"Phase {phase_num} status changed from {old_status.value} to {status.value}",
                phase=phase_num,
            )
        )

        await self.session.commit()

        # Trigger SMS for specific phase status changes
        try:
            if status in (ApplicationPhaseStatus.WITHHELD, ApplicationPhaseStatus.TERMINATED):
                # We need the application's mobile number
                app_stmt = select(Application.mobile, Application.created_at).where(Application.id == application_id)
                app_res = await self.session.execute(app_stmt)
                app_row = app_res.one_or_none()
                
                if app_row:
                    year = app_row.created_at.year if app_row.created_at else datetime.now().year
                    token_number = f"TKN-{year}-{phase_record.id:03d}"
                    status_text = "put on hold" if status == ApplicationPhaseStatus.WITHHELD else "terminated"
                    await sms_service.send_token_sms(app_row.mobile, token_number, status_text)
        except Exception as e:
            print(f"Error sending phase status SMS: {e}")

        return SuccessResponse(message=f"Phase {phase_num} status updated to {status.value}")

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
                    "phase": phase_rec.phase,
                    "remaining_quantity_pct": remaining_pct,
                    "valid_till": valid_till,
                    "status": phase_rec.status,
                    "applicant_name": phase_rec.application.applicant_name,
                    "mobile": phase_rec.application.mobile,
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
            "phase": phase_rec.phase,
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
            .options(joinedload(ApprovedApplicationPhase.application))
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

        # Search filter (on token_number, application_number, applicant_name, or mobile)
        if search:
            search_lower = search.lower()
            tokens = [
                t
                for t in tokens
                if search_lower in t["token_number"].lower()
                or search_lower in t["application_number"].lower()
                or search_lower in (t["applicant_name"] or "").lower()
                or search_lower in (t["mobile"] or "").lower()
            ]

        # Paginate
        return tokens[offset : offset + limit]

    async def get_application_tokens(self, application_id: int) -> list[dict]:
        """Get all tokens (phases) for a single application with material summaries."""
        stmt = (
            select(ApprovedApplicationPhase)
            .options(joinedload(ApprovedApplicationPhase.application))
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
