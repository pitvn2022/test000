from datetime import datetime, time
from typing import Literal

import discord
import genshin
import sqlalchemy
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import database
from database import (
    Database,
    GenshinScheduleNotes,
    ScheduleDailyCheckin,
    StarrailScheduleNotes,
    ZZZScheduleNotes,
)
from utility import EmbedTemplate, get_app_command_mention
from utility.custom_log import SlashCommandLogger

from .ui import (
    DailyRewardOptionsView,
    GenshinNotesThresholdModal,
    StarrailCheckNotesThresholdModal,
    ZZZCheckNotesThresholdModal,
)


class ScheduleCommandCog(commands.Cog, name="Schedule"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 設定自動排程功能的斜線指令
    @app_commands.command(
        name="schedule", description="Set the schedule function (Hoyolab daily sign -in, resin full reminder)"
    )
    @app_commands.rename(function="function", switch="switch")
    @app_commands.describe(function="Choose the function to execute the schedule", switch="Choose to open or close this function")
    @app_commands.choices(
        function=[
            Choice(name="① Display use instructions", value="HELP"),
            Choice(name="② Message push test", value="TEST"),
            Choice(name="★ Automatic sign -in daily", value="DAILY"),
            Choice(name="★ Reminder (Genshin Impact)", value="GENSHIN_NOTES"),
            Choice(name="★ Reminder (Honkai: Star Rail)", value="STARRAIL_NOTES"),
            Choice(name="★ Reminder (Zenless Zone Zero)", value="ZZZ_NOTES"),
        ],
        switch=[Choice(name="Open or update settings", value="ON"), Choice(name="Close function", value="OFF")],
    )
    @SlashCommandLogger
    async def slash_schedule(
        self,
        interaction: discord.Interaction,
        function: Literal["HELP", "TEST", "DAILY", "GENSHIN_NOTES", "STARRAIL_NOTES", "ZZZ_NOTES"],
        switch: Literal["ON", "OFF"],
    ):
        msg: str | None  # 欲傳給使用者的訊息
        if function == "HELP":  # 排程功能使用說明
            msg = (
                "· Schedules execute functions at specific times, and results are pushed to the channel set by the command\n"
                "· Before setting up, ensure bot has permission to send messages in that channel. If message delivery fails, bot will automatically remove the schedule\n"
                "· To change the push channel, please set up the command again in the new channel\n\n"
                f"· Daily Auto Check-in: Automatically checks in daily according to your set time and game settings. "
                f"Before setting up, use the {get_app_command_mention('daily_check-in')} command to confirm bot can check you in\n"
                f"· Real-time Notes Reminder: Sends reminders when exceeding the set values. Before setting up, use {get_app_command_mention('realtime_notes')} "
                f"command to confirm bot can read your real-time notes information\n\n"
                f"· Check-in Captcha Issue: Currently, Genshin Impact check-ins may encounter captcha issues. You need to use "
                f"{get_app_command_mention('daily_check-in')} command and select 'Set Captcha Verification' option first"
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(msg, title="How to use the schedule function"), ephemeral=True
            )
            return

        if function == "TEST":  # 測試機器人是否能在該頻道推送訊息
            try:
                msg_sent = await interaction.channel.send(embed=EmbedTemplate.normal("Test Push Messages..."))  # type: ignore
            except Exception:
                await interaction.response.send_message(
                    embed=EmbedTemplate.error(
                        "Bot can't push messages on this channel, please ask the administrator to check if Bot or this channel has the authorization of [Send Message] and [Embed Link]."
                    )
                )
            else:
                await interaction.response.send_message(
                    embed=EmbedTemplate.normal("Test is completed, the small helpers can tweet the message on this channel.")
                )
                await msg_sent.delete()
            return

        # 設定前先確認使用者是否有Cookie資料
        user = await Database.select_one(
            database.User, database.User.discord_id.is_(interaction.user.id)
        )
        match function:
            case "DAILY":
                check, msg = await database.Tool.check_user(user)
            case "GENSHIN_NOTES":
                check, msg = await database.Tool.check_user(
                    user, check_uid=True, game=genshin.Game.GENSHIN
                )
            case "STARRAIL_NOTES":
                check, msg = await database.Tool.check_user(
                    user, check_uid=True, game=genshin.Game.STARRAIL
                )
            case "ZZZ_NOTES":
                check, msg = await database.Tool.check_user(
                    user, check_uid=True, game=genshin.Game.ZZZ
                )

        if check is False:
            await interaction.response.send_message(embed=EmbedTemplate.error(msg))
            return

        if function == "DAILY":  # 每日自動簽到
            if switch == "ON":  # 開啟簽到功能
                # 使用下拉選單讓使用者選擇要簽到的遊戲、要簽到的時間
                options_view = DailyRewardOptionsView(interaction.user)
                await interaction.response.send_message(
                    "Please select in order:\n"
                    "1. Games to check-in (multiple selections allowed)\n"
                    "2. Check-in time\n"
                    f"3. Do you want bot to tag you ({interaction.user.mention}) when checking in?",
                    view=options_view,
                )
                await options_view.wait()
                if options_view.selected_games is None or options_view.is_mention is None:
                    await interaction.edit_original_response(
                        embed=EmbedTemplate.normal("Cancelled"), content=None, view=None
                    )
                    return

                # 新增使用者
                checkin_time = datetime.combine(
                    datetime.now().date(), time(options_view.hour, options_view.minute)
                )
                checkin_user = ScheduleDailyCheckin(
                    discord_id=interaction.user.id,
                    discord_channel_id=interaction.channel_id or 0,
                    is_mention=options_view.is_mention,
                    next_checkin_time=checkin_time,
                    has_genshin=options_view.has_genshin,
                    has_honkai3rd=options_view.has_honkai3rd,
                    has_starrail=options_view.has_starrail,
                    has_zzz=options_view.has_zzz,
                    has_themis=options_view.has_themis,
                    has_themis_tw=options_view.has_themis_tw,
                )
                if checkin_user.next_checkin_time < datetime.now():
                    checkin_user.update_next_checkin_time()
                await Database.insert_or_replace(checkin_user)

                await interaction.edit_original_response(
                    embed = EmbedTemplate.normal(
                        f"{options_view.selected_games} Daily auto check-in has been enabled. "
                        f"bot {'will' if options_view.is_mention else 'will not'} tag you during check-in. "
                        f"Check-in time is approximately every day at {options_view.hour:02d}:{options_view.minute:02d}"
                    ),
                    content=None,
                    view=None,
                )

            elif switch == "OFF":  # 關閉簽到功能
                await Database.delete(
                    ScheduleDailyCheckin, ScheduleDailyCheckin.discord_id.is_(interaction.user.id)
                )
                await interaction.response.send_message(
                    embed=EmbedTemplate.normal("Daily Auto Check-In is turned off")
                )

        elif function == "GENSHIN_NOTES":  # 原神即時便箋檢查提醒
            if switch == "ON":  # 開啟即時便箋檢查功能
                genshin_setting = await Database.select_one(
                    GenshinScheduleNotes,
                    GenshinScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_modal(GenshinNotesThresholdModal(genshin_setting))
            elif switch == "OFF":  # 關閉即時便箋檢查功能
                await Database.delete(
                    GenshinScheduleNotes,
                    GenshinScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_message(
                    embed=EmbedTemplate.normal("Real-time notes checking reminder for Genshin Impact has been turned off.")
                )

        elif function == "STARRAIL_NOTES":  # 星穹鐵道即時便箋檢查提醒
            if switch == "ON":  # 開啟即時便箋檢查功能
                starrail_setting = await Database.select_one(
                    StarrailScheduleNotes,
                    StarrailScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_modal(
                    StarrailCheckNotesThresholdModal(starrail_setting)
                )
            elif switch == "OFF":  # 關閉即時便箋檢查功能
                await Database.delete(
                    StarrailScheduleNotes,
                    StarrailScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_message(
                    embed=EmbedTemplate.normal("Real-time notes checking reminder for Honkai: Star Rail has been turned off.")
                )

        elif function == "ZZZ_NOTES":  # 絕區零即時便箋檢查提醒
            if switch == "ON":  # 開啟即時便箋檢查功能
                zzz_setting = await Database.select_one(
                    ZZZScheduleNotes,
                    ZZZScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_modal(ZZZCheckNotesThresholdModal(zzz_setting))
            elif switch == "OFF":  # 關閉即時便箋檢查功能
                await Database.delete(
                    ZZZScheduleNotes,
                    ZZZScheduleNotes.discord_id.is_(interaction.user.id),
                )
                await interaction.response.send_message(
                    embed=EmbedTemplate.normal("絕區零即時便箋檢查提醒已關閉")
                )

    # 具有頻道管理訊息權限的人可使用本指令，移除指定使用者的頻道排程設定
    @app_commands.command(
        name="schedule_manage_users", description="For administrator privileges, remove the schedule settings for a specific user."
    )
    @app_commands.rename(function="function", user="user")
    @app_commands.describe(function="Select features to remove")
    @app_commands.choices(
        function=[
            Choice(name="Daily auto sign-in", value="DAILY"),
            Choice(name="Real-time notes reminder (Genshin Impact)", value="GENSHIN_NOTES"),
            Choice(name="Real-time notes reminder (Honkai: Star Rail)", value="STARRAIL_NOTES"),
            Choice(name="Real-time notes reminder (Zenless Zone Zero)", value="ZZZ_NOTES"),
        ]
    )
    @app_commands.default_permissions(manage_messages=True)
    @SlashCommandLogger
    async def slash_remove_user(
        self,
        interaction: discord.Interaction,
        function: Literal["DAILY", "GENSHIN_NOTES", "STARRAIL_NOTES", "ZZZ_NOTES"],
        user: discord.User,
    ):
        channel_id = interaction.channel_id
        if function == "DAILY":
            await Database.delete(
                ScheduleDailyCheckin,
                ScheduleDailyCheckin.discord_id.is_(user.id)
                & ScheduleDailyCheckin.discord_channel_id.is_(channel_id),
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(f"{user.name} The daily automatic check-in has been turned off")
            )
        elif function == "GENSHIN_NOTES":
            await Database.delete(
                GenshinScheduleNotes,
                GenshinScheduleNotes.discord_id.is_(user.id)
                & GenshinScheduleNotes.discord_channel_id.is_(channel_id),
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(f"{user.name} The real-time notes reminder for Genshin Impact has been turned off")
            )
        elif function == "STARRAIL_NOTES":
            await Database.delete(
                StarrailScheduleNotes,
                StarrailScheduleNotes.discord_id.is_(user.id)
                & StarrailScheduleNotes.discord_channel_id.is_(channel_id),
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(f"{user.name} The real-time notes reminder for Honkai: Star Rail has been turned off")
            )
        elif function == "ZZZ_NOTES":
            await Database.delete(
                ZZZScheduleNotes,
                ZZZScheduleNotes.discord_id.is_(user.id)
                & ZZZScheduleNotes.discord_channel_id.is_(channel_id),
            )
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(f"{user.name}的絕區零即時便箋提醒已關閉")
            )

    # 具有頻道管理訊息權限的人可使用本指令，將頻道內所有排程使用者的訊息移動到另一個頻道
    @app_commands.command(
        name="schedule_manage_channel", 
        description="For administrators, move the messages of all scheduled users in this channel to another channel.",
    )
    @app_commands.rename(function="function", dest_channel="channel")
    @app_commands.describe(
        function="Select features to remove", dest_channel="Select which channel to move user notifications to"
    )
    @app_commands.choices(
        function=[
            Choice(name="All", value="All"),
            Choice(name="Daily auto sign-in", value="Daily auto sign-in"),
            Choice(name="Real-time notes reminder (Genshin Impact)", value="Real-time notes reminder (Genshin Impact)"),
            Choice(name="Real-time notes reminder (Honkai: Star Rail)", value="Real-time notes reminder (Honkai: Star Rail)"),
            Choice(name="Real-time notes reminder (Zenless Zone Zero)", value="Real-time notes reminder (Zenless Zone Zero)"),
        ]
    )
    @app_commands.default_permissions(manage_messages=True)
    @SlashCommandLogger
    async def slash_move_users(
        self,
        interaction: discord.Interaction,
        function: Literal[
            "All",
            "Daily auto sign-in",
            "Real-time notes reminder (Genshin Impact)",
            "Real-time notes reminder (Honkai: Star Rail)",
            "Real-time notes reminder (Zenless Zone Zero)",
        ],
        dest_channel: discord.TextChannel | discord.Thread,
    ):
        src_channel = interaction.channel
        if src_channel is None:
            await interaction.response.send_message(embed=EmbedTemplate.error("Channel does not exist"))
            return

        stmt_daily = (
            sqlalchemy.update(ScheduleDailyCheckin)
            .where(ScheduleDailyCheckin.discord_channel_id.is_(src_channel.id))
            .values({ScheduleDailyCheckin.discord_channel_id: dest_channel.id})
        )
        stmt_gs_notes = (
            sqlalchemy.update(GenshinScheduleNotes)
            .where(GenshinScheduleNotes.discord_channel_id.is_(src_channel.id))
            .values({GenshinScheduleNotes.discord_channel_id: dest_channel.id})
        )
        stmt_st_notes = (
            sqlalchemy.update(StarrailScheduleNotes)
            .where(StarrailScheduleNotes.discord_channel_id.is_(src_channel.id))
            .values({StarrailScheduleNotes.discord_channel_id: dest_channel.id})
        )
        stmt_zzz_notes = (
            sqlalchemy.update(ZZZScheduleNotes)
            .where(ZZZScheduleNotes.discord_channel_id.is_(src_channel.id))
            .values({ZZZScheduleNotes.discord_channel_id: dest_channel.id})
        )
        async with Database.sessionmaker() as session:
            if function == "All" or function == "Daily auto sign-in":
                await session.execute(stmt_daily)
            if function == "All" or function == "Real-time notes reminder (Genshin Impact)":
                await session.execute(stmt_gs_notes)
            if function == "All" or function == "Real-time notes reminder (Honkai: Star Rail)":
                await session.execute(stmt_st_notes)
            if function == "全部" or function == "Real-time notes reminder (Zenless Zone Zero)":
                await session.execute(stmt_zzz_notes)
            await session.commit()

        await interaction.response.send_message(
            embed=EmbedTemplate.normal(
                f"Successfully moved {function} notification messages of all users in this channel to {dest_channel.mention} channel"
            )
        )


async def setup(client: commands.Bot):
    await client.add_cog(ScheduleCommandCog(client))
