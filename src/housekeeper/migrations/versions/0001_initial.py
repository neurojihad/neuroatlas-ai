"""initial empty baseline

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-19 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op baseline. Service ORM models land in later phases."""


def downgrade() -> None:
    """No-op baseline."""
