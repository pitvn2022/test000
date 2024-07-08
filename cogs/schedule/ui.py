from datetime import date, datetime, time, timedelta
from typing import overload

import discord

from database import Database, GenshinScheduleNotes, StarrailScheduleNotes, ZZZScheduleNotes
from utility import EmbedTemplate, config


class DailyRewardOptionsView(discord.ui.View):
    """自動簽到每日的選項，包含遊戲、簽到時間與是否 tag 使用者"""

    def __init__(self, author: discord.User | discord.Member):
        super().__init__(timeout=config.discord_view_short_timeout)
        self.selected_games: str | None = None
        """使用者選擇的遊戲，例：原神+星穹鐵道"""
        self.has_genshin: bool = False
        """是否有原神"""
        self.has_honkai3rd: bool = False
        """是否有崩壞3"""
        self.has_starrail: bool = False
        """是否有星穹鐵道"""
        self.has_zzz: bool = False
        """是否有絕區零"""
        self.has_themis: bool = False
        """是否有未定事件簿(國際服)"""
        self.has_themis_tw: bool = False
        """是否有未定事件簿(台服)"""
        self.hour: int = 8
        """每天簽到時間 (時：0 ~ 23)"""
        self.minute: int = 0
        """每天簽到時間 (分：0 ~ 59)"""
        self.is_mention: bool | None = None
        """簽到訊息是否要 tag"""
        self.author = author
        """使用者"""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

    @discord.ui.select(
        cls=discord.ui.Select,
        options=[
            discord.SelectOption(label="Genshin Impact", value="Genshin Impact"),
            discord.SelectOption(label="Honkai Impact 3", value="Honkai Impact 3"),
            discord.SelectOption(label="Honkai: Star Rail", value="Honkai: Star Rail"),
            discord.SelectOption(label="Zenless Zone Zero", value="Zenless Zone Zero"),
            discord.SelectOption(label="Tears of Themis", value="Tears of Themis"),
            discord.SelectOption(label="Tears of Themis(TW)", value="Tears of Themis(TW)"),
        ],
        min_values=1,
        max_values=6,
        placeholder="Please select the game you want to sign in (multiple choices possible):",
    )
    async def select_games_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()
        self.selected_games = " + ".join(select.values)
        if "Genshin Impact" in self.selected_games:
            self.has_genshin = True
        if "Honkai Impact 3" in self.selected_games:
            self.has_honkai3rd = True
        if "Honkai: Star Rail" in self.selected_games:
            self.has_starrail = True
        if "Zenless Zone Zero" in self.selected_games:
            self.has_zzz = True
        if "Tears of Themis" in self.selected_games:
            self.has_themis = True
        if "Tears of Themis(TW)" in self.selected_games:
            self.has_themis_tw = True

    @discord.ui.select(
        cls=discord.ui.Select,
        options=[discord.SelectOption(label=str(i).zfill(2), value=str(i)) for i in range(0, 24)],
        min_values=0,
        max_values=1,
        placeholder="Please select the time (hour) you want to sign in:",
    )
    async def select_hour_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()
        if len(select.values) > 0:
            self.hour = int(select.values[0])

    @discord.ui.select(
        cls=discord.ui.Select,
        options=[
            discord.SelectOption(label=str(i).zfill(2), value=str(i)) for i in range(0, 60, 5)
        ],
        min_values=0,
        max_values=1,
        placeholder="Please select the time (in minutes) you would like to sign in:",
    )
    async def select_minute_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        await interaction.response.defer()
        if len(select.values) > 0:
            self.minute = int(select.values[0])

    @discord.ui.button(label="tag", style=discord.ButtonStyle.blurple)
    async def button1_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.is_mention = True
        self.stop()

    @discord.ui.button(label="no tag", style=discord.ButtonStyle.blurple)
    async def button2_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.is_mention = False
        self.stop()


