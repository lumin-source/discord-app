from modules.embed_builder import EmbedBuilder
from discord.ext import commands

import time
import discord
import scheduler.game_scraper as game_scraper


class AllGamesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)

        self.add_item(discord.ui.Button(
            label="Purchase",
            style=discord.ButtonStyle.link,
            url="https://lumin-rocks.mysellauth.com/",
            row=0,
        ))

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, row=0)
    async def get_script(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button
        script = '```lua\nloadstring(game:HttpGet("https://lumin.rest/"))()\n```'
        await interaction.response.send_message(script, ephemeral=True)


class AllGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="all-games", description="Lists all games supported by Lumin.")
    @commands.cooldown(3, 6, commands.BucketType.user)
    async def all_games(self, ctx: commands.Context) -> None:
        games = game_scraper.games_cache

        if not games:
            started = game_scraper.scrape_started_at
            if started is not None:
                elapsed = time.monotonic() - started
                estimated = game_scraper.last_scrape_duration
                pct = min(99, int((elapsed / estimated) * 100))
                remaining = max(0, estimated - elapsed)
                await ctx.reply(
                    f"Game list is still loading, try again in a moment. "
                    f"({pct}% done, {remaining:.0f}s est. remaining)"
                )
            else:
                await ctx.reply("Game list is still loading, try again in a moment.")
            return

        lines = "```diff\n" + "\n".join(
            f"+ {name}" for name in games
        ) + "\n```"
        embed = (
            EmbedBuilder(
                title="Supported Games",
                description=lines,
                color=discord.Color.blurple(),
            )
            .set_description(f"All games are supported and fully working.\n- View them on our website [by clicking here](https://lumin.rest/).\n{lines}")
            .set_timestamp()
            .build()
        )
        await ctx.reply(embed=embed, view=AllGamesView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AllGames(bot))
