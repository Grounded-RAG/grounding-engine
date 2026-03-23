"""scope document checksum uniqueness to dataset

Revision ID: c91a8d7e4b2f
Revises: f3c7a9d2b6e4
Create Date: 2026-03-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c91a8d7e4b2f"
down_revision: Union[str, Sequence[str], None] = "f3c7a9d2b6e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_documents_tenant_checksum", "documents", type_="unique")
    op.create_unique_constraint(
        "uq_documents_tenant_namespace_checksum",
        "documents",
        ["tenant_id", "namespace_id", "checksum"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_tenant_namespace_checksum",
        "documents",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_documents_tenant_checksum",
        "documents",
        ["tenant_id", "checksum"],
    )
