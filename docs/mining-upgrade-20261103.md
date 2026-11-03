# 每日视频目录 v6

公开入口：https://elabation.github.io/bewly-pure/god-shelf.html

## 界面与性能

页头和整页 Livehouse 背景使用原创生成的孤独摇滚同人插画，去掉 Side B 品牌、口号、大块顶部留白和机器主推视频。顶部拖动条支持向上收起、向下展开，键盘方向键也可调整高度。

收录日历按本地首次发现日切换候选目录，空日期禁用，可以翻月、返回最近一期。这不是发布时间日历，也不提供签到或运势。日历结构参考洛谷；背景的层次感参考 Nous Hermes，未搬用其神话画风。

唱片机使用真实 HTMLAudioElement，提供选曲、前后曲、播放暂停、进度、音量、自动续播。仅在实际 playing 事件发生时旋转唱片；缓冲、暂停或失败停止。默认连接 Apple Music 官方试听，有 Spotify 官方试听备用；完整版跳转官方曲目。用户选择的本地音频通过浏览器对象 URL 播放，不上传。

旧复核页将约 3.9 万条记录嵌进 23 MB HTML 并同步处理。现在 HTML 约 96 KB，只内嵌 24 条首屏记录；96 条为一份内容寻址分页，页面始终只有 24 张卡片。全库索引仅搜索时在 Web Worker 中载入，翻页替换而不无限追加。页头约 273 KB，背景约 240 KB；UI 字体为 Noto Sans SC 子集，SIL OFL 许可证随资产提供。首批封面有有界缓存，避免防盗链失败。

## 内容规则

- 每日更新和候选目录要求时长严格大于 150 秒；恰好 2:30 也降档。历史短视频仍可在全部探索中查找，并标注短片。
- 标题出现黑丝、白丝、纯欲、擦边、性感、热舞、福利姬，或出现特定异常互动组合，分流到全部探索供复核。线索不等于内容判决，也不能保证识别所有擦边。
- 不以高投币、应援、感动、辛苦或收藏直接认定神作，不设机器主推区。日常目录按发现日和发布时间呈现，候选目录是互动召回，不是制作质量榜。
- 公开收藏夹的 173 条记录中，170 条可用；标题 TF-IDF 只提供最多 10% 的题材提示，不作为质量正例。兴趣资料不发布。
- 你实际观看并记录制作、共鸣和依据后，符合标准的条目进入“我的认可”。标注只在本地浏览器保存，可导入、导出、撤销，不会自动训练模型。

## 数据修复

共享实现统一固定参照库（2026-09-03 截止），按 BV 去重，采用最近的完整计数快照；无日期的回填仅补元数据。严格 CDF 修复超过 100% 的百分位。历史相关推荐全部合并；R9 声援仅记录，不能重新提档绕过时长限制。旧机器标签不作为人工确认的种子。

## 每日更新

Windows 任务 `GodShelfDaily` 使用 Python 3.7，每天北京时间 12:00 启动 `engine/daily_refresh.py`，漏点可补跑，失败每 15 分钟重试，最多 3 次。

流程：读取 10 页热门（最多 200 条）→ 使用返回的完整元数据，避免逐个调用会 412 的 view 接口 → 最多 8 次相关推荐 → 原始文件按时间戳追加 → 重建轻页面和搜索索引 → 只提交公开网页资产并推送现有 GitHub Pages。接口没有有效结果时返回非零并保留上一版；已有暂存改动时拒绝自动提交，避免夹带无关文件。

任务依赖本机开机、联网和已有 Git 推送配置，日志在 `data/logs/daily_YYYYMMDD.log`。`data/preferences`、`data/review` 不参与公开发布。静态网页的个人标注不会在不同浏览器间自动同步。

## 运行与验证

```powershell
python -X utf8 engine/publish_discovery.py
python -X utf8 engine/serve_discovery.py
# 或运行 run_review.ps1

python -X utf8 engine/daily_refresh.py --no-publish
python -X utf8 engine/daily_refresh.py --build-only --no-publish
python -m unittest discover -s engine -p test_mining_upgrade.py
python -m unittest discover -s engine -p test_discovery_site.py
node --test engine/test_discovery_ui.cjs
```

29 项挖掘回归、6 项站点回归、9 项 UI/搜索测试通过；4 万条夹具首屏小于 100 KB，严格时长边界、空接口保护、首次发现日期、日历、真实播放事件与后台搜索都有覆盖。另在浏览器实际检查拖动收起、切换日期、分页、搜索、标注弹窗、官方试听和手机宽度。

这些检查证明实现行为，不证明“神作”识别准确率。没有完成全部视频的实片审阅；互动与标题都不足以判断内容的制作与表达。

## 公开参考与资产

- Nous Hermes：https://hermes-agent.nousresearch.com/
- 洛谷：https://www.luogu.com.cn/
- Bocchi-Wallpaper（MIT）：https://github.com/OriginalCube/Bocchi-Wallpaper ，参考配色与音乐场景，未复制代码。
- Apple 官方曲目元数据：https://itunes.apple.com/lookup?id=1657318546&entity=song&country=jp
- Spotify 官方专辑：https://open.spotify.com/album/5ZGzGGNAB6U7QlKpdaMu0d
- Noto Sans SC：https://github.com/google/fonts/tree/main/ofl/notosanssc

插画通过内置 imagegen 生成，没有运行额外生成脚本。设计要求为四位乐队成员在排练后的 Livehouse 场景、暖暗舞台光，以及低对比的粉色排练室背景，留出内容阅读区域；无额外文字和标志。项目资产：`assets/bocchi-livehouse-v1.webp` 与 `assets/livehouse-room-v6.webp`。
