import discord
from discord import app_commands
from discord.ext import commands

from database import Database
from utility import custom_log

from .ui import ConfirmButton


class ClearSettingCog(commands.Cog, name="user_data"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="user_data", description="Delete all user's personal information saved in Bot.")
    @custom_log.SlashCommandLogger
    async def slash_clear(self, interaction: discord.Interaction):
        view = ConfirmButton()
        await interaction.response.send_message("Is it confirmed to be deleted?", view=view, ephemeral=True)

        await view.wait()
        if view.value is True:
            await Database.delete_all(interaction.user.id)
            await interaction.edit_original_response(content="All user information has been deleted", view=None)
        else:
            await interaction.edit_original_response(content="Cancel command", view=None)


async def setup(client: commands.Bot):
    await client.add_cog(ClearSettingCog(client))
