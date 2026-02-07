"""
Database session management utilities.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from src.db.base import async_session_maker, TimestampMixin


class SessionManager:
    """Manager for database session operations."""

    @staticmethod
    async def get_session() -> AsyncSession:
        """Get a new database session."""
        return async_session_maker()

    @staticmethod
    async def execute_select(
        statement: select,
        session: Optional[AsyncSession] = None,
    ) -> list:
        """
        Execute a SELECT statement.

        Args:
            statement: SQLAlchemy select statement
            session: Optional session to use (creates new if not provided)

        Returns:
            List of results
        """
        should_close = session is None
        if should_close:
            session = await SessionManager.get_session()

        try:
            result = await session.execute(statement)
            return result.scalars().all()
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def execute_get_one(
        statement: select,
        session: Optional[AsyncSession] = None,
    ) -> Optional[object]:
        """
        Execute a SELECT statement and return one result.

        Args:
            statement: SQLAlchemy select statement
            session: Optional session to use (creates new if not provided)

        Returns:
            Single result or None
        """
        should_close = session is None
        if should_close:
            session = await SessionManager.get_session()

        try:
            result = await session.execute(statement)
            return result.scalar_one_or_none()
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def execute_update(
        statement: update,
        session: Optional[AsyncSession] = None,
        commit: bool = True,
    ) -> int:
        """
        Execute an UPDATE statement.

        Args:
            statement: SQLAlchemy update statement
            session: Optional session to use
            commit: Whether to commit the transaction

        Returns:
            Number of rows affected
        """
        should_close = session is None
        if should_close:
            session = await SessionManager.get_session()

        try:
            result = await session.execute(statement)
            if commit:
                await session.commit()
            return result.rowcount
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def execute_delete(
        statement: delete,
        session: Optional[AsyncSession] = None,
        commit: bool = True,
    ) -> int:
        """
        Execute a DELETE statement.

        Args:
            statement: SQLAlchemy delete statement
            session: Optional session to use
            commit: Whether to commit the transaction

        Returns:
            Number of rows affected
        """
        should_close = session is None
        if should_close:
            session = await SessionManager.get_session()

        try:
            result = await session.execute(statement)
            if commit:
                await session.commit()
            return result.rowcount
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def execute_insert(
        instance,
        session: Optional[AsyncSession] = None,
        commit: bool = True,
    ) -> object:
        """
        Insert a new instance.

        Args:
            instance: Model instance to insert
            session: Optional session to use
            commit: Whether to commit the transaction

        Returns:
            The inserted instance
        """
        should_close = session is None
        if should_close:
            session = await SessionManager.get_session()

        try:
            session.add(instance)
            if commit:
                await session.commit()
                await session.refresh(instance)
            return instance
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            if should_close:
                await session.close()
