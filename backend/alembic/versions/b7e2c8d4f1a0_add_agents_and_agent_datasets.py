"""add agents and agent_datasets tables

Revision ID: b7e2c8d4f1a0
Revises: a4d3e8f2719c
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7e2c8d4f1a0"
down_revision: Union[str, Sequence[str], None] = "a4d3e8f2719c"
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
agent_status_enum = postgresql.ENUM(
    "active",
    "archived",
    name="agent_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    user_facing_mode_enum.create(bind, checkfirst=True)
    agent_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "system_instructions",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "default_mode",
            user_facing_mode_enum,
            server_default=sa.text("'auto'"),
            nullable=False,
        ),
        sa.Column(
            "allowed_modes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[\"auto\", \"instant\"]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            agent_status_enum,
            server_default=sa.text("'active'"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "workspace_id"],
            ["workspaces.tenant_id", "workspaces.workspace_id"],
            name="fk_agents_tenant_workspace",
        ),
        sa.PrimaryKeyConstraint("agent_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "workspace_id",
            "name",
            name="uq_agents_workspace_name",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "agent_id",
            name="uq_agents_tenant_agent_id",
        ),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"], unique=False)
    op.create_index("ix_agents_workspace_id", "agents", ["workspace_id"], unique=False)
    op.create_index("ix_agents_status", "agents", ["status"], unique=False)

    op.create_table(
        "agent_datasets",
        sa.Column("attachment_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.agent_id"],
            name="fk_agent_datasets_tenant_agent",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "dataset_id"],
            ["namespaces.tenant_id", "namespaces.namespace_id"],
            name="fk_agent_datasets_tenant_dataset",
        ),
        sa.PrimaryKeyConstraint("attachment_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "agent_id",
            "dataset_id",
            name="uq_agent_datasets_tenant_agent_dataset",
        ),
    )
    op.create_index(
        "ix_agent_datasets_tenant_id",
        "agent_datasets",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_datasets_agent_id",
        "agent_datasets",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_datasets_dataset_id",
        "agent_datasets",
        ["dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_datasets_dataset_id", table_name="agent_datasets")
    op.drop_index("ix_agent_datasets_agent_id", table_name="agent_datasets")
    op.drop_index("ix_agent_datasets_tenant_id", table_name="agent_datasets")
    op.drop_table("agent_datasets")

    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_workspace_id", table_name="agents")
    op.drop_index("ix_agents_tenant_id", table_name="agents")
    op.drop_table("agents")

    bind = op.get_bind()
    agent_status_enum.drop(bind, checkfirst=True)
    user_facing_mode_enum.drop(bind, checkfirst=True)
