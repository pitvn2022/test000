from typing import Any

import discord
import sentry_sdk

from database import Database, StarrailShowcase, User
from star_rail.showcase import Showcase
from utility import EmbedTemplate, config, emoji, get_app_command_mention
from utility.custom_log import LOG


class ShowcaseCharactersDropdown(discord.ui.Select):
    """展示櫃角色下拉選單"""

    showcase: Showcase

    def __init__(self, showcase: Showcase) -> None:
        self.showcase = showcase
        options = [discord.SelectOption(label="Player Profile", value="-1", emoji="📜")]
        for i, character in enumerate(showcase.data.characters):
            if i >= 23:  # Discord 下拉欄位上限
                break
            options.append(
                discord.SelectOption(
                    label=f"★{character.rarity} Lv.{character.level} {character.name}",
                    value=str(i),
                    emoji=emoji.starrail_elements.get(character.element.name),
                )
            )
        options.append(discord.SelectOption(label="Delete character cache data", value="-2", emoji="❌"))
        super().__init__(placeholder="Select Showcase：", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        index = int(self.values[0])
        if index >= 0:  # 角色資料
            await interaction.response.defer()
            embed, file = await self.showcase.get_character_card_embed_file(index)
            await interaction.edit_original_response(
                embed=embed, view=ShowcaseView(self.showcase, index), attachments=[file]
            )
        elif index == -1:  # 玩家資料一覽
            embed = self.showcase.get_player_overview_embed()
            await interaction.response.edit_message(
                embed=embed, view=ShowcaseView(self.showcase), attachments=[]
            )
        elif index == -2:  # 刪除快取資料
            # 檢查互動者的 UID 是否符合展示櫃的 UID
            user = await Database.select_one(User, User.discord_id.is_(interaction.user.id))
            if user is None or user.uid_starrail != self.showcase.uid:
                await interaction.response.send_message(
                    embed=EmbedTemplate.error("Not the owner of this UID, cannot delete data"), ephemeral=True
                )
            elif user.cookie_default is None:
                await interaction.response.send_message(
                    embed=EmbedTemplate.error("Cookie not set, cannot verify owner of this UID, cannot delete data"),
                    ephemeral=True,
                )
            else:
                embed = self.showcase.get_player_overview_embed()
                await Database.delete(
                    StarrailShowcase,
                    StarrailShowcase.uid.is_(self.showcase.uid),
                )
                await interaction.response.edit_message(embed=embed, view=None, attachments=[])


class ShowcaseButton(discord.ui.Button):
    """角色展示櫃按鈕"""

    def __init__(self, label: str, showcase: Showcase, chatacter_index: int):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.label = label
        self.showcase = showcase
        self.character_index = chatacter_index

    async def callback(self, interaction: discord.Interaction) -> Any:
        match self.label:
            case "Image":
                await interaction.response.defer()
                try:
                    embed, file = await self.showcase.get_character_card_embed_file(
                        self.character_index
                    )
                except Exception:
                    embed = self.showcase.get_character_stat_embed(self.character_index)
                    await interaction.edit_original_response(embed=embed, attachments=[])
                else:
                    await interaction.edit_original_response(embed=embed, attachments=[file])
            case "Character":
                embed = self.showcase.get_character_stat_embed(self.character_index)
                await interaction.response.edit_message(embed=embed, attachments=[])
            case "RelicStat":
                embed = self.showcase.get_relic_stat_embed(self.character_index)
                await interaction.response.edit_message(embed=embed, attachments=[])
            case "RelicScore":
                embed = self.showcase.get_relic_score_embed(self.character_index)
                await interaction.response.edit_message(embed=embed, attachments=[])


class ShowcaseView(discord.ui.View):
    """角色展示櫃View，顯示角色面板、聖遺物詞條按鈕，以及角色下拉選單"""

    def __init__(self, showcase: Showcase, character_index: int | None = None):
        super().__init__(timeout=config.discord_view_long_timeout)
        if character_index is not None:
            self.add_item(ShowcaseButton("Picture", showcase, character_index))
            self.add_item(ShowcaseButton("Character", showcase, character_index))
            self.add_item(ShowcaseButton("RelicStats", showcase, character_index))
            self.add_item(ShowcaseButton("RelicScore", showcase, character_index))

        if len(showcase.data.characters) > 0:
            self.add_item(ShowcaseCharactersDropdown(showcase))


async def showcase(
    interaction: discord.Interaction,
    user: discord.User | discord.Member,
    uid: int | None = None,
):
    await interaction.response.defer()
    _u = await Database.select_one(User, User.discord_id.is_(user.id))
    uid = uid or (_u.uid_starrail if _u else None)
    if uid is None:
        await interaction.edit_original_response(
            embed=EmbedTemplate.error(
                f"Please use {get_app_command_mention('uid_settings')} first, or directly input the UID you want to query into the UID parameter of the command.",
                title = "Character UID not found",
            )
        )
    elif len(str(uid)) != 9 or str(uid)[0] not in ["1", "2", "5", "6", "7", "8", "9"]:
        await interaction.edit_original_response(embed=EmbedTemplate.error("The format of the entered UID is incorrect"))
    else:
        showcase = Showcase(uid)
        try:
            await showcase.load_data()
            view = ShowcaseView(showcase)
            embed = showcase.get_player_overview_embed()
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception as e:
            LOG.ErrorLog(interaction, e)
            sentry_sdk.capture_exception(e)
            embed = EmbedTemplate.error(e, title=f"UID：{uid}")
            await interaction.edit_original_response(embed=embed)
