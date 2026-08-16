from alembic import op
import sqlalchemy as sa


revision = "4d08ed8120c4"
down_revision = "1eb1b60779fa"
branch_labels = None
depends_on = None


def upgrade():
    userrole_enum = sa.Enum(
        "CUSTOMER",
        "SELLER",
        "ADMIN",
        name="userrole",
    )

    # Create the PostgreSQL enum type first.
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Existing customers need a value, so temporarily use CUSTOMER.
    op.add_column(
        "customers",
        sa.Column(
            "role",
            userrole_enum,
            nullable=False,
            server_default="CUSTOMER",
        ),
    )

    # Remove the permanent database default.
    op.alter_column(
        "customers",
        "role",
        server_default=None,
    )


def downgrade():
    op.drop_column("customers", "role")

    userrole_enum = sa.Enum(
        "CUSTOMER",
        "SELLER",
        "ADMIN",
        name="userrole",
    )

    userrole_enum.drop(op.get_bind(), checkfirst=True)