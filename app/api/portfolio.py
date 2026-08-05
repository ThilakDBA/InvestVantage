from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database.models import Instrument, PortfolioHolding

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio research"])


class HoldingInput(BaseModel):
    symbol: str
    quantity: float = Field(ge=0)
    average_cost: float = Field(ge=0)
    target_weight: float | None = Field(default=None, ge=0, le=100)


@router.put("/holdings", response_model=dict)
def upsert_holding(payload: HoldingInput, request: Request) -> dict:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(
            select(Instrument).where(Instrument.symbol == payload.symbol.upper())
        )
        if instrument is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
        holding = session.scalar(
            select(PortfolioHolding).where(PortfolioHolding.instrument_id == instrument.id)
        )
        if holding is None:
            holding = PortfolioHolding(instrument_id=instrument.id)
            session.add(holding)
        holding.quantity = payload.quantity
        holding.average_cost = payload.average_cost
        holding.target_weight = payload.target_weight
        session.commit()
        return {"symbol": instrument.symbol, **payload.model_dump(exclude={"symbol"})}


@router.get("/exposure", response_model=dict)
def portfolio_exposure(request: Request) -> dict:
    with request.app.state.database.session_factory() as session:
        rows = session.execute(
            select(PortfolioHolding, Instrument)
            .join(Instrument, Instrument.id == PortfolioHolding.instrument_id)
            .where(PortfolioHolding.quantity > 0)
        ).all()
        values = [
            {
                "symbol": instrument.symbol,
                "sector": instrument.sector or "Unknown",
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "cost_value": holding.quantity * holding.average_cost,
            }
            for holding, instrument in rows
        ]
        total = sum(row["cost_value"] for row in values)
        sectors: dict[str, float] = defaultdict(float)
        for row in values:
            sectors[row["sector"]] += row["cost_value"]
        exposure = {
            sector: round(value / total * 100, 2) if total else 0
            for sector, value in sectors.items()
        }
        warnings = [
            f"{sector} exposure exceeds the 25% research guardrail"
            for sector, weight in exposure.items()
            if weight > 25
        ]
        return {"holdings": values, "sector_exposure": exposure, "warnings": warnings}
