"""Migrate negative weights

Revision ID: a67119aa3ee5
Revises: afbf27e6ef20
Create Date: 2018-12-25 18:34:20.220844

"""

# revision identifiers, used by Alembic.
revision = "a67119aa3ee5"
down_revision = "afbf27e6ef20"

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, UnicodeText, Boolean, Float, ForeignKeyConstraint, PrimaryKeyConstraint, MetaData, Table


# Snapshot of the person table
person_helper = Table(
    "person",
    MetaData(),
    Column("id", Integer(), nullable=False),
    Column("project_id", String(length=64), nullable=True),
    Column("name", UnicodeText(), nullable=True),
    Column("activated", Boolean(), nullable=True),
    Column("weight", Float(), nullable=True),
    ForeignKeyConstraint(["project_id"], ["project.id"]),
    PrimaryKeyConstraint("id"),
)


def upgrade():
    op.execute(
        person_helper.update().where(person_helper.c.weight <= 0).values(weight=1)
    )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
