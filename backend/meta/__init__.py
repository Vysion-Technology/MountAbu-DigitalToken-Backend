from enum import Enum as PyEnum


class UserRole(str, PyEnum):
    SUPERADMIN = "SUPERADMIN"
    COMMISSIONER = "COMMISSIONER"
    CITIZEN = "CITIZEN"
    NAKA_INCHARGE = "NAKA_INCHARGE"
    DEPT_LAND = "DEPT_LAND"
    DEPT_LEGAL = "DEPT_LEGAL"
    DEPT_ATP = "DEPT_ATP"
    JEN = "JEN"


class ApplicationStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    WITHHELD = "WITHHELD"
    REJECTED = "REJECTED"


class ApplicationType(str, PyEnum):
    NEW = "NEW"
    RENOVATION = "RENOVATION"
    FENCING = "FENCING"


class ApplicationDocumentType(str, PyEnum):
    """..."""

    APPLICATION = "APPLICATION"
    INSPECTION = "INSPECTION"
    OTHER = "OTHER"


class ApplicationPhaseStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class PropertyUsageType(str, PyEnum):
    DOMESTIC = "DOMESTIC"
    COMMERCIAL = "COMMERCIAL"
    HOTEL = "HOTEL"


class DepartmentType(str, PyEnum):
    ULB = "ULB"