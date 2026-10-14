"""add product reviews

Revision ID: f2b5e8a7c430
Revises: e7a4c1d8b920
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f2b5e8a7c430"
down_revision: Union[str, Sequence[str], None] = "e7a4c1d8b920"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_reviews_order_item"),
    )
    op.create_index("ix_reviews_product_visible_created", "reviews", ["product_id", "is_hidden", "created_at", "id"])
    op.create_index("ix_reviews_customer_created", "reviews", ["customer_id", "created_at", "id"])

def downgrade() -> None:
    op.drop_index("ix_reviews_customer_created", table_name="reviews")
    op.drop_index("ix_reviews_product_visible_created", table_name="reviews")
    op.drop_table("reviews")
