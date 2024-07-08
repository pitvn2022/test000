import asyncio
from typing import Mapping, Sequence

import genshin
import sentry_sdk

import database
from database import Database, GeetestChallenge, User
from utility import LOG, config, get_app_command_mention

from ..errors import UserDataNotFound
from ..errors_decorator import generalErrorHandler


async def get_client(
    user_id: int,
    *,
    game: genshin.Game = genshin.Game.GENSHIN,
    check_uid=True,
) -> genshin.Client:
    """設定並取得原神 API 的 Client

    Parameters
    ------
    user_id: `int`
        使用者 Discord ID
    game: `genshin.Game`
        要取得的遊戲 Client
    check_uid: `bool`
        是否檢查 UID

    Returns
    ------
    `genshin.Client`
        原神 API 的 Client
    """
    user = await Database.select_one(User, User.discord_id.is_(user_id))
    check, msg = await database.Tool.check_user(user, check_uid=check_uid, game=game)
    if check is False or user is None:
        raise UserDataNotFound(msg)

    client = genshin.Client(lang="vi-vn")
    match game:
        case genshin.Game.GENSHIN:
            uid = user.uid_genshin or 0
            cookie = user.cookie_genshin or user.cookie_default
            if len(str(uid)) == 9 and str(uid)[0] in ["1", "2", "5"]:
                client = genshin.Client(region=genshin.Region.CHINESE, lang="zh-cn")
        case genshin.Game.HONKAI:
            uid = user.uid_honkai3rd or 0
            cookie = user.cookie_honkai3rd or user.cookie_default
        case genshin.Game.STARRAIL:
            uid = user.uid_starrail or 0
            cookie = user.cookie_starrail or user.cookie_default
            if str(uid)[0] in ["1", "2", "5"]:
                client = genshin.Client(region=genshin.Region.CHINESE, lang="zh-cn")
        case genshin.Game.ZZZ:
            uid = user.uid_zzz or 0
            cookie = user.cookie_zzz or user.cookie_default
        case genshin.Game.THEMIS:
            uid = 0
            cookie = user.cookie_themis or user.cookie_default
        case genshin.Game.THEMIS_TW:
            uid = 0
            cookie = user.cookie_themis or user.cookie_default
        case _:
            uid = 0
            cookie = user.cookie_default

    client.set_cookies(cookie)
    client.default_game = game
    client.uid = uid
    client.proxy = config.genshin_py_proxy_server
    return client


@generalErrorHandler
async def get_game_accounts(
    user_id: int, game: genshin.Game
) -> Sequence[genshin.models.GenshinAccount]:
    """取得同一個Hoyolab帳號下，指定遊戲的所有伺服器帳號

    Parameters
    ------
    user_id: `int`
        使用者 Discord ID
    game: `genshin.Game`
        指定遊戲

    Returns
    ------
    `Sequence[GenshinAccount]`
        查詢結果
    """
    client = await get_client(user_id, game=game, check_uid=False)
    accounts = await client.get_game_accounts()
    return [account for account in accounts if account.game == game]


