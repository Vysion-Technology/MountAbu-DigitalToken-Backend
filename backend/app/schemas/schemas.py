"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import phonenumbers


# ============ BASE SCHEMAS ============


class BaseSchema(BaseModel):
    """Base schema with common config."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SuccessResponse(BaseModel):
    """Standard success response wrapper."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    success: bool = False
    error: dict


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    page: int
    limit: int
    total: int
    total_pages: int


# ============ AUTH SCHEMAS ============


class LoginRequest(BaseModel):
    """Login request schema."""

    user_type: str = Field(..., pattern="^(applicant|authority)$")
    identifier: str = Field(..., min_length=1)  # mobile or email
    password: Optional[str] = None  # Required for authority

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str, info) -> str:
        """Validate mobile number or email format."""
        # Try validating as phone number
        if v.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            try:
                parsed = phonenumbers.parse(v, "IN")
                if not phonenumbers.is_valid_number(parsed):
                    raise ValueError("Invalid mobile number")
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
            except phonenumbers.NumberParseException:
                raise ValueError("Invalid mobile number format")
        return v


class LoginResponse(BaseModel):
    """Login initiation response."""

    session_id: str
    otp_sent: bool
    otp_expires_in: int
    masked_mobile: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    """OTP verification request."""

    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# ============ USER SCHEMAS ============


class UserBase(BaseModel):
    """Base user schema."""

    name: str = Field(..., min_length=2, max_length=255)
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """User creation schema for applicants."""

    pass


class AuthorityCreate(UserBase):
    """Authority creation schema."""

    role: str
    department: str
    designation: str


class UserProfile(BaseSchema):
    """User profile response."""

    id: UUID
    user_type: str
    name: str
    mobile: Optional[str]
    email: Optional[str]
    aadhaar_verified: bool
    preferred_language: str
    created_at: datetime


class UserProfileWithStats(UserProfile):
    """User profile with application statistics."""

    stats: Optional[dict] = None
    blacklist_status: Optional[dict] = None


class AddressUpdate(BaseModel):
    """Address update schema."""

    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Profile update schema."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[AddressUpdate] = None
    preferred_language: Optional[str] = None


# ============ APPLICATION SCHEMAS ============


class PropertyAddress(BaseModel):
    """Property address schema."""

    line1: str
    line2: Optional[str] = None
    city: str = "Mount Abu"
    state: str = "Rajasthan"
    pincode: str


class PropertyOwner(BaseModel):
    """Property owner details."""

    name: str
    father_name: Optional[str] = None


class PropertyDetails(BaseModel):
    """Property details schema."""

    plot_number: str
    khasra_number: Optional[str] = None
    area: float = Field(..., gt=0)
    area_unit: str = "SQ_METERS"
    address: PropertyAddress
    owner_details: PropertyOwner


class ConstructionDetails(BaseModel):
    """Construction details schema."""

    purpose: str  # RESIDENTIAL, COMMERCIAL, etc.
    floors: int = Field(..., ge=1, le=10)
    built_up_area: float = Field(..., gt=0)
    estimated_cost: float = Field(..., gt=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ApplicationCreate(BaseModel):
    """Create application request."""

    application_type: str = Field(..., pattern="^(NEW_CONSTRUCTION|RENOVATION)$")
    property_details: PropertyDetails
    construction_details: ConstructionDetails
    terms_accepted: bool = True
    declaration_accepted: bool = True


class ApplicationSummary(BaseSchema):
    """Application summary for list view."""

    id: UUID
    application_number: str
    application_type: str
    status: str
    submitted_at: datetime
    last_action_at: Optional[datetime]


class ApplicationDetail(ApplicationSummary):
    """Full application details."""

    property_details: dict
    construction_details: dict
    current_authority_role: Optional[str]
    sla_deadline: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]


class ApplicationApprove(BaseModel):
    """Application approval request."""

    comments: Optional[str] = None
    conditions: Optional[List[str]] = None
    generate_tokens: bool = True


class ApplicationReject(BaseModel):
    """Application rejection request."""

    reason: str
    comments: str
    rejection_category: str = Field(
        ..., pattern="^(DOCUMENT_ISSUE|FRAUD|INCOMPLETE|INVALID_DATA|OTHER)$"
    )
    allow_resubmission: bool = True


class ApplicationForward(BaseModel):
    """Application forward request."""

    forward_to: str  # Role name
    comments: Optional[str] = None
    priority: str = "NORMAL"


# ============ TOKEN SCHEMAS ============


class MaterialQuantity(BaseModel):
    """Material quantity schema."""

    material_type: str
    material_name: Optional[str] = None
    approved_quantity: float
    consumed_quantity: float = 0
    remaining_quantity: float
    unit: str


class TokenSummary(BaseSchema):
    """Token summary for list view."""

    id: UUID
    token_number: str
    phase_number: int
    phase_name: Optional[str]
    status: str
    valid_from: datetime
    valid_until: datetime
    usage_count: int


class TokenDetail(TokenSummary):
    """Full token details."""

    materials: List[MaterialQuantity]
    qr_code: Optional[str] = None  # Base64 QR image
    shareable_link: Optional[str] = None


class TokenShare(BaseModel):
    """Token share request."""

    driver_name: str
    driver_mobile: str
    vehicle_number: str
    share_method: str = "SMS"  # SMS, WHATSAPP, BOTH
    valid_for_hours: int = 24
    material_limit: Optional[dict] = None


class TokenScan(BaseModel):
    """Token scan at naka."""

    token_qr: str
    vehicle_number: str
    driver_mobile: Optional[str] = None
    material_type: str
    quantity: float
    unit: str
    naka_location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TokenScanResponse(BaseModel):
    """Token scan response."""

    valid: bool
    token_id: Optional[str] = None
    entry_id: Optional[str] = None
    applicant: Optional[dict] = None
    property_address: Optional[str] = None
    material_allowed: bool = False
    quantity_allowed: bool = False
    previous_balance: Optional[float] = None
    entered_quantity: Optional[float] = None
    new_balance: Optional[float] = None
    error_reason: Optional[str] = None


# ============ BLACKLIST SCHEMAS ============


class BlacklistStatus(BaseSchema):
    """User blacklist status."""

    user_id: UUID
    is_blacklisted: bool
    consecutive_rejections: int
    total_rejections: int
    blacklisted_at: Optional[datetime]
    blacklist_reason: Optional[str]
    warning_issued: bool


class RejectionHistory(BaseSchema):
    """Rejection history item."""

    application_id: UUID
    application_number: str
    rejected_at: datetime
    rejected_by_role: str
    reason: str
    category: str
    comments: Optional[str]
    was_consecutive: bool


class WhitelistRequest(BaseModel):
    """Whitelist user request."""

    reason: str
    verification_method: str = "IN_PERSON"
    conditions: Optional[List[str]] = None


# ============ REPORT SCHEMAS ============


class DateRangeParams(BaseModel):
    """Date range parameters for reports."""

    date_from: str
    date_to: str


class ReportSummary(BaseModel):
    """Report summary response."""

    report_period: dict
    summary: dict
    trend: Optional[List[dict]] = None
