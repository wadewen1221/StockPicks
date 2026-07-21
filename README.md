# 智能 A 股投资助手 (Stock Picks V2)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> 一站式 A 股智能选股与回测平台：多策略评分 + 历史数据本地化 + Web 可视化 + 定时任务自动化

---

## ✨ 这是什么

**Stock Picks V2** 是一个面向个人投资者和量化研究者的 A 股量化分析平台。它把"**数据获取 + 选股策略 + 回测验证 + 结果可视化**"做成完整闭环，每日在盘后自动运行，把推荐股票推到 Web 端供您查看。

### 核心能力

| 模块 | 功能 |
|---|---|
| 📊 **多策略选股** | 4 套并行选股策略（中长线价值 / 激进超短 / 稳健超短 / RSRS 组合），从 5300+ 只 A 股中精选 |
| 📈 **智能股票分析** | 输入股票代码 → 17 种技术指标 + 买卖评分 + 综合建议 |
| 🔁 **专业回测** | 基于 Backtrader，真实 A 股佣金模型（含印花税/过户费/规费），输出 SQN、夏普、最大回撤等指标 |
| 📅 **自动调度** | APScheduler 触发数据下载、选股、回测、新闻更新 |
| 📰 **早间资讯** | 每日 7:00 抓取热点板块、财经新闻 |
| 🎨 **可视化** | Vue 3 + ECharts + Bokeh，K 线、MACD、布林带、RSRS 一图全收 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+ （推荐 3.12）
- Node.js 18+ 和 npm
- Windows / macOS / Linux 任一

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/<your-username>/stock-picks-v2.git
cd stock-picks-v2

# 2. 后端依赖
cd backend
pip install -r ../requirements.txt

# 3. 前端依赖
cd ../frontend
npm install

# 4. 配置环境变量
cd ..
cp backend/.env.example backend/.env
# 编辑 backend/.env,设置 COOKIE_SECRET(可用: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 开发模式

```bash
# 一键启动 (开发模式,自带调试)
python backend/start_v2.py

# 浏览器打开
# http://localhost:5001
```

