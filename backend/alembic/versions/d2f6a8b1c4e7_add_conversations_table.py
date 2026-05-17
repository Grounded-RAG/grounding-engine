"""add conversations table

Revision ID: d2f6a8b1c4e7
Revises: b7e2c8d4f1a0
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d2f6a8b1c4e7"
down_revision: Union[str, Sequence[str], None] = "b7e2c8d4f1a0"
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

    op.create_table(
        "conversations",
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("created_by_api_key_id", sa.UUID(), nullable=True),
        sa.Column(
            "title",
            sa.String(length=255),
            server_default=sa.text("'New Chat'"),
            nullable=False,
        ),
        sa.Column(
            "last_used_mode",
            user_facing_mode_enum,
            server_default=sa.text("'auto'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(title) > 0",
            name="ck_conversations_title_non_empty",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["created_by_api_key_id"], ["api_keys.key_id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "workspace_id"],
            ["workspaces.tenant_id", "workspaces.workspace_id"],
            name="fk_conversations_tenant_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.agent_id"],
            name="fk_conversations_tenant_agent",
        ),
        sa.PrimaryKeyConstraint("conversation_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "conversation_id",
            name="uq_conversations_tenant_conversation_id",
        ),
    )
    op.create_index(
        "ix_conversations_tenant_id",
        "conversations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_workspace_id",
        "conversations",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_agent_id",
        "conversations",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_updated_at",
        "conversations",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_index("ix_conversations_agent_id", table_name="conversations")
    op.drop_index("ix_conversations_workspace_id", table_name="conversations")
    op.drop_index("ix_conversations_tenant_id", table_name="conversations")
    op.drop_table("conversations")
