from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.dependencies import get_db
from app.models.customer import Category,Customer
from app.schemas.customer import CategoryCreate, CategoryResponse,CategoryUpdate,AdminCategoryResponse
from app.dependencies import require_admin

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@router.post("/")
def create_category(
    data: CategoryCreate,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    category = Category(
        name=data.name,
        description=data.description
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "message": "Category created successfully"
    }

@router.get("/", response_model=list[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db)
):
    statement = select(Category)
    result = db.execute(statement)

    return result.scalars().all()
@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    statement = select(Category).where(
        Category.id == category_id
    )

    result = db.execute(statement)

    category = result.scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return category
@router.patch("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    statement = select(Category).where(
        Category.id == category_id
    )

    category = db.execute(
        statement
    ).scalar_one_or_none()

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    if data.name is not None:
        category.name = data.name

    if data.description is not None:
        category.description = data.description

    if data.is_active is not None:
        category.is_active = data.is_active

    db.commit()

    return {
        "message": "Category updated successfully"
    }
@router.get(
    "/admin",
    response_model=list[AdminCategoryResponse]
)
def get_all_categories_for_admin(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    statement = select(Category)

    result = db.execute(statement)

    return result.scalars().all()