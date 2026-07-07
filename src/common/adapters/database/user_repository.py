from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.adapters.database.models.user import UserORM
from common.core.entities.user import UserInfo
from common.core.ports.user_repository import UserRepository


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of shadow user upsert."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_from_user_info(self, user_info: UserInfo, *, display_name: str | None = None) -> None:
        keycloak_sub = user_info.user_id.removeprefix("usr_")
        stmt = (
            pg_insert(UserORM)
            .values(
                id=user_info.user_id,
                keycloak_sub=keycloak_sub,
                email=user_info.email,
                display_name=display_name,
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[UserORM.keycloak_sub],
                set_={
                    "email": user_info.email,
                    "display_name": display_name,
                    "updated_at": func.now(),
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
