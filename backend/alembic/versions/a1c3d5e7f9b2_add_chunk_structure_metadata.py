"""add chunk structure metadata

Revision ID: a1c3d5e7f9b2
Revises: c91a8d7e4b2f
Create Date: 2026-04-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c3d5e7f9b2"
down_revision: Union[str, Sequence[str], None] = "c91a8d7e4b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("section_title", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("section_slug", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "chunk_role",
            sa.String(length=32),
            nullable=False,
            server_default="body",
        ),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "starts_with_heading",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "is_list_block",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_document_chunks_section_slug",
        "document_chunks",
        ["section_slug"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_section_slug", table_name="document_chunks")
    op.drop_column("document_chunks", "is_list_block")
    op.drop_column("document_chunks", "starts_with_heading")
    op.drop_column("document_chunks", "chunk_role")
    op.drop_column("document_chunks", "section_slug")
    op.drop_column("document_chunks", "section_title")
