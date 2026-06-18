import abc


class UnitOfWork(abc.ABC):
    """Abstract transactional boundary.

    Concrete units of work live in each service's `adapters/database` layer.
    The domain only ever depends on this interface.
    """

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abc.abstractmethod
    async def commit(self) -> None:
        """Persist all changes made in this unit of work."""
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        """Discard all changes made in this unit of work."""
        raise NotImplementedError
