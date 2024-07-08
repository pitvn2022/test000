import random
from io import BytesIO
from pathlib import Path
from typing import Sequence

import aiohttp
import enkanetwork
import genshin
from PIL import Image, ImageDraw

from database.dataclass import spiral_abyss
from utility import get_server_name

from .common import draw_avatar, draw_text

__all__ = ["draw_abyss_card", "draw_exploration_card", "draw_record_card"]


def draw_rounded_rect(img: Image.Image, pos: tuple[float, float, float, float], **kwargs):
    """畫半透明圓角矩形"""
    transparent = Image.new("RGBA", img.size, 0)
    draw = ImageDraw.Draw(transparent, "RGBA")
    draw.rounded_rectangle(pos, **kwargs)
    img.paste(Image.alpha_composite(img, transparent))


def draw_basic_card(
    avatar_bytes: bytes, uid: int, user_stats: genshin.models.PartialGenshinUserStats
) -> Image.Image:
    img: Image.Image = Image.open(f"data/image/record_card/{random.randint(1, 12)}.jpg")
    img = img.convert("RGBA")

    avatar: Image.Image = Image.open(BytesIO(avatar_bytes)).resize((250, 250))
    draw_avatar(img, avatar, (70, 210))

    draw_rounded_rect(img, (340, 270, 990, 460), radius=30, fill=(0, 0, 0, 120))
    draw_rounded_rect(img, (90, 520, 990, 1810), radius=30, fill=(0, 0, 0, 120))

    info = user_stats.info
    draw_text(
        img, (665, 335), info.nickname, "SourceHanSerifTC-Bold.otf", 88, (255, 255, 255, 255), "mm"
    )
    draw_text(
        img,
        (665, 415),
        f"{get_server_name(info.server)}  Lv.{info.level}  UID:{uid}",
        "SourceHanSansTC-Medium.otf",
        40,
        (255, 255, 255, 255),
        "mm",
    )

    return img


def draw_record_card(
    avatar_bytes: bytes, uid: int, user_stats: genshin.models.PartialGenshinUserStats
) -> BytesIO:
    """製作個人紀錄卡片圖

    ------
    Parameters
    avatar_bytes `bytes`: Discord使用者的頭像圖片，以bytes方式傳入
    uid `int`: 原神角色UID
    user_stats `PartialGenshinUserStats`: 從Hoyolab取得的使用者遊戲紀錄
    ------
    Returns
    `BytesIO`: 製作完成的圖片存在記憶體，回傳file pointer，存取前需要先`seek(0)`
    """
    img = draw_basic_card(avatar_bytes, uid, user_stats)

    white = (255, 255, 255, 255)
    grey = (230, 230, 230, 255)

    s = user_stats.stats
    stat_list = [
        (s.days_active, "Days Active"),
        (s.achievements, "Achievements"),
        (s.characters, "Characters"),
        (s.anemoculi, "Anemoculi"),
        (s.geoculi, "Geoculi"),
        (s.electroculi, "Electroculi"),
        (s.dendroculi, "Dendroculi"),
        (s.hydroculi, "Hydroculi"),
        (s.unlocked_waypoints, "Waypoints"),
        (s.unlocked_domains, "Domains"),
        (s.spiral_abyss, "Spiral Abyss"),
        (s.luxurious_chests, "LuxuriousChests"),
        (s.precious_chests, "PreciousChests"),
        (s.exquisite_chests, "ExquisiteChests"),
        (s.common_chests, "CommonChests"),
        (s.remarkable_chests, "RemarkableChests"),
    ]

    for n, stat in enumerate(stat_list):
        column = int(n % 3)
        row = int(n / 3)
        draw_text(
            img,
            (245 + column * 295, 630 + row * 200),
            str(stat[0]),
            "SourceHanSansTC-Bold.otf",
            80,
            white,
            "mm",
        )
        draw_text(
            img,
            (245 + column * 295, 700 + row * 200),
            str(stat[1]),
            "SourceHanSansTC-Regular.otf",
            40,
            grey,
            "mm",
        )

    img = img.convert("RGB")
    fp = BytesIO()
    img.save(fp, "jpeg", optimize=True, quality=50)
    return fp


