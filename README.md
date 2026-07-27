# InvestVantage

InvestVantage is an explainable investment-research and paper-trading platform.
Milestone 1 provides the secure development foundation only; it does not place
broker orders or provide guaranteed investment outcomes.

## Safety boundary

- Research and decision support only.
- Paper trading only.
- Human approval is required before any future trade.
- No broker credentials or live-order implementation are included.
- Market-data and notification keys must be supplied through secrets.

## Included in Milestone 1

- FastAPI application with `GET /health`
- SQLAlchemy database layer
- SQLite development fallback
- PostgreSQL 17 with pgvector through Docker Compose
- Alembic migration framework
- Initial `Instrument` model
- JSON container logging
- Pytest, Ruff and GitHub Actions
- GitHub Codespaces configuration
- Non-root application container

## GitHub Codespaces

1. On GitHub, select **Code → Codespaces → Create codespace**.
2. Wait for `.devcontainer/setup.sh` to install dependencies and start Compose.
3. Open the private forwarded port named **InvestVantage API**.
4. Visit `/health` or `/docs`.

The setup script creates an ignored `.env` with a random development PostgreSQL
password. Real Finnhub, Twelve Data, Telegram and broker secrets are not required
for Milestone 1.

## Local development

Python 3.12 or newer is required.

```bash
cp .env.example .env
make setup
make test
make lint
make api
```

The default local configuration uses SQLite at `data/investvantage.db`.

## Docker development

Copy `.env.example` to `.env` and replace `POSTGRES_PASSWORD` before starting:

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 api postgres
```

The API is available at `http://127.0.0.1:8000`. PostgreSQL is not published to
the host or internet.

Stop without deleting PostgreSQL data:

```bash
docker compose down
```

## Database migrations

```bash
alembic upgrade head
```

SQLite tables are created automatically for simple local development. Docker
Compose runs `alembic upgrade head` in a one-shot migration container before
starting the API, keeping Alembic authoritative for PostgreSQL.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection URL |
| `FINNHUB_API_KEY` | Reserved for the Finnhub provider |
| `TWELVE_DATA_API_KEY` | Reserved for the Twelve Data provider |
| `TELEGRAM_BOT_TOKEN` | Reserved for notifications |
| `JWT_SECRET` | Reserved for authenticated pilot access |
| `TRADING_MODE` | Fixed to `paper` in this milestone |
| `ENABLE_BROKER_ORDERS` | Must remain `false` |

## Common commands

```bash
make setup
make test
make lint
make format
make api
make compose-up
make compose-down
make migrate
```

## Next milestone

Milestone 2 will introduce market-provider interfaces, mocked provider tests,
watchlist ingestion and controlled Finnhub/Twelve Data integration. It should
begin only after this foundation passes in Codespaces.
