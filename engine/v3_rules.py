# -*- coding: utf-8 -*-
"""Legacy engagement tiers, retained for compatibility; not content-quality labels.

2026-11-03: R9 describes support but never raises a tier. In particular it cannot
undo duration/utility caps. The new craft/resonance workflow is review_miner.py.
"""
T_GOD, T_GOOD, T_NORMAL = 0.93, 0.85, 0.72
DUR_EXEC, DUR_CAP = 150, 30
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
    elif dur and dur <= DUR_EXEC and tier == "神作候选":
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
    # R9 only describes support. Support is not evidence of craft/resonance,
    # and must never undo the duration/utility caps applied above.
    if coin_rate > fav_rate or coin_rate > like_rate:
        if pct >= R9_GUARD_PCT:
            why = "币>赞" if coin_rate > like_rate else "币>藏"
            firings.append(f"R9声援信号({why},不提档)")
    return tier, firings
