"""add agent chat fields to query traces

Revision ID: f3c7a9d2b6e4
Revises: e4a9c6b2f0d1
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f3c7a9d2b6e4"
down_revision: Union[str, Sequence[str], None] = "e4a9c6b2f0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_facing_mode_enum = postgresql.ENUM(
    "auto",
    "instant",
    "thinking",
    "verified",
    name="user_facing_mode_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    user_facing_mode_enum.create(bind, checkfirst=True)

    op.add_column("query_traces", sa.Column("agent_id", sa.UUID(), nullable=True))
    op.add_column("query_traces", sa.Column("conversation_id", sa.UUID(), nullable=True))
    op.add_column(
        "query_traces",
        sa.Column("selected_mode", user_facing_mode_enum, nullable=True),
    )

    op.create_foreign_key(
        "fk_query_traces_tenant_agent",
        "query_traces",
        "agents",
        ["tenant_id", "agent_id"],
        ["tenant_id", "agent_id"],
    )
    op.create_foreign_key(
        "fk_query_traces_tenant_conversation",
        "query_traces",
        "conversations",
        ["tenant_id", "conversation_id"],
        ["tenant_id", "conversation_id"],
    )
    op.create_index("ix_query_traces_agent_id", "query_traces", ["agent_id"], unique=False)
    op.create_index(
        "ix_query_traces_conversation_id",
        "query_traces",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_query_traces_conversation_id", table_name="query_traces")
    op.drop_index("ix_query_traces_agent_id", table_name="query_traces")
    op.drop_constraint("fk_query_traces_tenant_conversation", "query_traces", type_="foreignkey")
    op.drop_constraint("fk_query_traces_tenant_agent", "query_traces", type_="foreignkey")
    op.drop_column("query_traces", "selected_mode")
    op.drop_column("query_traces", "conversation_id")
    op.drop_column("query_traces", "agent_id")
