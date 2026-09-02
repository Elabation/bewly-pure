# 手机端方案 —— 路线决策（2026-09）

> **现役路线：A —— Android Firefox + BewlyBewly(Firefox 版) + 本仓库增量（cb17 同源代码）。**
> 路线 B/C 评估结论与法律边界见文末「路线取舍」。

## 路线 A · BewlyBewly Firefox 版平移（现役）

PC 增量版（cb17）与 Firefox 版共享同一套源码：上游 `pnpm build-firefox` 产物 `extension-firefox/`（gecko id `addon@bewlybewly.com`），我们的 cleanBili 三件套 + ForYou 接线 + 设置面板为纯 webextension API（webextension-polyfill 兼容 Firefox）。

- 仓库产物：`extension-bewly-firefox/` 与 `extension-bewly-firefox.zip`（cb17 同源，manifest 已改名「BewlyBewly · 洁净B站版」）
- 体验取舍：手机 Firefox 需以「桌面模式 UA」打开 www.bilibili.com；核心过滤/角标/胶囊 100% 复用
- **Android 正式版 Firefox 只能安装 AMO 签名扩展**——自构建包的安装路径：
  1. 先装 AMO 官方 [BewlyBewly Firefox 版](https://addons.mozilla.org/zh-CN/firefox/addon/bewlybewly/) 验证地基（网格/角标在手机上能否工作）
  2. 想装我们的增量版：Firefox Beta/Nightly → about:config → `xpinstall.signatures.required = false` → about:addons → 从文件安装 `extension-bewly-firefox.zip`
  3. 正规化路径（后续）：注册 AMO 开发者账号，提交我们的构建做自签名（签后正式版也能装）

## 原型遗留 · m 站 userscript（路线 B 内核，保留备用）

> 主线曾实现：`userscript/bilibili-clean-mobile.user.js`（m.bilibili.com 全站）。
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

- **Android 推荐**：Via / X 浏览器（内置脚本引擎，轻量）
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

## 路线取舍（2026-09 调研结论）

- **路线 C（基于第三方客户端 pilipala 增量）：否决。** PiliPala 开发者已收到 B 站侵权告知函并[停止更新](https://m.ithome.com/html/869202.htm)；patch 官方 App 的头部项目「哔哩漫游」同样[收律师函后删库](https://tech.ifeng.com/c/8uXfJ0dMB61?ch=ttsearch)。经验法则：**增强公开网页 = 合法存活（Bilibili-Evolved 多年）；复刻/修改客户端 = 高危清场区**。本仓库以真实身份发布，不进入该区间。
- **路线 B+（m 站 WebView 套壳 App）：备用。** 若路线 A 的桌面 UA 体验不可接受，用自有 WebView 壳加载 m.bilibili.com + 注入 userscript 内核——合法性与 B/油猴同级，形态是 App。内核即本文档的 userscript（单测 21/21、817 条样本 23.3% 过滤率）。
- **路线 A 现役理由**：同一 MIT 地基、同一份增量代码（零改写）、Firefox Android 2023-12 起[原生支持扩展](https://gigazine.net/news/20231215-android-firefox-addon-debut/)。风险点仅剩「桌面 UA 打开桌面站」的移动端体验，待真机验证。
