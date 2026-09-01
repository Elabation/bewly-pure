# 洁净B站 Clean Bilibili

![report](https://img.shields.io/badge/调查报告-在线阅读-334EAC) ![userscript](https://img.shields.io/badge/脚本-一键安装-081F5C) ![samples](https://img.shields.io/badge/样本-7,537条·2019--2026-7096D1) ![license](https://img.shields.io/badge/立场-过滤低质·不封神-7096D1)

> **📖 调查报告《看过，却不给》在线阅读 → https://elabation.github.io/clean-bilibili-report/web/ecosystem-report.html**
>
> **⚡ 三分钟安装浏览器插件（当前已可用）→ 教程见 [docs/tutorial.md](docs/tutorial.md)**
>
> 一键安装链接（Tampermonkey 启用时点击即装）：
> - CDN 镜像（国内推荐）：https://cdn.jsdelivr.net/gh/Elabation/clean-bilibili-report@main/userscript/bilibili-clean.user.js
> - GitHub 直连：https://github.com/Elabation/clean-bilibili-report/raw/main/userscript/bilibili-clean.user.js

> 过滤B站首页推荐的：**短视频 / 竖屏视频 / 直播 / 低质量视频**。
> 主战场手机端（免 root），PC 端同步覆盖。动机：夺回注意力，拒绝「下滑刷视频」的投喂设计。
>
> **核心立场（先生定调）：过滤低质，而不是保留高质。**
> 低质的可操作定义 = **「看过，却不给」**——播放量早已消耗了大量注意力，互动比却低于同播放段基线。
> 手搓高投入内容比值虽高，但品味因人而异；算法只砍「注意力小偷」，不做「封神判官」。

## 核心评分机制（全部可手调）

```
比值 = (收藏×w_fav + 投币×w_coin + 点赞×w_like) / 分母
分母 = view（原始播放，先生的原始公式）| sqrt(view) | log10(view)
```

- **比值越高 → 视频质量越高**（收藏/投币是强付出行为，刷子视频刷不出来）
- 播放量 < `min_view_threshold` → 判 `unproven`（比率不可信，新视频保护）
- 所有权重、阈值、开关集中在 **`config/clean.config.json`** 一个文件里，改完即生效

### 手调指南（先生最关心的部分）

| 想调什么 | 改哪个字段 | 默认 | 说明 |
|---|---|---|---|
| 收藏权重 | `scoring.weights.favorite` | 3.0 | 收藏是最强信号，权重最高 |
| 投币权重 | `scoring.weights.coin` | 2.0 | 硬币第二强 |
| 点赞权重 | `scoring.weights.like` | 0.3 | 轻信号，别给太高否则全是「顺手赞」 |
| **播放阈值** | `scoring.min_view_threshold` | 3000 | 低于此播放量不参与分级（比率噪声大） |
| 高质量线 | `scoring.tiers.high` | 待校准 | 比值 ≥ 此 → high |
| 正常线 | `scoring.tiers.normal` | 待校准 | |
| 过滤线 | `scoring.tiers.low` | 待校准 | 低于 normal 且 ≥ low → low；再低 → junk |
| 短视频判定 | `filters.short_video_max_duration_sec` | 75s | 时长 ≤ 此判短视频 |
| 竖屏判定 | `filters.portrait.wh_ratio_min` | 0.9 | 有效宽/高 < 此值判竖屏 |
| 直播过滤 | `filters.live` | true | |
| 低播放硬过滤 | `filters.min_views` | 1000 | 总播放低于此直接过滤 |
| 屏蔽哪些档位 | `filters.hide_tiers` | [low, junk] | unproven 默认显示打标，想隐藏就加 |
| 标题关键词 | `filters.block_keywords` | [] | 命中即过滤 |

改完配置怎么验证效果：

```bash
python engine\scoring.py --data data\samples\<样本>.json   # 批量打分，看 tier 分布
python engine\scoring.py --bvid BV1xxxx                    # 单视频在线试算
python engine\calibrate.py --data data\samples\<样本>.json # 让真实数据建议阈值
```

## 目录结构

```
bilibili-clean/
├── config/clean.config.json      # 唯一真源：所有权重/阈值/开关
├── engine/
│   ├── collect_stats.py          # 数据采集（B站API，零依赖，wbi签名已内置）
│   ├── scoring.py                # 评分引擎（tier 分级 + 过滤原因）
│   ├── calibrate.py              # 校准：按分位数建议阈值，出报告
│   ├── ecosystem_collect*.py     # 生态采集（榜单/热门/推荐流/新稿/搜索深页）
│   ├── ecosystem_collect_v5.py   # 大采样：每周必看387期(2020-2026)/入站必刷/热门深页
│   ├── ecosystem_analysis.py     # 生态分析（公式扫描/分位段/四象限/分区画像）
│   ├── deep_analysis.py          # 深度统计实验：偏相关/CBI基线/洛伦兹/PCA/检验/时代演化/时长分析
│   └── build_report.py           # 报告网页构建（幂等注入数据）
├── data/
│   ├── samples/                  # 采集样本（v5 约2万条，2020-2026 跨度）+ 校准报告
│   └── analysis/                 # 生态分析 + 深度分析结果 JSON
├── web/
│   └── ecosystem-report.html     # 《看过，却不给》调查报告 v3（单文件可分享，15章节）
├── userscript/
│   └── bilibili-clean.user.js    # PC端 Tampermonkey 原型（两层过滤）
└── docs/mobile-plan.md           # 手机端免root方案评估
```

## 快速开始

```bash
# 1. 采集样本（约1-2分钟，仅API元数据，不下载视频）
python engine\collect_stats.py

# 2. 校准：真实数据建议权重/阈值，报告在 data/samples/calibration-report_*.md
python engine\calibrate.py --data data\samples\sample_xxx.json

# 3. 把建议阈值粘回 config/clean.config.json，跑打分验证
python engine\scoring.py --data data\samples\sample_xxx.json
```

PC 端：Tampermonkey 安装 `userscript/bilibili-clean.user.js`（CONFIG 与 clean.config.json 手动同步）。

**手机端（免 root，主战场）**：Via/X 浏览器（Android）或 Safari + Userscripts App（iOS）安装 `userscript/bilibili-clean-mobile.user.js`，打开 `m.bilibili.com` 即生效——首页热榜（SSR）/频道流（region/feed/rcmd）/视频页相关流（archive/related）三股全过滤，判定核心与 PC 版逐字段一致。详见 `docs/mobile-plan.md`。

### userscript v0.2 判定流程（对应报告 §13 过滤器设计）

```
同步层（响应即删，卡片根本不渲染）：
  直播 R1 / 时长≤75s R1 / 标题命中签名正则 R7（第N集/话、挑战体）

异步层（view API 补全收藏/投币后判定，CBI 曲线内置）：
  竖屏 R1 → hide
  播放 < 1000 R1 → hide
  官方区白名单（电影/电视剧/纪录片）R4 → 跳过 CBI，不判低质
  播放 ≥ 5万 且 CBI < 0.5 R2 → hide「看过不给」
  播放 3千~5万 全局兜底 R2' → 只 hide junk（low 打标不隐藏）
  「投币X更新」乞讨文本 R8 → badge 打「乞」标，不惩罚
```

控制台调试：`CleanBili.test(stat, title, tname, dimension)` 单视频试算；`CleanBili.counts` 看实时过滤统计。

## 工作原理

- **数据层**：`x/web-interface/view` 拿 `stat`（view/favorite/coin/like）+ `dimension`（宽高/rotate）+ `duration`；
  采集来源 = 排行榜 + 热门 + 首页推荐流（wbi 签名、buvid3、节流与风控退避已内置）
- **竖屏识别**：dimension 宽/高比（考虑 rotate 旋转标志），不下载视频不用 FFmpeg
- **PC userscript 两层过滤**：① 劫持首页推荐接口响应，直播/短视频/关键词卡片直接不渲染；
  ② 异步调 view API 补收藏/投币算评分，低分/竖屏/低播放卡片渲染后隐藏 + 计数角标

## 路线图状态（对照 HANDOFF.md）

| # | 阶段 | 状态 |
|---|---|---|
| 1 | 数据层：API 采集播放/收藏/投币 | ✅ 采集五件套 + **每周必看/入站必刷大采样**（累计 7000+ 条，2020-2026 七年跨度） |
| 2 | 评分模型：验证公式、定权重与阈值 | ✅ 首轮校准 + 31 配置网格扫描（币/播 = 低质探测冠军，详见报告§9） |
| 2.5 | 生态调查《看过，却不给》 | ✅✅ **第三版：十三项统计实验**（偏相关/分位回归/洛伦兹/PCA/χ²/MWU/**时代演化 2020-2026**/**时长×质量**/**层间对比**），单栏可读性重写，报告 web/ecosystem-report.html |
| 3 | 过滤验证：真实页面验证规则 | ✅ **userscript v0.2 已实测**（dsh 浏览器注入 bilibili.com：拦截 12 批推荐、CBI 判定 149 条、过滤 59 条、badge 41 张；离线全样本模拟 feed 层砍 32% 卡片收回 54% 播放份额） |
| 3.5 | 引擎 v2：CBI 相对基线取代全局阈值 | ✅ 设计+参数落地：config 新增 `cbi` 段（threshold 0.5 / min_view 5w）+ 8 条过滤器规则（报告§13），userscript 同步待做 |
| 4 | 手机端方案（免 root） | ✅ **机制落地**：`userscript/bilibili-clean-mobile.user.js`（m.bilibili.com 首页热榜 SSR / 频道流 / 视频页相关流三股全过滤），单测 21/21 + 真实样本端到端 23.3% 过滤率验证，安装指南见 docs/mobile-plan.md，待真机实测 |
| 5 | 成果发布 | ⏳ 配置即成果；GitHub 备份通道已就绪 |

## 现成方案对比（为什么自己写）

| 项目 | 平台 | 与本项目关系 |
|---|---|---|
| [Bilibili-Evolved](https://github.com/the1812/Bilibili-Evolved) | PC | 最强增强套件，有首页简化/屏蔽；但无「收藏/投币比值」评分机制 → 我们引用它做补充，不重复造轮子 |
| [BlocksShortVideos](https://github.com/qiye45/BlocksShortVideos) | PC | 只屏蔽短视频，无评分 |
| [Bilibili-Gate](https://github.com/magicdawn/bilibili-gate) | PC | 自定义首页 |
| [MBGA](https://github.com/Xposed-Modules-Repo/top.trangle.mbga) | 手机 | 需 root（LSPosed）；免root用户用不了 → 我们的差异化空间 |

**差异化**：① 手机端免 root（浏览器+脚本路线）；② 收藏/投币/播放比值的质量评分，阈值全手调。
