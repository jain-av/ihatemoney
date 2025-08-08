"""
SQLAlchemy 2.0 compatibility layer for IHateMoney migration.

This module provides wrapper functions and compatibility shims to ease the transition
from SQLAlchemy 1.x query patterns to SQLAlchemy 2.0 select/execute patterns.
During the migration period, these functions provide backward compatibility
while enabling gradual migration to new query patterns.
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload, joinedload
from flask_sqlalchemy import SQLAlchemy


def legacy_query_wrapper(model_class, db_session):
    """
    Provides a compatibility wrapper that mimics the old .query attribute behavior
    while using SQLAlchemy 2.0 patterns underneath.
    
    Args:
        model_class: The SQLAlchemy model class
        db_session: The database session
        
    Returns:
        A wrapper object that provides legacy query methods
    """
    
    class QueryWrapper:
        def __init__(self, model_class, session):
            self.model_class = model_class
            self.session = session
            self._select_stmt = select(model_class)
            
        def filter(self, *criterion):
            """Legacy filter method using SQLAlchemy 2.0 where clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.where(*criterion)
            return new_wrapper
            
        def filter_by(self, **kwargs):
            """Legacy filter_by method using SQLAlchemy 2.0 where clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            conditions = [getattr(self.model_class, k) == v for k, v in kwargs.items()]
            new_wrapper._select_stmt = self._select_stmt.where(*conditions)
            return new_wrapper
            
        def join(self, *args, **kwargs):
            """Legacy join method using SQLAlchemy 2.0 join clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.join(*args, **kwargs)
            return new_wrapper
            
        def options(self, *args):
            """Legacy options method for eager loading"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.options(*args)
            return new_wrapper
            
        def order_by(self, *criterion):
            """Legacy order_by method using SQLAlchemy 2.0 order_by clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.order_by(*criterion)
            return new_wrapper
            
        def limit(self, limit):
            """Legacy limit method using SQLAlchemy 2.0 limit clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.limit(limit)
            return new_wrapper
            
        def offset(self, offset):
            """Legacy offset method using SQLAlchemy 2.0 offset clause"""
            new_wrapper = QueryWrapper(self.model_class, self.session)
            new_wrapper._select_stmt = self._select_stmt.offset(offset)
            return new_wrapper
            
        def get(self, primary_key):
            """Legacy get method using SQLAlchemy 2.0 session.get"""
            return self.session.get(self.model_class, primary_key)
            
        def all(self):
            """Legacy all method using SQLAlchemy 2.0 execute().scalars().all()"""
            result = self.session.execute(self._select_stmt)
            return result.scalars().all()
            
        def first(self):
            """Legacy first method using SQLAlchemy 2.0 execute().scalars().first()"""
            result = self.session.execute(self._select_stmt)
            return result.scalars().first()
            
        def one(self):
            """Legacy one method using SQLAlchemy 2.0 execute().scalars().one()"""
            result = self.session.execute(self._select_stmt)
            return result.scalars().one()
            
        def one_or_none(self):
            """Legacy one_or_none method using SQLAlchemy 2.0 execute().scalars().one_or_none()"""
            result = self.session.execute(self._select_stmt)
            return result.scalars().one_or_none()
            
        def count(self):
            """Legacy count method using SQLAlchemy 2.0 scalar() with func.count()"""
            from sqlalchemy.sql import func
            count_stmt = select(func.count()).select_from(self._select_stmt.subquery())
            result = self.session.execute(count_stmt)
            return result.scalar()
    
    return QueryWrapper(model_class, db_session)


def convert_legacy_subqueryload_to_selectinload(loader):
    """
    Convert legacy subqueryload options to SQLAlchemy 2.0 selectinload.
    
    Args:
        loader: The legacy subqueryload option
        
    Returns:
        SQLAlchemy 2.0 compatible selectinload option
    """
    # This is a simple conversion - in practice you might need more sophisticated logic
    if hasattr(loader, 'path'):
        return selectinload(loader.path[0])
    return selectinload(loader)


def legacy_bulk_insert_mappings(session, model_class, mappings):
    """
    Compatibility wrapper for bulk_insert_mappings using SQLAlchemy 2.0 patterns.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        mappings: List of dictionaries with column mappings
    """
    # In SQLAlchemy 2.0, bulk_insert_mappings is deprecated
    # Use session.execute(insert(...).values(...)) instead
    from sqlalchemy import insert
    
    if mappings:
        stmt = insert(model_class).values(mappings)
        session.execute(stmt)


def legacy_bulk_update_mappings(session, model_class, mappings):
    """
    Compatibility wrapper for bulk_update_mappings using SQLAlchemy 2.0 patterns.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class  
        mappings: List of dictionaries with column mappings including primary key
    """
    # In SQLAlchemy 2.0, bulk_update_mappings is deprecated
    from sqlalchemy.dialects import sqlite, postgresql, mysql
    from sqlalchemy import update as sql_update
    
    if mappings:
        # Use bulk update with multiple parameter sets
        stmt = sql_update(model_class)
        session.execute(stmt, mappings)


def create_legacy_query_property(db_session):
    """
    Create a property that mimics the legacy .query attribute behavior
    for SQLAlchemy model classes during the transition period.
    
    Args:
        db_session: The database session to use for queries
        
    Returns:
        A property that returns a QueryWrapper when accessed
    """
    def query_property(cls):
        return legacy_query_wrapper(cls, db_session)
    
    return property(lambda self: query_property(self.__class__))


# Common query pattern wrappers
def get_or_404(session, model_class, primary_key):
    """
    Get an object by primary key or raise 404 error.
    Compatibility wrapper for the common get_or_404 pattern.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        primary_key: Primary key value
        
    Returns:
        The model instance or raises 404
    """
    from flask import abort
    
    obj = session.get(model_class, primary_key)
    if obj is None:
        abort(404)
    return obj


def filter_by_project(session, model_class, project_id, **filters):
    """
    Common pattern for filtering models by project with additional filters.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        project_id: Project ID to filter by
        **filters: Additional filter conditions
        
    Returns:
        Query result
    """
    stmt = select(model_class).where(model_class.project_id == project_id)
    
    for attr, value in filters.items():
        stmt = stmt.where(getattr(model_class, attr) == value)
        
    result = session.execute(stmt)
    return result.scalars()


def get_by_name_and_project(session, model_class, name, project):
    """
    Common pattern for getting a model by name within a specific project.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        name: Name to search for
        project: Project instance
        
    Returns:
        Model instance or None
    """
    stmt = select(model_class).where(
        model_class.name == name,
        model_class.project_id == project.id
    )
    result = session.execute(stmt)
    return result.scalars().one_or_none()


def get_by_names_and_project(session, model_class, names, project):
    """
    Common pattern for getting multiple models by names within a specific project.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        names: List of names to search for
        project: Project instance
        
    Returns:
        List of model instances
    """
    stmt = select(model_class).where(
        model_class.name.in_(names),
        model_class.project_id == project.id
    )
    result = session.execute(stmt)
    return result.scalars().all()


# SQLAlchemy 2.0 imports for convenience
__all__ = [
    'DeclarativeBase',
    'Mapped', 
    'mapped_column',
    'select',
    'update', 
    'delete',
    'selectinload',
    'joinedload',
    'legacy_query_wrapper',
    'convert_legacy_subqueryload_to_selectinload',
    'legacy_bulk_insert_mappings',
    'legacy_bulk_update_mappings', 
    'create_legacy_query_property',
    'get_or_404',
    'filter_by_project',
    'get_by_name_and_project',
    'get_by_names_and_project'
]