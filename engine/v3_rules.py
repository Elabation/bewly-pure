# -*- coding: utf-8 -*-
"""v3 规则引擎 · 单一定义源（R9 版）。

Elabation 立法（2026-09-04）：R9 声援提档——
  · 币 > 赞 或 币 > 收藏（计数比较，等价于币率比较）
  · 护栏：带内币率百分位 ≥ 0.50（不低于带内中位，防零总量比率说谎——PvZ 案教训）
  · 满足则从基础档升一级（垃圾→一般→优秀→神，神封顶）
规则次序：pct 定基础档 → R2 时长 → R3 吃灰（fav 系惩罚）→ R9 声援（coin 系奖励）。
R3 与 R9 条件天然互斥（fav/coin>8 vs coin>fav），不会互相抵消。
全管线 import 本文件，改口径只改这里。
"""
T_GOD, T_GOOD, T_NORMAL = 0.93, 0.85, 0.72
DUR_EXEC, DUR_CAP = 90, 30
R_FAVCOIN, R_FAVRATE = 8.0, 0.15
R_EDGE_LIKE, R_EDGE_COIN, R_EDGE_FAV = 0.20, 0.02, 0.10
R9_GUARD_PCT = 0.50
TIERS = ["垃圾候选", "一般候选", "优秀候选", "神作候选"]

# R10 博同情降级（Elabation 立法 2026-09-04）：求助/感谢/感动/苦难类标题特征过强者降一级。
# 强特征单次即降；弱特征累计 ≥2 降。R10 触发时压制 R9（博同情视频的「声援币」不是工艺信号）。
R10_STRONG = ["求助", "众筹", "水滴筹", "救救", "化疗", "白血病", "病危", "尿毒症", "渐冻", "重症", "病重", "卖惨", "绝症"]
R10_WEAK = ["感谢", "感恩", "感动", "泪目", "妈妈", "爸爸", "奶奶", "爷爷", "外婆", "外公",
            "生病", "手术", "续命", "苦难", "艰难", "负债", "落魄", "流浪", "抗体", "药"]


def r10_score(title):
    """返回 (hit, desc)：hit=True 表示应降级。"""
    t = title or ""
    hits = [w for w in R10_STRONG if w in t]
    if hits:
        return True, "R10博同情降级(强:" + "/".join(hits[:3]) + ")"
    weak = [w for w in R10_WEAK if w in t]
    if len(weak) >= 2:
        return True, "R10博同情降级(弱:" + "/".join(weak[:3]) + ")"
    return False, ""


def v3_tier(pct, dur, fav_rate, coin_rate, like_rate, title=""):
    """返回 (tier, firings)。pct=None → 无数据。"""
    if pct is None:
        return "无数据", []
    tier = "一般候选"
    if pct >= T_GOD:
        tier = "神作候选"
    elif pct >= T_GOOD:
        tier = "优秀候选"
    elif pct < T_NORMAL:
        tier = "垃圾候选"
    firings = []
    if dur and dur < DUR_CAP:
        if tier in ("神作候选", "优秀候选"):
            tier = "一般候选"
        firings.append(f"R2a<{DUR_CAP}s")
    elif dur and dur < DUR_EXEC and tier == "神作候选":
        tier = "优秀候选"
        firings.append(f"R2b<{DUR_EXEC}s斩神")
    fc = fav_rate / max(coin_rate, 1e-6)
    if fc > R_FAVCOIN and fav_rate > R_FAVRATE:
        if tier == "神作候选":
            tier = "优秀候选"
        firings.append(f"R3吃灰fc={fc:.0f}")
    if like_rate > R_EDGE_LIKE and coin_rate < R_EDGE_COIN and fav_rate > R_EDGE_FAV:
        firings.append("R4擦边三连")
    # R10 博同情降级（标题特征；触发时压制 R9——博同情的声援币不是工艺信号）
    r10hit, r10desc = r10_score(title)
    if r10hit:
        if tier != "垃圾候选":
            tier = TIERS[TIERS.index(tier) - 1]
        firings.append(r10desc)
        return tier, firings
    # R9 声援提档（coin 系奖励，与 R3 的 fav 系惩罚互为镜像）
    if coin_rate > fav_rate or coin_rate > like_rate:
        if pct >= R9_GUARD_PCT and tier != "神作候选":
            tier = TIERS[TIERS.index(tier) + 1]
            why = "币>赞" if coin_rate > like_rate else "币>藏"
            firings.append(f"R9声援提档({why},pct={pct:.2f})")
    return tier, firings
