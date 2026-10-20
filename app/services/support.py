from datetime import datetime, timezone
import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, UserRole
from app.models.delivery_assignment import DeliveryAssignment
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.seller_product import SellerProduct
from app.models.support import SupportMessage, SupportTicket, SupportTicketStatus
from app.services.notification import notify


ADMIN_TRANSITIONS = {
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"waiting_for_user", "resolved", "closed"},
    "waiting_for_user": {"in_progress", "resolved", "closed"},
    "resolved": {"closed"},
    "closed": set(),
}


def _now():
    return datetime.now(timezone.utc)
def ensure_ticket_replyable(ticket_status: str) -> None:
    if ticket_status in {
        SupportTicketStatus.RESOLVED.value,
        SupportTicketStatus.CLOSED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail="Reopen the ticket before replying",
        )


async def _authorized_order(db: AsyncSession, actor: Customer, order_id: int) -> bool:
    if actor.role == UserRole.CUSTOMER:
        return (await db.execute(select(Order.id).where(Order.id == order_id, Order.customer_id == actor.id))).scalar_one_or_none() is not None
    if actor.role == UserRole.SELLER:
        stmt = select(OrderItem.id).join(SellerProduct, SellerProduct.id == OrderItem.seller_product_id).where(OrderItem.order_id == order_id, SellerProduct.seller_id == actor.id).limit(1)
        return (await db.execute(stmt)).scalar_one_or_none() is not None
    if actor.role == UserRole.DELIVERY_AGENT:
        return (await db.execute(select(DeliveryAssignment.id).where(DeliveryAssignment.order_id == order_id, DeliveryAssignment.delivery_agent_id == actor.id).limit(1))).scalar_one_or_none() is not None
    return False


async def _notify_admins(db: AsyncSession, ticket: SupportTicket, event: str, title: str, message: str, key_suffix: str) -> None:
    admins = (await db.execute(select(Customer.id).where(Customer.role == UserRole.ADMIN, Customer.is_active.is_(True)))).scalars().all()
    for admin_id in admins:
        await notify(db, admin_id, event, title, message, "support_ticket", ticket.id, f"support:{event}:{ticket.id}:{key_suffix}")


async def create_ticket(db: AsyncSession, actor: Customer, subject: str, category: str, body: str, order_id: int | None) -> SupportTicket:
    if actor.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrators cannot create support tickets")
    if order_id is not None and not await _authorized_order(db, actor, order_id):
        raise HTTPException(status_code=404, detail="Order not available")
    ticket = SupportTicket(public_reference=secrets.token_urlsafe(24)[:32], creator_customer_id=actor.id, subject=subject, category=category, order_id=order_id)
    db.add(ticket)
    await db.flush()
    message = SupportMessage(ticket_id=ticket.id, author_customer_id=actor.id, body=body)
    db.add(message)
    await db.flush()
    await _notify_admins(db, ticket, "support_ticket_created", "New support ticket", f"Ticket {ticket.public_reference} requires attention.", str(message.id))
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: int, actor: Customer, lock: bool = False) -> SupportTicket:
    stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
    if lock:
        stmt = stmt.with_for_update()
    ticket = (await db.execute(stmt)).scalar_one_or_none()
    if ticket is None or (actor.role != UserRole.ADMIN and ticket.creator_customer_id != actor.id):
        raise HTTPException(status_code=404, detail="Support ticket not found")
    return ticket


