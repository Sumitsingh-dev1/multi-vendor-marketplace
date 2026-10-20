"""add support tickets

Revision ID: b7d4e2f9a630
Revises: a9c3d7e1f640
"""
from alembic import op
import sqlalchemy as sa

revision = "b7d4e2f9a630"
down_revision = "a9c3d7e1f640"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("support_tickets", sa.Column("id", sa.Integer(), nullable=False), sa.Column("public_reference", sa.String(32), nullable=False), sa.Column("creator_customer_id", sa.Integer(), nullable=False), sa.Column("subject", sa.String(200), nullable=False), sa.Column("category", sa.String(30), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("order_id", sa.Integer(), nullable=True), sa.Column("assigned_admin_id", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True), sa.CheckConstraint("category IN ('order', 'payment', 'delivery', 'product', 'account', 'return_refund', 'other')", name="ck_support_tickets_category"), sa.CheckConstraint("status IN ('open', 'in_progress', 'waiting_for_user', 'resolved', 'closed')", name="ck_support_tickets_status"), sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="ck_support_tickets_priority"), sa.ForeignKeyConstraint(["assigned_admin_id"], ["customers.id"]), sa.ForeignKeyConstraint(["creator_customer_id"], ["customers.id"]), sa.ForeignKeyConstraint(["order_id"], ["orders.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("public_reference"))
    op.create_index("ix_support_tickets_creator_updated", "support_tickets", ["creator_customer_id", "updated_at", "id"])
    op.create_index("ix_support_tickets_admin_filters", "support_tickets", ["status", "priority", "category", "updated_at", "id"])
    op.create_index("ix_support_tickets_order_id", "support_tickets", ["order_id"])
    op.create_index("ix_support_tickets_assigned_admin_id", "support_tickets", ["assigned_admin_id"])
    op.create_table("support_messages", sa.Column("id", sa.Integer(), nullable=False), sa.Column("ticket_id", sa.Integer(), nullable=False), sa.Column("author_customer_id", sa.Integer(), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["author_customer_id"], ["customers.id"]), sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_support_messages_ticket_created", "support_messages", ["ticket_id", "created_at", "id"])

def downgrade() -> None:
    op.drop_index("ix_support_messages_ticket_created", table_name="support_messages")
    op.drop_table("support_messages")
    op.drop_index("ix_support_tickets_assigned_admin_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_order_id", table_name="support_tickets")
    op.drop_index("ix_support_tickets_admin_filters", table_name="support_tickets")
    op.drop_index("ix_support_tickets_creator_updated", table_name="support_tickets")
    op.drop_table("support_tickets")
