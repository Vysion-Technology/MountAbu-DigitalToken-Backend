from datetime import datetime
from backend.meta import ApplicationDocumentType, CommentType, WorkflowAction
from typing import Optional

from sqlalchemy import Enum, Float, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationPhaseStatus,
    PropertyUsageType,
)
from backend.dbmodels.user import User
from backend.dbmodels.master import Ward, Department


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
    # Classification
    is_agriculture_land: Mapped[bool] = mapped_column(default=False)
    property_usage: Mapped[PropertyUsageType] = mapped_column(
        Enum(PropertyUsageType), default=PropertyUsageType.DOMESTIC
    )

    # Master Data Foreign Keys
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), nullable=True)

    # Relationships
    department_rel: Mapped["Department"] = relationship("Department")
    ward_rel: Mapped["Ward"] = relationship("Ward")

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
    comments: Mapped[list["ApplicationComment"]] = relationship(
        "ApplicationComment", back_populates="application"
    )
    approvals: Mapped[list["ApplicationApproval"]] = relationship(
        "ApplicationApproval", back_populates="application"
    )
    phases: Mapped[list["ApprovedApplicationPhase"]] = relationship(
        "ApprovedApplicationPhase", back_populates="application"
    )
    phase_materials: Mapped[list["ApplicationPhaseMaterial"]] = relationship(
        "ApplicationPhaseMaterial", back_populates="application"
    )
    vehicle_entries: Mapped[list["VehicleEntry"]] = relationship(
        "VehicleEntry", back_populates="application"
    )
    inspections: Mapped[list["InspectionReport"]] = relationship(
        "InspectionReport", back_populates="application"
    )
    action_logs: Mapped[list["ApplicationActionLog"]] = relationship(
        "ApplicationActionLog", back_populates="application"
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
    comment_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    comment_type: Mapped[CommentType] = mapped_column(
        Enum(CommentType), index=True, default=CommentType.GENERAL
    )
    media_paths: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )

    commenter: Mapped[User] = relationship("User")
    application: Mapped["Application"] = relationship("Application", back_populates="comments")


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
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="phases")
    phase_materials: Mapped[list["ApplicationPhaseMaterial"]] = relationship(
        "ApplicationPhaseMaterial",
        back_populates="phase_record",
        primaryjoin="and_(ApprovedApplicationPhase.application_id==ApplicationPhaseMaterial.application_id, "
                    "ApprovedApplicationPhase.phase==ApplicationPhaseMaterial.phase)",
        foreign_keys="[ApplicationPhaseMaterial.application_id, ApplicationPhaseMaterial.phase]",
        viewonly=True,
    )
    vehicle_entries: Mapped[list["VehicleEntry"]] = relationship(
        "VehicleEntry",
        back_populates="phase_record",
        primaryjoin="and_(ApprovedApplicationPhase.application_id==VehicleEntry.application_id, "
                    "ApprovedApplicationPhase.phase==VehicleEntry.phase)",
        foreign_keys="[VehicleEntry.application_id, VehicleEntry.phase]",
        viewonly=True,
    )


class ApplicationPhaseMaterial(Base):
    __tablename__ = "application_phase_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[int] = mapped_column(Integer, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, index=True)

    application: Mapped["Application"] = relationship("Application", back_populates="phase_materials")
    material: Mapped["Material"] = relationship("Material")
    phase_record: Mapped["ApprovedApplicationPhase"] = relationship(
        "ApprovedApplicationPhase",
        back_populates="phase_materials",
        primaryjoin="and_(ApplicationPhaseMaterial.application_id==ApprovedApplicationPhase.application_id, "
                    "ApplicationPhaseMaterial.phase==ApprovedApplicationPhase.phase)",
        foreign_keys="[ApplicationPhaseMaterial.application_id, ApplicationPhaseMaterial.phase]",
        viewonly=True,
    )

class ApplicationApproval(Base):
    __tablename__ = "application_approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        index=True,
    )
    phase: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    action: Mapped[WorkflowAction] = mapped_column(
        Enum(WorkflowAction), index=True, default=WorkflowAction.APPROVE
    )
    remarks: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    approver: Mapped[User] = relationship("User")
    application: Mapped["Application"] = relationship("Application", back_populates="approvals")


__all__ = [
    "Material",
    "Application",
    "ApplicationMaterial",
    "ApplicationApproval",
    "ApplicationComment",
    "ApplicationDocument",
    "ApprovedApplicationPhase",
    "ApplicationPhaseMaterial",
    "VehicleEntry",
    "VehicleMaterial",
    "InspectionReport",
    "ApplicationActionLog",
]


class VehicleEntry(Base):
    """Vehicle material entry at Naka by NAKA_INCHARGE."""
    __tablename__ = "vehicle_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    phase: Mapped[int] = mapped_column(Integer, index=True)
    
    # Vehicle Details
    vehicle_number: Mapped[str] = mapped_column(String, index=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    driver_mobile: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    entry_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    
    remarks: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    media_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="vehicle_entries")
    entered_by_user: Mapped[User] = relationship("User")
    phase_record: Mapped["ApprovedApplicationPhase"] = relationship(
        "ApprovedApplicationPhase",
        back_populates="vehicle_entries",
        primaryjoin="and_(VehicleEntry.application_id==ApprovedApplicationPhase.application_id, "
                    "VehicleEntry.phase==ApprovedApplicationPhase.phase)",
        foreign_keys="[VehicleEntry.application_id, VehicleEntry.phase]",
        viewonly=True,
    )
    
    materials: Mapped[list["VehicleMaterial"]] = relationship(
        "VehicleMaterial", back_populates="vehicle_entry", cascade="all, delete-orphan"
    )


class VehicleMaterial(Base):
    """Materials within a single vehicle entry."""
    __tablename__ = "vehicle_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_entry_id: Mapped[int] = mapped_column(ForeignKey("vehicle_entries.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    
    vehicle_entry: Mapped["VehicleEntry"] = relationship("VehicleEntry", back_populates="materials")
    material: Mapped["Material"] = relationship("Material")


class InspectionReport(Base):
    """Site inspection report by JEN."""
    __tablename__ = "inspection_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    inspected_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    remarks: Mapped[str] = mapped_column(String)
    media_paths: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommended_phases: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="inspections")
    inspector: Mapped[User] = relationship("User")


class ApplicationActionLog(Base):
    """Audit log of every workflow action taken on an application."""
    __tablename__ = "application_action_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    action: Mapped[WorkflowAction] = mapped_column(Enum(WorkflowAction), index=True)
    from_status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus))
    to_status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus))
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phase: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="action_logs")
    performer: Mapped[User] = relationship("User")
