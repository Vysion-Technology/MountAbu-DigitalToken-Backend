from datetime import datetime
from backend.meta import ApplicationDocumentType
from typing import Optional

from sqlalchemy import Enum, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.meta import ApplicationStatus, ApplicationType, ApplicationPhaseStatus
from backend.dbmodels.user import User


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    unit: Mapped[str] = mapped_column(String, index=True)


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), index=True, default=ApplicationStatus.PENDING
    )
    type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType), index=True, default=ApplicationType.NEW
    )
    num_stages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, max=5)


class ApplicationMaterial(Base):
    __tablename__ = "application_materials"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    material_id: Mapped[int] = mapped_column(Integer, index=True)
    quantity: Mapped[int] = mapped_column(Integer, index=True)


class ApplicationComment(Base):
    __tablename__ = "application_comments"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    comment: Mapped[str] = mapped_column(String, index=True)
    comment_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    commenter: Mapped[User] = relationship("User")


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    document_type: Mapped[ApplicationDocumentType] = mapped_column(
        Enum(ApplicationDocumentType), index=True
    )
    document_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_path: Mapped[str] = mapped_column(String, nullable=False)
    document_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    documenter: Mapped[User] = relationship("User")


class ApprovedApplicationPhase(Base):
    __tablename__ = "application_phases"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[ApplicationPhaseStatus] = mapped_column(
        Enum(ApplicationPhaseStatus), index=True, default=ApplicationPhaseStatus.PENDING
    )


class ApplicationPhaseMaterial(Base):
    __tablename__ = "application_phase_materials"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[int] = mapped_column(Integer, index=True)
    material_id: Mapped[int] = mapped_column(Integer, index=True)
    quantity: Mapped[int] = mapped_column(Integer, index=True)


class ApplicationApproval(Base):
    __tablename__ = "application_approvals"
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    approver: Mapped[User] = relationship("User")


__all__ = [
    "Material",
    "Application",
    "ApplicationMaterial",
    "ApplicationApproval",
    "ApplicationComment",
    "ApplicationDocument",
    "ApprovedApplicationPhase",
    "ApplicationPhaseMaterial",
]
