# 洁净B站 · BewlyBewly 增量版（预构建产物）

> 这是**构建好的扩展目录**，下载本文件夹即可安装，无需 Node 环境。
> UI 框架：BewlyBewly v0.41.1（MIT，© Hakadao）——网格、暗色主题、无限下滑、设置面板全部是它的。
> 我们的增量：CBI 感谢指数过滤算法（同步层 + 懒判定层 + 评分角标）。版权划分见仓库根 `THIRD_PARTY_NOTICES.md`。

## 安装

1. Edge 地址栏输入 `edge://extensions` → 打开左下角「开发人员模式」
2. 点「加载解压缩的扩展」→ 选中**本文件夹**（含 manifest.json 的这个）
3. 打开 bilibili.com——BewlyBewly 首页已接管，且推荐流经过 CBI 过滤

## 验证洁净B站生效

- 推荐卡片右上角出现等宽字体角标：`CBI 1.32`（≥1 达到同类平均感谢水平）或 `F7 0.081`
- 低质卡片（CBI < 0.5 的「看过不给」、短视频 ≤75s、竖屏、直播、标题签名）**根本不出现**
- F12 控制台输入 `__CLEAN_BILI_COUNTS` 查看实时过滤分类计数

## 与原版的关系

- BewlyBewly 全部功能保留（首页多标签/设置/主题/布局切换），可随时在设置里关闭洁净B站增量行为（后续版本将暴露开关，当前以默认参数运行）
- 上游更新：`git pull` vendor 后重跑 `pnpm build`（插入点仅 3 处，见 `docs/bewly-integration-plan.md`）

## 源码

增量源码在 `vendor/BewlyBewly/src/logic/cleanBili/`（core.ts 判定核心 + useCleanBili.ts 接线层）与 `ForYou.vue` 的三处插入点。构建命令：`cd vendor/BewlyBewly && pnpm install && pnpm build`。
