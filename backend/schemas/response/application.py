from datetime import datetime, timedelta

from backend.meta import (
    ApplicationStatus,
    ApplicationType,
    ApplicationDocumentType,
    ApplicationPhaseStatus,
    CommentType,
    PropertyUsageType,
    WorkflowAction,
    StructureType,
    JurisdictionZone,
    UserRole,
)
from pydantic import BaseModel, ConfigDict, model_validator

from typing import Optional, List

# Default token validity period (days from activation)
TOKEN_VALIDITY_DAYS = 60


class ApplicationDocumentResponse(BaseModel):
    id: int
    document_path: str
    document_type: ApplicationDocumentType
    document_name: Optional[str]
    access_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        """Generate a signed download URL from *document_path*."""
        from backend.services.storage import generate_signed_file_url

        path = None
        if hasattr(data, "document_path"):
            path = data.document_path
        elif isinstance(data, dict):
            path = data.get("document_path")

        if path:
            url = generate_signed_file_url(path)
            if hasattr(data, "__dict__"):
                return {
                    "id": data.id,
                    "document_path": path,
                    "document_type": data.document_type,
                    "document_name": getattr(data, "document_name", None),
                    "access_url": url,
                }
            else:
                data["access_url"] = url
        return data


class ApplicationMaterialResponse(BaseModel):
    """Response schema for application materials."""

    id: int
    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    custom_unit: Optional[str] = None
    quantity: int
    material_name: Optional[str] = None
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_material_info(cls, data):
        """Extract material name and unit from the nested material relationship."""
        # Handle master material
        if hasattr(data, "material") and data.material:
            m_name = getattr(data.material, "name", None)
            m_unit = getattr(data.material, "unit", None)
        else:
            m_name = getattr(data, "custom_name", None)
            m_unit = getattr(data, "custom_unit", None)

        if hasattr(data, "__dict__"):
            return {
                "id": getattr(data, "id"),
                "material_id": getattr(data, "material_id", None),
                "custom_name": getattr(data, "custom_name", None),
                "custom_unit": getattr(data, "custom_unit", None),
                "quantity": getattr(data, "quantity"),
                "material_name": m_name,
                "unit": m_unit,
            }
        return data


class CommentResponse(BaseModel):
    """Response schema for application comments."""

    id: int
    application_id: int
    comment: str
    comment_by: int
    commenter_name: Optional[str] = None
    commenter_role: Optional[str] = None
    comment_type: Optional[CommentType] = CommentType.GENERAL
    media_paths: Optional[list] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_commenter_name(cls, data):
        """Extract commenter name and sign media paths."""
        from backend.services.storage import generate_signed_file_url

        raw_paths = None
        if hasattr(data, "media_paths"):
            raw_paths = data.media_paths
        elif isinstance(data, dict):
            raw_paths = data.get("media_paths")

        signed_paths = []
        if raw_paths:
            signed_paths = [generate_signed_file_url(p) for p in raw_paths if p]

        if hasattr(data, "commenter") and data.commenter:
            role_val = getattr(data.commenter, "role", None)
            if hasattr(role_val, "value"):
                role_val = role_val.value
            data = dict(
                id=data.id,
                application_id=data.application_id,
                comment=data.comment,
                comment_by=data.comment_by,
                commenter_name=data.commenter.name,
                commenter_role=str(role_val) if role_val else None,
                comment_type=getattr(data, "comment_type", CommentType.GENERAL),
                media_paths=signed_paths if signed_paths else getattr(data, "media_paths", None),
                created_at=getattr(data, "created_at", None),
            )
        else:
            if signed_paths:
                if hasattr(data, "__dict__"):
                    # Create a dict if it is an object
                    res_dict = {
                        "id": getattr(data, "id", None),
                        "application_id": getattr(data, "application_id", None),
                        "comment": getattr(data, "comment", None),
                        "comment_by": getattr(data, "comment_by", None),
                        "commenter_name": getattr(data, "commenter_name", None),
                        "commenter_role": getattr(data, "commenter_role", None),
                        "comment_type": getattr(data, "comment_type", CommentType.GENERAL),
                        "media_paths": signed_paths,
                        "created_at": getattr(data, "created_at", None),
                    }
                    return res_dict
                elif isinstance(data, dict):
                    data["media_paths"] = signed_paths
        return data


