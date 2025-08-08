"""
SQLAlchemy 2.0 compatibility layer for IHateMoney migration.

This module provides compatibility imports and wrapper functions to ease the
transition from SQLAlchemy 1.x patterns to SQLAlchemy 2.0 patterns.
"""

# SQLAlchemy 2.0 modern typing imports
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLAlchemy 2.0 query syntax imports
from sqlalchemy import select, update, delete

# Additional SQLAlchemy 2.0 imports for modern patterns
from sqlalchemy.orm import selectinload, joinedload, subqueryload
from sqlalchemy import func
from sqlalchemy.sql import Select

# Compatibility wrapper functions for legacy query patterns during transition period
def execute_select(session, stmt):
    """
    Execute a select statement and return the result.
    Wrapper to standardize select execution patterns.
    """
    return session.execute(stmt)


def scalar_one_or_none(session, stmt):
    """
    Execute a select statement and return scalar result or None.
    Replaces .query.filter(...).first() patterns.
    """
    return session.execute(stmt).scalar_one_or_none()


def scalars_all(session, stmt):
    """
    Execute a select statement and return all scalar results.
    Replaces .query.filter(...).all() patterns.
    """
    return session.execute(stmt).scalars().all()


def count_records(session, model_class, *filters):
    """
    Count records with optional filters.
    Replaces .query.filter(...).count() patterns.
    """
    stmt = select(func.count()).select_from(model_class)
    if filters:
        stmt = stmt.where(*filters)
    return session.execute(stmt).scalar()


def exists_record(session, model_class, *filters):
    """
    Check if record exists with optional filters.
    Replaces .query.filter(...).exists() patterns.
    """
    from sqlalchemy import exists
    stmt = select(exists().where(*filters)) if filters else select(exists().select_from(model_class))
    return session.execute(stmt).scalar()