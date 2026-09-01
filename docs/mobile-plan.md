# 手机端（免 root）方案评估 v0.1

> 洁净B站 的主战场是手机。先说结论：**免 root 主线 = 手机浏览器 + 油猴脚本跑移动版过滤脚本**；
> root 用户可以直接用现成的 MBGA。下面是各路线对比与下一步验证清单。

## 方案对比

| # | 方案 | 需要 root | 可行性 | 过滤能力 | 说明 |
|---|---|---|---|---|---|
| 1 | **Android: Via浏览器 / X浏览器** 内置脚本引擎，跑在 `m.bilibili.com` | 否 | 高 | 与 PC userscript 同级 | 推荐**主线**。Via 体积小、自带油猴兼容层；免费 |
| 2 | **Android: Firefox + Tampermonkey** | 否 | 高 | 同上 | 脚本生态最完整，但 Firefox 较重 |
| 3 | **iOS: Safari + Userscripts App**（免费开源）/ Stay | 否 | 高 | 同上 | iOS 唯一免root正道；Safari 对 requestAnimationFrame 限流注意 |
| 4 | **MBGA**（LSPosed 模块，github.com/Xposed-Modules-Repo/top.trangle.mbga） | **要 root** | — | 强（App 内直接净化） | 现成方案：首页过滤/屏蔽推荐类别。root 用户首选；**功能清单可当作我们的需求参照** |
| 5 | 自建 mitmproxy 改写响应（WiFi 代理，手机装证书） | 否 | 中 | 强但折腾 | 免 root 的"App 内过滤"路线；配置门槛高，作为备选差异化 |
| 6 | B站 App 内手动工作流（稍后再看/收藏夹/不看该UP） | 否 | — | 人工缓解 | 非根治，仅过渡 |

## 关键未知（下一步验证，路线图 step 4）

1. **移动版首页 feed 用什么接口**：`m.bilibili.com` 的首页推荐流接口待探测
   （候选：web 的 `x/web-interface/index/top/feed/rcmd`、移动 web 专用接口、或带 appkey 签名的 App API `x/v2/feed/index`）。
   → 用 `dsh-cdp-browser` 手机 UA 模拟打开 m.bilibili.com，看 Network 请求即可确认。
2. **移动端推荐卡片 DOM 结构**：决定 MutationObserver 的选择器（`.bili-video-card` 是 PC 的，移动版不同）。
3. **竖屏流（下滑刷视频）入口**：移动版首页可能混入竖屏卡片（`goto` 值不同），需要抓一份真实响应确认字段。
4. **iOS Userscripts 对 fetch 劫持的兼容性**：原则上支持，待真机验证。

## 技术设计约定

- **一份 CONFIG，两个运行时**：`config/clean.config.json` 为唯一真源；PC 与移动 userscript 内嵌同一份 CONFIG 手动同步（后续可加构建步骤自动注入）。
- **评分函数同构**：`scoreOf()` 在 Python（engine/scoring.py）与 JS（userscript）保持逐字段一致，改公式必须两边同步。
- 移动版脚本独立成 `userscript/bilibili-clean-mobile.user.js`，复用 PC 版 90% 逻辑，只换 feed 接口匹配与 DOM 选择器。

## 结论

先做 Via/Firefox Android 路线（成本最低、见效最快），MBGA 作为 root 用户的"完整体验"推荐项引用，
mitmproxy 路线留作 Phase 2 差异化（App 内免 root 过滤）。
