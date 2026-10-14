from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_db, require_admin
from app.models.category import Category
from app.models.customer import Customer
from app.schemas.category import (
    AdminCategoryResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)


router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


@router.post("/")
async def create_category(
    data: CategoryCreate,
    admin: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    category = Category(
        name=data.name,
        description=data.description,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return {
        "message": "Category created successfully",
    }


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_async_db),
):
    statement = select(Category)

    result = await db.execute(statement)

    return result.scalars().all()


@router.get(
    "/admin",
    response_model=list[AdminCategoryResponse],
)
async def get_all_categories_for_admin(
    admin: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    statement = select(Category)

    result = await db.execute(statement)

    return result.scalars().all()


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    statement = select(Category).where(
        Category.id == category_id
    )

    result = await db.execute(statement)

    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    return category


@router.patch("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    admin: Customer = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
):
    statement = select(Category).where(
        Category.id == category_id
    )

    result = await db.execute(
        statement
    )
    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    if data.name is not None:
        category.name = data.name

    if data.description is not None:
        category.description = data.description

    if data.is_active is not None:
        category.is_active = data.is_active

    await db.commit()

    return {
        "message": "Category updated successfully",
    }
