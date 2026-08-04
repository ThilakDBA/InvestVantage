import argparse
from pathlib import Path

from app.core.config import get_settings
from app.database.session import Database
from app.services.watchlists import load_watchlist_file, upsert_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a YAML watchlist into InvestVantage")
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("config/watchlist.example.yml"),
    )
    args = parser.parse_args()
    database = Database(get_settings().database_url)
    try:
        request = load_watchlist_file(args.path)
        with database.session_factory() as session:
            watchlist = upsert_watchlist(session, request)
            count = len(request.instruments)
            print(f"Loaded watchlist '{watchlist.name}' with {count} instruments")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
