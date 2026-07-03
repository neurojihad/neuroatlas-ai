import abc

from common.core.entities.user import UserInfo


class UserRepository(abc.ABC):
    """Port for shadow user persistence."""

    @abc.abstractmethod
    async def upsert_from_user_info(self, user_info: UserInfo, *, display_name: str | None = None) -> None:
        """Insert or update a user row keyed by Keycloak subject."""
