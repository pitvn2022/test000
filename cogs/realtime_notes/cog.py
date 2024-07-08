import asyncio
import typing

import discord
import genshin
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import genshin_py
from utility import EmbedTemplate
from utility.custom_log import ContextCommandLogger, SlashCommandLogger


class RealtimeNotes:
    """即時便箋"""

    @staticmethod
    async def notes(
        interaction: discord.Interaction,
        user: discord.User | discord.Member,
        game: genshin.Game,
        *,
        short_form: bool = False,
    ):
        try:
            match game:
                case genshin.Game.GENSHIN:
                    defer, notes = await asyncio.gather(
                        interaction.response.defer(), genshin_py.get_genshin_notes(user.id)
                    )
                    embed = await genshin_py.parse_genshin_notes(
                        notes, user=user, short_form=short_form
                    )
                case genshin.Game.STARRAIL:
                    defer, notes = await asyncio.gather(
                        interaction.response.defer(), genshin_py.get_starrail_notes(user.id)
                    )
                    embed = await genshin_py.parse_starrail_notes(
                        notes, user, short_form=short_form
                    )
                case genshin.Game.ZZZ:
                    defer, notes = await asyncio.gather(
                        interaction.response.defer(), genshin_py.get_zzz_notes(user.id)
                    )
                    embed = await genshin_py.parse_zzz_notes(notes, user)
                case _:
                    return
        except Exception as e:
            await interaction.edit_original_response(embed=EmbedTemplate.error(e))
        else:
            await interaction.edit_original_response(embed=embed)


class RealtimeNotesCog(commands.Cog, name="realtime_notes"):
    """取得使用者即時便箋資訊(樹脂、洞天寶錢、派遣...等)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="realtime_notes", description="Check real-time notes, including resin, realm currency, expedition dispatch, etc"
    )
    @app_commands.rename(game="game", short_form="short_form", user="user")
    @app_commands.describe(
        short_form="Choose to display in full or simplified format (comit daily, weekly, expedition dispatch)", 
        user="Retrieve data for other members; leave blank to retrieve your own.",
    )
    @app_commands.choices(
        game=[
            Choice(name="Genshin Impact", value="genshin"),
            Choice(name="Honkai: Star Rail", value="hkrpg"),
            Choice(name="Zenless Zone Zero", value="nap"),
        ],
        short_form=[Choice(name="Yes", value="完整"), Choice(name="No", value="簡約")],
    )
    @SlashCommandLogger
    async def slash_notes(
        self,
        interaction: discord.Interaction,
        game: genshin.Game,
        short_form: typing.Literal["完整", "簡約"] = "完整",
        user: discord.User | None = None,
    ):
        await RealtimeNotes.notes(
            interaction, user or interaction.user, game, short_form=(short_form == "簡約")
        )


async def setup(client: commands.Bot):
    await client.add_cog(RealtimeNotesCog(client))

    @client.tree.context_menu(name="realtime notes")
    @ContextCommandLogger
    async def context_notes(interaction: discord.Interaction, user: discord.User):
        await RealtimeNotes.notes(interaction, user, genshin.Game.GENSHIN)
