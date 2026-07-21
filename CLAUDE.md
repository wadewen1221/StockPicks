# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**智能A股投资助手** — 自动化 A 股股票推荐网站，每日更新中长线价值投资组合和短线动量股票。

**技术栈**: Python Flask + HTML + ECharts

**数据源**: akshare + 腾讯财经 API，本地历史数据存储

---

## 目录结构

```
stock-picks-v2/
├── backend/
│   ├── main.py              # Flask 服务器入口
│   ├── scheduler.py         # 定时任务调度
│   ├── config.py            # 配置文件
│   ├── handlers/            # 请求处理器
│   ├── indicators/          # 技术指标计算
│   ├── jobs/                # 定时任务实现
│   ├── libs/                # 公共库
│   ├── data/                # 数据存储
│   │   └── historical/      # 历史 K 线数据 (5000+ 股票)
│   ├── backtest/            # 回测模块
│   └── logs/                # 日志文件
├── frontend/
│   ├── index.html           # 主页
│   └── app.js               # 前端逻辑
└── data -> /d/D:/stock-picks/data/  # 符号链接到数据目录
```

---

## 核心模块

| 模块 | 文件 | 用途 |
|------|------|------|
| Flask 入口 | `main.py` | 服务器启动、路由定义 |
| 定时调度 | `scheduler.py` | 定时任务调度器 |
| 数据获取 | `libs/data_fetcher.py` | akshare/腾讯 API 数据抓取 |
| 选股器基类 | `libs/stock_selector.py` | 评分逻辑基类 |
| 三步法选股 | `jobs/three_step_selector.py` | 技术面→基本面→消息面 |
| 新闻抓取 | `libs/news_fetcher.py` | 新闻舆情分析 |
| 技术指标 | `indicators/` | MA, MACD, KDJ 等指标计算 |
| 基本面筛选 | `libs/financial_filter.py` | ROE、利润增速、市盈率筛选 |
| 周报生成 | `libs/report_generator.py` | 生成 docx 格式周报 |
| K线下载 | `jobs/historical_data_downloader.py` | 历史 K 线批量下载 |

---

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/stocks` | GET | 获取当前推荐股票列表 |
| `/api/stock/<code>` | GET | 获取单只股票 K 线数据 |
| `/api/market` | GET | 市场指数（沪深 300、上证等） |
| `/api/sectors` | GET | 热门板块排行 |
| `/api/report` | GET | 最新周报 |
| `/api/news` | GET | 最新财经新闻 |

---

## 定时任务

| 时间 | 任务 |
|------|------|
| 交易日 15:30 | 下载历史数据 + 三步法选股 |
| 交易日 20:00 | 发送选股结果通知 |
| 每周日 20:00 | 生成并发送周报 |
| 交易日 09:30 | 早间选股快速更新 |

---

## 选股规则

### 中长线价值投资
1. **技术面初选** → 16 只候选
2. **基本面筛选** → 财务指标过滤
3. **消息面确认** → 舆情分析
4. **目标**: 精选 4 只
5. **评分门槛**: > 30 分

### 超短线动量策略
- **激进型**: 3 只，评分 > 15
- **稳健型**: 6 只，评分 > 20
- **目标**: 精选 3 只

---

## 启动方式

```bash
# 生产环境
cd D:/stock-picks-v2/backend
python main.py

# 或使用脚本
.\start_prod.bat

# 开发环境
python start_v2.py
```

---

## 测试

```bash
cd D:/stock-picks-v2/backend
pytest tests/ -v                    # 运行所有测试
pytest tests/test_stock_selector.py  # 运行单个测试文件
```

---

## 数据源优先级

1. 新浪财经
2. 腾讯行情
3. 东方财富（仅财务数据）

**注意**: 绝对不用东方财富历史 K 线 API（易被封禁）

---

## 用户偏好

- 喜欢**简洁代码**，不喜欢过度抽象
- 如果 API 连不上就用**网络爬虫**
- 成交量异常（超过历史中位数 100 倍）时自动触发修正流程
- 绝对不进行实盘交易操作
- 绝对不修改未备份的原始数据文件
