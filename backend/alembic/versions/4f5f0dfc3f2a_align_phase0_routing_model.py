"""align phase 0 routing model

Revision ID: 4f5f0dfc3f2a
Revises: 903d46f03385
Create Date: 2026-03-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4f5f0dfc3f2a"
down_revision: Union[str, Sequence[str], None] = "903d46f03385"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_tier_enum = postgresql.ENUM(
    "standard",
    "enterprise",
    "critical",
    name="plan_tier_enum",
    create_type=False,
)
subscription_plan_enum = postgresql.ENUM(
    "free",
    "pro",
    "business",
    "enterprise",
    name="subscription_plan_enum",
    create_type=False,
)
execution_tier_enum = postgresql.ENUM(
    "standard",
    "enterprise",
    "critical",
    name="execution_tier_enum",
    create_type=False,
)
freshness_profile_enum = postgresql.ENUM(
    "stable",
    "balanced",
    "aggressive",
    name="freshness_profile_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    subscription_plan_enum.create(bind, checkfirst=True)
    execution_tier_enum.create(bind, checkfirst=True)
    freshness_profile_enum.create(bind, checkfirst=True)

    op.add_column(
        "tenants",
        sa.Column("subscription_plan", subscription_plan_enum, nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("max_execution_tier", execution_tier_enum, nullable=True),
    )
    op.execute(
        """
        update tenants
        set
            subscription_plan = case plan_tier::text
                when 'standard' then 'free'::subscription_plan_enum
                when 'enterprise' then 'pro'::subscription_plan_enum
                when 'critical' then 'enterprise'::subscription_plan_enum
            end,
            max_execution_tier = plan_tier::text::execution_tier_enum
        """
    )
    op.alter_column("tenants", "subscription_plan", nullable=False)
    op.alter_column("tenants", "max_execution_tier", nullable=False)
    op.drop_column("tenants", "plan_tier")

    op.add_column(
        "namespaces",
        sa.Column(
            "domain",
            sa.String(length=100),
            server_default=sa.text("'general'"),
            nullable=False,
        ),
    )
    op.add_column(
        "namespaces",
        sa.Column(
            "freshness_profile",
            freshness_profile_enum,
            server_default=sa.text("'balanced'"),
            nullable=False,
        ),
    )
    op.add_column(
        "namespaces",
        sa.Column(
            "min_execution_tier",
            execution_tier_enum,
            server_default=sa.text("'standard'"),
            nullable=False,
        ),
    )
    op.add_column(
        "namespaces",
        sa.Column(
            "allow_web_fallback",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "namespaces",
        sa.Column(
            "allow_internal_model_retrieval",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_namespaces_domain_non_empty",
        "namespaces",
        "char_length(domain) > 0",
    )

    op.add_column(
        "query_traces",
        sa.Column("namespace_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "query_traces",
        sa.Column("requested_tier", execution_tier_enum, nullable=True),
    )
    op.add_column(
        "query_traces",
        sa.Column("router_recommendation", execution_tier_enum, nullable=True),
    )
    op.add_column(
        "query_traces",
        sa.Column("effective_tier", execution_tier_enum, nullable=True),
    )
    op.add_column(
        "query_traces",
        sa.Column("routing_reason", sa.Text(), nullable=True),
    )
    op.execute(
        """
        update query_traces
        set
            router_recommendation = tier::text::execution_tier_enum,
            effective_tier = tier::text::execution_tier_enum,
            routing_reason = 'migrated from pre-routing trace schema'
        """
    )
    op.alter_column("query_traces", "router_recommendation", nullable=False)
    op.alter_column("query_traces", "effective_tier", nullable=False)
    op.alter_column("query_traces", "routing_reason", nullable=False)
    op.create_foreign_key(
        "fk_query_traces_tenant_namespace",
        "query_traces",
        "namespaces",
        ["tenant_id", "namespace_id"],
        ["tenant_id", "namespace_id"],
    )
    op.create_index(
        "ix_query_traces_namespace_id",
        "query_traces",
        ["namespace_id"],
        unique=False,
    )
    op.drop_column("query_traces", "tier")

    plan_tier_enum.drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    plan_tier_enum.create(bind, checkfirst=True)

    op.add_column(
        "query_traces",
        sa.Column("tier", plan_tier_enum, nullable=True),
    )
    op.execute(
        """
        update query_traces
        set tier = effective_tier::text::plan_tier_enum
        """
    )
    op.alter_column("query_traces", "tier", nullable=False)
    op.drop_index("ix_query_traces_namespace_id", table_name="query_traces")
    op.drop_constraint(
        "fk_query_traces_tenant_namespace",
        "query_traces",
        type_="foreignkey",
    )
    op.drop_column("query_traces", "routing_reason")
    op.drop_column("query_traces", "effective_tier")
    op.drop_column("query_traces", "router_recommendation")
    op.drop_column("query_traces", "requested_tier")
    op.drop_column("query_traces", "namespace_id")

    op.drop_constraint("ck_namespaces_domain_non_empty", "namespaces", type_="check")
    op.drop_column("namespaces", "allow_internal_model_retrieval")
    op.drop_column("namespaces", "allow_web_fallback")
    op.drop_column("namespaces", "min_execution_tier")
    op.drop_column("namespaces", "freshness_profile")
    op.drop_column("namespaces", "domain")

    op.add_column(
        "tenants",
        sa.Column("plan_tier", plan_tier_enum, nullable=True),
    )
    op.execute(
        """
        update tenants
        set plan_tier = max_execution_tier::text::plan_tier_enum
        """
    )
    op.alter_column("tenants", "plan_tier", nullable=False)
    op.drop_column("tenants", "max_execution_tier")
    op.drop_column("tenants", "subscription_plan")

    freshness_profile_enum.drop(bind, checkfirst=True)
    execution_tier_enum.drop(bind, checkfirst=True)
    subscription_plan_enum.drop(bind, checkfirst=True)
