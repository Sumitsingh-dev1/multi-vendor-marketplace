"""allow delivery assignment history

Revision ID: 8fa7916c57d1
Revises: 9af5d7acd575
Create Date: 2026-09-27 22:40:18.029803

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8fa7916c57d1"
down_revision: Union[str, Sequence[str], None] = "9af5d7acd575"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Find the old unique constraint on delivery_assignments.order_id.
    unique_constraints = inspector.get_unique_constraints(
        "delivery_assignments"
    )

    for constraint in unique_constraints:
        constraint_name = constraint.get("name")
        columns = constraint.get("column_names", [])

        if (
            constraint_name
            and columns == ["order_id"]
        ):
            op.drop_constraint(
                constraint_name,
                "delivery_assignments",
                type_="unique",
            )
            break

    # Allow multiple historical assignments for an order,
    # but only one active assignment at a time.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_delivery_assignment_order
        ON delivery_assignments (order_id)
        WHERE status NOT IN ('CANCELLED', 'DELIVERED')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_active_delivery_assignment_order
        """
    )

    op.create_unique_constraint(
        "uq_delivery_assignments_order_id",
        "delivery_assignments",
        ["order_id"],
    )