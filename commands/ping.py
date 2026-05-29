import discord
from discord.ext import commands

from modules.embed_builder import EmbedBuilder


class PingView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.primary)
    async def get_script(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button
        script = '```lua\nloadstring(game:HttpGet("https://lumin.rest/"))()\n```'
        await interaction.response.send_message(script, ephemeral=True)


class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Replies with the bot's latency.")
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        embed = (
            EmbedBuilder(
                title="Pong!",
                description=f"**Response delay**: {latency_ms}ms",
                color=discord.Color.green(),
            )
            .set_timestamp()
            .build()
        )

        view = PingView()
        await ctx.reply(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ping(bot))
