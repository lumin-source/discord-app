from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import discord
from discord.ext import tasks

LOGIN_CHANNEL_ID = 1507730987973611694
LOGIN_URL = "https://wispbyte.com/client"
LOGIN_PERIOD_DAYS = 30
FIRST_REMINDER_DAY = 14
REMINDER_INTERVAL_DAYS = 7
OWNER_ID: int = 1002377371892072498

DATA_FILE = Path(__file__).parent.parent / "data" / "login_reminder.json"


def _load_state() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            logging.warning("login_reminder: could not read state file: %s", exc)

    state = {"last_login": datetime.now(UTC).timestamp(), "last_reminder": 0.0}
    _save_state(state)
    return state


def _save_state(state: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


class LoginReminderView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Login",
                style=discord.ButtonStyle.link,
                url=LOGIN_URL,
            )
        )


def _build_message(deadline: datetime) -> str:
    deadline_ts = int(deadline.timestamp())
    ping = f"<@{OWNER_ID}>" if OWNER_ID else "@here"
    return (
        f"{ping} Press the button below to login. "
        f"You must login <t:{deadline_ts}:R>, "
        f"otherwise the bot will turn off until the next login."
    )


def register(bot) -> None:
    if not OWNER_ID:
        logging.warning("login_reminder: OWNER_ID is not set — reminders won't mention anyone")

    @tasks.loop(hours=1)
    async def reminder_loop() -> None:
        channel = bot.get_channel(LOGIN_CHANNEL_ID)
        if channel is None:
            try:
                channel = await bot.fetch_channel(LOGIN_CHANNEL_ID)
            except Exception as exc:
                logging.error("login_reminder: cannot fetch channel %s: %s", LOGIN_CHANNEL_ID, exc)
                return

        state = _load_state()
        now = datetime.now(UTC)
        last_login = datetime.fromtimestamp(state["last_login"], tz=UTC)
        last_reminder = datetime.fromtimestamp(state["last_reminder"], tz=UTC)
        deadline = last_login + timedelta(days=LOGIN_PERIOD_DAYS)
        days_elapsed = (now - last_login).days
        should_send = (
            days_elapsed >= FIRST_REMINDER_DAY
            and (now - last_reminder) >= timedelta(days=REMINDER_INTERVAL_DAYS)
        )

        if should_send:
            try:
                await channel.send(content=_build_message(deadline), view=LoginReminderView())
                state["last_reminder"] = now.timestamp()
                _save_state(state)
                logging.info("login_reminder: sent reminder (days_elapsed=%d)", days_elapsed)
            except Exception as exc:
                logging.error("login_reminder: failed to send reminder: %s", exc)

    @reminder_loop.before_loop
    async def _before() -> None:
        await bot.wait_until_ready()

        channel = bot.get_channel(LOGIN_CHANNEL_ID)
        if channel is None:
            try:
                channel = await bot.fetch_channel(LOGIN_CHANNEL_ID)
            except Exception as exc:
                logging.error("login_reminder: cannot fetch channel on init: %s", exc)
                channel = None

        if channel is not None:
            state = _load_state()
            last_login = datetime.fromtimestamp(state["last_login"], tz=UTC)
            deadline = last_login + timedelta(days=LOGIN_PERIOD_DAYS)
            try:
                await channel.send(content=_build_message(deadline), view=LoginReminderView())
                logging.info("login_reminder: sent startup ping")
            except Exception as exc:
                logging.error("login_reminder: failed to send startup ping: %s", exc)

    reminder_loop.start()
