import discord
from discord.ext import commands

from modules.embed_builder import EmbedBuilder

STATUS_CHANNEL_ID = 1508004563007967392


class SetStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="set-status", description="Sets the script status channel name.")
    @commands.has_permissions(manage_channels=True)
    @commands.cooldown(3, 6, commands.BucketType.user)
    async def set_status(self, ctx: commands.Context, working: bool) -> None:
        channel = ctx.guild.get_channel(STATUS_CHANNEL_ID)
        if channel is None:
            await ctx.reply("Status channel not found.", ephemeral=True)
            return

        new_name = "UPDATED • [✅]" if working else "OUTDATED • [❌]"
        await channel.edit(name=new_name)

        embed = (
            EmbedBuilder(
                title="Status Updated",
                description=f"Channel renamed to **{new_name}**.",
                color=discord.Color.green() if working else discord.Color.red(),
            )
            .set_timestamp()
            .build()
        )
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetStatus(bot))
