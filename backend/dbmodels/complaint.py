from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, Integer, String, ForeignKey, DateTime, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.database import Base
from backend.dbmodels.user import User
from backend.dbmodels.master import Ward, Department, ComplaintCategory


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )  # Optional for now, guest complaints?

    # Classification
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), nullable=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("complaint_categories.id"), nullable=True
    )

    # Details
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    from backend.meta import ComplaintStatus

    status: Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name='complaintstatus'), default=ComplaintStatus.PENDING, index=True
    )  # Complaint status as enum

    # Applicant Info (Redundant if user_id linked, but keep for explicit capture)
    applicant_name: Mapped[str] = mapped_column(String)
    applicant_mobile: Mapped[str] = mapped_column(String)

    # Location
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    location_address: Mapped[str] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="complaints")
    ward: Mapped["Ward"] = relationship("Ward")
    department: Mapped["Department"] = relationship("Department")
    category: Mapped["ComplaintCategory"] = relationship("ComplaintCategory")

    media: Mapped[list["ComplaintMedia"]] = relationship(
        "ComplaintMedia", back_populates="complaint", cascade="all, delete-orphan"
    )
    comments: Mapped[list["ComplaintComment"]] = relationship(
        "ComplaintComment", back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintMedia(Base):
    __tablename__ = "complaint_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)

    media_path: Mapped[str] = mapped_column(String)  # S3 Key
    media_type: Mapped[str] = mapped_column(String)  # image/png, video/mp4 etc

    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    # To distinguish between initial complaint media and media added later by authorities/users
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    complaint: Mapped["Complaint"] = relationship("Complaint", back_populates="media")
    uploader: Mapped["User"] = relationship("User")


class ComplaintComment(Base):
    __tablename__ = "complaint_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)

    comment: Mapped[str] = mapped_column(Text)
    comment_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Optional media attached to comment
    media_path: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    complaint: Mapped["Complaint"] = relationship(
        "Complaint", back_populates="comments"
    )
    commenter: Mapped["User"] = relationship("User")
