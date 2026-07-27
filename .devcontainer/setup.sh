#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

if [[ ! -f .env ]]; then
  cp .env.example .env
  generated_password="$(openssl rand -hex 24)"
  sed -i "s/replace-with-a-secret/${generated_password}/" .env
  sed -i "s|sqlite:///./data/investvantage.db|postgresql+psycopg://investvantage_app:${generated_password}@postgres:5432/investvantage|" .env
fi

docker compose up --build -d
echo "InvestVantage setup complete. Open the forwarded API port 8000."
