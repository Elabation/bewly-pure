"""Recognize episode markers and route ambiguous title numbers to review."""
import re
import unicodedata
from datetime import date


_ORDINAL = r"[0-9零〇一二两三四五六七八九十百千万]+"
_EPISODE = re.compile(
    r"第\s*" + _ORDINAL + r"\s*[集话話章回期季部]"
    r"|(?:更新至|连载至|更新到)\s*(?:第\s*)?" + _ORDINAL +
    r"|(?<![a-z0-9])s\s*\d+\s*e\s*\d+(?!\d)"
    r"|(?:连续剧|短剧|漫剧|动态漫画|有声小说).{0,16}\d+\s*[集话話]"
)
_NUMBER = re.compile(r"(?<![\d.])\d{2,}(?!\d|\.\d)")
_UNIT = re.compile(
    r"\s*(?:周年|年|月|日|天|小时|分钟|秒|帧|岁|元|万|亿|期货|人|抽|册|块|刀|攻速|"
    r"公里|千米|米|℃|%|fps\b|hz\b|khz\b|kb\b|mb\b|gb\b|"
    r"p\b|k\b|×|x\s*\d)"
)


_ANIME_GAME = re.compile(
    r"原神|崩坏|星穹|星铁|绝区零|未定事件簿|明日方舟|蔚蓝档案|碧蓝档案|blue\s*archive"
    r"|碧蓝航线|少女前线|公主连结|fgo|fate\s*(?:/|系列|zero|stay)|阴阳师|战双|鸣潮|重返未来"
    r"|无期迷途|第五人格|偶像梦幻祭|忘川风华录|7日之都|七日之都|7都|pjsk|プロセカ|世界计划|边狱巴士|limbus|逆转裁判|弹丸论破"
    r"|赛马娘|东方project|车万|一目连|茨木|酒吞|大天狗|玉藻前|妖刀姬|御馔津|彼岸花"
    r"|派蒙|雷电将军|钟离|可莉|胡桃|甘雨|芙宁娜|纳西妲|阿米娅|凯尔希|斯卡蒂|史尔特尔"
    r"|璃月|蒙德|稻妻|须弥|枫丹|纳塔|开拓者|旅行者|愚人众|执行官")


def anime_game_flag(title):
    """标题点名二次元游戏或其中角色时为 True（用户指定：这类作品一律不收录）。"""
    return bool(_ANIME_GAME.search(unicodedata.normalize("NFKC", title or "").lower()))


def numeric_title_flag(title):
    title = unicodedata.normalize("NFKC", title or "").lower()
    if _EPISODE.search(title):
        return "series"
    for match in _NUMBER.finditer(title):
        number = match.group()
        if len(number) == 4 and "1900" <= number <= "2099":
            continue
        if is_calendar_date(number):
            continue
        if _UNIT.match(title[match.end():]):
            continue
        if len(number) >= 3 or not title[match.end():].strip(" 】]）)！!。．.？?"):
            return "number_review"
    return None


def is_calendar_date(number):
    if re.fullmatch(r"(?:20)?(?:1[5-9]|2[0-9]|30)[0-1][0-9][0-3][0-9]", number) is None:
        return False
    full = "20" + number if len(number) == 6 else number
    try:
        date(int(full[:4]), int(full[4:6]), int(full[6:]))
    except ValueError:
        return False
    return True