def draw_exploration_card(
    avatar_bytes: bytes, uid: int, user_stats: genshin.models.PartialGenshinUserStats
) -> BytesIO:
    """製作個人世界探索度卡片圖

    ------
    Parameters
    avatar_bytes `bytes`: Discord使用者的頭像圖片，以bytes方式傳入
    uid `int`: 原神角色UID
    user_stats `PartialGenshinUserStats`: 從Hoyolab取得的使用者遊戲紀錄
    ------
    Returns
    `BytesIO`: 製作完成的圖片存在記憶體，回傳file pointer，存取前需要先`seek(0)`
    """
    img = draw_basic_card(avatar_bytes, uid, user_stats)

    white = (255, 255, 255, 255)
    grey = (230, 230, 230, 255)

    explored_list = {  # {id: [地名, 探索度]}
        1: ["Mondstadt", 0],
        2: ["Liyue", 0],
        3: ["Dragonspine", 0],
        4: ["Inazuma", 0],
        5: ["Enkanomiya", 0],
        6: ["Chasm-Up", 0],
        7: ["Chasm-Low", 0],
        8: ["Sumeru", 0],
        9: ["Fontaine", 0],
        12: ["Chenyu-Up", 0],
        13: ["Chenyu-South", 0],
    }
    offering_list = [["Frostbearing", 0], ["SakuraFavor", 0], ["Lumenstone", 0], ["DreamTree", 0], ["Lucine", 0]]

    for e in user_stats.explorations:
        if e.id not in explored_list:
            continue
        explored_list[e.id][1] = e.explored

        if e.id == 3 and len(e.offerings) >= 1:  # 3: 雪山
            offering_list[0][1] = e.offerings[0].level
        if e.id == 4 and len(e.offerings) >= 2:  # 4: 稻妻
            offering_list[1][1] = e.offerings[0].level
        if e.id == 6 and len(e.offerings) >= 1:  # 6: 層岩·表
            offering_list[2][1] = e.offerings[0].level
        if e.id == 8 and len(e.offerings) >= 2:  # 8: 須彌
            offering_list[3][1] = e.offerings[0].level
        if e.id == 9 and len(e.offerings) >= 2:  # 9: 楓丹
            offering_list[4][1] = e.offerings[0].level

    stat_list: list[tuple[str, float, str]] = []  # (探索/等級, 數值, 地名)
    for id, e in explored_list.items():
        stat_list.append(("Exploration", e[1], e[0]))
    for o in offering_list:
        stat_list.append(("Level", o[1], o[0]))

    for n, stat in enumerate(stat_list):
        column = int(n % 3)
        row = int(n / 3)
        draw_text(
            img,
            (245 + column * 295, 590 + row * 205),
            stat[0],
            "SourceHanSansTC-Regular.otf",
            30,
            grey,
            "mm",
        )
        draw_text(
            img,
            (245 + column * 295, 643 + row * 205),
            f"{stat[1]:g}",
            "SourceHanSansTC-Bold.otf",
            82,
            white,
            "mm",
        )
        draw_text(
            img,
            (245 + column * 295, 710 + row * 205),
            stat[2],
            "SourceHanSansTC-Regular.otf",
            45,
            grey,
            "mm",
        )

    img = img.convert("RGB")
    fp = BytesIO()
    img.save(fp, "jpeg", optimize=True, quality=50)
    return fp


