"""secure identity phase one

Revision ID: c3d91e4f5a20
Revises: a07579849330
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c3d91e4f5a20"
down_revision: Union[str, Sequence[str], None] = "a07579849330"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("password_reset_tokens", sa.Column("verification_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("password_reset_tokens", "verification_attempts", server_default=None)
    status_enum = sa.Enum("pending", "approved", "rejected", name="sellerapplicationstatus")
    op.create_table("seller_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("business_name", sa.String(length=150), nullable=False),
        sa.Column("business_address", sa.Text(), nullable=False),
        sa.Column("tax_identifier", sa.String(length=100), nullable=True),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seller_applications_customer_id", "seller_applications", ["customer_id"])
    op.create_index("ix_seller_applications_status", "seller_applications", ["status"])

def downgrade() -> None:
    op.drop_index("ix_seller_applications_status", table_name="seller_applications")
    op.drop_index("ix_seller_applications_customer_id", table_name="seller_applications")
    op.drop_table("seller_applications")
    sa.Enum(name="sellerapplicationstatus").drop(op.get_bind(), checkfirst=True)
    op.drop_column("password_reset_tokens", "verification_attempts")
