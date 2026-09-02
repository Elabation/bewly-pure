# -*- coding: utf-8 -*-
"""F7 几何 · CBI 分档单一定义源（Single Source of Truth）

Elabation 定档（2026-09-02）：1 正常 / 2 优秀 / 3 神。
数据纪律（刻入 DNA）：
  1. 原始挖掘文件（favmine_*.json）immutable——统计/口径改动永远不写回；
  2. tier 一律以 cbi 数值现算（cbi_scale.tier_of），不信任存量 tier 字符串；
  3. 分档阈值只在此处定义，全管线 import——改口径只改这一个文件。
"""
SCALE = {"low": 0.5, "normal": 1.0, "good": 2.0, "high": 3.0}
MIN_VIEW = 3000  # 不足此播放量不判档（unproven）
GOOD_TIERS = ("high", "good")   # 「优秀及以上」= CBI>=2.0
GOD_TIERS = ("high",)           # 「神作」= CBI>=3.0


def tier_of(cbi: float, view: int) -> str:
    if not view or view < MIN_VIEW:
        return "unproven"
    if cbi >= SCALE["high"]:
        return "high"      # 神
    if cbi >= SCALE["good"]:
        return "good"      # 优秀
    if cbi >= SCALE["normal"]:
        return "normal"    # 正常
    if cbi >= SCALE["low"]:
        return "low"
    return "junk"
