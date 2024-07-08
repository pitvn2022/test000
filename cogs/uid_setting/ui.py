import typing

import discord
import genshin

from database import Database, User
from utility import EmbedTemplate, get_server_name


class UIDModal(discord.ui.Modal, title="提交UID"):
    """提交 UID 的表單"""

    def __init__(self, game: genshin.Game) -> None:
        self.game = game
        super().__init__()

    uid: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="UID",
        placeholder="Please enter the UID (9 or 10 digits) of the game.",
        required=True,
        min_length=9,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        user = await Database.select_one(User, User.discord_id.is_(interaction.user.id))
        if user is None:
            user = User(interaction.user.id)

        match self.game:
            case genshin.Game.GENSHIN:
                user.uid_genshin = int(self.uid.value)
            case genshin.Game.HONKAI:
                user.uid_honkai3rd = int(self.uid.value)
            case genshin.Game.STARRAIL:
                user.uid_starrail = int(self.uid.value)
            case genshin.Game.ZZZ:
                user.uid_zzz = int(self.uid.value)
        try:
            await Database.insert_or_replace(user)
        except Exception as e:
            await interaction.response.send_message(embed=EmbedTemplate.error(e), ephemeral=True)
        else:
            await interaction.response.send_message(
                embed=EmbedTemplate.normal("UID設定成功"), ephemeral=True
            )


class UidDropdown(discord.ui.Select):
    """選擇欲保存的 UID 的下拉選單"""

    def __init__(
        self, accounts: typing.Sequence[genshin.models.GenshinAccount], game: genshin.Game
    ):
        options = [
            discord.SelectOption(
                label=f"[{get_server_name(str(account.uid)[0])}] {account.uid}",
                description=f"Lv.{account.level} {account.nickname}",
                value=str(i),
            )
            for i, account in enumerate(accounts)
        ]
        super().__init__(placeholder="Please select the UID you want to used:", options=options)
        self.accounts = accounts
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        uid = self.accounts[int(self.values[0])].uid
        user = await Database.select_one(User, User.discord_id.is_(interaction.user.id))
        if user is None:
            raise (ValueError("This user cannot be found"))
        match self.game:
            case genshin.Game.GENSHIN:
                user.uid_genshin = uid
            case genshin.Game.STARRAIL:
                user.uid_starrail = uid
            case genshin.Game.ZZZ:
                user.uid_zzz = uid
        await Database.insert_or_replace(user)
        await interaction.response.edit_message(
            embed=EmbedTemplate.normal(f"UID {uid} set completed"), view=None
        )
