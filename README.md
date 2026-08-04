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

## Market-data foundation

Milestone 2 adds normalized instruments, watchlists and OHLCV history together
with mock, Finnhub and Twelve Data provider adapters. The mock provider is the
default so development and tests never consume a paid API quota.

Compose loads the example US pilot watchlist automatically after applying
migrations. It is idempotent and can also be run manually:

```bash
make load-watchlist
```

The following endpoints are available in `/docs`:

```text
GET  /api/v1/instruments
GET  /api/v1/instruments/{symbol}
GET  /api/v1/watchlists
POST /api/v1/watchlists
GET  /api/v1/market/{symbol}
POST /api/v1/market/refresh
```

Use mock data without any key:

```bash
curl "http://127.0.0.1:8000/api/v1/market/AAPL?provider=mock&limit=5"
```

For a controlled provider test, add `FINNHUB_API_KEY` and
`TWELVE_DATA_API_KEY` as Codespaces secrets, restart the Codespace, and select
`finnhub` or `twelve_data` through the endpoint's `provider` parameter. Finnhub
uses its real-time quote endpoint in this milestone; Twelve Data provides daily
historical bars. Provider credentials are sent in headers and are never returned
by the API.

Supported market-data configuration:

| Variable | Purpose | Default |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `mock`, `finnhub`, or `twelve_data` | `mock` |
| `MARKET_DATA_TIMEOUT_SECONDS` | HTTP timeout | `10` |
| `MARKET_DATA_MAX_RETRIES` | Transient request retries | `2` |

## Next milestone

Milestone 3 adds deterministic moving averages, RSI, MACD, ATR, volume analysis,
support and resistance references, and an explainable technical score.

```text
GET /api/v1/analysis/{symbol}/technical
```

The Streamlit research dashboard runs as a separate Compose service on port
`8501`. In Codespaces, open the private forwarded port named
**InvestVantage Dashboard**. It provides instrument and provider controls, price
history, technical metrics, scoring factors and risk factors. It does not place
trades.

```bash
make dashboard
```

Milestone 4 adds the deterministic Quality Momentum Swing strategy and persists
explainable `BUY`, `WATCH`, `HOLD`, `REDUCE`, and `AVOID` research signals.

```text
POST /api/v1/signals/generate
GET  /api/v1/signals
GET  /api/v1/signals/latest/{symbol}
```

Signals include confidence, risk, entry, stop and target references, positive
and negative factors, invalidation conditions and data completeness. They are
research outputs only; broker order submission remains disabled.

## Real research-data ingestion

Keep `FINNHUB_API_KEY` and `TWELVE_DATA_API_KEY` in Codespaces secrets or a local ignored
`.env` file. Never commit their values. After the database and migrations are running:

```bash
docker compose --profile ingestion run --rm seed-real
docker compose up --build -d api dashboard
```

The job stores up to 500 real daily Twelve Data OHLCV bars and, for stocks, Finnhub
fundamental metrics, recent company news and earnings-calendar events. Price bars are rejected
when timestamps are unordered, duplicated, stale, in the future, or contain invalid OHLCV
values. Provider and retrieval times remain visible through the API.

```text
GET  /api/v1/research/{symbol}
GET  /api/v1/research/{symbol}?refresh=true
POST /api/v1/signals/outcomes/evaluate?horizon_days=20
GET  /api/v1/signals/outcomes
GET  /api/v1/signals/backtest/{symbol}?provider=twelve_data&horizon_days=20
```

Quality Momentum now combines technical (40%), fundamental (20%), news (10%), market-regime
(10%), sector-relative strength (10%) and portfolio suitability (10%) scores. Missing provider
data remains `null` and lowers `data_completeness`; it is never silently replaced with mock
data. News scoring is a deterministic headline-cue baseline and requires human review.

### Backtest integrity controls

The backtest laboratory models configurable position value, commission per order, regulatory
fees, entry/exit slippage and cash dividends. Daily Twelve Data prices are split-adjusted;
dividend and split-event ingestion is attempted separately and is shown as unavailable when the
configured provider plan does not include those premium endpoints. The dashboard reports net
returns, modeled fees, drawdown, equity curve, trade detail and all active assumptions.

The current universe is today's configured watchlist, so results retain survivorship bias. A
future point-in-time universe dataset is required to remove that limitation. Historical
fundamentals are also excluded until filing-date-aware snapshots are available. Broker execution
remains disabled; backtest settings cannot submit an order.
