from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_db, get_current_customer, require_admin
from app.models.customer import Customer
from app.models.seller_application import SellerApplication, SellerApplicationStatus
from app.schemas.seller_application import SellerApplicationCreate, SellerApplicationResponse, SellerApplicationReview
from app.services.seller_application import review_seller_application, submit_seller_application

router = APIRouter(prefix="/seller-applications", tags=["Seller Applications"])

@router.post("/", response_model=SellerApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(data: SellerApplicationCreate, db: AsyncSession = Depends(get_async_db), customer: Customer = Depends(get_current_customer)):
    return await submit_seller_application(db, customer, **data.model_dump())

@router.get("/pending", response_model=list[SellerApplicationResponse])
async def list_pending_applications(db: AsyncSession = Depends(get_async_db), _: Customer = Depends(require_admin)):
    result = await db.execute(select(SellerApplication).where(SellerApplication.status == SellerApplicationStatus.PENDING).order_by(SellerApplication.created_at))
    return result.scalars().all()

@router.patch("/{application_id}", response_model=SellerApplicationResponse)
async def review_application(application_id: int, data: SellerApplicationReview, db: AsyncSession = Depends(get_async_db), admin: Customer = Depends(require_admin)):
    return await review_seller_application(db, application_id, admin, data.status, data.admin_notes)
