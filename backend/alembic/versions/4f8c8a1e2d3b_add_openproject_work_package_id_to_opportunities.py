"""add_openproject_work_package_id_to_opportunities

Revision ID: 4f8c8a1e2d3b
Revises: 19ff03ff2ceb
Create Date: 2026-05-06 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "4f8c8a1e2d3b"
down_revision: Union[str, None] = "19ff03ff2ceb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("openproject_work_package_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("opportunities", "openproject_work_package_id")
