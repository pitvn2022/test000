import asyncio
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import genshin_py
from utility import EmbedTemplate, custom_log


class DailyCheckinCog(commands.Cog, name="daily_check-in"):
    """斜線指令"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily_check-in", description="Get Hoyolab Daily Check-In")
    @app_commands.rename(game="genshin", is_geetest="geetest", user="user")
    @app_commands.choices(
        game=[
            Choice(name="Genshin Impact", value="Genshin Impact"),
            Choice(name="Honkai Impact 3", value="Honkai Impact 3"),
            Choice(name="Honkai: Star Rail", value="Honkai: Star Rail"),
            Choice(name="Zenless Zone Zero", value="Zenless Zone Zero"),
            Choice(name="Tears of Themis", value="Tears of Themis"),
            Choice(name="Tears of Themis(TW)", value="Tears of Themis(TW)"),
        ]
    )
    @app_commands.choices(
        is_geetest=[
            Choice(name="number", value="是"),
            Choice(name="deny", value="否"),
        ]
    )
    @custom_log.SlashCommandLogger
    async def slash_daily(
        self,
        interaction: discord.Interaction,
        game: Literal["Genshin Impact", "Honkai Impact 3", "Honkai: Star Rail", "Zenless Zone Zero", "Tears of Themis", "Tears of Themis(TW)"],
        is_geetest: Literal["是", "否"] = "否",
        user: Optional[discord.User] = None,
    ):
        choice = {
            "has_genshin": True if game == "Genshin Impact" else False,
            "has_honkai3rd": True if game == "Honkai Impact 3" else False,
            "has_starrail": True if game == "Honkai: Star Rail" else False,
            "has_themis": True if game == "Tears of Themis" else False,
            "has_zzz": True if game == "Zenless Zone Zero" else False,
            "has_themis_tw": True if game == "Tears of Themis(TW)" else False,
            "is_geetest": True if is_geetest == "是" else False,
        }

        _user = user or interaction.user
        if _user.id == self.bot.application_id:
            _user = interaction.user

        defer, result = await asyncio.gather(
            interaction.response.defer(ephemeral=(is_geetest == "是")),
            genshin_py.claim_daily_reward(_user.id, **choice),
        )
        await interaction.edit_original_response(embed=EmbedTemplate.normal(result))


async def setup(client: commands.Bot):
    await client.add_cog(DailyCheckinCog(client))
