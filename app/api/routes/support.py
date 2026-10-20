from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, get_current_customer, require_admin
from app.models.customer import Customer
from app.schemas.support import TicketAdminUpdate, TicketCategory, TicketCreate, TicketListResponse, TicketMessageCreate, TicketMessageListResponse, TicketMessageResponse, TicketPriority, TicketResponse, TicketStatus
from app.services.support import add_message, admin_update_ticket, create_ticket, get_ticket, list_messages, list_tickets, reopen_ticket

router = APIRouter(tags=["Support"])


async def _customer_displays(db, customer_ids):
    ids = {customer_id for customer_id in customer_ids if customer_id is not None}
    if not ids:
        return {}
    customers = (await db.execute(select(Customer).where(Customer.id.in_(ids)))).scalars().all()
    return {customer.id: {"id": customer.id, "name": customer.name} for customer in customers}


async def ticket_response(db, ticket):
    displays = await _customer_displays(db, [ticket.creator_customer_id, ticket.assigned_admin_id])
    return _ticket_response(ticket, displays)


def _ticket_response(ticket, displays):
    return TicketResponse(id=ticket.id, public_reference=ticket.public_reference, subject=ticket.subject, category=ticket.category, status=ticket.status, priority=ticket.priority, order_id=ticket.order_id, creator=displays[ticket.creator_customer_id], assigned_admin=displays.get(ticket.assigned_admin_id), created_at=ticket.created_at, updated_at=ticket.updated_at, resolved_at=ticket.resolved_at, closed_at=ticket.closed_at)


async def ticket_responses(db, tickets):
    displays = await _customer_displays(db, [customer_id for ticket in tickets for customer_id in (ticket.creator_customer_id, ticket.assigned_admin_id)])
    return [_ticket_response(ticket, displays) for ticket in tickets]


async def message_response(db, message):
    displays = await _customer_displays(db, [message.author_customer_id])
    return _message_response(message, displays)


def _message_response(message, displays):
    return TicketMessageResponse(id=message.id, ticket_id=message.ticket_id, author=displays[message.author_customer_id], body=message.body, created_at=message.created_at)


async def message_responses(db, messages):
    displays = await _customer_displays(db, [message.author_customer_id for message in messages])
    return [_message_response(message, displays) for message in messages]


@router.post("/support/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create(data: TicketCreate, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    return await ticket_response(db, await create_ticket(db, customer, data.subject, data.category, data.message, data.order_id))


@router.get("/support/tickets/me", response_model=TicketListResponse)
async def mine(status_filter: TicketStatus | None = Query(None, alias="status"), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    rows, has_next = await list_tickets(db, customer, limit, offset, status=status_filter)
    return TicketListResponse(items=await ticket_responses(db, rows), limit=limit, offset=offset, has_next=has_next)


@router.get("/support/tickets/{ticket_id}", response_model=TicketResponse)
async def details(ticket_id: int, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    return await ticket_response(db, await get_ticket(db, ticket_id, customer))


@router.get("/support/tickets/{ticket_id}/messages", response_model=TicketMessageListResponse)
async def messages(ticket_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    ticket = await get_ticket(db, ticket_id, customer)
    rows, has_next = await list_messages(db, ticket, limit, offset)
    return TicketMessageListResponse(items=await message_responses(db, rows), limit=limit, offset=offset, has_next=has_next)


@router.post("/support/tickets/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=status.HTTP_201_CREATED)
async def reply(ticket_id: int, data: TicketMessageCreate, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    return await message_response(db, await add_message(db, ticket_id, customer, data.body))


@router.post("/support/tickets/{ticket_id}/reopen", response_model=TicketResponse)
async def reopen(ticket_id: int, customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_async_db)):
    return await ticket_response(db, await reopen_ticket(db, ticket_id, customer))


@router.get("/admin/support/tickets", response_model=TicketListResponse)
async def admin_list(status_filter: TicketStatus | None = Query(None, alias="status"), priority: TicketPriority | None = None, category: TicketCategory | None = None, assignee_id: int | None = Query(None, gt=0), creator_id: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), admin: Customer = Depends(require_admin), db: AsyncSession = Depends(get_async_db)):
    rows, has_next = await list_tickets(db, admin, limit, offset, status_filter, priority, category, assignee_id, creator_id)
    return TicketListResponse(items=await ticket_responses(db, rows), limit=limit, offset=offset, has_next=has_next)


@router.patch("/admin/support/tickets/{ticket_id}", response_model=TicketResponse)
async def admin_update(ticket_id: int, data: TicketAdminUpdate, admin: Customer = Depends(require_admin), db: AsyncSession = Depends(get_async_db)):
    if not data.model_fields_set:
        raise HTTPException(status_code=422, detail="Provide at least one supported field")
    ticket = await admin_update_ticket(db, ticket_id, admin, data.status, data.priority, data.assigned_admin_id, "assigned_admin_id" in data.model_fields_set)
    return await ticket_response(db, ticket)
