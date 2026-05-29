import discord
from discord.ext import commands

import scheduler.executor_scraper as executor_scraper
from modules.embed_builder import EmbedBuilder


class ExecutorsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)

        self.add_item(discord.ui.Button(
            label="Purchase Lifetime",
            style=discord.ButtonStyle.link,
            url="https://lumin.rest/key/",
            row=0,
        ))

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary, row=0)
    async def get_script(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button
        script = '```lua\nloadstring(game:HttpGet("https://lumin.rest/"))()\n```'
        await interaction.response.send_message(script, ephemeral=True)


class Executors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="executors", description="Lists all executors supported by Lumin.")
    @commands.cooldown(3, 6, commands.BucketType.user)
    async def executors(self, ctx: commands.Context) -> None:
        executors = executor_scraper.executors_cache

        if not executors:
            await ctx.reply("Executor list is still loading, try again in a moment.")
            return

        lines = "```diff\n" + "\n".join(f"+ {e}" for e in executors) + "\n```"
        embed = (
            EmbedBuilder(
                title="Supported Executors",
                description=lines,
                color=discord.Color.blurple(),
            )
            .set_description(f"All **verified** working executors.\n- **Missed one**? Let us know in <#1508165069635063998>\n{lines}")
            .set_timestamp()
            .build()
        )
        await ctx.reply(embed=embed, view=ExecutorsView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Executors(bot))
