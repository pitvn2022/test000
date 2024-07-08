import asyncio
import random
import typing
from datetime import datetime, time, timedelta

import discord
import enkanetwork
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks

from genshin_py import auto_task
from utility import SlashCommandLogger, config


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.presence_string: list[str] = ["Hoyolab"]
        self.change_presence.start()
        self.refresh_genshin_db.start()

    async def cog_unload(self) -> None:
        self.change_presence.cancel()
        self.refresh_genshin_db.cancel()

    # /status指令：顯示機器人相關狀態
    @app_commands.command(name="status", description="Show Bot Status")
    @app_commands.choices(
        option=[
            Choice(name="Bot connection delay", value="BOT_LATENCY"),
            Choice(name="Number of connected servers", value="SERVER_COUNT"),
            Choice(name="Connected Server Name", value="SERVER_NAMES"),
        ]
    )
    @SlashCommandLogger
    async def slash_status(self, interaction: discord.Interaction, option: str):
        match option:
            case "BOT_LATENCY":
                await interaction.response.send_message(f"Delay: {round(self.bot.latency*1000)} ms")
            case "SERVER_COUNT":
                await interaction.response.send_message(f"Connected {len(self.bot.guilds)} servers")
            case "SERVER_NAMES":
                await interaction.response.defer()
                names = [guild.name for guild in self.bot.guilds]
                for i in range(0, len(self.bot.guilds), 100):
                    msg = "、".join(names[i : i + 100])
                    embed = discord.Embed(title=f"Connected Server Name({i + 1})", description=msg)
                    await interaction.followup.send(embed=embed)

    # /system指令：更改機器人狀態、執行任務...
    @app_commands.command(name="system", description="Use system commands (change bot status, execute tasks...)")
    @app_commands.rename(option="options", param="parameters")
    @app_commands.choices(
        option=[
            Choice(name="Customized Bot Status", value="CHANGE_PRESENCE"),
            Choice(name="Run now to get your daily rewards", value="CLAIM_DAILY_REWARD"),
            Choice(name="Update Enka New Release Information", value="UPDATE_ENKA_ASSETS"),
        ]
    )
    @SlashCommandLogger
    async def slash_system(
        self, interaction: discord.Interaction, option: str, param: typing.Optional[str] = None
    ):
        await interaction.response.defer()
        match option:
            case "CHANGE_PRESENCE":  # 更改機器人狀態
                if param is not None:
                    self.presence_string = param.split(",")
                    await interaction.edit_original_response(
                        content=f"Presence list has been changed to:{self.presence_string}"
                    )
            case "CLAIM_DAILY_REWARD":  # 立即執行領取每日獎勵
                await interaction.edit_original_response(content="Start Daily Auto Check-In")
                asyncio.create_task(auto_task.DailyReward.execute(self.bot))
            case "UPDATE_ENKA_ASSETS":  # 更新 Enka 新版本素材資料
                client = enkanetwork.EnkaNetworkAPI()
                async with client:
                    await client.update_assets()
                enkanetwork.Assets(lang=enkanetwork.Language.EN)
                await interaction.edit_original_response(content="Enka data update completed")

    # /config指令：設定config配置檔案的參數值
    @app_commands.command(name="config", description="Change the configuration")
    @app_commands.rename(option="options", value="number")
    @app_commands.choices(
        option=[
            Choice(name="schedule_daily_reward_time", value="schedule_daily_reward_time"),
            Choice(
                name="schedule_check_resin_interval",
                value="schedule_check_resin_interval",
            ),
            Choice(name="schedule_loop_delay", value="schedule_loop_delay"),
        ]
    )
    @SlashCommandLogger
    async def slash_config(self, interaction: discord.Interaction, option: str, value: str):
        if option in [
            "schedule_daily_reward_time",
            "schedule_check_resin_interval",
        ]:
            setattr(config, option, int(value))
        elif option in ["schedule_loop_delay"]:
            setattr(config, option, float(value))
        await interaction.response.send_message(f"已將{option}的值設為: {value}")

    # /maintenance指令：設定遊戲維護時間
    @app_commands.command(name="maintenance", description="Set the game maintenance time, enter 0 to set the maintenance time to off.")
    @app_commands.rename(month="month", day="day", hour="hour", duration="few_hours")
    @SlashCommandLogger
    async def slash_maintenance(
        self,
        interaction: discord.Interaction,
        month: int,
        day: int,
        hour: int = 6,
        duration: int = 5,
    ):
        if month == 0 or day == 0:
            config.game_maintenance_time = None
            await interaction.response.send_message("Maintenance time has been set to: Off")
        else:
            now = datetime.now()
            start_time = datetime(
                (now.year if month >= now.month else now.year + 1), month, day, hour
            )
            end_time = start_time + timedelta(hours=duration)
            config.game_maintenance_time = (start_time, end_time)
            await interaction.response.send_message(
                f"The maintenance time has been set to：{start_time} ~ {end_time}\n"
                + "If the daily autosign-in time is within this range, use the /config command to change the daily autosign-in time."
            )

    # ======== Loop Task ========

    # 每一定時間更改機器人狀態
    @tasks.loop(minutes=1)
    async def change_presence(self):
        length = len(self.presence_string)
        n = random.randint(0, length)
        if n < length:
            await self.bot.change_presence(activity=discord.Game(self.presence_string[n]))
        elif n == length:
            await self.bot.change_presence(activity=discord.Game(f" in {len(self.bot.guilds)} Servers"))

    @change_presence.before_loop
    async def before_change_presence(self):
        await self.bot.wait_until_ready()

    # 每天定時重整 genshin_db API 資料
    @tasks.loop(time=time(hour=20, minute=00))
    async def refresh_genshin_db(self):
        await self.bot.reload_extension("cogs.data_search.cog")

    @refresh_genshin_db.before_loop
    async def before_refresh_genshin_db(self):
        await self.bot.wait_until_ready()


async def setup(client: commands.Bot):
    await client.add_cog(Admin(client), guild=discord.Object(id=config.test_server_id))
