from modules.embed_builder import EmbedBuilder
from discord.ext import commands

import discord


class RoleGiverView(discord.ui.View):
    def __init__(self, role: discord.Role) -> None:
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.primary)
    async def give_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        _ = button
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )
            return

        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(
                f"Removed **{self.role.name}** from you.", ephemeral=True
            )
        else:
            await member.add_roles(self.role)
            await interaction.response.send_message(
                f"Gave you the **{self.role.name}** role!", ephemeral=True
            )


class NewRoleGiver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="new-role-giver",
        description="Sends an embed with a button that will give you the specified role when pressed.",
    )
    @commands.has_permissions(manage_roles=True)
    async def new_role_giver(
        self,
        ctx: commands.Context,
        role: discord.Role,
        channel: discord.TextChannel | None = None,
    ) -> None:
        target_channel = channel or ctx.channel

        embed = (
            EmbedBuilder(
                title="Role Giver",
                description=f"Click the button below to get the **{role.name}** role.",
                color=role.color if role.color.value else discord.Color.blurple(),
            )
            .set_timestamp()
            .build()
        )

        view = RoleGiverView(role)
        await target_channel.send(embed=embed, view=view)
        if channel and channel != ctx.channel:
            await ctx.reply(
                f"Role giver sent to {channel.mention}.", ephemeral=True
            )
        else:
            await ctx.message.delete()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NewRoleGiver(bot))
