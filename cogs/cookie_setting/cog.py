import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from utility import EmbedTemplate, custom_log, get_app_command_mention

from .ui import GameSelectionView


class CookieSettingCog(commands.Cog, name="Cookie 設定"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cookie_settings", description="Set Cookie, you must use this command to set cookie before using it for the first time."
    )
    @app_commands.rename(option="options")
    @app_commands.choices(
        option=[
            Choice(name="① Shows how to get cookies", value=0),
            Choice(name="② Submit Acquired Cookies to Bot", value=1),
            Choice(name="③ Displaying information on the use and saving of cookies for Bot.", value=2),
        ]
    )
    @custom_log.SlashCommandLogger
    async def slash_cookie(self, interaction: discord.Interaction, option: int):
        if option == 0:  # 顯示說明如何取得 Cookie
            embed = EmbedTemplate.normal(
                "**1.** Use browser to open [HoYoLAB official website](https://www.hoyolab.com) and login to your account.\n"
                "**2.** Press **F12** to open the browser developer tool.\n"
                "**3.** Switch to the **Application** page (refer to the figure below).\n"
                "**4.** Click on the URL at the bottom of the cookies on the left to see your cookies on the right.\n"
                "**5.** Find **ltuid_v2**, **ltoken_v2**, **ltmid_v2**, and copy the values of these three fields\n"
                f"**6.** Use the command here {get_app_command_mention('cookie_settings')} paste into the appropriate field\n",
                title="Help | Getting Cookies",
            )
            embed.set_image(url="https://i.imgur.com/tgjWuvy.png")
            await interaction.response.send_message(embed=embed)

        elif option == 1:  # 提交已取得的Cookie給小幫手
            view = GameSelectionView()
            await interaction.response.send_message(
                embed=EmbedTemplate.normal(
                    "Please select the game you want to set cookies for. Different games can set cookies for different accounts."
                ),
                view=view,
                ephemeral=True,
            )

        elif option == 2:  # 顯示小幫手Cookie使用與保存告知
            msg = (
                "· The content of the Cookie includes your personal identification code, not your account and password\n"
                "· Therefore, it cannot be used to log in to the game, nor can it change your account and password. The content of the Cookie looks like this: `ltoken_v2=xxxx ltuid_v2=1234 ltmid_v2=yyyy`\n"
                "· Bot stores and uses the Cookie to retrieve your Genshin Impact data from the Hoyolab website and provide services\n"
                "· Bot will store the data in an independent cloud server environment, only connecting to the Discord and Hoyolab servers\n"
                "· You can see more details at [Bahamut's explanation article](https://forum.gamer.com.tw/Co.php?bsn=36730&sn=162433), if you still have concerns, please do not use bot\n"
                "· By submitting the Cookie to bot, you agree to allow bot to store and use your information\n"
                f'· You can delete the data stored in bot at any time, please use the {get_app_command_mention("clear_data")} command\n'
            )
            embed = EmbedTemplate.normal(msg, title="Cookie Use and Retention Information for Bot")
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(client: commands.Bot):
    await client.add_cog(CookieSettingCog(client))
