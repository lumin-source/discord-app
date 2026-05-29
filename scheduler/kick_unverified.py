from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from discord.ext import tasks


def register(bot) -> None:
    @tasks.loop(minutes=30)
    async def kick_unverified_loop() -> None:
        for guild in bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                if len(member.roles) > 1:
                    continue
                if member.joined_at is None:
                    continue
                if datetime.now(UTC) - member.joined_at < timedelta(hours=24):
                    continue
                try:
                    await member.kick(reason="No roles assigned within 24 hours of joining.")
                    logging.info("kick_unverified: kicked %s (%s)", member, member.id)
                except Exception as exc:
                    logging.error("kick_unverified: failed to kick %s: %s", member, exc)

    @kick_unverified_loop.before_loop
    async def _before() -> None:
        await bot.wait_until_ready()

    kick_unverified_loop.start()
