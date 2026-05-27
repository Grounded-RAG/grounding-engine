"""add invitation token hash to workspace members

Revision ID: b3f1d7c2a9e4
Revises: a1b2c3d4e5f6
Create Date: 2026-05-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f1d7c2a9e4"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_members",
        sa.Column("invitation_token_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_workspace_members_invitation_token_hash",
        "workspace_members",
        ["invitation_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_members_invitation_token_hash",
        table_name="workspace_members",
    )
    op.drop_column("workspace_members", "invitation_token_hash")
