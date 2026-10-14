"""add in-app notifications

Revision ID: a9c3d7e1f640
Revises: f2b5e8a7c430
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "a9c3d7e1f640"
down_revision: Union[str, Sequence[str], None] = "f2b5e8a7c430"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("notifications", sa.Column("id", sa.Integer(), nullable=False), sa.Column("recipient_customer_id", sa.Integer(), nullable=False), sa.Column("notification_type", sa.String(length=80), nullable=False), sa.Column("title", sa.String(length=160), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("resource_type", sa.String(length=50), nullable=True), sa.Column("resource_id", sa.Integer(), nullable=True), sa.Column("deduplication_key", sa.String(length=255), nullable=False), sa.Column("is_read", sa.Boolean(), nullable=False), sa.Column("read_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["recipient_customer_id"], ["customers.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("recipient_customer_id", "deduplication_key", name="uq_notifications_recipient_deduplication"))
    op.create_index("ix_notifications_recipient_unread_created", "notifications", ["recipient_customer_id", "is_read", "created_at", "id"])
def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_unread_created", table_name="notifications")
    op.drop_table("notifications")
