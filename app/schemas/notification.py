from datetime import datetime
from pydantic import BaseModel

class NotificationResponse(BaseModel):
    id: int; notification_type: str; title: str; message: str; resource_type: str | None; resource_id: int | None; is_read: bool; read_at: datetime | None; created_at: datetime
class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]; limit: int; offset: int; has_next: bool
class UnreadCountResponse(BaseModel): unread_count: int