class PhaseMaterialResponse(BaseModel):
    """Response schema for phase-level materials."""

    id: int
    application_id: int
    phase: int
    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    custom_unit: Optional[str] = None
    quantity: int
    material_name: Optional[str] = None
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_material_info(cls, data):
        """Extract material name and unit from the nested material relationship."""
        if hasattr(data, "material") and data.material:
            m_name = getattr(data.material, "name", None)
            m_unit = getattr(data.material, "unit", None)
        else:
            m_name = getattr(data, "custom_name", None)
            m_unit = getattr(data, "custom_unit", None)

        if hasattr(data, "__dict__"):
            return {
                "id": getattr(data, "id"),
                "application_id": getattr(data, "application_id"),
                "phase": getattr(data, "phase"),
                "material_id": getattr(data, "material_id", None),
                "custom_name": getattr(data, "custom_name", None),
                "custom_unit": getattr(data, "custom_unit", None),
                "quantity": getattr(data, "quantity"),
                "material_name": m_name,
                "unit": m_unit,
            }
        return data


class PhaseResponse(BaseModel):
    """Response schema for application phases."""

    id: int
    application_id: int
    phase: int
    name: Optional[str] = None
    status: ApplicationPhaseStatus
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    transport_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_transport_code(cls, data):
        """Generate the HMAC transport code from application_id + phase."""
        from backend.core.transport_code import encode_transport_code

        if hasattr(data, "application_id") and hasattr(data, "phase"):
            app_id = data.application_id
            phase = data.phase
        elif isinstance(data, dict):
            app_id = data.get("application_id")
            phase = data.get("phase")
        else:
            return data
        if app_id is not None and phase is not None:
            if hasattr(data, "__dict__"):
                # ORM model — convert to dict for mutation
                d = {
                    "id": data.id,
                    "application_id": app_id,
                    "phase": phase,
                    "name": getattr(data, "name", None),
                    "status": data.status,
                    "activated_at": getattr(data, "activated_at", None),
                    "completed_at": getattr(data, "completed_at", None),
                    "transport_code": encode_transport_code(app_id, phase),
                }
                return d
            else:
                data["transport_code"] = encode_transport_code(app_id, phase)
        return data


class TokenMaterialResponse(BaseModel):
    """Per-material summary within a token (phase)."""

    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    custom_unit: Optional[str] = None
    material_name: Optional[str] = None
    unit: Optional[str] = None
    approved_quantity: float
    consumed_quantity: float
    remaining_quantity: float
    
    # Aliases for consistency with VehicleEntryMaterialItem
    permitted_material_quantity: float = 0.0
    remaining_material_quantity: float = 0.0

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def set_aliases(cls, data):
        if isinstance(data, dict):
            if "approved_quantity" in data:
                data["permitted_material_quantity"] = data["approved_quantity"]
            if "remaining_quantity" in data:
                data["remaining_material_quantity"] = data["remaining_quantity"]
        return data


class TokenResponse(BaseModel):
    """Lightweight token for the token-list table."""

    transport_code: str
    token_number: str
    application_number: str
    applicant_name: Optional[str] = None
    mobile: Optional[str] = None
    phase: int
    remaining_quantity_pct: Optional[float] = None
    valid_till: Optional[datetime] = None
    status: ApplicationPhaseStatus

    model_config = ConfigDict(from_attributes=True)


class VehicleEntryResponse(BaseModel):
    """A single vehicle / naka entry shown under the Vehicle Entries tab."""

    id: int
    vehicle_number: Optional[str] = None
    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    custom_unit: Optional[str] = None
    material_name: Optional[str] = None
    material_unit: Optional[str] = None
    quantity_entered: float
    entry_at: datetime
    remarks: Optional[str] = None
    media: Optional[dict] = None
    access_urls: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class TokenAuthorityInfo(BaseModel):
    """Authority / system information shown on the token detail page."""

    issued_by: Optional[str] = None  # e.g. "Nodal Officer (Ward 3)"
    issued_on: Optional[datetime] = None  # activated_at
    token_generated_from: Optional[str] = None  # e.g. "Approved Renovation Application"

    model_config = ConfigDict(from_attributes=True)


