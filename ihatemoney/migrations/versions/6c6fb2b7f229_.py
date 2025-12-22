revision = "6c6fb2b7f229"
down_revision = "a67119aa3ee5"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("bill", sa.Column("external_link", sa.UnicodeText(), nullable=True))


def downgrade():
    op.drop_column("bill", "external_link")