class BaseNotesThresholdModal(discord.ui.Modal):
    def _int_to_str(self, value: int | None) -> str | None:
        return str(value) if isinstance(value, int) else None

    def _str_to_int(self, value: str) -> int | None:
        return int(value) if len(value) > 0 else None

    @overload
    def _to_msg(self, title: str, value: int | None, date_frequency: str = "Every day") -> str: ...

    @overload
    def _to_msg(self, title: str, value: int | None, date_frequency: str = "Every day") -> str: ...

    def _to_msg(
        self, title: str, value: int | datetime | None, date_frequency: str = "Every day"
    ) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return f"． {title}：{date_frequency} {value.strftime('%H:%M')} check\n"
        if value == 0:
            return f"． {title}：Remind when completed\n"
        else:
            return f"． {title}：Remind {value} hours before completion\n"


class GenshinNotesThresholdModal(BaseNotesThresholdModal, title="Set Genshin Impact reminder"):
    """設定原神檢查即時便箋各項閾值的表單"""

    resin: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind resin",
        placeholder="Please enter an number between 0 and 8",
        required=False,
        max_length=1,
    )
    realm_currency: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind realm currency",
        placeholder="Please enter an number between 0 and 24",
        required=False,
        max_length=2,
    )
    transformer: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind transformer",
        placeholder="Please enter an number between 0 and 5",
        required=False,
        max_length=1,
    )
    expedition: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind expedition",
        placeholder="Please enter an number between 0 and 5",
        required=False,
        max_length=1,
    )
    commission: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind commissions",
        placeholder="Please enter a number between 0000 and 2359",
        required=False,
        max_length=4,
        min_length=4,
    )

    def __init__(self, user_setting: GenshinScheduleNotes | None = None) -> None:
        """設定表單預設值；若使用者在資料庫已有設定值，則帶入表單預設值"""
        self.resin.default = "1"
        self.realm_currency.default = None
        self.transformer.default = None
        self.expedition.default = None
        self.commission.default = None

        if user_setting:
            self.resin.default = self._int_to_str(user_setting.threshold_resin)
            self.realm_currency.default = self._int_to_str(user_setting.threshold_currency)
            self.transformer.default = self._int_to_str(user_setting.threshold_transformer)
            self.expedition.default = self._int_to_str(user_setting.threshold_expedition)
            self.commission.default = (
                user_setting.check_commission_time.strftime("%H%M")
                if user_setting.check_commission_time
                else None
            )
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            resin = self._str_to_int(self.resin.value)
            realm_currency = self._str_to_int(self.realm_currency.value)
            transformer = self._str_to_int(self.transformer.value)
            expedition = self._str_to_int(self.expedition.value)
            commission = self._str_to_int(self.commission.value)

            # 檢查數字範圍
            if (
                resin is None
                and realm_currency is None
                and transformer is None
                and expedition is None
                and commission is None
            ):
                raise ValueError()
            if (
                (isinstance(resin, int) and not (0 <= resin <= 8))
                or (isinstance(realm_currency, int) and not (0 <= realm_currency <= 24))
                or (isinstance(transformer, int) and not (0 <= transformer <= 5))
                or (isinstance(expedition, int) and not (0 <= expedition <= 5))
            ):
                raise ValueError()
            commission_time = None
            if isinstance(commission, int):
                _time = time(commission // 100, commission % 100)  # 當數字超過範圍時time會拋出例外
                _date = date.today()
                commission_time = datetime.combine(_date, _time)
                # 當今天已經超過設定的時間，則將檢查時間設為明日
                if commission_time < datetime.now():
                    commission_time += timedelta(days=1)
        except Exception:
            await interaction.response.send_message(
                embed=EmbedTemplate.error("The input value is incorrect. Please ensure the input value is an integer and within the specified range"),
                ephemeral=True,
            )
        else:
            # 儲存設定資料
            await Database.insert_or_replace(
                GenshinScheduleNotes(
                    discord_id=interaction.user.id,
                    discord_channel_id=interaction.channel_id or 0,
                    threshold_resin=resin,
                    threshold_currency=realm_currency,
                    threshold_transformer=transformer,
                    threshold_expedition=expedition,
                    check_commission_time=commission_time,
                )
            )
            await interaction.response.send_message(
                embed = EmbedTemplate.normal(
                    f"Genshin Impact settings completed. Reminders will be sent when the following thresholds are reached:\n"
                    f"{self._to_msg('Resin', resin)}"
                    f"{self._to_msg('Realm Currency', realm_currency)}"
                    f"{self._to_msg('Transformer', transformer)}"
                    f"{self._to_msg('Expedition', expedition)}"
                    f"{self._to_msg('Daily Commissions', commission_time)}"
                )
            )


class StarrailCheckNotesThresholdModal(BaseNotesThresholdModal, title="Set Honkai: Star Rail reminder"):
    """設定星穹鐵道檢查即時便箋各項閾值的表單"""

    power: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours remind Trailblaze Power",
        placeholder="Please enter an number between 0 and 8",
        required=False,
        max_length=1,
    )
    expedition: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind Expedition",
        placeholder="Please enter an number between 0 and 5",
        required=False,
        max_length=1,
    )
    dailytraining: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours to remind Daily",
        placeholder="Please enter a number between 0000 and 2359",
        required=False,
        max_length=4,
        min_length=4,
    )
    universe: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours remind Simulated Universe",
        placeholder="Please enter a number between 0000 and 2359",
        required=False,
        max_length=4,
        min_length=4,
    )
    echoofwar: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours on Sundays remind Weekly Bosses",
        placeholder="Please enter a number between 0000 and 2359",
        required=False,
        max_length=4,
        min_length=4,
    )

    def __init__(self, user_setting: StarrailScheduleNotes | None = None):
        """設定表單預設值；若使用者在資料庫已有設定值，則帶入表單預設值"""
        self.power.default = "1"
        self.expedition.default = None
        self.dailytraining.default = None

        if user_setting:
            self.power.default = self._int_to_str(user_setting.threshold_power)
            self.expedition.default = self._int_to_str(user_setting.threshold_expedition)
            self.dailytraining.default = (
                user_setting.check_daily_training_time.strftime("%H%M")
                if user_setting.check_daily_training_time
                else None
            )
            self.universe.default = (
                user_setting.check_universe_time.strftime("%H%M")
                if user_setting.check_universe_time
                else None
            )
            self.echoofwar.default = (
                user_setting.check_echoofwar_time.strftime("%H%M")
                if user_setting.check_echoofwar_time
                else None
            )
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            power = self._str_to_int(self.power.value)
            expedition = self._str_to_int(self.expedition.value)
            dailytraining = self._str_to_int(self.dailytraining.value)
            universe = self._str_to_int(self.universe.value)
            echoofwar = self._str_to_int(self.echoofwar.value)

            # 檢查數字範圍
            if (
                power is None
                and expedition is None
                and dailytraining is None
                and universe is None
                and echoofwar is None
            ):
                raise ValueError()
            if (isinstance(power, int) and not (0 <= power <= 8)) or (
                isinstance(expedition, int) and not (0 <= expedition <= 5)
            ):
                raise ValueError()

            dailytraining_time: datetime | None = None
            if isinstance(dailytraining, int):
                _time = time(dailytraining // 100, dailytraining % 100)
                _date = date.today()
                dailytraining_time = datetime.combine(_date, _time)
                # 當今天已經超過設定的時間，則將檢查時間設為明日
                if dailytraining_time < datetime.now():
                    dailytraining_time += timedelta(days=1)

            universe_time: datetime | None = None
            echoofwar_time: datetime | None = None
            if isinstance(universe, int) or isinstance(echoofwar, int):
                # 取得本周日的日期
                _date = date.today() + timedelta(days=6 - date.today().weekday())
                if isinstance(universe, int):
                    universe_time = datetime.combine(_date, time(universe // 100, universe % 100))
                    # 當今天已經超過設定的時間，則將檢查時間設為下周日
                    if universe_time < datetime.now():
                        universe_time += timedelta(days=7)
                if isinstance(echoofwar, int):
                    echoofwar_time = datetime.combine(
                        _date, time(echoofwar // 100, echoofwar % 100)
                    )
                    # 當今天已經超過設定的時間，則將檢查時間設為下周日
                    if echoofwar_time < datetime.now():
                        echoofwar_time += timedelta(days=7)

        except Exception:
            await interaction.response.send_message(
                embed=EmbedTemplate.error("The input value is incorrect. Please ensure the input value is an integer and within the specified range."),
                ephemeral=True,
            )
        else:
            # 儲存設定資料
            await Database.insert_or_replace(
                StarrailScheduleNotes(
                    discord_id=interaction.user.id,
                    discord_channel_id=interaction.channel_id or 0,
                    threshold_power=power,
                    threshold_expedition=expedition,
                    check_daily_training_time=dailytraining_time,
                    check_universe_time=universe_time,
                    check_echoofwar_time=echoofwar_time,
                )
            )
            await interaction.response.send_message(
                embed = EmbedTemplate.normal(
                    f"Honkai: Star Rail settings completed. Reminders will be sent when the following thresholds are reached:\n"
                    f"{self._to_msg('Trailblaze Power', power)}"
                    f"{self._to_msg('Expedition', expedition)}"
                    f"{self._to_msg('Daily Training', dailytraining_time)}"
                    f"{self._to_msg('Simulated Universe', universe_time, 'on Sundays')}"
                    f"{self._to_msg('Weekly bosses', echoofwar_time, 'on Sundays')}"
                )
            )


class ZZZCheckNotesThresholdModal(BaseNotesThresholdModal, title="Set Zenless Zone Zero reminder"):
    """設定絕區零檢查即時便箋各項閾值的表單"""

    battery: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours remind Battery",
        placeholder="Please enter an number between 0 and 8",
        required=False,
        max_length=1,
    )
    dailyengagement: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Set hours remind Daily Engagement",
        placeholder="Please enter a number between 0000 and 2359",
        required=False,
        max_length=4,
        min_length=4,
    )

    def __init__(self, user_setting: ZZZScheduleNotes | None = None):
        """設定表單預設值；若使用者在資料庫已有設定值，則帶入表單預設值"""
        self.battery.default = "1"
        self.dailyengagement.default = None

        if user_setting:
            self.battery.default = self._int_to_str(user_setting.threshold_battery)
            self.dailyengagement.default = (
                user_setting.check_daily_engagement_time.strftime("%H%M")
                if user_setting.check_daily_engagement_time
                else None
            )
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            battery = self._str_to_int(self.battery.value)
            dailyengagement = self._str_to_int(self.dailyengagement.value)

            # 檢查數字範圍
            if battery is None and dailyengagement is None:
                raise ValueError()
            if isinstance(battery, int) and not (0 <= battery <= 8):
                raise ValueError()

            dailyengagement_time: datetime | None = None
            if isinstance(dailyengagement, int):
                _time = time(dailyengagement // 100, dailyengagement % 100)
                _date = date.today()
                dailyengagement_time = datetime.combine(_date, _time)
                # 當今天已經超過設定的時間，則將檢查時間設為明日
                if dailyengagement_time < datetime.now():
                    dailyengagement_time += timedelta(days=1)
        except Exception:
            await interaction.response.send_message(
                embed=EmbedTemplate.error("The input value is incorrect. Please ensure the input value is an integer and within the specified range"),
                ephemeral=True,
            )
        else:
            # 儲存設定資料
            await Database.insert_or_replace(
                ZZZScheduleNotes(
                    discord_id=interaction.user.id,
                    discord_channel_id=interaction.channel_id or 0,
                    threshold_battery=battery,
                    check_daily_engagement_time=dailyengagement_time,
                )
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(
                    f"Zenless Zone Zero settings completed. Reminders will be sent when the following thresholds are reached：\n"
                    f"{self._to_msg('Battery', battery)}"
                    f"{self._to_msg('Daily Engagement', dailyengagement_time)}"
                )
            )