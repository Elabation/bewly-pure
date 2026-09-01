# 手机端（免 root）方案 v1.0 —— 已落地

> 主线已实现：`userscript/bilibili-clean-mobile.user.js`（m.bilibili.com 全站）。
> 判定核心与 PC 版逐字段一致（config v2：CBI 感谢指数 R2 / F7 加权感谢率 R3 / 硬偏好 R1 / 标题签名 R7 / 乞讨打标 R8 / 官方豁免 R4）。

## 已验证的三股流（2026-09-01 探测，engine/probe_mobile*.py）

| 流 | 机制 | 数据字段 | 判定方式 |
|---|---|---|---|
| A. 首页热榜 | SSR：`window.__INITIAL_STATE__.home.hotList`（result + extra.list 共 ~100 条） | stat 全字段（view/like/coin/favorite）+ duration + tname | 同步判定；dimension 缺失走 view API 补竖屏 |
| B. 频道流 | fetch/XHR 劫持 `GET /x/web-interface/region/feed/rcmd`（参数页面自带：from_region/display_id/request_cnt/device=m_station/plat=15） | `data.archives[]`（archives 家族标准字段） | 同步层 + 本地判 + enrich 补全 |
| C. 视频页相关流 | fetch/XHR 劫持 `GET /x/web-interface/archive/related` | `data[]`：stat + dimension + duration 全字段 | 全本地判定（is_ogv=1 走 R4 豁免） |

移动版卡片 DOM：`.v-card`（v-card__wrap/__cover/__title/__stats），`a[href*="/video/BV…"]` 定位。

## 端到端验证（真实样本 817 条，engine/test_mobile_e2e.js）

- 过滤 23.3%：看过不给（CBI<0.5）186 · 低分 4 · 标题签名 3 · 短视频 ~16
- 与报告 §5「29.3% 大热门看过不给」量级一致——有效且克制
- 判定核心单测 21/21（engine/test_mobile_logic.js）：F7 公式、CBI 插值、官方区/is_ogv 豁免、低播放硬过滤、乞讨不隐藏、view=0 边界

## 安装（免 root）

- **Android 推荐**：Via / X 浏览器（内置脚本引擎，轻量）或 Firefox + Tampermonkey
  1. 安装脚本：新建脚本 → 粘贴 `userscript/bilibili-clean-mobile.user.js` 全文 → 保存
  2. 用浏览器打开 `m.bilibili.com`（建议设为书签/主页）
- **iOS**：App Store 装 Userscripts（免费开源）或 Stay → Safari 关联 → 导入脚本 → 打开 m.bilibili.com
- root 用户可同时用 MBGA（App 内净化，体验更完整）

## 设计约定（与 PC 版共同遵守）

- 一份 CONFIG：`config/clean.config.json` 为唯一真源，两个 userscript 内嵌同值手动同步
- 评分函数同构：`f7Of/baselineCBI/tierOf/asyncVerdict` 与 engine/scoring.py 逐字段一致
- 宁可漏放不误杀：item 缺字段（dimension/stat）→ enrich 补全后再判；补全失败 → 放行

## 遗留（真机验证项）

1. iOS Userscripts 对 fetch/XHR 双劫持的兼容性（原则支持，待真机确认）
2. Via 浏览器对 `document-start` 时序的落实（脚本在 SSR 渲染前注入是关键）
3. 频道流 region/feed/rcmd 离线复现未通（wbi+参数仍 -400）——不影响脚本运行（页面自带参数），仅影响采集器