class TokenDetailResponse(BaseModel):
    """Full token detail returned for GET /tokens/{transport_code}.

    Maps to the "Token Details" screen that shows:
    - Header: token_number, status, date range
    - Left panel: QR/application info
    - Vehicle Entries tab
    - Material Summary tab
    """

    # Identity
    transport_code: str
    token_number: str
    phase: int
    status: ApplicationPhaseStatus
    valid_from: Optional[datetime] = None  # activated_at
    valid_till: Optional[datetime] = None

    # Application info
    application_id: int
    application_number: str
    applicant_name: str
    property_address: str
    property_usage: PropertyUsageType
    application_type: ApplicationType

    # Authority & system info
    authority: TokenAuthorityInfo

    # Material summary (same as before)
    materials: List[TokenMaterialResponse] = []
    remaining_quantity_pct: Optional[float] = None

    # Vehicle entries (naka entries)
    vehicle_entries: List[VehicleEntryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class NakaEntryResponse(BaseModel):
    """Response for a Naka checkpoint entry."""

    id: int
    application_id: int
    phase: int
    material_id: Optional[int] = None
    custom_name: Optional[str] = None
    custom_unit: Optional[str] = None
    quantity_brought: float
    entry_by: int
    entry_at: datetime
    vehicle_number: Optional[str] = None
    remarks: Optional[str] = None
    media: Optional[dict] = None
    access_urls: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_urls(cls, data):
        from backend.services.storage import generate_signed_file_url

        # Handle both ORM objects and dicts
        media = (
            getattr(data, "media", None)
            if hasattr(data, "media")
            else (data.get("media") if isinstance(data, dict) else None)
        )

        if not media or not isinstance(media, dict):
            return data

        access_urls = {}

        # 1. Vehicle Plate
        plate_path = media.get("vehicle_plate")
        if plate_path:
            access_urls["vehicle_plate"] = generate_signed_file_url(plate_path)

        # 2. Entry Proofs (List)
        proof_paths = media.get("entry_proofs", [])
        if proof_paths and isinstance(proof_paths, list):
            access_urls["entry_proofs"] = [
                generate_signed_file_url(p) for p in proof_paths if p
            ]

        # Update data
        if hasattr(data, "media") and not isinstance(data, dict):
            # It's an ORM object, return a dict with access_urls
            d = {
                k: getattr(data, k)
                for k in [
                    "id",
                    "application_id",
                    "phase",
                    "material_id",
                    "custom_name",
                    "custom_unit",
                    "quantity_brought",
                    "entry_by",
                    "entry_at",
                    "vehicle_number",
                    "remarks",
                    "media",
                ]
            }
            d["access_urls"] = access_urls
            return d
        elif isinstance(data, dict):
            data["access_urls"] = access_urls

        return data


class InspectionReportResponse(BaseModel):
    """Response for an inspection report."""

    id: int
    application_id: int
    inspected_by: int
    inspector_name: Optional[str] = None
    inspected_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    remarks: str
    media_paths: Optional[list] = None
    access_urls: Optional[List[str]] = None
    recommended_phases: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def process_inspection_data(cls, data):
        """Extract inspector name and generate signed URLs for media paths."""
        from backend.services.storage import generate_signed_file_url

        # Handle inspector name
        if hasattr(data, "inspector") and data.inspector:
            inspector_name = data.inspector.name
        else:
            inspector_name = None

        # Handle media access URLs
        paths = getattr(data, "media_paths", []) or []
        urls = [generate_signed_file_url(p) for p in paths if p]

        if hasattr(data, "__dict__"):
            return {
                "id": data.id,
                "application_id": data.application_id,
                "inspected_by": data.inspected_by,
                "inspector_name": inspector_name,
                "inspected_at": data.inspected_at,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "remarks": data.remarks,
                "media_paths": paths,
                "access_urls": urls,
                "recommended_phases": data.recommended_phases,
            }
        return data


class ActionLogResponse(BaseModel):
    """Response for an action log entry."""

    id: int
    application_id: int
    action: WorkflowAction
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    performed_by: int
    performed_at: datetime
    remarks: Optional[str] = None
    phase: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationObjectionResponse(BaseModel):
    id: int
    application_id: int
    objected_by_id: int
    objected_by_name: Optional[str] = None
    objected_by_role: str
    objected_to_role: str
    remarks: Optional[str] = None
    reverted_document_url: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolved_by_role: Optional[str] = None
    resolution_remarks: Optional[str] = None

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data):
        if hasattr(data, "__dict__"):
            dict_keys = set(data.__dict__.keys())
            d = {k: data.__dict__[k] for k in dict_keys if not k.startswith("_")}
            if "objected_by_user" in dict_keys and data.__dict__["objected_by_user"]:
                d["objected_by_name"] = getattr(data.__dict__["objected_by_user"], "name", None)
            if "resolved_by_user" in dict_keys and data.__dict__["resolved_by_user"]:
                d["resolved_by_name"] = getattr(data.__dict__["resolved_by_user"], "name", None)
            return d
        return data


