# A股智能投资助手 V2

> **多策略选股平台** — 4 套策略 × 17 项技术指标 × 财务数据筛选 × 可视化回测

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Vue](https://img.shields.io/badge/Vue-3.5-green)
![Tests](https://img.shields.io/badge/tests-87%20passing-brightgreen)

## 🎯 项目定位

针对 A 股市场的多策略智能选股助手，覆盖 **短线 / 中长线 / 综合** 三类投资风格，通过技术指标 + 基本面财务数据双重筛选，输出可解释的选股结果。

## ✨ 核心特性

| 特性 | 说明 |
| --- | --- |
| 🎯 **4 套选股策略** | 短线激进、中长线稳健、综合均衡、RSRS 阻力支撑 |
| 📊 **17 项技术指标** | MACD / KDJ / RSI / BOLL / RSI / MA / RSRS / 量价 ... |
| 💼 **基本面财务** | ROE / 净利润同比 / 营收增长 / 资产负债率 ... |
| 📈 **回测验证** | Backtrader 框架，支持历史收益与回撤计算 |
| 🌐 **Web 界面** | Vue 3 + Element Plus，支持股票详情、回测图、新闻 |
| 🐳 **一键启动** | Docker Compose 编排，5 分钟跑通 |
| ✅ **87 单元测试** | pytest 全绿，mypy 0 错误 |
| 🚀 **CI/CD** | GitHub Actions 矩阵测试 (Linux/Win × Py3.11/3.12) |

## 📦 快速开始

=== "Docker Compose (推荐)"

    ```bash
    git clone https://github.com/your-username/stock-picks-v2.git
    cd stock-picks-v2
    docker-compose up -d
    # 浏览器访问 http://localhost:8080
    ```

=== "本地开发"

    ```bash
    # 后端
    cd backend
    pip install -r requirements.txt
    python start_v2.py  # http://localhost:5001

    # 前端
    cd frontend
    npm install
    npm run dev  # http://localhost:5173
    ```

## 📚 文档导航

- **[快速上手](getting-started.md)** — 5 分钟跑通项目
- **[选股策略](strategies/overview.md)** — 4 套策略的逻辑与适用场景
- **[技术指标](indicators/list.md)** — 17 项指标的算法说明
- **[部署运维](deployment/local.md)** — 本地 / Docker / 数据更新
- **[开发贡献](contributing/pr-guide.md)** — 提 PR 流程 + 本地开发
- **[API 参考](api/backend.md)** — 后端接口 + 选股模块

## ⚠️ 风险声明

**本项目仅用于学习与研究目的，不构成任何投资建议。**

- 股市有风险，投资需谨慎
- 历史回测表现不代表未来收益
- 请根据个人风险承受能力独立决策

## 📄 License

MIT License — 详见 [LICENSE](https://github.com/your-username/stock-picks-v2/blob/master/LICENSE)