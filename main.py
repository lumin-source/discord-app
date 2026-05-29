import importlib.util
import logging
import os
import sys
import discord

from pathlib import Path
from dotenv import load_dotenv
from discord.ext import commands


logging.basicConfig(level=logging.INFO)
logging.getLogger("discord").setLevel(logging.WARNING)

BASE_DIR = Path(__file__).parent
EVENTS_DIR = BASE_DIR / "events"
COMMANDS_DIR = BASE_DIR / "commands"
SCHEDULER_DIR = BASE_DIR / "scheduler"

load_dotenv(BASE_DIR / ".env")

PREFIX = os.getenv("BOT_PREFIX", "l.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

global_cooldown = commands.CooldownMapping.from_cooldown(3, 6, commands.BucketType.user)


@bot.check
async def global_rate_limit(ctx: commands.Context) -> bool:
    bucket = global_cooldown.get_bucket(ctx.message)
    retry_after = bucket.update_rate_limit() if bucket else None
    if retry_after:
        raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)
    return True


def load_event_module(module_path: Path) -> None:
    module_name = f"events.{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load event module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    register = getattr(module, "register", None)
    if not callable(register):
        logging.warning("Skipping event module %s: missing register(bot)", module_name)
        return

    register(bot)
    logging.info("Loaded event module: %s", module_name)


def load_scheduler_module(module_path: Path) -> None:
    module_name = f"scheduler.{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load scheduler module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    register = getattr(module, "register", None)
    if not callable(register):
        logging.warning("Skipping scheduler module %s: missing register(bot)", module_name)
        return

    register(bot)
    logging.info("Loaded scheduler module: %s", module_name)


async def load_command_extensions() -> None:
    for command_file in sorted(COMMANDS_DIR.glob("*.py")):
        if command_file.name.startswith("_"):
            continue

        extension = f"commands.{command_file.stem}"
        await bot.load_extension(extension)
        logging.info("Loaded command extension: %s", extension)


@bot.event
async def setup_hook() -> None:
    for event_file in sorted(EVENTS_DIR.glob("*.py")):
        if event_file.name.startswith("_"):
            continue
        load_event_module(event_file)

    for scheduler_file in sorted(SCHEDULER_DIR.glob("*.py")):
        if scheduler_file.name.startswith("_"):
            continue
        load_scheduler_module(scheduler_file)

    await load_command_extensions()
    await bot.tree.sync()
    logging.info("Synced slash commands")


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()

