from datetime import datetime, timezone
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from app.models.notification import Notification


async def notify(db, recipient_id: int, event: str, title: str, message: str, resource_type: str, resource_id: int, key: str) -> None:
    statement = insert(Notification).values(recipient_customer_id=recipient_id, notification_type=event, title=title, message=message, resource_type=resource_type, resource_id=resource_id, deduplication_key=key)
    await db.execute(statement.on_conflict_do_nothing(index_elements=["recipient_customer_id", "deduplication_key"]))


async def list_notifications(db, customer_id: int, unread_only: bool, limit: int, offset: int):
    statement = select(Notification).where(Notification.recipient_customer_id == customer_id)
    if unread_only: statement = statement.where(Notification.is_read.is_(False))
    rows = (await db.execute(statement.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1).offset(offset))).scalars().all()
    return rows[:limit], len(rows) > limit


async def unread_count(db, customer_id: int) -> int:
    return (await db.execute(select(func.count(Notification.id)).where(Notification.recipient_customer_id == customer_id, Notification.is_read.is_(False)))).scalar_one()


async def mark_read(db, customer_id: int, notification_id: int):
    notification = (await db.execute(select(Notification).where(Notification.id == notification_id, Notification.recipient_customer_id == customer_id).with_for_update())).scalar_one_or_none()
    if notification is None: return None
    if not notification.is_read: notification.is_read, notification.read_at = True, datetime.now(timezone.utc)
    await db.commit(); await db.refresh(notification); return notification


async def mark_all_read(db, customer_id: int) -> int:
    result = await db.execute(update(Notification).where(Notification.recipient_customer_id == customer_id, Notification.is_read.is_(False)).values(is_read=True, read_at=datetime.now(timezone.utc)))
    await db.commit(); return result.rowcount or 0