async def list_tickets(db: AsyncSession, actor: Customer, limit: int, offset: int, status: str | None = None, priority: str | None = None, category: str | None = None, assignee_id: int | None = None, creator_id: int | None = None):
    stmt = select(SupportTicket)
    if actor.role != UserRole.ADMIN:
        stmt = stmt.where(SupportTicket.creator_customer_id == actor.id)
    else:
        if priority: stmt = stmt.where(SupportTicket.priority == priority)
        if category: stmt = stmt.where(SupportTicket.category == category)
        if assignee_id: stmt = stmt.where(SupportTicket.assigned_admin_id == assignee_id)
        if creator_id: stmt = stmt.where(SupportTicket.creator_customer_id == creator_id)
    if status: stmt = stmt.where(SupportTicket.status == status)
    rows = (await db.execute(stmt.order_by(SupportTicket.updated_at.desc(), SupportTicket.created_at.desc(), SupportTicket.id.desc()).limit(limit + 1).offset(offset))).scalars().all()
    return rows[:limit], len(rows) > limit


async def list_messages(db: AsyncSession, ticket: SupportTicket, limit: int, offset: int):
    rows = (await db.execute(select(SupportMessage).where(SupportMessage.ticket_id == ticket.id).order_by(SupportMessage.created_at.asc(), SupportMessage.id.asc()).limit(limit + 1).offset(offset))).scalars().all()
    return rows[:limit], len(rows) > limit


async def add_message(db: AsyncSession, ticket_id: int, actor: Customer, body: str) -> SupportMessage:
    ticket = await get_ticket(db, ticket_id, actor, lock=True)
    ensure_ticket_replyable(ticket.status)
    message = SupportMessage(ticket_id=ticket.id, author_customer_id=actor.id, body=body)
    ticket.updated_at = _now()
    db.add(message)
    await db.flush()
    if actor.role == UserRole.ADMIN:
        if ticket.creator_customer_id != actor.id:
            await notify(db, ticket.creator_customer_id, "support_message", "Support ticket reply", "An administrator replied to your support ticket.", "support_ticket", ticket.id, f"support:message:{message.id}:{ticket.creator_customer_id}")
    else:
        await _notify_admins(db, ticket, "support_message", "New support ticket reply", "A customer replied to a support ticket.", str(message.id))
    await db.commit()
    await db.refresh(message)
    return message


async def reopen_ticket(db: AsyncSession, ticket_id: int, actor: Customer) -> SupportTicket:
    ticket = await get_ticket(db, ticket_id, actor, lock=True)
    if actor.role == UserRole.ADMIN or ticket.status not in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="Ticket cannot be reopened")
    ticket.status, ticket.updated_at = "open", _now()
    ticket.resolved_at = None
    ticket.closed_at = None
    await _notify_admins(db, ticket, "support_ticket_reopened", "Support ticket reopened", f"Ticket {ticket.public_reference} was reopened.", str(ticket.updated_at.timestamp()))
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def admin_update_ticket(db: AsyncSession, ticket_id: int, admin: Customer, status: str | None, priority: str | None, assigned_admin_id: int | None, assigned_supplied: bool) -> SupportTicket:
    ticket = await get_ticket(db, ticket_id, admin, lock=True)
    if status is not None and status != ticket.status:
        if status not in ADMIN_TRANSITIONS.get(ticket.status, set()):
            raise HTTPException(status_code=409, detail="Invalid ticket status transition")
        ticket.status = status
        if status == "resolved": ticket.resolved_at = _now()
        if status == "closed": ticket.closed_at = _now()
    if priority is not None:
        ticket.priority = priority
    if assigned_supplied:
        assignee = None
        if assigned_admin_id is not None:
            assignee = (await db.execute(select(Customer).where(Customer.id == assigned_admin_id, Customer.role == UserRole.ADMIN, Customer.is_active.is_(True)))).scalar_one_or_none()
            if assignee is None:
                raise HTTPException(status_code=422, detail="Assigned administrator is not available")
        ticket.assigned_admin_id = assignee.id if assignee else None
    ticket.updated_at = _now()
    await notify(db, ticket.creator_customer_id, "support_ticket_updated", "Support ticket updated", "Your support ticket status or assignment was updated.", "support_ticket", ticket.id, f"support:update:{ticket.id}:{ticket.updated_at.timestamp()}")
    await db.commit()
    await db.refresh(ticket)
    return ticket
