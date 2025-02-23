"""hash project passwords

Revision ID: b78f8a8bdb16
Revises: f629c8ef4ab0
Create Date: 2017-12-17 11:45:44.783238

"""

# revision identifiers, used by Alembic.
revision = "b78f8a8bdb16"
down_revision = "f629c8ef4ab0"

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, UnicodeText, MetaData, Table, PrimaryKeyConstraint
from werkzeug.security import generate_password_hash


def upgrade():
    connection = op.get_bind()
    project_helper = Table(
        "project",
        MetaData(),
        Column("id", String(length=64), nullable=False),
        Column("name", UnicodeText(), nullable=True),
        Column("password", String(length=128), nullable=True),
        Column("contact_email", String(length=128), nullable=True),
        PrimaryKeyConstraint("id"),
    )
    for project in connection.execute(sa.select(project_helper)):
        connection.execute(
            sa.update(project_helper)
            .where(project_helper.c.name == project.name)
            .values(password=generate_password_hash(project.password))
        )


def downgrade():
    # Downgrade path is not possible, because information has been lost.
    pass
