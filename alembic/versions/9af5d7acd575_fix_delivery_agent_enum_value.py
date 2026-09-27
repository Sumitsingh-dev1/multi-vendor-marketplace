"""fix delivery agent enum value

Revision ID: 9af5d7acd575
Revises: 2f158f8fa554
Create Date: 2026-09-27 00:45:20.674913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9af5d7acd575'
down_revision: Union[str, Sequence[str], None] = '2f158f8fa554'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE userrole RENAME VALUE 'delivery_agent' TO 'DELIVERY_AGENT'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TYPE userrole RENAME VALUE 'DELIVERY_AGENT' TO 'delivery_agent'"
    )