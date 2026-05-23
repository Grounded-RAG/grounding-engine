"""add team members, audit logs, and billing subscriptions

Revision ID: a1b2c3d4e5f6
Revises: d4e6f8a1b2c3
Create Date: 2026-05-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d4e6f8a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    workspacememberrole = postgresql.ENUM(
        "admin", "member", "viewer", name="workspacememberrole", create_type=False
    )
    workspacememberstatus = postgresql.ENUM(
        "pending", "active", "removed", name="workspacememberstatus", create_type=False
    )
    billingsubscriptionstatus = postgresql.ENUM(
        "active", "past_due", "canceled", "trialing",
        name="billingsubscriptionstatus", create_type=False,
    )

    op.execute("CREATE TYPE workspacememberrole AS ENUM ('admin', 'member', 'viewer')")
    op.execute("CREATE TYPE workspacememberstatus AS ENUM ('pending', 'active', 'removed')")
    op.execute(
        "CREATE TYPE billingsubscriptionstatus AS ENUM "
        "('active', 'past_due', 'canceled', 'trialing')"
    )

    # workspace_members
    op.create_table(
        "workspace_members",
        sa.Column("member_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            workspacememberrole,
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "status",
            workspacememberstatus,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint(
            "workspace_id", "email", name="uq_workspace_members_workspace_email"
        ),
    )
    op.create_index(
        "ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_workspace_members_tenant_id", "workspace_members", ["tenant_id"], unique=False
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("actor_key_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.workspace_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["actor_key_id"], ["api_keys.key_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("ix_audit_logs_workspace_id", "audit_logs", ["workspace_id"], unique=False)
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    # billing_subscriptions
    op.create_table(
        "billing_subscriptions",
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False, unique=True),
        sa.Column(
            "plan",
            postgresql.ENUM(
                "free", "pro", "business", "enterprise",
                name="subscriptionplan", create_type=False,
            ),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "status",
            billingsubscriptionstatus,
            nullable=False,
            server_default="active",
        ),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subscription_id"),
    )
    op.create_index(
        "ix_billing_subscriptions_tenant_id",
        "billing_subscriptions",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_billing_subscriptions_tenant_id", table_name="billing_subscriptions")
    op.drop_table("billing_subscriptions")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_workspace_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_workspace_members_tenant_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")

    op.execute("DROP TYPE IF EXISTS billingsubscriptionstatus")
    op.execute("DROP TYPE IF EXISTS workspacememberstatus")
    op.execute("DROP TYPE IF EXISTS workspacememberrole")
