"""Add explainable strategy signals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("strategy_name", sa.String(128), nullable=False),
        sa.Column("strategy_version", sa.String(32), nullable=False),
        sa.Column("recommendation", sa.String(16), nullable=False),
        sa.Column("technical_score", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("target_price", sa.Float(), nullable=True),
        sa.Column("holding_period_days", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("positive_factors", sa.JSON(), nullable=False),
        sa.Column("negative_factors", sa.JSON(), nullable=False),
        sa.Column("invalidation_conditions", sa.JSON(), nullable=False),
        sa.Column("data_completeness", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_instrument_id", "signals", ["instrument_id"])
    op.create_index("ix_signals_recommendation", "signals", ["recommendation"])
    op.create_index("ix_signals_generated_at", "signals", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_signals_generated_at", table_name="signals")
    op.drop_index("ix_signals_recommendation", table_name="signals")
    op.drop_index("ix_signals_instrument_id", table_name="signals")
    op.drop_table("signals")
