"""add_ai_provider_and_prompt_profile_to_message_drafts

Revision ID: a5b9c3d4e5f6
Revises: 4f8c8a1e2d3b
Create Date: 2026-05-06 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "a5b9c3d4e5f6"
down_revision: Union[str, None] = "4f8c8a1e2d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "message_drafts",
        sa.Column("ai_provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "message_drafts",
        sa.Column("prompt_profile", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("message_drafts", "prompt_profile")
    op.drop_column("message_drafts", "ai_provider")
