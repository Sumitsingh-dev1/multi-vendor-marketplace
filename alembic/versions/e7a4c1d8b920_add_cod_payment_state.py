"""add COD payment method and collection state

Revision ID: e7a4c1d8b920
Revises: d4e2b6c9f810
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e7a4c1d8b920"
down_revision: Union[str, Sequence[str], None] = "d4e2b6c9f810"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # PostgreSQL requires new enum values to be committed before normal use.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'pending_collection'")
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'collected'")
    payment_method = sa.Enum("cod", "razorpay", name="paymentmethod")
    payment_method.create(op.get_bind(), checkfirst=True)
    op.add_column("payments", sa.Column("payment_method", payment_method, nullable=True))
    op.add_column("payments", sa.Column("amount_collected_paise", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("collected_by_delivery_agent_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_payments_collected_by_delivery_agent", "payments", "customers", ["collected_by_delivery_agent_id"], ["id"])
    op.create_check_constraint("ck_payments_amount_collected_nonnegative", "payments", "amount_collected_paise IS NULL OR amount_collected_paise >= 0")
    op.create_index("uq_payments_one_cod_per_order", "payments", ["order_id"], unique=True, postgresql_where=sa.text("payment_method = 'cod'"))

def downgrade() -> None:
    op.drop_index("uq_payments_one_cod_per_order", table_name="payments")
    op.drop_constraint("ck_payments_amount_collected_nonnegative", "payments", type_="check")
    op.drop_constraint("fk_payments_collected_by_delivery_agent", "payments", type_="foreignkey")
    op.drop_column("payments", "collected_by_delivery_agent_id")
    op.drop_column("payments", "collected_at")
    op.drop_column("payments", "amount_collected_paise")
    op.drop_column("payments", "payment_method")
    sa.Enum(name="paymentmethod").drop(op.get_bind(), checkfirst=True)
    # PostgreSQL enum values cannot be removed safely without recreating the type.