@generalErrorHandler
async def set_cookie(user_id: int, cookie: str, games: Sequence[genshin.Game]) -> str:
    """根據遊戲設定使用者 Cookie

    Parameters
    ------
    user_id: `int`
        使用者Discord ID
    cookie: `str`
        Hoyolab cookie
    games: `Sequence[genshin.Game]`
        要設定哪些遊戲的 cookie

    Returns
    ------
    `str`
        回覆給使用者的訊息
    """
    LOG.Info(f"設定 {LOG.User(user_id)} 的Cookie：{cookie}")

    client = genshin.Client(lang="vi-vn")
    client.set_cookies(cookie)

    # 先以國際服 client 取得帳號資訊，若失敗則嘗試使用中國服 client
    try:
        accounts = await client.get_game_accounts()
    except genshin.errors.InvalidCookies:
        client.region = genshin.Region.CHINESE
        accounts = await client.get_game_accounts()
    gs_accounts = [a for a in accounts if a.game == genshin.Game.GENSHIN]
    hk3_accounts = [a for a in accounts if a.game == genshin.Game.HONKAI]
    sr_accounts = [a for a in accounts if a.game == genshin.Game.STARRAIL]
    zzz_accounts = [a for a in accounts if a.game == genshin.Game.ZZZ]

    user = await Database.select_one(User, User.discord_id.is_(user_id))
    if user is None:
        user = User(user_id)

    # 個別遊戲設定 cookie、UID
    character_list: list[str] = []  # 保存角色數量訊息
    user.cookie_default = cookie
    if genshin.Game.GENSHIN in games:
        user.cookie_genshin = cookie
        if len(gs_accounts) == 1:
            user.uid_genshin = gs_accounts[0].uid
        elif len(gs_accounts) > 1:
            character_list.append(f"{len(gs_accounts)}Genshin Impact Character")

    if genshin.Game.HONKAI in games:
        user.cookie_honkai3rd = cookie
        if len(hk3_accounts) == 1:
            user.uid_honkai3rd = hk3_accounts[0].uid
        elif len(hk3_accounts) > 1:
            character_list.append(f"{len(hk3_accounts)}Honkai Impact 3 Character")

    if genshin.Game.STARRAIL in games:
        user.cookie_starrail = cookie
        if len(sr_accounts) == 1:
            user.uid_starrail = sr_accounts[0].uid
        if len(sr_accounts) > 1:
            character_list.append(f"{len(sr_accounts)}Honkai: Star Rail Character")

    if genshin.Game.ZZZ in games:
        user.cookie_zzz = cookie
        if len(zzz_accounts) == 1:
            user.uid_zzz = zzz_accounts[0].uid
        if len(zzz_accounts) > 1:
            character_list.append(f"{len(zzz_accounts)}Zenless Zone Zero Character")

    if genshin.Game.THEMIS in games:
        user.cookie_themis = cookie

    await Database.insert_or_replace(user)
    LOG.Info(f"{LOG.User(user_id)} Cookie Setting Successful")

    result = "Cookie has been set！"
    # 若有多名角色，則提示使用者要設定 UID
    if len(character_list) > 0:
        result += (
            f"\nYour account has a total of{'、'.join(character_list)}，"
            + f"Please use {get_app_command_mention('uid settings')} Specify the roles to be saved。"
        )
    return result


async def claim_daily_reward(
    user_id: int,
    *,
    has_genshin: bool = False,
    has_honkai3rd: bool = False,
    has_starrail: bool = False,
    has_zzz: bool = False,
    has_themis: bool = False,
    has_themis_tw: bool = False,
    is_geetest: bool = False,
) -> str:
    """為使用者在 Hoyolab 簽到

    Parameters
    ------
    user_id: `int`
        使用者Discord ID
    has_genshin: `bool`
        是否簽到原神
    honkai3rd: `bool`
        是否簽到崩壞3
    has_starrail: `bool`
        是否簽到星穹鐵道
    has_zzz: `bool`
        是否簽到絕區零
    has_themis: `bool`
        是否簽到未定事件簿(國際服)
    has_themis_tw: `bool`
        是否簽到未定事件簿(台服)
    is_geetest: `bool`
        是否要設定 Geetest 驗證，若 True 的話返回設定網頁連結

    Returns
    ------
    `str`
        回覆給使用者的訊息
    """
    try:
        client = await get_client(user_id, check_uid=False)
    except Exception as e:
        return str(e)

    # Hoyolab 社群簽到
    try:
        await client.check_in_community()
    except genshin.errors.GenshinException as e:
        if e.retcode != 2001:
            LOG.FuncExceptionLog(user_id, "claimDailyReward: Hoyolab", e)
    except Exception as e:
        LOG.FuncExceptionLog(user_id, "claimDailyReward: Hoyolab", e)

    # 遊戲簽到
    if (
        any([has_genshin, has_honkai3rd, has_starrail, has_zzz, has_themis, has_themis_tw])
        is False
    ):
        return "Did not select any game to sign in"

    # 使用者保存的 geetest 驗證資料
    gt_challenge: GeetestChallenge | None = None
    if not is_geetest:  # 若要設定新的 geetest 驗證，則不從資料庫取出舊的資料帶入 header
        gt_challenge = await Database.select_one(
            GeetestChallenge, GeetestChallenge.discord_id.is_(user_id)
        )

    result = ""
    if has_genshin:
        challenge = gt_challenge.genshin if gt_challenge else None
        client = await get_client(user_id, game=genshin.Game.GENSHIN, check_uid=False)
        result += await _claim_reward(user_id, client, genshin.Game.GENSHIN, is_geetest, challenge)
    if has_honkai3rd:
        challenge = gt_challenge.honkai3rd if gt_challenge else None
        client = await get_client(user_id, game=genshin.Game.HONKAI, check_uid=False)
        result += await _claim_reward(user_id, client, genshin.Game.HONKAI, is_geetest, challenge)
    if has_starrail:
        challenge = gt_challenge.starrail if gt_challenge else None
        client = await get_client(user_id, game=genshin.Game.STARRAIL, check_uid=False)
        result += await _claim_reward(
            user_id, client, genshin.Game.STARRAIL, is_geetest, challenge
        )
    if has_zzz:
        client = await get_client(user_id, game=genshin.Game.ZZZ, check_uid=False)
        result += await _claim_reward(user_id, client, genshin.Game.ZZZ)
    if has_themis:
        client = await get_client(user_id, game=genshin.Game.THEMIS, check_uid=False)
        result += await _claim_reward(user_id, client, genshin.Game.THEMIS)
    if has_themis_tw:
        client = await get_client(user_id, game=genshin.Game.THEMIS_TW, check_uid=False)
        result += await _claim_reward(user_id, client, genshin.Game.THEMIS_TW)

    return result


