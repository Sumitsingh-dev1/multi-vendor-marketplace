from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_db, get_current_customer
from app.models.customer import Customer
from app.schemas.notification import NotificationListResponse, NotificationResponse, UnreadCountResponse
from app.services.notification import list_notifications, mark_all_read, mark_read, unread_count

router = APIRouter(prefix="/notifications", tags=["Notifications"])
def response(n): return NotificationResponse(id=n.id, notification_type=n.notification_type, title=n.title, message=n.message, resource_type=n.resource_type, resource_id=n.resource_id, is_read=n.is_read, read_at=n.read_at, created_at=n.created_at)
@router.get("/me", response_model=NotificationListResponse)
async def mine(unread_only: bool = False, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    rows, has_next = await list_notifications(db, customer.id, unread_only, limit, offset); return NotificationListResponse(items=[response(n) for n in rows], limit=limit, offset=offset, has_next=has_next)
@router.get("/me/unread-count", response_model=UnreadCountResponse)
async def count(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)): return UnreadCountResponse(unread_count=await unread_count(db, customer.id))
@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def read(notification_id: int, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    n = await mark_read(db, customer.id, notification_id)
    if n is None: raise HTTPException(status_code=404, detail="Notification not found")
    return response(n)
@router.patch("/me/read-all")
async def read_all(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)): return {"updated": await mark_all_read(db, customer.id)}
