from datetime import datetime
from backend.meta import ApplicationDocumentType
from typing import Optional

from sqlalchemy import Enum, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationPhaseStatus,
    PropertyUsageType,
    DepartmentType,
)
from backend.dbmodels.user import User


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    unit: Mapped[str] = mapped_column(String, index=True)


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Applicant Details
    applicant_name: Mapped[str] = mapped_column(String, index=True)
    father_name: Mapped[str] = mapped_column(String)
    mobile: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_address: Mapped[str] = mapped_column(String)

    # Property & Work Details
    property_address: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(
        String, index=True
    )  # Keeping original title field
    work_description: Mapped[str] = mapped_column(String)
    contractor_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Classification
    is_agriculture_land: Mapped[bool] = mapped_column(default=False)
    property_usage: Mapped[PropertyUsageType] = mapped_column(
        Enum(PropertyUsageType), default=PropertyUsageType.DOMESTIC
    )
    department: Mapped[DepartmentType] = mapped_column(
        Enum(DepartmentType), default=DepartmentType.ULB
    )
    ward_zone: Mapped[str] = mapped_column(String, default="")

    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), index=True, default=ApplicationStatus.PENDING
    )
    type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType), index=True, default=ApplicationType.NEW
    )
    num_stages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    documents: Mapped[list["ApplicationDocument"]] = relationship(
        "ApplicationDocument", back_populates="application"
    )
    materials: Mapped[list["ApplicationMaterial"]] = relationship(
        "ApplicationMaterial", back_populates="application"
    )


class ApplicationMaterial(Base):
    __tablename__ = "application_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"),  # Added foreign key constraint
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, index=True)

    application: Mapped["Application"] = relationship(
        "Application", back_populates="materials"
    )
    material: Mapped["Material"] = relationship("Material")

class ApplicationComment(Base):
    __tablename__ = "application_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    comment: Mapped[str] = mapped_column(String, index=True)
    comment_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    commenter: Mapped[User] = relationship("User")


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
    application: Mapped["Application"] = relationship(
        "Application", back_populates="documents"
    )


class ApprovedApplicationPhase(Base):
    __tablename__ = "application_phases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[int] = mapped_column(Integer, index=True)
    material_id: Mapped[int] = mapped_column(Integer, index=True)
    quantity: Mapped[int] = mapped_column(Integer, index=True)


class ApplicationApproval(Base):
    __tablename__ = "application_approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
