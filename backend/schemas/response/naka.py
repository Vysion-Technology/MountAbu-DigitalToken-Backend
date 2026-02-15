"""Response schemas for NAKA checkpoint operations."""

from pydantic import BaseModel

from backend.meta import ApplicationPhaseStatus


class NakaMaterialSummary(BaseModel):
    """Per-material summary for a phase at the naka checkpoint."""
    material_id: int
    material_name: str
    unit: str
    allowed_qty: int
    brought_qty: int
    remaining_qty: int


class NakaPhaseResponse(BaseModel):
    """Phase-level material summary shown to NAKA incharge. No PII."""
    transport_code: str
    phase: int
    phase_status: ApplicationPhaseStatus
    materials: list[NakaMaterialSummary]
