# 交接名录 · 洁净B站（bewly-pure）—— DSH 插件 × 自研引擎 × 运维要点

> 写给接手人。分四部分：harness 内置插件、自研引擎、运维要点、进行中工作。
> 所有路径相对仓库根 `bilibili-clean/`（GitHub: Elabation/bewly-pure）。

## 一、DSH harness 内置插件/工具

| 工具 | 用途 | 本项目角色 | 状态 |
|---|---|---|---|
| `bilibili_extract` / `bilibili_login` / `bilibili_doctor`（dsh-bilibili 插件） | 单视频转写+热评+弹幕抓取；扫码授权 SESSDATA 自动保存 | **E1 实验的评论采集通道**（高分作品→热评用户）；扫码登录比 F12 抓 cookie 优雅（但登的是真实账号，风控自担） | E1 时启用 |
| `rss_add` / `rss_fetch` / `rss_digest`（dsh-rss 插件） | RSS 订阅与摘要 | 可订阅 bilibili-API-collect 仓库动态，监控公开接口变更（管线全压在公开接口上，预警有价值） | 可选，未配置 |
| AI4Scholar（`search_papers` 等） | 学术文献检索 | 报告理论章引用弹药（HITS/RWR/函数深度/Ricci flow 原始文献） | 理论章动笔时用 |
| `session_audit` | 会话审计（工具调用/失败/job 统计） | 风控与故障盘点（本次已用：987 调用/7.5% 失败/零封禁） | 随用随查 |
| browser（`browser_*` / `pilot_*`） | 网页渲染与操作 | 报告 HTML 的渲染验证（截图+DOM 断言） | 已验证两份报告 |
| 后台 job（`run_in_background` / `job_output` / `job_kill`） | 长任务后台化 | 全部挖掘轮次后台跑（12-20 分钟/轮），`job_output wait:true` 收割 | ✅ 成熟用法 |
| `pwsh` | 全部命令执行 | python 引擎、pnpm 构建、GitHub 上传 | ✅ |
| `web_search` / `scrape_webpage` | 调研 | 路线调研（PiliPala 死因）、接口文档抓取 | ✅ |
| GitHub contents API（无 git 插件，pwsh 直调） | 文件上传 | PUT + sha 三重试（现成模式在各上传脚本里） | ✅ |

## 二、自研引擎（交接核心，全部纯标准库+numpy）

| 文件 | 职责 | 关键点 |
|---|---|---|
| `engine/collect_stats.py` | BiliClient：wbi 签名/节流/风控重试 + 采集 | 一切采集的地基，零第三方依赖 |
| `engine/scoring.py` | F7/tier 打分 | config 驱动 |
| `engine/fav_miner.py` | **收藏夹考古挖掘器** | 种子（uploader+评论）→ 公开夹 → 条目 → stat 补全 → 匿名入库；`--analyze ALL` 合并全目录；登录态读 `data/fav_mine/.sessdata`；去重映射 `.mid2hash.json` |
| `engine/ag_depth.py` | AG-Depth（流形子空间深度） | 邻域=view桶×年代×来源；PCA 累计方差 85% 取流形基；正向性门槛（F7≥邻域中位）；构型残差（coin\|fav,like 回归）；V2/V3 验证内置 |
| `engine/ag_folium.py` | AG-Folium（年代叶基线） | 叶=n≥30 年代；V4/V5 验证内置；年代行为档案（coin -60%/fav ×2.8 十年迁移） |
| `engine/build_report.py` / `build_nostalgia.py` | 两份报告幂等注入 | `const DEEP/POINTS/MINE` 行替换 |
| `engine/ecosystem_*.py` / `deep_analysis.py` | 前作生态采集与统计实验 | 《看过，却不给》v3 的家底 |
| `config/clean.config.json` | 唯一真源 | 权重/阈值/cbi 段 |
| `data/samples/` | 对照组样本（166 条带全 stat） | 对照口径见 nostalgia 报告 §3 |
| `data/fav_mine/` | 考古数据（4 轮合并 2593 条） | `*_analysis.json` 是分析层；`ag_depth_summary.json`/`ag_folium_summary.json` 是验证结果 |
| `web/ecosystem-report.html` | 《看过，却不给》v3 | Pages: elabation.github.io/bewly-pure/web/ecosystem-report.html |
| `web/nostalgia-report.html` | 《给过，却不再被看见》N01 | 同上 `/web/nostalgia-report.html` |
| `docs/appreciation-geometry.md` | **感谢几何算法设计文档（当前主线）** | AG-Depth/Folium/Compass/Flow 四组件 + V1-V7/E1-E3 验证协议 + 首轮结果 |
| `docs/mobile-plan.md` | 手机端路线 A 现役 | Firefox 路线，`extension-bewly-firefox.zip` 已构建 |
| `extension-bewly/` + `vendor/BewlyBewly/` | PC 现役 cb17（BewlyBewly MIT + cleanBili 增量） | 判定核心 `src/logic/cleanBili/core.ts`（CBI 曲线源） |
| `docs/tutorial.md` | 用户教程 | 安装/胶囊/FAQ |

## 三、运维要点（接手人必读）

1. **凭据（永不入仓，.gitignore 已防呆）**：
   - GitHub token：`%USERPROFILE%\tools\gh.token`（上传用）
   - 可选 SESSDATA：放 `data/fav_mine/.sessdata`（**建议小号**；登录态收益=评论区翻页，代价=风控记在账号头上）
   - `.mid2hash.json`（mid→匿名哈希映射）仅本机
2. **风控经验**：请求间隔 0.42-0.45s；412 退避已内置（3 次）；未登录评论区每视频约 3 条（sort=1）；粉丝列表未登录 -352 死锁（勿试）；五轮挖掘零封禁、全 exit 0
3. **构建**：`$env:COREPACK_ENABLE_DOWNLOAD_PROMPT='0'; corepack pnpm build`（Chrome 产物）／`corepack pnpm build-firefox`（Firefox 产物）；lint `corepack pnpm exec eslint --fix`
4. **中文文件**：PowerShell 读写一律 UTF-8；GitHub body 用 UTF8 bytes
5. **报告部署**：`web/*.html` 入仓 main 分支即 Pages 自动构建（约 1 分钟），验证用 `raw.githubusercontent.com` 或等 Pages builds API

## 四、进行中 / 待办（按优先级）

1. **V5 复测**：ag_folium 桶中位数→连续回归（log F7 ~ log view 分叶），目标 ratio ≤0.90
2. **V1 人工核对**：`ag_depth_summary.json` 的 ag_only_examples 12 条，人工判「是否真值得捞」
3. **种子来源分层**：fav_miner 的 users 记录加 `seed_type` 字段（uploader/comment），E1 的前提
4. **E1 三臂对照**：流引导 vs uploader vs 随机评论用户（同预算 60 用户，MWU 检验）；可用 bilibili_extract 插件抓高分作品热评
5. **E2/E3**：流效果 + 剪枝曲线（依赖 E1）
6. **报告「感谢几何」理论章**：几何注脚机制（正文统计叙事 + 「ℹ 几何注」小框），锚点已列 appreciation-geometry.md；**验收门：Elabation 拍板「封神」后才启动开发**（时间机器页面/扩展集成）
7. 手机端：等真机验证 Firefox 路线（extension-bewly-firefox.zip 现成）
