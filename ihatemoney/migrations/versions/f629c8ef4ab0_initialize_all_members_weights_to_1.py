"""Initialize all members weights to 1

Revision ID: f629c8ef4ab0
Revises: 26d6a218c329
Create Date: 2016-06-15 09:40:30.400862

"""

# revision identifiers, used by Alembic.
revision = "f629c8ef4ab0"
down_revision = "26d6a218c329"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute(
        sa.update(sa.table("person",
            sa.column("id", sa.Integer(), nullable=False),
            sa.column("project_id", sa.String(length=64), nullable=True),
            sa.column("name", sa.UnicodeText(), nullable=True),
            sa.column("activated", sa.Boolean(), nullable=True),
            sa.column("weight", sa.Float(), nullable=True),
        )).where(sa.column("weight") == None).values(weight=1)
    )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
