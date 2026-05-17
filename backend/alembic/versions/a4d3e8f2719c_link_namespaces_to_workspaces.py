"""link namespaces to workspaces

Revision ID: a4d3e8f2719c
Revises: f8b92d1a4c3e
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4d3e8f2719c"
down_revision: Union[str, Sequence[str], None] = "f8b92d1a4c3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_workspaces_tenant_workspace_id",
        "workspaces",
        ["tenant_id", "workspace_id"],
    )
    op.add_column("namespaces", sa.Column("workspace_id", sa.UUID(), nullable=True))
    op.create_index("ix_namespaces_workspace_id", "namespaces", ["workspace_id"], unique=False)
    op.create_foreign_key(
        "fk_namespaces_tenant_workspace",
        "namespaces",
        "workspaces",
        ["tenant_id", "workspace_id"],
        ["tenant_id", "workspace_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_namespaces_tenant_workspace", "namespaces", type_="foreignkey")
    op.drop_index("ix_namespaces_workspace_id", table_name="namespaces")
    op.drop_column("namespaces", "workspace_id")
    op.drop_constraint(
        "uq_workspaces_tenant_workspace_id",
        "workspaces",
        type_="unique",
    )
