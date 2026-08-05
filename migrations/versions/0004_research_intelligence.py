"""research intelligence and signal outcomes

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in (
        "fundamental_score",
        "news_score",
        "market_regime_score",
        "sector_strength_score",
        "portfolio_score",
    ):
        op.add_column("signals", sa.Column(name, sa.Integer(), nullable=True))
    op.create_table(
        "research_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "instrument_id", sa.Integer(), sa.ForeignKey("instruments.id", ondelete="CASCADE")
        ),
        sa.Column("data_type", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("instrument_id", "data_type", "provider", name="uq_research_snapshot"),
    )
    op.create_index("ix_research_snapshots_data_type", "research_snapshots", ["data_type"])
    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.Integer(),
            sa.ForeignKey("instruments.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("average_cost", sa.Float(), nullable=False),
        sa.Column("target_weight", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "signal_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id", ondelete="CASCADE")),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=False),
        sa.Column("return_percentage", sa.Float(), nullable=False),
        sa.Column("maximum_favourable_excursion", sa.Float(), nullable=False),
        sa.Column("maximum_adverse_excursion", sa.Float(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signal_outcomes_signal_id", "signal_outcomes", ["signal_id"])


def downgrade() -> None:
    op.drop_table("signal_outcomes")
    op.drop_table("portfolio_holdings")
    op.drop_table("research_snapshots")
    for name in (
        "portfolio_score",
        "sector_strength_score",
        "market_regime_score",
        "news_score",
        "fundamental_score",
    ):
        op.drop_column("signals", name)
