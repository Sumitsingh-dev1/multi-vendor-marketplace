"""add delivery agent role

Revision ID: fb37c2e5099a
Revises: 455dcddec29f
Create Date: 2026-09-25 10:55:00.888420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb37c2e5099a'
down_revision: Union[str, Sequence[str], None] = '455dcddec29f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'delivery_agent'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass