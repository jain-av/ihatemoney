"""
SQLAlchemy 2.0 Compatibility Layer

This module provides compatibility imports and wrapper functions to ease the
transition from SQLAlchemy 1.x patterns to SQLAlchemy 2.0 patterns.
"""

# SQLAlchemy 2.0 modern typing imports
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLAlchemy 2.0 query syntax patterns
from sqlalchemy import select, update, delete

# Additional imports for modern ORM patterns
from sqlalchemy.orm import selectinload, joinedload, subqueryload
from sqlalchemy import func


# Compatibility wrapper functions for legacy query patterns during transition
def legacy_query_to_select(model_class, *conditions):
    """
    Convert legacy Model.query.filter(...) patterns to select(...).where(...)
    
    Args:
        model_class: The SQLAlchemy model class
        *conditions: Filter conditions
        
    Returns:
        SQLAlchemy select statement
    """
    stmt = select(model_class)
    for condition in conditions:
        stmt = stmt.where(condition)
    return stmt


def execute_scalar_query(session, model_class, *conditions):
    """
    Execute a query and return a single scalar result
    
    Args:
        session: Database session
        model_class: The SQLAlchemy model class
        *conditions: Filter conditions
        
    Returns:
        Single model instance or None
    """
    stmt = legacy_query_to_select(model_class, *conditions)
    return session.execute(stmt).scalar_one_or_none()


def execute_scalars_query(session, model_class, *conditions):
    """
    Execute a query and return multiple scalar results
    
    Args:
        session: Database session
        model_class: The SQLAlchemy model class
        *conditions: Filter conditions
        
    Returns:
        List of model instances
    """
    stmt = legacy_query_to_select(model_class, *conditions)
    return session.execute(stmt).scalars().all()