### 生产部署

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 复制构建产物到后端
# Windows:
xcopy /E /I /Y frontend\dist\* backend\static\
# macOS / Linux:
cp -r frontend/dist/* backend/static/

# 3. 用 Gunicorn 启动
cd backend
pip install gunicorn
export COOKIE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DEBUG=False
export ALLOWED_ORIGINS=https://your-domain.com
gunicorn -w 4 -b 0.0.0.0:5001 main:app
```

> 完整部署指南（含 Docker、Nginx、HTTPS、监控）：见 [DEPLOY.md](DEPLOY.md)

---

## 🧠 选股策略详解

| 策略 | 评分体系 | 特点 |
|---|---|---|
| **中长线价值** | 趋势(20) + 动量(15) + 位置(20) + 量价(20) + 波动(20) | 满 95 分,基本面筛选 ROE≥10%,适合 1-3 个月持有 |
| **激进超短** | 涨停基因 + 情绪 + 资金 + 位置(满分 100) | 满 100 分,筛选近期涨停股,适合 1-3 天博弈 |
| **稳健超短** | 低位 + 量价 + 趋势(满分 100) | 满 100 分,寻找超跌反弹,适合 1-2 周 |
| **RSRS 组合** | KDJ + RSI + CCI + RSRS(满分 60) | 满 60 分,新增阻力支撑相对强度指标,捕捉趋势拐点 |

**所有策略都用本地 1500+ 日数据回测验证**，配合真实 A 股交易成本结构（印花税 0.05% + 过户费 0.001% + 规费 0.003% + 佣金 0.01%）。

---

## 🏗️ 架构

```
┌────────────────────────────────────────────────────────────┐
│                          前端 (Vue 3)                      │
│   Dashboard │  StockList │ StockDetail │ Backtest │ Charts │
└───────────────────────────┬────────────────────────────────┘
                            │  REST API (/api/*)
┌───────────────────────────▼────────────────────────────────┐
│                    后端 (Tornado)                           │
│  Handlers ──► 选股引擎 ──► Backtrader 回测 ──► 数据持久化  │
└───────────────────────────┬────────────────────────────────┘
                            │
        ┌───────────────────┼─────────────────────┐
        ▼                   ▼                     ▼
  Tencent/Sina API   本地历史数据(JSON)      APScheduler
                     (5000+ 只 × 1500 日)      (07:00 / 17:30 / 18:30)
```

详细的模块文档：[docs/](docs/)

---

## 📂 目录结构

```
stock-picks-v2/
├── backend/                # 后端
│   ├── main.py             # Tornado 入口
│   ├── config.py           # 配置(支持环境变量)
│   ├── scheduler.py        # 定时任务
│   ├── selector/           # ✨ 选股引擎(模块化拆分)
│   │   ├── cache.py        # LRU 缓存
│   │   ├── data_fetcher.py # 历史数据获取
│   │   ├── fiscal.py       # 基本面财务数据
│   │   ├── indicators.py   # 17 种技术指标(MA/MACD/RSRS/KDJ/RSI/CCI)
│   │   ├── scorer.py       # 5 套打分函数
│   │   ├── strategies.py   # 选股主流程
│   │   └── __init__.py     # StockSelector 门面类
│   ├── stock_selector.py   # 向后兼容入口(转发到 selector/ 包)
│   ├── handlers/           # 11 个 HTTP handler
│   ├── jobs/               # 4 个定时任务实现
│   ├── backtest_handler.py # 回测引擎 + A 股佣金模型
│   ├── indicators_handler.py # 17 种技术指标
│   └── tests/              # ✨ pytest 单元测试(87 用例)
├── frontend/               # Vue 3 SPA
│   ├── src/views/          # 6 个核心页面
│   ├── vite.config.js
│   └── package.json
├── .github/workflows/      # ✨ GitHub Actions CI
│   └── ci.yml              # 多平台自动测试
├── requirements.txt        # Python 依赖
├── DEPLOY.md               # 生产部署指南
├── .env.example            # 环境变量模板
└── LICENSE                 # MIT 协议
```

---

## 🔌 API 接口

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 健康检查 |
| `/api/stocks` | GET | 选股结果列表（4 套策略） |
| `/api/stock/<code>` | GET | 单只股票详情 |
| `/api/indicators/config` | GET | 17 种技术指标配置 |
| `/api/indicators/<code>` | GET | 单只股票指标图表 (Bokeh) |
| `/api/backtest` | POST | 批量回测 |
| `/api/backtest/<code>` | GET | 单只股票回测 |
| `/api/selection` | POST | 触发单次选股 |
| `/api/selection/only` | GET | 仅返回选股结果 |
| `/api/analyze/<code>` | GET | 智能股票分析（买卖评分） |
| `/api/news` | GET | 早间资讯 |

---

## 🤝 参与贡献

我们欢迎任何形式的贡献：

- 🐛 报告 Bug：[Issues](../../issues)
- 💡 提出新功能：[Issues](../../issues)
- 🔧 提交 PR：[CONTRIBUTING.md](CONTRIBUTING.md)
- 📖 完善文档：直接提交 PR

### 运行测试

项目采用 pytest 单元测试，**87 个用例,覆盖核心模块**:

```bash
cd backend
python -m pytest tests/ -v
```

测试涵盖:
- **技术指标** - MA/MACD/RSRS/KDJ/RSI/CCI (23 用例)
- **打分函数** - 4 套策略评分逻辑 (14 用例)
- **LRU 缓存** - 过期/淘汰/统计 (8 用例)
- **配置加载** - 环境变量/生产校验 (12 用例)
- **数据获取** - JSON 解析/缓存/校验 (12 用例)
- **财务评分** - ROE/ST/现金流 (8 用例)
- **模块拆分兼容** - 验证旧 API 仍可用 (10 用例)

提交 PR 前请确保 `pytest tests/` 全绿。

### CI/CD

推送 PR 后,GitHub Actions 会自动在以下环境运行测试:

- **后端**: Ubuntu + Windows, Python 3.11 / 3.12
- **前端**: Ubuntu + Windows, Node 18 / 20 / 22

查看 `.github/workflows/ci.yml` 获取详情。

> 📌 **重要**：本项目**不进行任何实盘交易**，所有数据用于学术研究和策略验证。

---

## ⚠️ 风险声明

本项目仅供**学习和研究**使用：

- ❌ 不构成任何投资建议
- ❌ 不提供实盘交易接口
- ❌ 历史回测业绩不代表未来收益
- ✅ 投资有风险，入市需谨慎

---

## 📜 开源协议

[MIT License](LICENSE)

---

## 🙏 致谢

- [akshare](https://github.com/akfamily/akshare) - A 股数据接口
- [Backtrader](https://github.com/mementum/backtrader) - 回测引擎
- [stockstats](https://github.com/jealous/stockstats) / [finta](https://github.com/peerchemist/finta) - 技术指标库
- [Bokeh](https://github.com/bokeh/bokeh) - 交互式图表
- [Vue 3](https://github.com/vuejs/core) + [Element Plus](https://github.com/element-plus/element-plus) - 前端框架

---

## 📊 Star History

如果这个项目对您有帮助，欢迎 ⭐ Star 支持一下！

![Star History Chart](https://api.star-history.com/svg?repos=<your-username>/stock-picks-v2&type=Date)

