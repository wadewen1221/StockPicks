# 智能 A 股投资助手 (Stock Picks V2)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Tests](https://img.shields.io/badge/tests-99%20passed-brightgreen.svg)](backend/tests/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](.github/workflows/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub stars](https://img.shields.io/github/stars/wadewen1221/StockPicks?style=social)](https://github.com/wadewen1221/StockPicks/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/wadewen1221/StockPicks?style=social)](https://github.com/wadewen1221/StockPicks/network)

[English](#english) | [中文](#中文)

---

# English

> One-stop A-share quantitative stock-picking platform: multi-strategy scoring + local historical data + Web dashboard + automated scheduling.

## What is this?

**Stock Picks V2** is an A-share quantitative analysis platform for individual investors and quant researchers. It wraps the full loop — **data acquisition → stock-picking strategy → backtest validation → web visualization** — and runs automatically every trading day, so recommended stocks land on your Web dashboard while you sleep.

## ✨ Highlights

| Module | Feature |
|---|---|
| 🎯 **Multi-strategy selection** | 4 parallel strategies (mid-long value / aggressive breakout / steady oversold / RSRS combo) screen 5300+ A-shares |
| 🧠 **Smart analysis** | Input a stock code → 17 technical indicators + buy/sell score + composite recommendation |
| 📊 **Pro backtest** | Backtrader-based, real A-share commission model (stamp duty / transfer fee / regulatory fee), outputs SQN / annualized / max drawdown |
| 📅 **Auto scheduler** | APScheduler triggers data download / selection / backtest / news update |
| 📰 **Morning news** | Daily 07:00 fetch hot sectors / financial news |
| 📈 **Visualization** | Vue 3 + ECharts + Bokeh — K-line / MACD / Bollinger / RSRS in one chart |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (recommended 3.12)
- Node.js 18+ and npm
- Windows / macOS / Linux

### One-Click (Docker)

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
docker-compose up -d
# Frontend: http://localhost:8080
# Backend API: http://localhost:5001/api/health
```

### Development Mode

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
pip install -r requirements.txt
cd frontend && npm install && cd ..
python backend/start_v2.py  # http://localhost:5001
```

### Production Deployment

See [DEPLOY.md](DEPLOY.md) for full guide (Docker, Nginx, HTTPS, monitoring).

## 📊 Strategies

| Strategy | Score System | Description |
|---|---|---|
| **Mid-long value** | Trend(20) + Momentum(15) + Position(20) + Volume/Price(20) + Volatility(20) | Score ≥95, ROE ≥10%, 1-3 month holding |
| **Aggressive breakout** | Limit-up gene + Sentiment + Capital + Position (100 max) | Score 100, near-term trend continuation, 1-3 day trade |
| **Steady oversold** | Low position + Volume/Price + Trend (100 max) | Score 100, oversold rebound, 1-2 week |
| **RSRS combo** | KDJ + RSI + CCI + RSRS (60 max) | Score 60, resistance/support relative strength |

All strategies backtested on **local 1500+ daily bars** with **real A-share commission model** (stamp 0.05% + transfer 0.001% + regulatory 0.003% + brokerage 0.01%).

## 🏗️ Architecture

```
┌────────────────────────────────────────┐
│         Frontend (Vue 3)               │
│  Dashboard │ StockList │ StockDetail   │
│  Backtest  │ Charts    │ News          │
└──────────────┬─────────────────────────┘
               │ REST API (/api/*)
┌──────────────▼─────────────────────────┐
│         Backend (Tornado)              │
│  Handlers ─ Selector Engine ─ Backtest │
└──────────────┬─────────────────────────┘
               │
   ┌───────────┼───────────┐
   ▼           ▼           ▼
Tencent/Sina  Local JSON   APScheduler
API           (5500×1500)  (07:00/17:30/18:30)
```

## 🎯 Strategies in Detail

| Strategy | Score | Description |
|---|---|---|
| Mid-long value | 95+ | ROE≥10%, multi-timeframe trend alignment |
| Aggressive breakout | 100 | Limit-up gene + sentiment + capital |
| Steady oversold | 100 | Low-position + volume contraction |
| RSRS combo | 60 | Resistance/support relative strength |

All backtested on local 1500+ daily bars with real A-share commission model.

## 📚 Documentation

- [Quick Start](https://wadewen1221.github.io/StockPicks/getting-started/) — 5-min walkthrough
- [Strategy Details](https://wadewen1221.github.io/StockPicks/strategies/overview/) — 4 strategies explained
- [Docker Deployment](https://wadewen1221.github.io/StockPicks/deployment/docker/) — one-click
- [API Reference](https://wadewen1221.github.io/StockPicks/api/backend/) — backend endpoints
- [PR Workflow](https://wadewen1221.github.io/StockPicks/contributing/pr-guide/) — contribute guide

Local preview:

```bash
pip install mkdocs mkdocs-material mkdocstrings[python] pymdown-extensions
mkdocs serve   # http://localhost:8000
```

## 🤝 Contributing

We welcome any form of contribution:

- 🐛 [Report bugs](../../issues)
- 💡 [Suggest features](../../issues)
- 📝 [Submit PRs](CONTRIBUTING.md)
- 📚 [Improve docs](docs/)

### Tests

Project uses pytest. Currently **99 unit tests** cover core modules:

```bash
cd backend
python -m pytest tests/ -v
```

Coverage:

- **Technical indicators** — MA/MACD/RSRS/KDJ/RSI/CCI (23 cases)
- **Scoring** — 4 strategies logic (14 cases)
- **LRU cache** — expiry/eviction/stats (8 cases)
- **Config loading** — env/production checks (12 cases)
- **Data fetcher** — JSON parse/cache/validate (12 cases)
- **Fiscal scoring** — ROE/ST/cash (8 cases)
- **Quarterly fiscal** — baostock + akshare fallback (12 cases)
- **Module compat** — verify old API still works (10 cases)

### CI/CD

PRs trigger GitHub Actions across:

- **Backend**: Ubuntu + Windows, Python 3.11 / 3.12
- **Frontend**: Ubuntu + Windows, Node 18 / 20 / 22
- **Docs**: MkDocs build + GitHub Pages deploy

## ⚠️ Disclaimer

This project is for **learning and research only**:

- ❌ Does NOT constitute investment advice
- ❌ Does NOT provide real-trading interface
- ❌ Past backtest performance ≠ future returns
- ✅ Investing carries risk, enter market cautiously

## 📜 License

[MIT License](LICENSE)

## 🙏 Acknowledgments

- [akshare](https://github.com/akfamily/akshare) — A-share data interface
- [baostock](https://baostock.com) — primary financial data source
- [Backtrader](https://github.com/mementum/backtrader) — backtest framework
- [stockstats](https://github.com/jealous/stockstats) / [finta](https://github.com/peerchemist/finta) — technical indicators
- [Bokeh](https://github.com/bokeh/bokeh) — interactive charts
- [Vue 3](https://github.com/vuejs/core) + [Element Plus](https://github.com/element-plus/element-plus) — frontend framework

## ⭐ Star History

If this project helps you, a star would be appreciated!

![Star History Chart](https://api.star-history.com/svg?repos=wadewen1221/StockPicks&type=Date)

---

# 中文

> 一站式 A 股智能选股与回测平台：多策略评分 + 历史数据本地化 + Web 可视化 + 定时任务自动化。

## 这是什么？

**Stock Picks V2** 是一个面向个人投资者和量化研究者的 A 股量化分析平台。它把 **数据获取 + 选股策略 + 回测验证 + 结果可视化** 做成完整闭环，每天在盘后自动运行，把推荐股票推到 Web 端供您查看。

## ✨ 核心能力

| 模块 | 功能 |
|---|---|
| 🎯 **多策略选股** | 4 套并行选股策略（中长线价值 / 激进超短 / 稳健超短 / RSRS 组合），从 5300+ 只 A 股中精选 |
| 🧠 **智能股票分析** | 输入股票代码 → 17 种技术指标 + 买卖评分 + 综合建议 |
| 📊 **专业回测** | 基于 Backtrader，真实 A 股佣金模型（印花税/过户费/规费），输出 SQN、年化、最大回撤 |
| 📅 **自动调度** | APScheduler 触发数据下载、选股、回测、新闻更新 |
| 📰 **早间资讯** | 每天 7:00 抓取热点板块、经济新闻 |
| 📈 **可视化** | Vue 3 + ECharts + Bokeh，K 线、MACD、布林带、RSRS 一图全览 |

## 🚀 快速开始

### 环境要求

- Python 3.10+ (推荐 3.12)
- Node.js 18+ 和 npm
- Windows / macOS / Linux

### 一键启动（Docker）

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
docker-compose up -d
# 前端: http://localhost:8080
# 后端 API: http://localhost:5001/api/health
```

### 开发模式

```bash
git clone https://github.com/wadewen1221/StockPicks.git
cd StockPicks
pip install -r requirements.txt
cd frontend && npm install && cd ..
python backend/start_v2.py  # http://localhost:5001
```

### 生产部署

完整部署指南（含 Docker、Nginx、HTTPS、监控）：见 [DEPLOY.md](DEPLOY.md)

## 📊 选股策略详解

| 策略 | 评分体系 | 特点 |
|---|---|---|
| **中长线价值** | 趋势(20) + 动量(15) + 位置(20) + 量价(20) + 波动(20) | 满分 95+，基本 ROE≥10%，适合 1-3 个月持有 |
| **激进超短** | 涨停基因 + 情绪 + 资金 + 位置 (满分 100) | 满分 100，精选近期定停股，适合 1-3 天博弈 |
| **稳健超短** | 低位 + 量价 + 趋势 (满分 100) | 满分 100，寻找超跌反弹，适合 1-2 周 |
| **RSRS 组合** | KDJ + RSI + CCI + RSRS (满分 60) | 满分 60，新增阻力支撑相对强度指标，挖掘趋势拐点 |

所有策略都用本地 **1500+ 日数据回测验证**，配合真实 A 股交易成本结构（印花 0.05% + 过户 0.001% + 规费 0.003% + 佣金 0.01%）。

## 🏗️ 架构

```
┌────────────────────────────────────────┐
│          前端 (Vue 3)                   │
│  Dashboard │ StockList │ StockDetail   │
│  Backtest  │ Charts    │ News          │
└──────────────┬─────────────────────────┘
               │ REST API (/api/*)
┌──────────────▼─────────────────────────┐
│          后端 (Tornado)                 │
│  Handlers ─ 选股引擎 ─ Backtrader 回测  │
└──────────────┬─────────────────────────┘
               │
   ┌───────────┼───────────┐
   ▼           ▼           ▼
Tencent/Sina  本地 JSON    APScheduler
API           (5500×1500)  (07:00 / 17:30 / 18:30)
```

详细的模块文档：[docs/](docs/)

## 📚 在线文档站

项目使用 MkDocs + Material 主题构建文档站，推到 master 后自动部署到 GitHub Pages。

文档内容：

- 🚀 [快速上手](https://wadewen1221.github.io/StockPicks/getting-started/) — 5 分钟跑通
- 🧠 [选股策略详解](https://wadewen1221.github.io/StockPicks/strategies/overview/) — 4 套策略逻辑
- 🐳 [Docker 部署](https://wadewen1221.github.io/StockPicks/deployment/docker/) — 一键启动
- 📖 [API 参考](https://wadewen1221.github.io/StockPicks/api/backend/) — 后端接口
- 🤝 [提 PR 流程](https://wadewen1221.github.io/StockPicks/contributing/pr-guide/) — 完整指南

本地预览文档：

```bash
pip install mkdocs mkdocs-material mkdocstrings[python] pymdown-extensions
mkdocs serve   # http://localhost:8000
```

## 🤝 参与贡献

我们欢迎任何形式的贡献：

- 🐛 报告 Bug：[Issues](../../issues)
- 💡 提出新功能：[Issues](../../issues)
- 📝 提交 PR：[CONTRIBUTING.md](CONTRIBUTING.md)
- 📚 完善文档：直接提 PR

### 运行测试

项目采用 pytest 单元测试，**99 个用例**覆盖核心模块：

```bash
cd backend
python -m pytest tests/ -v
```

测试覆盖：

- **技术指标** - MA/MACD/RSRS/KDJ/RSI/CCI (23 用例)
- **打分函数** - 4 套策略评分逻辑 (14 用例)
- **LRU 缓存** - 过期/淘汰/统计 (8 用例)
- **配置加载** - 环境变量/生产校验 (12 用例)
- **数据获取** - JSON 解析/缓存/校验 (12 用例)
- **财务评分** - ROE/ST/现金 (8 用例)
- **季度财报** - baostock + akshare 兜底 (12 用例)
- **模块拆分兼容** - 验证旧 API 仍可用 (10 用例)

提交 PR 前请确保 `pytest tests/` 全绿。

### CI/CD

推到 PR 后 GitHub Actions 会在以下环境自动运行测试：

- **后端**: Ubuntu + Windows, Python 3.11 / 3.12
- **前端**: Ubuntu + Windows, Node 18 / 20 / 22
- **文档**: MkDocs build + GitHub Pages 自动部署

### Docker 一键部署

本项目提供 `docker-compose.yml`，可以**不装 Python/Node** 就能跑起来。

前置要求：[Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows / Mac / Linux）

```bash
# 在项目根目录执行：
docker-compose up -d              # 后台启动全部服务
docker-compose ps                 # 查看运行状态
docker-compose logs -f backend    # 实时查看后端日志
docker-compose down               # 停止并清理
```

启动后访问：

- **前端**: [http://localhost:8080](http://localhost:8080)
- **后端 API**: [http://localhost:5001/api/health](http://localhost:5001/api/health)
- **健康检查**: [http://localhost:8080/healthz](http://localhost:8080/healthz)

数据默认会持久化到 Docker volume（`stock_picks_data` / `stock_picks_fiscal` / `stock_picks_logs`），删除容器不丢数据。

查看 `.github/workflows/ci.yml` 获取详情。

> 📢 **重要**：本项目**不进行任何实盘交易**，所有数据用于学术研究和策略验证。

## ⚠️ 风险声明

本项目仅供**学习和研究**使用：

- ❌ 不构成任何投资建议
- ❌ 不提供实盘交易接口
- ❌ 历史回测业绩不代表未来收益
- ✅ 投资有风险，入市需谨慎

## 📜 开源协议

[MIT License](LICENSE)

## 🙏 致谢

- [akshare](https://github.com/akfamily/akshare) - A 股数据接口
- [baostock](https://baostock.com) - 主财务数据源
- [Backtrader](https://github.com/mementum/backtrader) - 回测框架
- [stockstats](https://github.com/jealous/stockstats) / [finta](https://github.com/peerchemist/finta) - 技术指标库
- [Bokeh](https://github.com/bokeh/bokeh) - 交互式图表
- [Vue 3](https://github.com/vuejs/core) + [Element Plus](https://github.com/element-plus/element-plus) - 前端框架

## ⭐ Star History

如果这个项目对您有帮助，欢迎 🙌 Star 支持一下！

![Star History Chart](https://api.star-history.com/svg?repos=wadewen1221/StockPicks&type=Date)