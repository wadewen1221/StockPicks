# V2EX 分享创造文案

## 标题
[A股开源] 自己做了个量化选股工具,4 套策略+真实回测+每日交易数据、季度财报自动下载

## 正文
[V2EX 分享创造]

做了个开源 A 股智能选股工具,业余时间一人撸出来,分享给同样玩量化的朋友。

### 一句话
**Stock Picks V2** = 数据下载 + 4 套选股策略 + Backtrader 真实回测 + Vue3 可视化,跑通就推到 Web,睡前看一眼。

### 主要特性

- **4 套策略并行选股**(满分筛选):
  - 中长线价值(95 分) - ROE ≥ 10%,适合 1-3 个月持有
  - 激进超短(100 分) - 涨停基因,适合 1-3 天博弈
  - 稳健超短(100 分) - 低位+缩量,适合 1-2 周
  - RSRS 组合(60 分) - 新增阻力支撑相对强度

- **17 个技术指标**:MA / MACD / KDJ / RSI / CCI / RSRS / BOLL / 成交量 / 换手率 ...

- **真实回测**:Backtrader + A 股佣金(印花 0.05% + 过户 0.001% + 规费 0.003% + 佣金 0.01%)
  - 1500+ 日 K 线回测
  - SQN、年化、最大回撤

- **7 项财务指标自动下载**(季度财报):营收/归母/扣非/BPS/负债率/总股本/流通股本
  - baostock + akshare 兜底(baostock 挂了也能跑)

- **定时任务全自动**:07:00 早间资讯 / 17:30 数据下载 / 18:30 选股+回测 / 5/9/11 月 10 号 02:00 季度财报

### 技术栈

- 后端:Python 3.10+ / Tornado / APScheduler
- 前端:Vue 3 + ECharts + Bokeh
- 测试:pytest 99 用例
- CI:GitHub Actions(多平台 + Python 3.11/3.12 + Node 18/20/22)
- 文档:MkDocs + GitHub Pages(https://wadewen1221.github.io/StockPicks/)

### Demo / 在线

- 📚 文档站:https://wadewen1221.github.io/StockPicks/
- 💻 GitHub:https://github.com/wadewen1221/StockPicks
- 🎬 截图:见仓库 README

### 一键启动

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
docker-compose up -d
# 前端: http://localhost:8080
# 后端 API: http://localhost:5001/api/health
```

不需要装 Python/Node,装个 Docker Desktop 就能跑。

### 风险提示

❗ 本项目**不构成任何投资建议**,所有数据用于学习研究。
❗ 历史回测业绩不代表未来收益。
❗ 投资有风险,入市需谨慎。

---

💬 **想合作 / 提需求 / 找贡献伙伴**:[Hi 平台站内联系](https://hi.hirey.ai/listing/listing_d03ad5792df6)（更稳，不会被邮件过滤）

欢迎 star / fork / issue / PR 一起搞~ 有问题可以评论里问。

## 标签
选股 / 量化 / A股 / Python / 开源 / 投资工具