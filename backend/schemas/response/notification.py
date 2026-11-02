from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    application_id: Optional[int] = None
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    unread_count: int
    total: int
