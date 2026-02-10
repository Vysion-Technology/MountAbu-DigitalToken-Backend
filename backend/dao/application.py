"""Application DAO."""

from fastapi import HTTPException
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import insert, select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta


from backend.database import get_db
from backend.dbmodels.application import ApplicationComment
from backend.dao.base import BaseDAO
from backend.meta import ApplicationStatus
from backend.schemas.request.application import ApplicationCreate
from backend.schemas.response.application import ApplicationResponse
from backend.schemas.response.meta import SuccessResponse
from backend.dbmodels.application import Application, ApplicationDocument, ApplicationApproval, ApplicationMaterial, Material
from backend.meta import ApplicationDocumentType, ApplicationFlags, UserRole, ApplicationType, ApplicationPhaseStatus


class ApplicationDAO(BaseDAO):
    """Application DAO."""

    def get_required_flags(self, application: Application) -> list[ApplicationFlags]:
        """Get the required flags for an application."""
        flags = []
        if application.type == ApplicationType.NEW:
            if application.status == ApplicationStatus.PENDING:
                flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_ACTION)
            elif application.status == ApplicationStatus.APPROVED:
                # Check if materials are added
                if not application.materials:
                    flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_JEN_MATERIAL_ENTRY)
                else:
                    # Check if phases are approved
                    approved_phases = {phase.phase for phase in application.phases if phase.status == ApplicationPhaseStatus.APPROVED}
                    if application.num_stages:
                        next_phase = len(approved_phases) + 1
                        if next_phase <= application.num_stages:
                            flags.append(ApplicationFlags.NEW_APPLICATION_REQUIRES_NODAL_OFFICER_TOKEN_GENERATION)
        elif application.type == ApplicationType.RENOVATION:
            if application.status == ApplicationStatus.PENDING:
                flags.append(ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_FORWARD)
            elif application.status == ApplicationStatus.APPROVED:
                # Find latest Commissioner approval
                commissioner_approvals = [a for a in application.approvals if a.approver.role == UserRole.COMMISSIONER and a.phase is None]
                if commissioner_approvals:
                    latest_comm_approval = max(commissioner_approvals, key=lambda a: a.approved_at)
                    now = datetime.now()
                    seven_days_ago = now - timedelta(days=7)
                    if latest_comm_approval.approved_at < seven_days_ago:
                        # Check overdue comments
                        commented_depts = {comment.commenter.role for comment in application.comments}
                        depts = [UserRole.JEN, UserRole.DEPT_ATP, UserRole.DEPT_LAND, UserRole.DEPT_LEGAL]
                        for dept in depts:
                            if dept not in commented_depts:
                                flags.append(getattr(ApplicationFlags, f"RENOVATION_OVERDUE_COMMENTS_{dept.name.split('_')[-1]}"))
                        if flags:
                            flags.append(ApplicationFlags.RENOVATION_OVERDUE_COMMENTS)
                    # Check if all depts commented
                    commented_depts = {comment.commenter.role for comment in application.comments}
                    depts = [UserRole.JEN, UserRole.DEPT_ATP, UserRole.DEPT_LAND, UserRole.DEPT_LEGAL]
                    if not all(dept in commented_depts for dept in depts):
                        flags.append(ApplicationFlags.RENOVATION_REQUIRES_DEPT_COMMENT)
                    else:
                        # After comments, Commissioner action again?
                        # Assuming after comments, status is still APPROVED, but need Commissioner action
                        # But the user said "After the entries, COMMISSIONER can approve, reject or object"
                        # So, perhaps after comments, it goes back to Commissioner
                        # But status is APPROVED, perhaps need another approval
                        # For simplicity, assume if comments are there, then Nodal token generation
                        flags.append(ApplicationFlags.RENOVATION_REQUIRES_COMMISSIONER_ACTION)
                # JEN material entry
                if not application.materials:
                    flags.append(ApplicationFlags.RENOVATION_REQUIRES_JEN_MATERIAL_ENTRY)
                # Nodal officer token generation
                approved_phases = {phase.phase for phase in application.phases if phase.status == ApplicationPhaseStatus.APPROVED}
                if application.num_stages:
                    next_phase = len(approved_phases) + 1
                    if next_phase <= application.num_stages:
                        flags.append(getattr(ApplicationFlags, f"RENOVATION_REQUIRES_NODAL_OFFICER_APPROVAL_PHASE_{next_phase}"))
        return flags

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

    async def comment_on_application(
        self, application_id: int, comment: str, user_id: int
    ) -> SuccessResponse:
        """Comment on application."""
        # Verify application exists
        application = await self.session.get(Application, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        await self.session.execute(
            insert(ApplicationComment)
            .values(
                application_id=application_id,
                comment=comment,
                comment_by=user_id,
            )
        )
        await self.session.commit()
        return SuccessResponse(message="Comment added successfully")

    async def approve_application(self, application_id: int) -> SuccessResponse:
        """Approve an Application."""
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


async def get_application_dao(
    session: AsyncSession = Depends(get_db),
) -> ApplicationDAO:
    """..."""
    return ApplicationDAO(session)
