from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single shared SQLAlchemy declarative base for every NeuroAtlas service.

    All ORM models across services inherit from this class so they register on
    one shared ``MetaData``. Housekeeper's Alembic autogenerate imports this Base
    to discover every table from a single source of truth.
    """
