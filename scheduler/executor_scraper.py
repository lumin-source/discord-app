from __future__ import annotations

import logging

import aiohttp
from discord.ext import tasks

EXECUTORS_URL = "https://raw.githubusercontent.com/lumin-rocks/garbage/main/executors.txt"

executors_cache: list[str] = []


def parse_txt_list(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines() if line.strip()]


async def fetch_and_cache() -> None:
    global executors_cache
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            async with session.get(EXECUTORS_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                executors_txt = await resp.text()

        found = parse_txt_list(executors_txt)
        if found and found != executors_cache:
            executors_cache = found
            logging.info("executor_scraper: cached %d executors", len(found))
        elif not found:
            logging.warning("executor_scraper: scrape returned no executors")
    except Exception as exc:
        logging.error("executor_scraper: scrape failed: %s", exc)


def register(bot) -> None:
    @tasks.loop(seconds=60)
    async def scrape_loop() -> None:
        await fetch_and_cache()

    @scrape_loop.before_loop
    async def before_loop() -> None:
        await bot.wait_until_ready()
        await fetch_and_cache()

    scrape_loop.start()
    logging.info("executor_scraper: scheduler started")
