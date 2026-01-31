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
]
