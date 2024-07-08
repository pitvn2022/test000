from typing import Literal, Optional

import discord
import enkanetwork
from discord import app_commands
from discord.ext import commands

from utility.custom_log import ContextCommandLogger, SlashCommandLogger

from .ui_genshin import showcase as genshin_showcase
from .ui_starrail import showcase as starrail_showcase


class ShowcaseCog(commands.Cog, name="showcase"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="showcase", description="Retrieve the public character showcase of a specified UID player")
    @app_commands.rename(game="game", user="user")
    @app_commands.describe(uid="The UID of the player you want to query. If the bot has saved your data, leave this field blank to query yourself", user="To query data for other members, leave this field blank to query yourself")
    @app_commands.choices(
        game=[
            app_commands.Choice(name="Genshin Impact", value="Genshin Impact"),
            app_commands.Choice(name="Honkai: Star Rail", value="Honkai: Star Rail"),
        ]
    )
    @SlashCommandLogger
    async def slash_showcase(
        self,
        interaction: discord.Interaction,
        game: Literal["Genshin Impact", "Honkai: Star Rail"],
        uid: Optional[int] = None,
        user: Optional[discord.User] = None,
    ):
        match game:
            case "Genshin Impact":
                await genshin_showcase(interaction, user or interaction.user, uid)
            case "Honkai: Star Rail":
                await starrail_showcase(interaction, user or interaction.user, uid)


async def setup(client: commands.Bot):
    # 更新 Enka 素材資料
    enka = enkanetwork.EnkaNetworkAPI()
    async with enka:
        await enka.update_assets()
    enkanetwork.Assets(lang=enkanetwork.Language.EN)

    await client.add_cog(ShowcaseCog(client))

    @client.tree.context_menu(name="showcase")
    @ContextCommandLogger
    async def context_showcase(interaction: discord.Interaction, user: discord.User):
        await genshin_showcase(interaction, user, None)
