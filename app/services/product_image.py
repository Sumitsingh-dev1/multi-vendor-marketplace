from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.seller_product import SellerProduct


UPLOAD_ROOT = Path("uploads")
MAX_IMAGE_SIZE = 5 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def _verify_seller_owns_product(
    db: AsyncSession,
    product_id: int,
    seller_id: int,
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    result = await db.execute(
        select(SellerProduct).where(
            SellerProduct.product_id == product_id,
            SellerProduct.seller_id == seller_id,
        )
    )
    seller_listing = result.scalar_one_or_none()

    if seller_listing is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found or does not belong to you",
        )

    return product


async def upload_product_image(
    db: AsyncSession,
    product_id: int,
    seller: Customer,
    image: UploadFile,
    is_primary: bool,
    sort_order: int,
):
    await _verify_seller_owns_product(
        db,
        product_id,
        seller.id,
    )

    extension = ALLOWED_IMAGE_TYPES.get(
        image.content_type
    )

    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, and WebP images are allowed",
        )

    contents = await image.read(MAX_IMAGE_SIZE + 1)

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image size must not exceed 5 MB",
        )

    product_directory = (
        UPLOAD_ROOT
        / "products"
        / str(product_id)
    )

    await run_in_threadpool(
        product_directory.mkdir,
        parents=True,
        exist_ok=True,
    )

    filename = f"{uuid4().hex}{extension}"
    file_path = product_directory / filename

    try:
        await run_in_threadpool(
            file_path.write_bytes,
            contents,
        )

        result = await db.execute(
            select(ProductImage).where(
                ProductImage.product_id == product_id
            )
        )
        existing_images = result.scalars().all()

        if not existing_images:
            is_primary = True

        if is_primary:
            for existing_image in existing_images:
                existing_image.is_primary = False

        product_image = ProductImage(
            product_id=product_id,
            image_url=(
                f"/uploads/products/"
                f"{product_id}/{filename}"
            ),
            is_primary=is_primary,
            sort_order=sort_order,
        )

        db.add(product_image)
        await db.commit()
        await db.refresh(product_image)

        return product_image

    except Exception:
        await db.rollback()

        if await run_in_threadpool(file_path.exists):
            await run_in_threadpool(file_path.unlink)

        raise


async def get_product_images(
    db: AsyncSession,
    product_id: int,
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    result = await db.execute(
        select(ProductImage)
        .where(
            ProductImage.product_id == product_id
        )
        .order_by(
            ProductImage.sort_order,
            ProductImage.id,
        )
    )
    return result.scalars().all()


async def delete_product_image(
    db: AsyncSession,
    product_id: int,
    image_id: int,
    seller: Customer,
):
    await _verify_seller_owns_product(
        db,
        product_id,
        seller.id,
    )

    result = await db.execute(
        select(ProductImage).where(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id,
        )
    )
    product_image = result.scalar_one_or_none()

    if product_image is None:
        raise HTTPException(
            status_code=404,
            detail="Product image not found",
        )

    was_primary = product_image.is_primary

    file_path = Path(
        "." + product_image.image_url
    )

    await db.delete(product_image)

    try:
        await db.flush()

        if was_primary:
            result = await db.execute(
                select(ProductImage)
                .where(
                    ProductImage.product_id == product_id
                )
                .order_by(
                    ProductImage.sort_order,
                    ProductImage.id,
                )
            )
            replacement = result.scalars().first()

            if replacement is not None:
                replacement.is_primary = True

        await db.commit()

        if await run_in_threadpool(file_path.exists):
            await run_in_threadpool(file_path.unlink)

        return {
            "message": "Product image deleted successfully"
        }

    except Exception:
        await db.rollback()
        raise
