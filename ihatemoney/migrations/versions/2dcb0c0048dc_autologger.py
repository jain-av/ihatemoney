"""autologger

Revision ID: 2dcb0c0048dc
Revises: 6c6fb2b7f229
Create Date: 2020-04-10 18:12:41.285590

"""

# revision identifiers, used by Alembic.
revision = "2dcb0c0048dc"
down_revision = "6c6fb2b7f229"

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "bill_version",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("payer_id", sa.Integer(), autoincrement=False, nullable=True),
        sa.Column("amount", sa.Float(), autoincrement=False, nullable=True),
        sa.Column("date", sa.Date(), autoincrement=False, nullable=True),
        sa.Column("creation_date", sa.Date(), autoincrement=False, nullable=True),
        sa.Column("what", sa.UnicodeText(), autoincrement=False, nullable=True),
        sa.Column(
            "external_link", sa.UnicodeText(), autoincrement=False, nullable=True
        ),
        sa.Column("archive", sa.Integer(), autoincrement=False, nullable=True),
        sa.Column(
            "transaction_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("end_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", "transaction_id"),
    )
    op.create_index(
        "ix_bill_version_end_transaction_id",
        "bill_version",
        ["end_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_bill_version_operation_type",
        "bill_version",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        "ix_bill_version_transaction_id",
        "bill_version",
        ["transaction_id"],
        unique=False,
    )
    op.create_table(
        "billowers_version",
        sa.Column("bill_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("person_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column(
            "transaction_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("end_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("bill_id", "person_id", "transaction_id"),
    )
    op.create_index(
        "ix_billowers_version_end_transaction_id",
        "billowers_version",
        ["end_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_billowers_version_operation_type",
        "billowers_version",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        "ix_billowers_version_transaction_id",
        "billowers_version",
        ["transaction_id"],
        unique=False,
    )
    op.create_table(
        "person_version",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column(
            "project_id", sa.String(length=64), autoincrement=False, nullable=True
        ),
        sa.Column("name", sa.UnicodeText(), autoincrement=False, nullable=True),
        sa.Column("weight", sa.Float(), autoincrement=False, nullable=True),
        sa.Column("activated", sa.Boolean(), autoincrement=False, nullable=True),
        sa.Column(
            "transaction_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("end_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", "transaction_id"),
    )
    op.create_index(
        "ix_person_version_end_transaction_id",
        "person_version",
        ["end_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_person_version_operation_type",
        "person_version",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        "ix_person_version_transaction_id",
        "person_version",
        ["transaction_id"],
        unique=False,
    )
    op.create_table(
        "project_version",
        sa.Column("id", sa.String(length=64), autoincrement=False, nullable=False),
        sa.Column("name", sa.UnicodeText(), autoincrement=False, nullable=True),
        sa.Column(
            "password", sa.String(length=128), autoincrement=False, nullable=True
        ),
        sa.Column(
            "contact_email", sa.String(length=128), autoincrement=False, nullable=True
        ),
        sa.Column(
            "logging_preference",
            sa.Enum("DISABLED", "ENABLED", "RECORD_IP", name="loggingmode"),
            server_default="ENABLED",
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "transaction_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("end_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", "transaction_id"),
    )
    op.create_index(
        "ix_project_version_end_transaction_id",
        "project_version",
        ["end_transaction_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_version_operation_type",
        "project_version",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        "ix_project_version_transaction_id",
        "project_version",
        ["transaction_id"],
        unique=False,
    )
    op.create_table(
        "transaction",
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("remote_addr", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        with op.batch_alter_table("project", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "logging_preference",
                    sa.Enum("DISABLED", "ENABLED", "RECORD_IP", name="loggingmode"),
                    server_default="ENABLED",
                    nullable=False,
                ),
            )
    else:
        op.add_column(
            "project",
            sa.Column(
                "logging_preference",
                sa.Enum("DISABLED", "ENABLED", "RECORD_IP", name="loggingmode"),
                server_default="ENABLED",
                nullable=False,
            ),
        )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        with op.batch_alter_table("project", recreate="always") as batch_op:
            batch_op.drop_column("logging_preference")
    else:
        op.drop_column("project", "logging_preference")
    op.drop_table("transaction")
    op.drop_index(
        "ix_project_version_transaction_id", table_name="project_version"
    )
    op.drop_index(
        "ix_project_version_operation_type", table_name="project_version"
    )
    op.drop_index(
        "ix_project_version_end_transaction_id", table_name="project_version"
    )
    op.drop_table("project_version")
    op.drop_index("ix_person_version_transaction_id", table_name="person_version")
    op.drop_index("ix_person_version_operation_type", table_name="person_version")
    op.drop_index(
        "ix_person_version_end_transaction_id", table_name="person_version"
    )
    op.drop_table("person_version")
    op.drop_index(
        "ix_billowers_version_transaction_id", table_name="billowers_version"
    )
    op.drop_index(
        "ix_billowers_version_operation_type", table_name="billowers_version"
    )
    op.drop_index(
        "ix_billowers_version_end_transaction_id", table_name="billowers_version"
    )
    op.drop_table("billowers_version")
    op.drop_index("ix_bill_version_transaction_id", table_name="bill_version")
    op.drop_index("ix_bill_version_operation_type", table_name="bill_version")
    op.drop_index("ix_bill_version_end_transaction_id", table_name="bill_version")
    op.drop_table("bill_version")
    # ### end Alembic commands ###
