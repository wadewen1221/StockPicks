# 更新日志 (Changelog)

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

---

## [Unreleased] - 2026-07-21

### 🛠️ 改进
- **架构调整**：从老版本 `D:\stock-picks\` 完整迁移到独立 V2 项目
- **代码清理**：移除 5 个空目录占位符，重整包结构
- **风险声明**：明确标注"不进行实盘交易"

### 🐛 Bug 修复
- 修复 `calculate_rsrs()` 函数**未返回 slope 字段**的 P0 bug（导致前端 RSRS 斜率永远显示为 0）
- 修复前端 `StockDetail.vue` 中**涨跌幅计算错误**（改用昨收价计算）

### 📝 文档
- 新增 README.md（项目介绍、快速启动、贡献指南）
- 新增 CONTRIBUTING.md（贡献流程、代码规范）
- 新增 CHANGELOG.md（本文件）
- 新增 LICENSE（MIT）
- 新增 .gitignore（覆盖敏感文件、缓存、构建产物）
- 新增 .env.example（环境变量模板，替代已误提交的 .env）

### ✨ V2.1 模块化重构（2026-07-21）

#### D1. 拆分选股引擎 - 模块化架构
- 原 `stock_selector.py` (1706 行) 拆分为 `backend/selector/` 包 (6 个模块):
  - `cache.py` (55 行) - LRU 缓存
  - `data_fetcher.py` (244 行) - 历史数据获取
  - `fiscal.py` (241 行) - 基本面财务数据
  - `indicators.py` (366 行) - 17 种技术指标
  - `scorer.py` (363 行) - 5 套打分函数
  - `strategies.py` (393 行) - 选股主流程
- `stock_selector.py` 变为 79 行薄壳,仅负责重导出 (向后兼容所有旧 import)
- `StockSelector` 门面类代理所有指标/打分/选择方法
- 纯函数设计: `select_*_stocks` 接收 fetcher 参数,便于测试
- `DataFetcher` / `FiscalDataFetcher` 接受可选 `historical_dir` / `fiscal_dir` 参数

#### D2. pytest 单元测试 - 87 个用例
- `tests/conftest.py` - 共享 fixtures (合成历史数据)
- `tests/test_cache.py` - 8 用例
- `tests/test_config.py` - 12 用例
- `tests/test_data_fetcher.py` - 12 用例
- `tests/test_fiscal.py` - 8 用例
- `tests/test_indicators.py` - 23 用例 (含 RSRS 修复回归保护)
- `tests/test_scorer.py` - 14 用例
- `tests/test_split_compat.py` - 10 用例

**运行**: `cd backend && python -m pytest tests/ -v` → **87 passed in ~7s**

#### D3. GitHub Actions CI
- `.github/workflows/ci.yml`
- 后端: Ubuntu + Windows × Python 3.11 / 3.12
- 前端: Ubuntu + Windows × Node 18 / 20 / 22
- flake8 + pyflakes 静态检查
- Codecov 覆盖率上传

---

## [2.0.0] - 2026-05-29 至 2026-06-08

### ✨ 核心功能
- **多策略选股引擎**（4 套并行策略）：
  - 中长线价值评分（95 分制）
  - 激进超短线（100 分制，追涨停）
  - 稳健超短线（100 分制，超跌反弹）
  - RSRS/KDJ/RSI/CCI 组合（60 分制，新增 RSRS 指标）
- **A股真实佣金模型**：印花税 0.05% + 过户费 0.001% + 规费 0.003% + 佣金 0.01%
- **Backtrader 回测引擎**：SQN + 夏普比率 + 最大回撤 + 年化收益
- **17 种技术指标**（基于 stockstats + finta）：MA、MACD、KDJ、RSI、CCI、RSRS、BOLL、ATR 等
- **Bokeh 交互式图表**：单页面内嵌图表（24 小时缓存）
- **APScheduler 定时任务**：
  - 交易日 17:30 下载历史数据
  - 交易日 18:30 三步法选股 + 自动回测
  - 每天 07:00 早间资讯更新
- **Vue 3 + Element Plus Web 界面**：
  - Dashboard 仪表盘
  - StockList 选股结果列表
  - StockDetail 单股分析（含买卖评分）
  - Backtest 回测结果
  - Indicators 技术指标页

### 🏗️ 架构
- 前后端分离
- Tornado 6.x + APScheduler 3.10 + Backtrader 1.9
- 本地 JSON 文件存储历史数据（5000+ 只股票）

### ⚙️ 部署
- Gunicorn 多进程生产部署
- Docker 支持（Dockerfile + docker-compose.yml）
- Nginx 反向代理配置
- 健康检查 `/api/health`

---

## 开发记录

- **2026-05-29**：项目初始化，从老版本 `D:\stock-picks\` 重构
- **2026-06-01**：完成 V2 系统技术评估报告（[V2系统技术评估报告.txt](V2系统技术评估报告.txt)）
- **2026-06-08**：完成部署文档（DEPLOY.md），git 初始化
- **2026-07-03**：代码结构整理
- **2026-07-17**：Claude 配置更新
- **2026-07-21**：首次提交，开源准备（README + LICENSE + CONTRIBUTING + .gitignore + 修复 2 个 P0 bug）

