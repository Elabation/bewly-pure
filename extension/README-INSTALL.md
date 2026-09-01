# Edge 扩展版 · 安装说明（自研扩展，零依赖）

这是洁净B站的独立浏览器扩展（Manifest V3），直接接管 bilibili.com 首页推荐流：网格铺平渲染，CBI 感谢指数判定，低质卡片根本不渲染。

## 安装（Edge，2 分钟）

1. 下载本仓库（Code → Download ZIP，或 git clone），得到 `extension/` 文件夹
2. Edge 地址栏输入 `edge://extensions` 回车
3. 打开左下角「**开发人员模式**」开关
4. 点顶部「**加载解压缩的扩展**」，选中本项目的 `extension/` 文件夹
5. 打开 https://www.bilibili.com ——完成

Chrome 同理（`chrome://extensions` → 开发者模式 → 加载已解压的扩展程序）。

## 它做了什么 / 没做什么

| | |
|---|---|
| 接管范围 | 仅 bilibili.com 首页推荐流（网格铺平 + 无限滚动） |
| 保留功能 | B 站原顶栏原样保留：搜索、头像、历史、收藏、消息全部原生可用 |
| 判定规则 | 与报告 §13 完全一致（R1-R8，CBI<0.5 看过不给） |
| 数据来源 | 自建 wbi 签名直连 B 站公开接口（rcmd 推荐 + view 详情），**不劫持页面请求** |
| 低质卡片 | **不渲染**（网格自动重排，无空洞） |
| 切回原版 | 状态条右上「切回原版」一键还原（本次会话内） |
| 隐私 | 全部本地计算，无任何上报 |

## 文件结构

```
extension/
  manifest.json   扩展清单（MV3，content_scripts 匹配首页）
  md5.js          MD5 实现（wbi 签名依赖）
  content.js      核心：wbi 签名 → 拉推荐流 → 同步过滤 → 网格渲染 → 懒判定
  content.css     网格布局样式（亮/暗双主题）
```

## 与手机版脚本的关系

`userscript/bilibili-clean-mobile.user.js` 是手机端方案（Android Via/X、iOS Safari + Userscripts，作用域 m.bilibili.com）。两者判定核心同源（同一套 CBI 曲线与阈值）：PC 用扩展、手机用脚本，合起来全平台覆盖。

## 更新

重新下载 ZIP 覆盖 `extension/` 文件夹 → `edge://extensions` 里点该扩展的「重新加载」→ 刷新 B 站。
