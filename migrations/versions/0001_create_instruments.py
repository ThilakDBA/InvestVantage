"""Create the initial instrument catalogue."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "exchange", name="uq_instrument_symbol_exchange"),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_instruments_symbol", table_name="instruments")
    op.drop_table("instruments")