async def _claim_reward(
    user_id: int,
    client: genshin.Client,
    game: genshin.Game,
    is_geetest: bool = False,
    gt_challenge: Mapping[str, str] | None = None,
    retry: int = 5,
) -> str:
    """遊戲簽到函式"""
    game_name = {
        genshin.Game.GENSHIN: "Genshin Impact",
        genshin.Game.HONKAI: "Honkai Impact 3",
        genshin.Game.STARRAIL: "Honkai: Star Rail",
        genshin.Game.ZZZ: "Zenless Zone Zero",
        genshin.Game.THEMIS: "Tears of Themis",
        genshin.Game.THEMIS_TW: "Tears of Themis(TW)",
    }

    try:
        reward = await client.claim_daily_reward(game=game, challenge=gt_challenge)
    except genshin.errors.AlreadyClaimed:
        return f"{game_name[game]}Today's reward has already been claimed.！"
    except genshin.errors.InvalidCookies:
        return "Cookie has expired, please get a new one from Hoyolab.。"
    except genshin.errors.DailyGeetestTriggered as exception:
        # 使用者選擇設定圖形驗證，回傳網址
        if is_geetest is True and config.geetest_solver_url is not None:
            url = config.geetest_solver_url
            url += f"/geetest/{game}/{user_id}?gt={exception.gt}&challenge={exception.challenge}"
            return f"Please go to the website to unlock the graphic validation: [click me to open the link].({url})\nIf an error occurs, use this command again to regenerate the link."
        # 提示使用者可以設定圖形驗證
        if config.geetest_solver_url is not None:
            command_str = get_app_command_mention("daily每日簽到")
            return f"{game_name[game]}Failed to sign in: Graphical validation is blocked. {command_str} Command to select Setup Graphic Validation "
        link: str = {
            genshin.Game.GENSHIN: "https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481",
            genshin.Game.HONKAI: "https://act.hoyolab.com/bbs/event/signin-bh3/index.html?act_id=e202110291205111",
            genshin.Game.STARRAIL: "https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311",
            genshin.Game.ZZZ: "https://act.hoyolab.com/bbs/event/signin/zzz/index.html?act_id=e202406031448091",
        }.get(game, "")
        return f"{game_name[game]}Failed to sign in: Graphical verification is blocked, please go to [Official Website].({link}) Getting Started。"
    except Exception as e:
        if isinstance(e, genshin.errors.GenshinException) and e.retcode == -10002:
            return f"{game_name[game]}Sign-in failed, no character information was found for the currently logged-in account."
        if isinstance(e, genshin.errors.GenshinException) and e.retcode == 50000:
            return f"{game_name[game]}The request failed. Please try again later."

        LOG.FuncExceptionLog(user_id, "claimDailyReward", e)
        if retry > 0:
            await asyncio.sleep(1)
            return await _claim_reward(user_id, client, game, is_geetest, gt_challenge, retry - 1)

        LOG.Error(f"{LOG.User(user_id)} {game_name[game]}Failed to sign in")
        sentry_sdk.capture_exception(e)
        return f"{game_name[game]}Failed to sign in：{e}。"
    else:
        return f"{game_name[game]} Sign in today and get {reward.amount}x {reward.name}！"
