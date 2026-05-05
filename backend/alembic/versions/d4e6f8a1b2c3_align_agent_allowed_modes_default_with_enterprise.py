"""align agent allowed modes default with enterprise

Revision ID: d4e6f8a1b2c3
Revises: a1c3d5e7f9b2
Create Date: 2026-04-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4e6f8a1b2c3"
down_revision: Union[str, Sequence[str], None] = "a1c3d5e7f9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agents",
        "allowed_modes",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'[\"auto\", \"instant\"]'::jsonb"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "agents",
        "allowed_modes",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'[\"auto\", \"instant\"]'::jsonb"),
        existing_nullable=False,
    )
