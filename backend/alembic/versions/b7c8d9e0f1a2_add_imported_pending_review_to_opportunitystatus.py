"""add_imported_pending_review_to_opportunitystatus

Revision ID: b7c8d9e0f1a2
Revises: a5b9c3d4e5f6
Create Date: 2026-05-08 14:10:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a5b9c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the imported_pending_review value to the PostgreSQL opportunitystatus enum.

    This is required because OpportunityStatus is stored as a native PostgreSQL enum.
    The Python enum value alone is not enough in production databases.

    IF NOT EXISTS keeps the migration safe when the enum value was already added
    manually as an operational hotfix.
    """
    op.execute(
        "ALTER TYPE opportunitystatus "
        "ADD VALUE IF NOT EXISTS 'imported_pending_review'"
    )


def downgrade() -> None:
    """No-op downgrade.

    PostgreSQL does not safely support removing a single enum value without
    recreating the enum type and rewriting dependent columns. Since production
    data may already use imported_pending_review, downgrade is intentionally
    left as a no-op.
    """
    pass
