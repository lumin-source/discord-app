from __future__ import annotations

import logging
import time

import aiohttp
from discord.ext import tasks

GAMES_URL = "https://raw.githubusercontent.com/lumin-rest/dumpster-fire/main/games.txt"

games_cache: list[str] = []
scrape_started_at: float | None = None
last_scrape_duration: float = 5.0


def parse_txt_list(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines() if line.strip()]


async def fetch_and_cache() -> None:
    global games_cache, scrape_started_at, last_scrape_duration
    scrape_started_at = time.monotonic()
    start = scrape_started_at
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            async with session.get(GAMES_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                games_txt = await resp.text()

        found = parse_txt_list(games_txt)
        if found and found != games_cache:
            games_cache = found
            last_scrape_duration = time.monotonic() - start
            logging.info("game_scraper: cached %d games", len(found))
        elif not found:
            logging.warning("game_scraper: scrape returned no games")
    except Exception as exc:
        logging.error("game_scraper: scrape failed: %s", exc)
    finally:
        scrape_started_at = None


def register(bot) -> None:
    @tasks.loop(seconds=60)
    async def scrape_loop() -> None:
        await fetch_and_cache()

    @scrape_loop.before_loop
    async def before_loop() -> None:
        await bot.wait_until_ready()
        await fetch_and_cache()

    scrape_loop.start()
    logging.info("game_scraper: scheduler started")
