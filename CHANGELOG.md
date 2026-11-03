# Changelog

本项目的所有重要变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

（暂无）

## [1.0.0] - 2026-11-03

### 新增
- 一条命令完成「抓取 → 三维分类 → 看板生成」，产物为零依赖自包含离线 HTML。
- 数据抓取：东方财富资讯列表 API，覆盖「宏观政策（column 345）」与「财经要闻（column 344）」双栏目；单栏目失败时优雅降级。
- 三维分类：
  - 情绪：利好 / 利空 / 中性，基于关键词权重打分；
  - 行业板块：15 类词典；
  - 个股：60 只常用 A 股词典 + 6 位代码识别。
- 看板交互：
  - 顶部 KPI 卡（今日新闻 / 利好 / 利空 / 中性 / 板块 / 个股）全部可点击聚合过滤，支持叠加组合；
  - 吸顶板块 chip 菜单，点击聚合该板块新闻；
  - 新闻行点击弹出详情（摘要、判定依据关键词、原文链接）。
- 自动刷新：`--loop 600` 常驻模式每 10 分钟重抓重绘；页面倒计时归零自动载入最新数据。
- 词典全开放：脚本顶部 `POS_KW / SECTORS / STOCKS` 等常量可直接扩展，无需改动逻辑。
- 分发校验：`manifest.json` 提供各文件 sha256 清单，可校验分发一致性。

### 说明
- 零第三方依赖，仅使用 Python 3.8+ 标准库。
- 产物 HTML 内联样式与原生 JS，无 CDN，断网可用。

[Unreleased]: https://github.com/henrychen8888/daily-finance-dashboard/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/henrychen8888/daily-finance-dashboard/releases/tag/v1.0.0
