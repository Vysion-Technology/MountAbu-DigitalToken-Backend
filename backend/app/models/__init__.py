"""Models module - SQLAlchemy models for Mount Abu E-Token System.

This module exports all models from their respective files:
- enums.py     - All enum definitions
- mixins.py    - TimestampMixin, SoftDeleteMixin
- core.py      - Role, User, Permission, Session
- application.py - Application, Document, Timeline
- estimate.py  - Estimate, EstimatePhase
- inspection.py - Inspection, InspectionPhoto
- token.py     - Token, TokenShare, VehicleEntry
- blacklist.py - Blacklist status and audit
- notification.py - Notifications
- content.py   - CMS Pages, Notices, Tenders
"""

# Enums
from app.models.enums import (
    ApplicationStatus,
    ApplicationType,
    BlacklistAction,
    ContentStatus,
    EstimatePhaseStatus,
    EstimateStatus,
    EstimateType,
    InspectionRecommendation,
    InspectionStatus,
    InspectionType,
    NotificationType,
    PermissionCategory,
    RoleType,
    TokenShareStatus,
    TokenStatus,
    UserStatus,
    UserType,
)

# Mixins
from app.models.mixins import SoftDeleteMixin, TimestampMixin

# Core Models
from app.models.core import (
    OTPSession,
    Permission,
    Role,
    RolePermission,
    Session,
    User,
)

# Application Models
from app.models.application import (
    Application,
    ApplicationTimeline,
    Document,
)

# Estimate Models
from app.models.estimate import (
    Estimate,
    EstimatePhase,
)

# Inspection Models
from app.models.inspection import (
    Inspection,
    InspectionPhoto,
)

# Token Models
from app.models.token import (
    Token,
    TokenShare,
    VehicleEntry,
)

# Blacklist & Audit Models
from app.models.blacklist import (
    ApplicationRejection,
    AuditLog,
    BlacklistAuditLog,
    UserBlacklistStatus,
)

# Notification Models
from app.models.notification import Notification

# Content Models
from app.models.content import (
    Notice,
    Page,
    Tender,
)

__all__ = [
    # Enums
    "ApplicationStatus",
    "ApplicationType",
    "BlacklistAction",
    "ContentStatus",
    "EstimatePhaseStatus",
    "EstimateStatus",
    "EstimateType",
    "InspectionRecommendation",
    "InspectionStatus",
    "InspectionType",
    "NotificationType",
    "PermissionCategory",
    "RoleType",
    "TokenShareStatus",
    "TokenStatus",
    "UserStatus",
    "UserType",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Core Models
    "Role",
    "User",
    "Permission",
    "RolePermission",
    "Session",
    "OTPSession",
    # Application Models
    "Application",
    "ApplicationTimeline",
    "Document",
    # Estimate Models
    "Estimate",
    "EstimatePhase",
    # Inspection Models
    "Inspection",
    "InspectionPhoto",
    # Token Models
    "Token",
    "TokenShare",
    "VehicleEntry",
    # Blacklist & Audit Models
    "UserBlacklistStatus",
    "ApplicationRejection",
    "BlacklistAuditLog",
    "AuditLog",
    # Notification Models
    "Notification",
    # Content Models
    "Page",
    "Notice",
    "Tender",
]
