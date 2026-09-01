# 第三方组件声明（THIRD PARTY NOTICES）

本项目使用了以下第三方开源代码，在此保留其版权与许可声明。

---

## BewlyBewly（UI 框架基础）

- 项目地址：https://github.com/hakadao/BewlyBewly
- 作者：Hakadao
- 协议：MIT License
- 使用方式：**在 BewlyBewly 源码基础上做增量开发**（保留其首页接管框架、网格布局、卡片组件、设置体系与无限滚动机制），插入本项目的自定义过滤算法。
- 本项目改动部分的版权归本项目所有，其余部分遵循以下原始许可：

```
MIT License

Copyright (c) 2021 Hakadao(hakadao2000@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 本项目自有部分的归属

以下内容为洁净B站项目的原创增量，不来自 BewlyBewly：

1. **CBI 感谢指数过滤算法**（加权感谢率 F7 ÷ 同播放段基线中位数，判定「看过，却不给」）——源自本项目的生态调查报告《看过，却不给》（7,537 条样本、十三项统计实验）
2. **过滤器判定核心**（同步层：直播/短视频/标题签名 R1/R7；懒判定层：竖屏/低播放/官方区白名单/CBI/junk 兜底/乞讨打标，R1-R8）
3. **数据与分析管线**（engine/ 目录：采集、评分、校准、统计实验、报告构建）
4. **调查报告本体**（web/ecosystem-report.html）

分发本扩展时，BewlyBewly 的上述版权声明须随副本一同保留。
