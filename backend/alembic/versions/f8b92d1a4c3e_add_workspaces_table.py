"""add workspaces table

Revision ID: f8b92d1a4c3e
Revises: 8e9a2fd1c4b1
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8b92d1a4c3e"
down_revision: Union[str, Sequence[str], None] = "8e9a2fd1c4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.CheckConstraint("char_length(name) > 0", name="ck_workspaces_name_non_empty"),
        sa.CheckConstraint("char_length(slug) > 0", name="ck_workspaces_slug_non_empty"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("workspace_id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_workspaces_tenant_name"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_workspaces_tenant_slug"),
    )
    op.create_index("ix_workspaces_tenant_id", "workspaces", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspaces_tenant_id", table_name="workspaces")
    op.drop_table("workspaces")
