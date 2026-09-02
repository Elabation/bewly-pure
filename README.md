# 洁净B站 Clean Bilibili

![report](https://img.shields.io/badge/调查报告-在线阅读-334EAC) ![extension](https://img.shields.io/badge/扩展-Edge·Chrome-081F5C) ![samples](https://img.shields.io/badge/样本-7,537条·2019--2026-7096D1) ![license](https://img.shields.io/badge/立场-过滤低质·不封神-7096D1)

> **📖 调查报告《看过，却不给》在线阅读 → https://elabation.github.io/bewly-pure/web/ecosystem-report.html**
>
> **⚡ 浏览器扩展安装（2 分钟）→ 教程见 [docs/tutorial.md](docs/tutorial.md)**

> 过滤B站首页推荐的：**短视频 / 竖屏视频 / 直播 / 低质量视频**。
> PC 端：**基于 BewlyBewly（MIT）做增量开发**——UI/网格/无限滚动用它的成熟框架，推荐过滤算法是我们自己的 CBI 感谢指数。
> **预构建产物在 `extension-bewly/`**（下载即装），增量源码与方案见 [docs/bewly-integration-plan.md](docs/bewly-integration-plan.md)，版权划分见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
> 手机端（免 root）：Via/X（Android）+ Userscripts（iOS）。
> 动机：夺回注意力，拒绝「下滑刷视频」的投喂设计。
>
> **核心立场：过滤低质，而不是保留高质。**
> 低质的可操作定义 = **「看过，却不给」**——播放量早已消耗了大量注意力，互动比却低于同播放段基线。
> 手搓高投入内容比值虽高，但品味因人而异；算法只砍「注意力小偷」，不做「封神判官」。

## 核心评分机制（全部可手调）

```
F7  加权感谢率 = (收藏×3.0 + 投币×2.0 + 点赞×0.3) / 播放
CBI 感谢指数   = F7 ÷ 同播放段基线中位数（6,734 条样本滑窗拟合，扩展内置曲线）
```

- **比值越高 → 视频质量越高**（收藏/投币是强付出行为，刷子视频刷不出来）
- 播放量 < 3000 → 判 `unproven`（比率不可信，新视频保护）
- 所有权重、阈值、开关集中在 **`config/clean.config.json`** 一个文件里；扩展判定核心与它同步

### 手调指南

| 想调什么 | 改哪个字段 | 默认 | 说明 |
|---|---|---|---|
| **CBI 判定线** | `cbi.threshold` | 0.5 | 调大（0.6）更严，调小（0.4）更宽容 |
| CBI 起判播放 | `cbi.min_view` | 50000 | 播放低于此值不做 CBI 判定 |
| 短视频判定 | `filters.short_video_max_duration_sec` | 75s | 时长 ≤ 此判短视频 |
| 竖屏判定 | `filters.portrait.wh_ratio_min` | 0.9 | 有效宽/高 < 此值判竖屏 |
| 低播放硬过滤 | `filters.min_views` | 1000 | 总播放低于此直接过滤 |
| 标题签名 | `filters.block_keywords` | 第N集/话·挑战体 | 命中即过滤（仅放检验过的签名，§14） |
| 官方区白名单 | `filters.zone_whitelist` | 电影/电视剧/纪录片 | 白名单区不做低质判定 |

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
├── extension/                    # 浏览器扩展 v1.0（Edge/Chrome，MV3）
│   ├── manifest.json             #   扩展清单
│   ├── content.js                #   核心：wbi签名→拉推荐流→同步过滤→网格渲染→懒判定
│   ├── md5.js                    #   MD5（wbi 签名依赖）
│   ├── content.css               #   网格布局样式（亮/暗双主题）
│   └── README-INSTALL.md         #   安装说明
├── engine/
│   ├── collect_stats.py          # 数据采集（B站API，零依赖，wbi签名已内置）
│   ├── scoring.py                # 评分引擎（tier 分级 + 过滤原因）
│   ├── calibrate.py              # 校准：按分位数建议阈值，出报告
│   ├── ecosystem_collect*.py     # 生态采集（榜单/热门/推荐流/新稿/搜索深页）
│   ├── ecosystem_collect_v5.py   # 大采样：每周必看387期(2020-2026)/入站必刷/热门深页
│   ├── ecosystem_analysis.py     # 生态分析（公式扫描/分位段/四象限/分区画像）
│   ├── deep_analysis.py          # 深度统计实验：偏相关/CBI基线/洛伦兹/PCA/检验/时代演化/时长分析
│   ├── simulate_userscript.py    # 判定逻辑离线模拟器（上线前验证过滤率）
│   └── build_report.py           # 报告网页构建（幂等注入数据）
├── data/
│   ├── samples/                  # 采集样本（v5 约2万条，2020-2026 跨度）+ 校准报告
│   └── analysis/                 # 生态分析 + 深度分析结果 JSON
├── web/
│   └── ecosystem-report.html     # 《看过，却不给》调查报告 v3（单文件可分享，15章节）
├── userscript/
│   └── bilibili-clean-mobile.user.js  # 手机端脚本（m.bilibili.com 三股流过滤）
└── docs/
    ├── tutorial.md               # 安装与使用教程（四种方式）
    └── mobile-plan.md            # 手机端免root方案评估
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

**PC 端（Edge/Chrome 扩展）**：`edge://extensions` → 开发人员模式 → 加载解压缩的扩展 → 选 `extension/` 文件夹 → 打开 bilibili.com 即网格模式。详见 [extension/README-INSTALL.md](extension/README-INSTALL.md)。

**手机端（免 root，主战场）**：Via/X 浏览器（Android）或 Safari + Userscripts App（iOS）安装 `userscript/bilibili-clean-mobile.user.js`，打开 `m.bilibili.com` 即生效——首页热榜（SSR）/频道流（region/feed/rcmd）/视频页相关流（archive/related）三股全过滤，判定核心与 PC 版逐字段一致。详见 `docs/mobile-plan.md`。

### 扩展 v1.0 判定流程（对应报告 §13 过滤器设计）

```
同步层（拉流即滤，卡片根本不渲染）：
  直播 R1 / 时长≤75s R1 / 标题命中签名正则 R7（第N集/话、挑战体）

懒判定层（卡片滚近视口才查详情，CBI 曲线内置）：
  竖屏 R1 → 不渲染
  播放 < 1000 R1 → 不渲染
  官方区白名单（电影/电视剧/纪录片）R4 → 跳过 CBI，不判低质
  播放 ≥ 5万 且 CBI < 0.5 R2 → 不渲染「看过不给」
  播放 3千~5万 全局兜底 R2' → 只砍 junk（low 打标不隐藏）
  「投币X更新」乞讨文本 R8 → 角标打「乞」标，不惩罚
```

控制台调试：`CleanBili.counts` 看实时过滤统计；`CleanBili.verdicts` 看每条判定明细。

## 工作原理

- **数据层**：自建 wbi 签名直连 `index/top/feed/rcmd`（推荐流）与 `x/web-interface/view`（详情 stat/dimension/duration），不劫持页面任何请求
- **竖屏识别**：dimension 宽/高比（考虑 rotate 旋转标志），不下载视频不用 FFmpeg
- **网格接管**：B 站顶栏（搜索/头像/历史/收藏）原生保留，推荐区替换为自绘网格；无限滚动 + CBI 懒判定；低质卡片不渲染，网格自动重排无空洞；状态条一键「切回原版」

## 路线图状态（对照 HANDOFF.md）

| # | 阶段 | 状态 |
|---|---|---|
| 1 | 数据层：API 采集播放/收藏/投币 | ✅ 采集五件套 + **每周必看/入站必刷大采样**（累计 7000+ 条，2020-2026 七年跨度） |
| 2 | 评分模型：验证公式、定权重与阈值 | ✅ 首轮校准 + 31 配置网格扫描（币/播 = 低质探测冠军，详见报告§9） |
| 2.5 | 生态调查《看过，却不给》 | ✅✅ **第三版：十三项统计实验**（偏相关/分位回归/洛伦兹/PCA/χ²/MWU/**时代演化 2020-2026**/**时长×质量**/**层间对比**），单栏可读性重写，报告 web/ecosystem-report.html |
| 3 | 过滤验证：真实页面验证规则 | ✅ **扩展 v1.0 真机全链路实测**（wbi 签名直连 code 0、网格 17 卡 CBI 角标全亮、砍 3 条）；判定逻辑离线模拟 feed 层砍 32% 卡片收回 54% 播放份额 |
| 3.5 | 引擎 v2：CBI 相对基线取代全局阈值 | ✅ 设计+参数落地：config 新增 `cbi` 段（threshold 0.5 / min_view 5w）+ 8 条过滤器规则（报告§13），扩展判定核心同步 |
| 4 | 手机端方案（免 root） | ✅ **机制落地**：`userscript/bilibili-clean-mobile.user.js`（m.bilibili.com 首页热榜 SSR / 频道流 / 视频页相关流三股全过滤），单测 21/21 + 真实样本端到端 23.3% 过滤率验证，安装指南见 docs/mobile-plan.md，待真机实测 |
| 5 | 成果发布 | ✅ GitHub 公开仓库 + Pages 报告 + 扩展教程齐备 |

## 现成方案对比（为什么自己写）

| 项目 | 平台 | 与本项目关系 |
|---|---|---|
| [Bilibili-Evolved](https://github.com/the1812/Bilibili-Evolved) | PC | 最强增强套件，有首页简化/屏蔽；但无「收藏/投币比值」评分机制 → 我们引用它做补充，不重复造轮子 |
| [BlocksShortVideos](https://github.com/qiye45/BlocksShortVideos) | PC | 只屏蔽短视频，无评分 |
| [Bilibili-Gate](https://github.com/magicdawn/bilibili-gate) | PC | 自定义首页 |
| [MBGA](https://github.com/Xposed-Modules-Repo/top.trangle.mbga) | 手机 | 需 root（LSPosed）；免root用户用不了 → 我们的差异化空间 |

**差异化**：① PC 网格接管 + 手机免 root；② 收藏/投币/播放比值的质量评分（CBI 相对基线），阈值全手调。

## 仓库命名与开发说明

**为什么叫 bewly-pure**：它是 [BewlyBewly](https://github.com/hakadao/BewlyBewly)（MIT, © Hakadao）的纯净演进版——UI/框架/无限滚动的功劳属于 BewlyBewly；本仓库的增量是一层 CBI 过滤算法（版权划分见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)）。调查报告只是本仓库的成果之一，故不入仓库名。

**AI 辅助开发**：本项目由 [Elabation](https://github.com/Elabation) 开发，**GLM-5.3-Flash（Z.ai）** 作为 AI 结对开发者深度参与——采样管线、统计实验、调查报告与扩展工程均为「人定方向与拍板、AI 执行与实现」的人机协作产物；过滤哲学与产品决策的最终裁量权在 Elabation。
