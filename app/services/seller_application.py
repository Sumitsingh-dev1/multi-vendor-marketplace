from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer, UserRole
from app.models.seller_application import SellerApplication, SellerApplicationStatus

async def submit_seller_application(db: AsyncSession, customer: Customer, **details):
    if customer.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=400, detail="Only customer accounts can apply to become sellers")
    existing = await db.execute(select(SellerApplication).where(SellerApplication.customer_id == customer.id, SellerApplication.status == SellerApplicationStatus.PENDING))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A seller application is already pending")
    application = SellerApplication(customer_id=customer.id, **details)
    try:
        db.add(application)
        await db.commit()
        await db.refresh(application)
    except Exception:
        await db.rollback()
        raise
    return application

async def review_seller_application(db: AsyncSession, application_id: int, admin: Customer, status: SellerApplicationStatus, admin_notes: str | None):
    if status not in {SellerApplicationStatus.APPROVED, SellerApplicationStatus.REJECTED}:
        raise HTTPException(status_code=422, detail="Application status must be approved or rejected")
    result = await db.execute(select(SellerApplication).where(SellerApplication.id == application_id).with_for_update())
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="Seller application not found")
    if application.customer_id == admin.id:
        raise HTTPException(status_code=403, detail="Administrators cannot review their own applications")
    if application.status != SellerApplicationStatus.PENDING:
        raise HTTPException(status_code=409, detail="Seller application has already been reviewed")
    result = await db.execute(select(Customer).where(Customer.id == application.customer_id).with_for_update())
    applicant = result.scalar_one()
    application.status, application.admin_notes = status, admin_notes
    application.reviewed_by_id, application.reviewed_at = admin.id, datetime.now(timezone.utc)
    if status == SellerApplicationStatus.APPROVED:
        applicant.role = UserRole.SELLER
    try:
        await db.commit()
        await db.refresh(application)
    except Exception:
        await db.rollback()
        raise
    return application
