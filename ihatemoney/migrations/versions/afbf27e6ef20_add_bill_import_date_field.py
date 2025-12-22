revision = "afbf27e6ef20"
down_revision = "b78f8a8bdb16"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("bill", sa.Column("creation_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("bill", "creation_date")
