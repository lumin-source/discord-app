from __future__ import annotations
from discord.ext import tasks
from modules.embed_builder import EmbedBuilder

import logging
import discord
import scheduler.game_scraper as game_scraper
import scheduler.executor_scraper as executor_scraper

LIVE_CHANNEL_ID = 1508174002680496350
SCRIPT_URL = "https://lumin.rest/"

games_message: discord.Message | None = None
executors_message: discord.Message | None = None
last_games: list[str] = []
last_executors: list[str] = []


class LiveGamesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Purchase Lifetime",
            style=discord.ButtonStyle.link,
            url="https://lumin.rest/key/",
            row=0,
        ))

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, custom_id="live_games_script", row=0)
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _ = button
        await interaction.response.send_message(
            f'```lua\nloadstring(game:HttpGet("{SCRIPT_URL}"))()\n```',
            ephemeral=True,
        )


class LiveExecutorsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Purchase Lifetime",
            style=discord.ButtonStyle.link,
            url="https://lumin.rest/key/",
            row=0,
        ))

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, custom_id="live_executors_script", row=0)
    async def get_script(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _ = button
        await interaction.response.send_message(
            f'```lua\nloadstring(game:HttpGet("{SCRIPT_URL}"))()\n```',
            ephemeral=True,
        )


def build_games_embed() -> discord.Embed:
    games = game_scraper.games_cache
    lines = "```diff\n" + "\n".join(f"+ {name}" for name in games) + "\n```"
    return (
        EmbedBuilder(title="Supported Games", description=lines, color=discord.Color.blurple())
        .set_description(
            f"All games are supported and fully working.\n"
            f"- View them on our website [by clicking here](https://lumin.rest/).\n{lines}"
        )
        .set_timestamp()
        .build()
    )


def build_executors_embed() -> discord.Embed:
    executors = executor_scraper.executors_cache
    lines = "```diff\n" + "\n".join(f"+ {e}" for e in executors) + "\n```"
    return (
        EmbedBuilder(title="Supported Executors", description=lines, color=discord.Color.blurple())
        .set_description(
            f"All **verified** working executors.\n"
            f"- **Missed one**? Let us know in <#1508165069635063998>\n{lines}"
        )
        .set_timestamp()
        .build()
    )


async def find_existing_messages(channel: discord.TextChannel, bot_id: int) -> None:
    global games_message, executors_message
    async for msg in channel.history(limit=100):
        if msg.author.id != bot_id or not msg.embeds:
            continue
        title = msg.embeds[0].title
        if title == "Supported Games" and games_message is None:
            games_message = msg
            logging.info("live_embeds: found existing games message (ID: %s)", msg.id)
        elif title == "Supported Executors" and executors_message is None:
            executors_message = msg
            logging.info("live_embeds: found existing executors message (ID: %s)", msg.id)
        if games_message and executors_message:
            break


def register(bot) -> None:
    bot.add_view(LiveGamesView())
    bot.add_view(LiveExecutorsView())

    @tasks.loop(seconds=30)
    async def update_loop() -> None:
        global games_message, executors_message, last_games, last_executors

        channel = bot.get_channel(LIVE_CHANNEL_ID)
        if channel is None:
            return

        games = game_scraper.games_cache
        executors = executor_scraper.executors_cache

        if not games or not executors:
            return

        try:
            if games != last_games:
                embed = build_games_embed()
                if games_message is None:
                    games_message = await channel.send(embed=embed, view=LiveGamesView())
                    logging.info("live_embeds: posted games message (ID: %s)", games_message.id)
                else:
                    await games_message.edit(embed=embed)
                    logging.info("live_embeds: updated games message")
                last_games = list(games)

            if executors != last_executors:
                embed = build_executors_embed()
                if executors_message is None:
                    executors_message = await channel.send(embed=embed, view=LiveExecutorsView())
                    logging.info("live_embeds: posted executors message (ID: %s)", executors_message.id)
                else:
                    await executors_message.edit(embed=embed)
                    logging.info("live_embeds: updated executors message")
                last_executors = list(executors)
        except Exception as exc:
            logging.error("live_embeds: update failed: %s", exc)

    @update_loop.before_loop
    async def before_loop() -> None:
        await bot.wait_until_ready()
        channel = bot.get_channel(LIVE_CHANNEL_ID)
        if channel is not None:
            await find_existing_messages(channel, bot.user.id)

    update_loop.start()
    logging.info("live_embeds: scheduler started")
