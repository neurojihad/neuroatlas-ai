from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common.core.ports.uow import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Reusable async SQLAlchemy unit of work.

    Subclasses attach their repositories (built from ``self.session``) inside an
    overridden ``__aenter__`` after calling ``super().__aenter__()``. The base
    opens a session on entry, commits on a clean exit / rolls back on exception,
    and always closes the session.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the session factory; the session is opened lazily on entry."""

        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        """Open a new session for the duration of the transaction."""

        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Commit or roll back, then always close the session."""

        try:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    @property
    def session(self) -> AsyncSession:
        """Return the active session, raising if used outside ``async with``."""

        if self._session is None:
            raise RuntimeError("Unit of work session accessed outside an `async with` block.")
        return self._session

    async def commit(self) -> None:
        """Persist all changes made in this unit of work."""

        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        """Discard all changes made in this unit of work."""

        if self._session is not None:
            await self._session.rollback()
