# BewlyBewly 增量开发方案

> 决策：PC 端放弃自研手搓 UI，改为 **在 BewlyBewly（MIT）源码基础上做增量开发**。
> 原则：UI/交互/工程骨架全部用 BewlyBewly 的成熟实现；**推荐过滤算法是我们自己的**（CBI 感谢指数，报告 §13）。
> 版权合规见 `THIRD_PARTY_NOTICES.md`（MIT：保留版权声明即可，已落）。

## 为什么放弃自研手搓

| 自研版的问题 | BewlyBewly 的现成答案 |
|---|---|
| 美术粗糙（白底卡片、无设计体系） | 成熟的暗色/亮色主题、毛玻璃质感、动画、多布局（网格/瀑布流） |
| 无限下滑失效（自研 sentinel 触发链不可靠） | `handleReachBottom` 生产级机制 + `noMoreContent`/骨架屏/失败重试 |
| 自己维护 rcmd 拉流与 wbi 细节 | background 消息代理统一管 API（含 rcmd / view 详情，我们判定所需接口全有） |
| 设置只能改代码 | 现成设置面板体系（storage.ts + Settings 组件），CBI 参数可做成可视化开关 |

## 架构调研结论（v0.41.1，Vite + Vue3 + tsup，pnpm@9.5.0）

关键文件与插入点：

```
src/background/messageListeners/api/video.ts
  └─ getRecommendVideos（rcmd，ps 30）        ← 数据入口，已就绪无需改
  └─ getVideoInfo（view 详情）                ← CBI 懒判定的数据源，已就绪
src/contentScripts/views/Home/components/ForYou.vue
  └─ L183 response.data.item.forEach          ← 【插入点 A】同步层过滤
      （直播/短视频/标题签名 在此直接跳过 push）
  └─ filterFunc 扩展钩子                       ← 可并入同步过滤
src/components/VideoCard/VideoCard.vue
  └─ 卡片角标区                                ← 【插入点 B】CBI/F7 评分角标
src/logic/storage.ts + components/Settings/
  └─ settings 存储 + 设置面板                  ← 【插入点 C】CBI 阈值/白名单/开关可视化
```

## 我们的模块设计（纯增量，尽量少改上游文件）

```
src/logic/cleanBili/
  ├── cbi.ts            # CBI 核心曲线（28 点基线内置）+ f7Of/tierOf/插值（从 userscript/扩展移植）
  ├── syncFilter.ts     # 同步层：goto/duration≤75s/标题签名正则 → 返回过滤原因
  ├── lazyJudge.ts      # 懒判定：调 getVideoInfo → asyncVerdict → hide: boolean + 角标数据
  └── config.ts         # 默认配置（与 config/clean.config.json 同步：threshold 0.5 等）
src/composables/useCleanBili.ts   # Vue 组合式封装：对组件暴露 filter/cull/badge API
```

- ForYou.vue 只加两行：`syncFilter` 跳过 + 渲染后 `lazyJudge`（hide 则从 `videoList` 移除，Vue 响应式自动重排，无空洞）
- VideoCard.vue 加一个可选 badge 槽（settings.cleanBiliBadge 控制显隐）
- 设置面板加「洁净B站」分区（threshold/min_view/白名单/短视频线/开关）
- 新增独立的 `CleanBiliHome.vue` 视图（可选二期）：把 ForYou 的数据源换成「仅 CBI 通过」流，BewlyBewly 原 ForYou 保留给不想要过滤的用户

## 构建链（一次性环境准备）

1. Node LTS + pnpm 9（`winget install OpenJS.NodeJS.LTS` + corepack enable pnpm）
2. `cd vendor/BewlyBewly && pnpm install`
3. `pnpm build` → 产出 `extension/`（MV3 目录）→ `edge://extensions` 加载解压缩
4. 开发热更：`pnpm dev`（WXT/Vite watch）

vendor/ 目录不提交（.gitignore 已加）；上游升级 = git pull 后重新应用我们 3 个插入点（改动面小，可控）。

## 分期

| 期 | 内容 | 验收 |
|---|---|---|
| P1 | 环境就绪 + 原版 BewlyBewly 构建跑通 + 加载进 Edge | 原版体验完整（网格/无限下滑/暗色） |
| P2 | cleanBili 模块移植（同步过滤 + 懒判定 + 角标）插入 ForYou/VideoCard | 首页 CBI 过滤生效，下滑补位正常，计数可在控制台看 |
| P3 | 设置面板「洁净B站」分区（阈值/白名单/开关可视化） | 不改代码即可调参 |
| P4 | CleanBiliHome 独立视图 + 文案/主题微调（洁净B站品牌） | 双模式共存：原版推荐 / CBI 过滤流 |

## 现状与自研版处置

- 自研 `extension/`（手搓网格版）保留在仓库作对照，但**不再是 PC 主线**；README 主线改为 BewlyBewly 增量版
- 手机的 `userscript/bilibili-clean-mobile.user.js` 不受影响（m.bilibili.com 场景独立）
- 待 P1 完成后，用真机过一遍原版功能清单，再动 P2
