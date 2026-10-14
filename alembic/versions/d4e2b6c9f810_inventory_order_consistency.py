"""inventory, order idempotency, and integrity constraints

Revision ID: d4e2b6c9f810
Revises: c3d91e4f5a20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e2b6c9f810"
down_revision: Union[str, Sequence[str], None] = "c3d91e4f5a20"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # These constraints deliberately fail on legacy invalid/duplicate rows rather
    # than modifying data during a schema migration.
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("idempotency_operation", sa.String(length=30), nullable=True))
    op.create_unique_constraint("uq_orders_customer_operation_idempotency_key", "orders", ["customer_id", "idempotency_operation", "idempotency_key"])
    op.create_check_constraint("ck_seller_products_stock_nonnegative", "seller_products", "stock >= 0")
    op.create_check_constraint("ck_seller_products_price_nonnegative", "seller_products", "price >= 0")
    op.create_check_constraint("ck_order_items_quantity_positive", "order_items", "quantity > 0")
    op.create_check_constraint("ck_order_items_price_nonnegative", "order_items", "price >= 0")
    op.create_unique_constraint("uq_cart_items_cart_seller_product", "cart_items", ["cart_id", "seller_product_id"])
    op.create_check_constraint("ck_cart_items_quantity_positive", "cart_items", "quantity > 0")
    op.create_unique_constraint("uq_seller_service_areas_seller_postal_code", "seller_service_areas", ["seller_id", "postal_code"])

def downgrade() -> None:
    op.drop_constraint("uq_seller_service_areas_seller_postal_code", "seller_service_areas", type_="unique")
    op.drop_constraint("ck_cart_items_quantity_positive", "cart_items", type_="check")
    op.drop_constraint("uq_cart_items_cart_seller_product", "cart_items", type_="unique")
    op.drop_constraint("ck_order_items_price_nonnegative", "order_items", type_="check")
    op.drop_constraint("ck_order_items_quantity_positive", "order_items", type_="check")
    op.drop_constraint("ck_seller_products_price_nonnegative", "seller_products", type_="check")
    op.drop_constraint("ck_seller_products_stock_nonnegative", "seller_products", type_="check")
    op.drop_constraint("uq_orders_customer_operation_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_operation")
    op.drop_column("orders", "idempotency_key")
