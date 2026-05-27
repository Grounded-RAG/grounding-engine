"""add feedback fields to query traces

Revision ID: c2e4f6a8b1d3
Revises: b3f1d7c2a9e4
Create Date: 2026-05-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e4f6a8b1d3"
down_revision: Union[str, None] = "b3f1d7c2a9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "query_traces",
        sa.Column("feedback_rating", sa.String(20), nullable=True),
    )
    op.add_column(
        "query_traces",
        sa.Column(
            "feedback_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=None,
        ),
    )
    op.add_column(
        "query_traces",
        sa.Column("feedback_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("query_traces", "feedback_text")
    op.drop_column("query_traces", "feedback_reasons")
    op.drop_column("query_traces", "feedback_rating")
