from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    database: Literal["ok"]
    trading_mode: Literal["paper"]


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    with request.app.state.database.session_factory() as session:
        session.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database="ok",
        trading_mode="paper",
    )
