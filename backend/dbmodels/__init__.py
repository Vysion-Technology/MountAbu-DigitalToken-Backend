from .user import User, ActiveUserOTP
from .application import (
    Application,
    ApplicationDocument,
    Material,
    ApplicationMaterial,
    ApplicationApproval,
    ApplicationComment,
    ApprovedApplicationPhase,
    ApplicationPhaseMaterial,
)
from .master import Ward, Department, Role, ComplaintCategory
from .city_profile import CityProfile
from .download import Download
from .notice import Notice
from .audit_log import AuditLog
from .contact_diary import ContactDiary


__all__ = [
    # Login Details
    "User",
    "ActiveUserOTP",
    # Application Related Data
    "Application",
    "ApplicationDocument",
    "Material",
    "ApplicationMaterial",
    "ApplicationApproval",
    "ApplicationComment",
    "ApprovedApplicationPhase",
    "ApplicationPhaseMaterial",
    # Master Data
    "Ward",
    "Department",
    "Role",
    "ComplaintCategory",
    # City Profile
    "CityProfile",
    # Downloads
    "Download",
    # Notices
    "Notice",
    # Tenders
    "Tender",
    # Events
    "Event",
    # Leaders
    "Leader",
    # Audit Logs
    "AuditLog",
    # Contact Diary
    "ContactDiary",
]
