---
name: daily-finance-dashboard
display_name: 每日财经新闻看板
display_name_en: Daily Finance News Dashboard
version: 1.0.0
description_zh: 每日财经新闻自动抓取与看板生成 —— 抓取东方财富宏观政策/财经要闻双栏目，按利好/利空/中性情绪 + 15 类行业板块 + 个股三维分类，生成零依赖自包含离线看板 HTML；KPI 卡与板块菜单可点击聚合过滤，新闻行点击弹出详情（摘要/判定依据关键词/原文链接），支持 10 分钟周期自动刷新（脚本常驻 --loop 或页面倒计时自载入）。
description_en: "Daily finance news scraper and dashboard generator: fetches EastMoney macro-policy and market-news columns, classifies by sentiment (bullish/bearish/neutral), 15 industry sectors and individual stocks, and produces a zero-dependency self-contained HTML dashboard with clickable KPI/sector aggregation filters, per-news detail popups (summary, evidence keywords, source link), and optional 10-minute auto refresh."
description: |
  每日财经新闻看板 Skill v1.0.0。一条命令完成「抓取 → 三维分类 → 看板生成」：
    抓取：东方财富资讯列表 API（column 345 宏观政策 / 344 财经要闻），公开接口，仅需标准库；
    分类：情绪（利好/利空关键词权重打分）+ 15 类行业板块词典 + 60 只常用 A 股个股识别；
    看板：自包含离线 HTML（零 CDN / 内联样式 / 原生 JS），紧凑单行排版，吸顶板块菜单；
    交互：KPI 卡与板块菜单点击聚合过滤（可叠加组合），新闻行点击查看详情弹层；
    刷新：--loop 600 常驻模式每 10 分钟重抓重绘，页面倒计时归零自动载入最新数据。

  何时触发：每日财经新闻、财经看板、新闻板块分类、利好利空分类、新闻聚合看板、
  财经资讯爬取看板、自动刷新新闻（完整触发词见 auto_trigger）。
auto_trigger:
  keywords: [每日财经新闻, 财经看板, 新闻看板, 板块分类, 利好利空, 利好板块,
    财经资讯看板, 新闻聚合, 财经新闻爬取, 自动刷新新闻, 每日新闻, 舆情看板,
    行业板块新闻, 个股新闻, 财经头条, 新闻仪表盘, dashboard news]
  patterns:
    - "(每日|每日)?(财经|金融)(新闻|资讯|要闻).*(看板|分类|聚合|刷新)"
    - "(利好|利空).*(板块|分类|看板)"
---

# 每日财经新闻看板（Daily Finance News Dashboard）

一条命令把「今日财经新闻」变成一张**可点击聚合过滤的离线看板**：
抓取 → 情绪/板块/个股三维分类 → 生成自包含 HTML，支持 10 分钟周期自动刷新。

## 快速开始

```bash
# 单次刷新：抓取最新新闻并生成/覆盖看板
python3 scripts/refresh_daily_news.py

# 常驻模式：每 600 秒（10 分钟）自动抓取刷新，Ctrl+C 退出
python3 scripts/refresh_daily_news.py --loop 600

# 自定义输出路径
python3 scripts/refresh_daily_news.py --out /path/to/我的看板.html
```

仅依赖 **Python 3.8+ 标准库**（urllib/json/re/html），零第三方依赖、零 CDN，
产物为自包含 HTML，可直接双击打开、内网分发或随交付包归档。

## 看板能力

| 能力 | 说明 |
|---|---|
| 三维分类 | 每条新闻标注 ① 情绪（利好🔴/利空🟢/中性⚪）② 行业板块（15 类，图标+名称）③ 个股（60 只词典 + 6 位代码正则） |
| 点击聚合过滤 | KPI 卡（利好/利空/中性/个股）与板块菜单 chip 均可点击过滤，**可叠加组合**（如「利空 × 电力能源」），再点取消，顶部显示当前聚合状态条 |
| 详情弹层 | 点击新闻行弹出详情：情绪、所属板块、日期、来源、命中个股、**判定依据关键词**、原文链接；ESC 或点遮罩关闭 |
| 紧凑排版 | 单行行条式列表（时间 + 情绪圆点 + 标题省略 + 标签），吸顶横向滚动板块菜单 |
| 自动刷新 | 页面右上角 10:00 倒计时，归零自动 `location.reload()` 载入脚本重抓的新数据；配 `--loop 600` 即为完整 10 分钟闭环 |
| 离线自包含 | 无 CDN、无外部字体、内联样式与 SVG，断网可用 |

## 数据源

- **东方财富资讯列表 API**（公开接口）：
  - column 345 = 宏观政策资讯
  - column 344 = 财经要闻
- 双栏目抓取后按标题去重，最多保留 60 条。
- 接口失败时单栏目优雅降级（打印 warn 继续跑），全部失败则以非零码退出。

## 定制指南（改词典即可扩展）

所有分类词典集中在 `scripts/refresh_daily_news.py` 顶部：

| 变量 | 用途 | 定制示例 |
|---|---|---|
| `POS_KW` / `NEG_KW` | 利好/利空关键词（`count × 权重`打分） | 加 `"回购"`、`"商誉减值"` |
| `POS_W` / `NEG_W` | 单词命中权重 | 利好词更敏感可调大 POS_W |
| `SECTORS` | 15 类行业板块（名称 + 关键词组），可增删 | 加 `("低空经济", ["低空","eVTOL","通航"])` |
| `STOCKS` | 个股词典（名称 → 代码） | 加 `"中芯国际":"688981"` |
| `EM_COLUMNS` | 东财栏目映射 | 加 `341: "全球资讯"` |
| `REFRESH_SEC` / `--loop` | 刷新周期 | `--loop 300` = 5 分钟 |

> 提示：情绪判定基于关键词词典，反转类消息（如"立案调查终止"）已加入利好词修正；
> 详情弹层展示判定依据关键词，便于人工复核误判并回补词典。

## 常见问题

- **抓取为 0 条**：多为网络/代理拦截或接口变更，脚本会打印每栏目 warn；可先用
  `curl 'https://np-listapi.eastmoney.com/comm/web/getNewsByColumns?client=web&biz=web_news_col&column=345&order=1&needInteractData=0&page_index=1&page_size=5&req_trace=1'`
  验证连通性。
- **个股恒为 0**：宏观主导日属正常（个股词典 + 6 位代码均未命中）；在 `STOCKS` 中补充关注标的即可。
- **倒计时刷新后数据未变**：确认常驻模式在跑（`--loop 600`）；单次模式下页面只会 reload 同一文件。
- **想换成每小时刷新**：`python3 scripts/refresh_daily_news.py --loop 3600 --refresh-sec 3600`。

## 文件结构

```
daily-finance-dashboard/
├── SKILL.md                    # 本文件（技能描述与使用说明）
├── README.md                   # 面向使用者的快速上手
├── manifest.json               # 文件清单 + sha256（可校验交付）
└── scripts/
    └── refresh_daily_news.py   # 自包含抓取/分类/看板生成脚本（单文件）
```