class ApplicationResponse(BaseModel):
    id: int
    applicant_id: Optional[int] = 0
    user_id: int
    assigned_role: Optional[UserRole] = None

    applicant_name: str
    father_name: Optional[str] = None
    mobile: str
    email: Optional[str] = None
    property_address: str
    current_address: Optional[str] = None
    is_agriculture_land: bool
    property_usage: PropertyUsageType
    existing_structure: Optional[StructureType] = None
    construction_floor: Optional[StructureType] = None
    jurisdiction_zone: JurisdictionZone

    organization_name: Optional[str] = None
    department_id: Optional[int]
    ward_id: Optional[int]

    ward_zone: Optional[str] = None

    description: Optional[str] = None
    contractor_name: Optional[str] = None
    work_description: Optional[str] = None
    status: ApplicationStatus
    type: ApplicationType
    num_stages: Optional[int]
    created_at: Optional[datetime] = None
    documents: List[ApplicationDocumentResponse] = []
    materials: List[ApplicationMaterialResponse] = []
    phase_materials: List[PhaseMaterialResponse] = []
    comments: List[CommentResponse] = []
    inspections: List[InspectionReportResponse] = []
    tokens: List[TokenResponse] = []
    objections: List[ApplicationObjectionResponse] = []
    rejection_remarks: Optional[str] = None
    objection_to_role: Optional[str] = None

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_ward_name(cls, data):
        """Extract ward name and rejection remarks."""
        ward_name = None
        rejection_remarks = None

        # Extract ward name
        if hasattr(data, "ward_rel") and data.ward_rel:
            ward_name = getattr(data.ward_rel, "name", None)

        # Extract rejection remarks from action_logs if present
        if hasattr(data, "action_logs") and data.action_logs:
            sorted_logs = sorted(
                data.action_logs,
                key=lambda x: getattr(x, "performed_at", None) or datetime.min,
                reverse=True
            )
            for log in sorted_logs:
                action_val = getattr(log, "action", None)
                if (
                    action_val == WorkflowAction.REJECT
                    or (hasattr(action_val, "value") and action_val.value == "REJECT")
                    or action_val == "REJECT"
                ):
                    rejection_remarks = getattr(log, "remarks", None)
                    break
        elif isinstance(data, dict):
            ward_rel = data.get("ward_rel")
            if ward_rel:
                ward_name = getattr(ward_rel, "name", None) if not isinstance(ward_rel, dict) else ward_rel.get("name")
            
            action_logs = data.get("action_logs", [])
            if action_logs:
                sorted_logs = []
                for log in action_logs:
                    if isinstance(log, dict):
                        performed_at = log.get("performed_at") or datetime.min
                        sorted_logs.append((performed_at, log))
                    else:
                        performed_at = getattr(log, "performed_at", None) or datetime.min
                        sorted_logs.append((performed_at, log))
                sorted_logs.sort(key=lambda x: x[0], reverse=True)
                for _, log in sorted_logs:
                    if isinstance(log, dict):
                        action = log.get("action")
                        remarks = log.get("remarks")
                    else:
                        action = getattr(log, "action", None)
                        remarks = getattr(log, "remarks", None)
                    
                    if (
                        action == WorkflowAction.REJECT
                        or action == "REJECT"
                        or (hasattr(action, "value") and action.value == "REJECT")
                    ):
                        rejection_remarks = remarks
                        break

        # Return dict or updated dict
        from backend.meta import ApplicationDocumentType

        if hasattr(data, "__dict__"):
            d = {k: getattr(data, k, None) for k in data.__dict__.keys() if not k.startswith("_")}
            d["ward_zone"] = ward_name
            d["rejection_remarks"] = rejection_remarks
            # Copy other attributes that may be descriptors/properties
            for field in cls.model_fields.keys():
                if field not in d and hasattr(data, field):
                    d[field] = getattr(data, field)
            
            if d.get("documents"):
                d["documents"] = [
                    doc for doc in d["documents"]
                    if getattr(doc, "document_type", None) != ApplicationDocumentType.GEO_TAGGED_PHOTO
                    and getattr(doc, "document_type", None) != "GEO_TAGGED_PHOTO"
                    and (not isinstance(doc, dict) or (doc.get("document_type") != ApplicationDocumentType.GEO_TAGGED_PHOTO and doc.get("document_type") != "GEO_TAGGED_PHOTO"))
                ]
            return d
        elif isinstance(data, dict):
            data["ward_zone"] = ward_name
            data["rejection_remarks"] = rejection_remarks
            if data.get("documents"):
                data["documents"] = [
                    doc for doc in data["documents"]
                    if getattr(doc, "document_type", None) != ApplicationDocumentType.GEO_TAGGED_PHOTO
                    and getattr(doc, "document_type", None) != "GEO_TAGGED_PHOTO"
                    and (not isinstance(doc, dict) or (doc.get("document_type") != ApplicationDocumentType.GEO_TAGGED_PHOTO and doc.get("document_type") != "GEO_TAGGED_PHOTO"))
                ]
            return data
        return data


