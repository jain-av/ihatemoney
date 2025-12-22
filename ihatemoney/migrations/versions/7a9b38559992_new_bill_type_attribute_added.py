revision = "7a9b38559992"
down_revision = "927ed575acbd"

from alembic import op
import sqlalchemy as sa
from ihatemoney.models import BillType


def upgrade():
    billtype_enum = sa.Enum(BillType)
    billtype_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "bill",
        sa.Column("bill_type", billtype_enum, server_default=BillType.EXPENSE.name),
    )
    op.add_column("bill_version", sa.Column("bill_type", sa.UnicodeText()))


def downgrade():
    op.drop_column("bill", "bill_type")
    op.drop_column("bill_version", "bill_type")

    billtype_enum = sa.Enum(BillType)
    billtype_enum.drop(op.get_bind())
