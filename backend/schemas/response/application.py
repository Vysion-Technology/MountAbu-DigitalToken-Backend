from backend.meta import ApplicationStatus, ApplicationType
from pydantic import BaseModel, ConfigDict


class ApplicationResponse(BaseModel):
    """..."""

    id: int
    user_id: int
    status: ApplicationStatus
    type: ApplicationType
    num_stages: int

    model_config = ConfigDict(extra="ignore")
