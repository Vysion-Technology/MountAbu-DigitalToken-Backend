"""Enum definitions for the Mount Abu E-Token System."""

from enum import Enum as PyEnum


# ============ USER ENUMS ============


class UserType(str, PyEnum):
    APPLICANT = "APPLICANT"
    AUTHORITY = "AUTHORITY"


class UserStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


# ============ APPLICATION ENUMS ============


class ApplicationType(str, PyEnum):
    NEW_CONSTRUCTION = "NEW_CONSTRUCTION"
    RENOVATION = "RENOVATION"


class ApplicationStatus(str, PyEnum):
    SUBMITTED = "SUBMITTED"
    SDM_REVIEW = "SDM_REVIEW"
    CMS_REVIEW = "CMS_REVIEW"
    LAND_VERIFICATION = "LAND_VERIFICATION"
    LEGAL_VERIFICATION = "LEGAL_VERIFICATION"
    ATP_VERIFICATION = "ATP_VERIFICATION"
    JEN_INSPECTION = "JEN_INSPECTION"
    PENDING_ESTIMATE = "PENDING_ESTIMATE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TOKENS_ISSUED = "TOKENS_ISSUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ============ TOKEN ENUMS ============


class TokenStatus(str, PyEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class TokenShareStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# ============ ROLE ENUMS ============


class RoleType(str, PyEnum):
    SDM = "SDM"
    CMS_UIT = "CMS_UIT"
    CMS_ULB = "CMS_ULB"
    JEN = "JEN"
    LAND = "LAND"
    LEGAL = "LEGAL"
    ATP = "ATP"
    NAKA = "NAKA"


class PermissionCategory(str, PyEnum):
    APPLICATION = "APPLICATION"
    TOKEN = "TOKEN"
    USER = "USER"
    CONTENT = "CONTENT"
    REPORT = "REPORT"


# ============ ESTIMATE ENUMS ============


class EstimateType(str, PyEnum):
    PHASE_WISE = "PHASE_WISE"
    ONE_TIME = "ONE_TIME"


class EstimateStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EstimatePhaseStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# ============ INSPECTION ENUMS ============


class InspectionType(str, PyEnum):
    SITE_VERIFICATION = "SITE_VERIFICATION"
    PROGRESS_CHECK = "PROGRESS_CHECK"
    COMPLETION_CHECK = "COMPLETION_CHECK"


class InspectionStatus(str, PyEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    PHOTOS_PENDING = "PHOTOS_PENDING"


class InspectionRecommendation(str, PyEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PENDING = "PENDING"


# ============ NOTIFICATION ENUMS ============


class NotificationType(str, PyEnum):
    APPLICATION_UPDATE = "APPLICATION_UPDATE"
    TOKEN_GENERATED = "TOKEN_GENERATED"
    TOKEN_SHARED = "TOKEN_SHARED"
    BLACKLIST_WARNING = "BLACKLIST_WARNING"
    BLACKLIST_ADDED = "BLACKLIST_ADDED"
    WHITELIST_ADDED = "WHITELIST_ADDED"
    SYSTEM = "SYSTEM"


# ============ CONTENT ENUMS ============


class ContentStatus(str, PyEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


# ============ BLACKLIST ENUMS ============


class BlacklistAction(str, PyEnum):
    BLACKLIST = "BLACKLIST"
    WHITELIST = "WHITELIST"
