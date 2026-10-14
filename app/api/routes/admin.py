from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.dependencies import get_async_db, require_admin
from app.models.customer import Customer, UserRole
from app.schemas.admin import DeliveryAgentCreate

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post("/delivery-agents", status_code=status.HTTP_201_CREATED)
async def provision_delivery_agent(data: DeliveryAgentCreate, db: AsyncSession = Depends(get_async_db), _: Customer = Depends(require_admin)):
    agent = Customer(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=await run_in_threadpool(hash_password, data.password),
        role=UserRole.DELIVERY_AGENT,
    )
    try:
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return {"id": agent.id, "email": agent.email, "role": agent.role}