class VehicleEntryMaterialItem(BaseModel):
    """Single material item within a vehicle entry."""
    id: int  # VehicleMaterial.id
    material_name: str
    quantity: float
    unit: str = ""
    permitted_material_quantity: float = 0.0
    remaining_material_quantity: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AuthorityVehicleEntryResponse(BaseModel):
    """Grouped response for authority view of vehicle entries."""

    id: int  # VehicleEntry.id
    application_id: int
    token_number: Optional[str] = None  # Hidden for NAKA_INCHARGE
    vehicle_number: str
    vehicle_type: Optional[str] = None
    entry_at: datetime
    naka_incharge_name: str
    has_dumping_photos: bool
    materials: List[VehicleEntryMaterialItem]
    media: Optional[dict] = None
    access_urls: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_urls(cls, data):
        from backend.services.storage import generate_signed_file_url

        media = data.get("media") if isinstance(data, dict) else getattr(data, "media", None)
        if not media or not isinstance(media, dict):
            return data

        access_urls = {}
        plate = media.get("vehicle_plate")
        if plate:
            access_urls["vehicle_plate"] = generate_signed_file_url(plate)

        proofs = media.get("entry_proofs", [])
        if proofs and isinstance(proofs, list):
            access_urls["entry_proofs"] = [generate_signed_file_url(p) for p in proofs if p]

        if isinstance(data, dict):
            data["access_urls"] = access_urls
        return data


class DumpingPhotoResponse(BaseModel):
    """Response for a dumping photo."""

    id: int
    photo_path: str
    uploaded_at: datetime
    access_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_access_url(cls, data):
        from backend.services.storage import generate_signed_file_url

        path = getattr(data, "photo_path", None) or data.get("photo_path")
        if path:
            if isinstance(data, dict):
                data["access_url"] = generate_signed_file_url(path)
            else:
                # Return a dict for Pydantic to validate
                return {
                    "id": data.id,
                    "photo_path": data.photo_path,
                    "uploaded_at": data.uploaded_at,
                    "access_url": generate_signed_file_url(path),
                }
        return data


class VehicleEntryDetailResponse(BaseModel):
    """Detailed response for a single vehicle entry."""

    id: int
    token_number: str
    issued_by: Optional[str] = None
    application_number: str
    token_validity: Optional[datetime] = None
    vehicle_number: str
    vehicle_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    entry_at: datetime
    naka_incharge_name: str

    material_entry_details: List[TokenMaterialResponse] = []
    vehicle_image: Optional[str] = None  # Signed URL
    entry_proof: List[str] = []  # List of signed URLs
    dumping_photos: List[DumpingPhotoResponse] = []


class ApplicationPaginatedResponse(BaseModel):
    """Paginated applications list response with total count."""

    applications: List[ApplicationResponse]
    total: int
    offset: int = 0
    limit: int = 10


    model_config = ConfigDict(from_attributes=True)


ApplicationResponse.model_rebuild()