async def draw_character(
    img: Image.Image,
    character: genshin.models.AbyssCharacter,
    size: tuple[int, int],
    pos: tuple[int, int],
):
    """畫角色頭像，包含背景框

    ------
    Parameters
    character `AbyssCharacter`: 角色資料
    size `Tuple[int, int]`: 背景框大小
    pos `Tuple[int, int]`: 要畫的左上角位置
    """
    background = (
        Image.open(f"data/image/character/char_{character.rarity}star_bg.png")
        .convert("RGBA")
        .resize(size)
    )
    avatar_file = Path(f"data/image/character/{character.id}.png")
    # 若本地沒有圖檔則從URL下載
    if avatar_file.exists() is False:
        avatar_img: bytes | None = None
        async with aiohttp.ClientSession() as session:
            # 嘗試從 Enkanetwork CDN 取得圖片
            try:
                enka_cdn = enkanetwork.Assets.character(character.id).images.icon.url  # type: ignore
            except Exception:
                pass
            else:
                async with session.get(enka_cdn) as resp:
                    if resp.status == 200:
                        avatar_img = await resp.read()
            # 當從 Enkanetwork CDN 取得圖片失敗時改用 Ambr
            if avatar_img is None:
                icon_name = character.icon.split("/")[-1]  # UI_AvatarIcon_XXXX.png
                ambr_url = "https://api.ambr.top/assets/UI/" + icon_name
                async with session.get(ambr_url) as resp:
                    if resp.status == 200:
                        avatar_img = await resp.read()
        if avatar_img is None:
            return
        else:
            with open(avatar_file, "wb") as fp:
                fp.write(avatar_img)
    avatar = Image.open(avatar_file).convert("RGBA").resize((size[0], size[0]))
    img.paste(background, pos, background)
    img.paste(avatar, pos, avatar)


def draw_abyss_star(
    img: Image.Image, number: int, size: tuple[int, int], pos: tuple[float, float]
):
    """畫深淵星星數量

    ------
    Parameters
    number `int`: 星星數量
    size `Tuple[int, int]`: 單顆星星大小
    pos `Tuple[float, float]`: 正中央位置，星星會自動置中
    """
    star = Image.open("data/image/spiral_abyss/star.png").convert("RGBA").resize(size)
    pad = 5
    upper_left = (pos[0] - number / 2 * size[0] - (number - 1) * pad, pos[1] - size[1] / 2)
    for i in range(0, number):
        img.paste(star, (int(upper_left[0] + i * (size[0] + 2 * pad)), int(upper_left[1])), star)


async def draw_abyss_card(
    abyss_floor: genshin.models.Floor,
    characters: Sequence[spiral_abyss.CharacterData] | None = None,
) -> BytesIO:
    """繪製深淵樓層紀錄圖，包含每一間星數以及上下半所使用的角色和等級

    ------
    Parameters
    abyss_floor `Floor`: 深境螺旋某一樓層的資料
    characters `Sequence[Character]`: 玩家的角色資料
    ------
    Returns
    `BytesIO`: 製作完成的圖片存在記憶體，回傳file pointer，存取前需要先`seek(0)`
    """
    img = Image.open("data/image/spiral_abyss/background_blur.jpg")
    img = img.convert("RGBA")

    character_size = (172, 210)
    character_pad = 8
    # 顯示第幾層深淵
    draw_text(
        img,
        (1050, 145),
        f"{abyss_floor.floor}",
        "SourceHanSansTC-Bold.otf",
        85,
        (50, 50, 50),
        "mm",
    )
    # 繪製每一間
    for i, chamber in enumerate(abyss_floor.chambers):
        # 顯示此間星星數
        draw_abyss_star(img, chamber.stars, (70, 70), (1050, 500 + i * 400))
        # 上下半間
        for j, battle in enumerate(chamber.battles):
            middle = 453 + j * 1196
            left_upper = (
                int(
                    middle
                    - len(battle.characters) / 2 * character_size[0]
                    - (len(battle.characters) - 1) * character_pad
                ),
                395 + i * 400,
            )
            for k, character in enumerate(battle.characters):
                x = left_upper[0] + k * (character_size[0] + 2 * character_pad)
                y = left_upper[1]
                await draw_character(img, character, (172, 210), (x, y))
                if characters is not None:
                    constellation = next(
                        (c.constellation for c in characters if c.id == character.id), 0
                    )  # 匹配角色ID並取得命座
                    text = f"C{constellation} Level {character.level}"
                else:
                    text = f"Level {character.level}"
                draw_text(
                    img,
                    (x + character_size[0] / 2, y + character_size[1] * 0.90),
                    text,
                    "SourceHanSansTC-Regular.otf",
                    30,
                    (50, 50, 50),
                    "mm",
                )
    img = img.convert("RGB")
    fp = BytesIO()
    img.save(fp, "jpeg", optimize=True, quality=40)
    return fp
