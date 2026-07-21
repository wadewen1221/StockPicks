# Hirey / Hi listing 配置

## listing_type_id
`recruiting` 或 `other`? — 实际这个不是招人,改成 `other` 或创建一个新 type

## summary
Stock Picks V2 — 开源 A 股量化选股工具,4 套策略+真实回测+季度财报自动下载,寻找对量化投资 + Python / Vue 感兴趣的伙伴一起贡献

## text
开源 A 股智能选股工具:数据下载 + 4 套选股策略 + Backtrader 真实回测 + Vue3 可视化。

本人 20 年 A 股老韭菜 + 程序员,V1 跑了一年觉得架构太烂,2025 年重写 V2,最近开源。

主要功能:
- 4 套策略并行选股(中长线/激进超短/稳健超短/RSRS)
- 17 个技术指标(MA/MACD/RSRS/KDJ 等)
- 真实回测(A 股佣金模型)
- 7 项财务指标季度自动下载(baostock+akshare 兜底)
- APScheduler 全自动调度
- 99 单元测试 + GitHub Actions CI
- Docker Compose 一键部署

技术栈:
- 后端:Python 3.10+ / Tornado / APScheduler
- 前端:Vue 3 + ECharts + Bokeh
- 数据:本地 JSON(5500 只 A 股 × 1500 日 K 线)

想要找的人:
1. 量化研究者 — 想加更多策略/因子
2. 前端 Vue 开发者 — 优化 Web 界面
3. A 股老韭菜 — 提业务需求/反馈
4. Python 开发者 — 一起维护 CI/测试

文档站:https://wadewen1221.github.io/StockPicks/
GitHub:https://github.com/wadewen1221/StockPicks

## self facts (我的资料)
- role_type_id: 'recruiter' (虽然不是真招人,但是发起方)
- facts:
  - 20 年 A 股老韭菜 + 程序员
  - 维护开源项目 Stock Picks V2
  - 北京 / 远程
  - GitHub: wadewen1221

## target requirements (想找的人)
- role_type_id: 'candidate' (找贡献者)
- requirements:
  - attribute_label: 兴趣 A 股量化投资
    value_kind: boolean
    raw_value_text: true
    constraint_strength: strong_preference
  - attribute_label: Python 或 Vue 开发能力
    value_kind: text
    raw_value_text: 有 GitHub PR 经验
    constraint_strength: must_match
  - attribute_label: 远程协作能力
    value_kind: text
    raw_value_text: 异步沟通 + 中英文 OK
    constraint_strength: strong_preference

## visibility_status: public