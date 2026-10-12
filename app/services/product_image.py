from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

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


def _verify_seller_owns_product(
    db: Session,
    product_id: int,
    seller_id: int,
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    seller_listing = (
        db.query(SellerProduct)
        .filter(
            SellerProduct.product_id == product_id,
            SellerProduct.seller_id == seller_id,
        )
        .first()
    )

    if seller_listing is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found or does not belong to you",
        )

    return product


def upload_product_image(
    db: Session,
    product_id: int,
    seller: Customer,
    image: UploadFile,
    is_primary: bool,
    sort_order: int,
):
    _verify_seller_owns_product(
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

    contents = image.file.read(
        MAX_IMAGE_SIZE + 1
    )

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

    product_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = f"{uuid4().hex}{extension}"
    file_path = product_directory / filename

    try:
        file_path.write_bytes(contents)

        existing_images = (
            db.query(ProductImage)
            .filter(
                ProductImage.product_id == product_id
            )
            .all()
        )

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
        db.commit()
        db.refresh(product_image)

        return product_image

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise


def get_product_images(
    db: Session,
    product_id: int,
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return (
        db.query(ProductImage)
        .filter(
            ProductImage.product_id == product_id
        )
        .order_by(
            ProductImage.sort_order,
            ProductImage.id,
        )
        .all()
    )


def delete_product_image(
    db: Session,
    product_id: int,
    image_id: int,
    seller: Customer,
):
    _verify_seller_owns_product(
        db,
        product_id,
        seller.id,
    )

    product_image = (
        db.query(ProductImage)
        .filter(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id,
        )
        .first()
    )

    if product_image is None:
        raise HTTPException(
            status_code=404,
            detail="Product image not found",
        )

    was_primary = product_image.is_primary

    file_path = Path(
        "." + product_image.image_url
    )

    db.delete(product_image)

    try:
        db.flush()

        if was_primary:
            replacement = (
                db.query(ProductImage)
                .filter(
                    ProductImage.product_id == product_id
                )
                .order_by(
                    ProductImage.sort_order,
                    ProductImage.id,
                )
                .first()
            )

            if replacement is not None:
                replacement.is_primary = True

        db.commit()

        if file_path.exists():
            file_path.unlink()

        return {
            "message": "Product image deleted successfully"
        }

    except Exception:
        db.rollback()
        raise