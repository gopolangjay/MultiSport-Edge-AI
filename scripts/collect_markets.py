"""Entrypoint for Render cron or one-shot market collection."""
import asyncio
import json

from app.market_collector import collect_public_markets


if __name__ == "__main__":
    print(json.dumps(asyncio.run(collect_public_markets()), default=str))
