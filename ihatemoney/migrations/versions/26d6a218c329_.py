revision = "26d6a218c329"
down_revision = "b9a10d5d63ce"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("person", sa.Column("weight", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("person", "weight")
