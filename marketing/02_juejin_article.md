# 掘金技术博文

## 标题
我用 Python 撸了一个开源 A 股选股工具:从数据下载到 Backtrader 回测全自动

## 简介
5000 只 A 股、4 套选股策略、17 个技术指标、真实回测、定时任务全自动——本文从技术架构到代码实现,讲清楚一个量化选股平台是怎么搭起来的。

## 正文大纲
- 序:为什么做这个工具(背景/痛点)
- 一、整体架构(Tornado + Vue3 + APScheduler)
- 二、数据层:5000+ 只 A 股 × 1500 日 K 线怎么存
- 三、选股引擎:4 套策略并行打分
  - 3.1 中长线价值(趋势+动量+位置+量价+波动)
  - 3.2 激进超短(涨停基因+情绪+资金+位置)
  - 3.3 稳健超短(低位+量价+趋势)
  - 3.4 RSRS 阻力支撑相对强度
- 四、回测层:Backtrader 接入真实 A 股佣金模型
- 五、定时任务:07:00 / 17:30 / 18:30 自动化
- 六、季度财报:baostock + akshare 兜底 7 项指标
- 七、前端可视化:Bokeh + ECharts + Vue3
- 八、CI/CD:GitHub Actions 多平台测试
- 九、Docker 一键部署
- 十、踩坑与反思(选股慢、回测慢、数据漂移)

## 完整正文

### 序:为什么做这个工具

作为一个 20 年 A 股老韭菜,我用过同花顺、通达信、聚宽、米筐,但都有一个共同问题:**闭源、收费、没法自定义策略**。

于是 2024 年我开始自己撸,V1 跑了一年觉得架构太烂(全塞在一个文件里 1700 行),2025 年决定重写 V2。

目标很简单:

1. 数据全自动下载(不依赖任何云服务)
2. 策略可插拔(增删改不重启)
3. 回测真实(用 A 股实际佣金)
4. 选股结果推 Web(手机能看)
5. **可维护**:模块拆分 + 单元测试 + CI 自动化

### 一、整体架构

```
┌─────────────────────────────┐
│      前端 (Vue 3)            │
│  Dashboard│StockList│Detail│
└──────────┬──────────────────┘
           │ REST API
┌──────────▼──────────────────┐
│     后端 (Tornado)           │
│  Handlers│Selector│Backtest │
└──────────┬──────────────────┘
           │
   ┌───────┼────────┐
   ▼       ▼        ▼
腾讯/新浪  本地JSON  APScheduler
API       5000×1500 07/17/18时
```

**部署**:Docker Compose 一键起。

### 二、数据层

5000+ 只 A 股 × 1500 日 K 线 ≈ 750 万条数据。

存储选 JSON 而不是数据库,理由:

- 量不大,单只 1500 行 ≈ 30KB
- 调试方便(`cat` 直接看)
- 不依赖额外服务

**增量下载**:每天 17:30 检查每只股票每个日期,缺失就补,已存在跳过。**5527 只股票**,正常增量 5 分钟完成。

### 三、选股引擎(核心)

**核心代码**:`backend/selector/`,我从 1700 行单文件拆出来。

#### 3.1 中长线价值策略

```python
def score_long_term(stock):
    return {
        '趋势': trend_score(stock),    # MA 60/120 多头排列 20分
        '动量': momentum_score(stock),  # 近 20 日涨幅 15分
        '位置': position_score(stock),  # 价格在 60 日线下方? 20分
        '量价': volume_price(stock),    # 量比+换手率 20分
        '波动': volatility_score(stock),# ATR 标准化 20分
    }
```

满分 100,中长线 ≥ 95 入选。

#### 3.2-3.4 其他策略类似

(完整代码见 GitHub)

### 四、回测层

Backtrader 框架。A 股佣金模型:

```python
COMMISSION_PCT = 0.0001   # 佣金 0.01%
STAMP_TAX = 0.0005        # 印花税 0.05%(卖出)
TRANSFER_FEE = 0.00001    # 过户费 0.001%
REGULATORY_FEE = 0.00003  # 规费 0.003%
```

回测结果给出:SQN、年化、最大回撤、夏普比率。

### 五、定时任务

```python
scheduler.add_job(_run_data_update,
    CronTrigger(hour=17, minute=30, ...))  # 17:30 数据下载
scheduler.add_job(_run_stock_selection,
    CronTrigger(hour=18, minute=30, ...))  # 18:30 选股+回测
scheduler.add_job(_run_news_update,
    CronTrigger(hour=7, minute=0, ...))    # 07:00 早间资讯
scheduler.add_job(_run_fiscal_update,
    CronTrigger(month='5,9,11', day=10, hour=2, ...))  # 季度财报
```

**踩坑**:启动时间晚于 18:30,选股任务就漏掉了。修复方案:`coalesce=True` + 启动检查。

### 六、季度财报(7 项财务指标)

baostock + akshare 双源兜底:

| 字段 | baostock | akshare 接口 |
|---|---|---|
| 营业总收入 | MBRevenue×1e6 | stock_financial_abstract |
| 归母净利润 | netProfit | stock_financial_abstract |
| **扣非净利润** | deductProfit | **stock_profit_sheet_by_report_em** |
| 每股净资产 | netProfit/totalShare | stock_financial_abstract |
| 资产负债率 | liabilityToAsset×100 | stock_financial_abstract |
| 总股本 | totalShare | stock_balance_sheet_by_report_em |
| 流通股本 | liqaShare | (akshare 缺,留空) |

**字段合并策略**:baostock 主源 + akshare 字段级补集(不覆盖已有)。

### 七、前端

- Vue 3 + Vite
- Bokeh:单只股票技术指标图(K线 + MA + MACD + RSRS)
- ECharts:选股结果对比、行业分布
- 响应式布局(手机能用)

### 八、CI/CD

GitHub Actions 矩阵:

- 后端:Ubuntu + Windows × Python 3.11/3.12/3.13
- 前端:Ubuntu + Windows × Node 18/20/22
- Docs:MkDocs build
- 文档站:自动 push GitHub Pages

**99 个单元测试**全绿。

### 九、Docker 一键部署

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["5001:5001"]
  frontend:
    image: nginx:alpine
    ports: ["8080:80"]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
```

不需要装 Python/Node。

### 十、踩坑与反思

1. **数据漂移**:老项目的财务数据 10 字段,新项目改成 7 字段,迁移要写脚本
2. **回测慢**:backtrader 串行回测 5000 只股票需要 30 分钟,后来改 multiprocessing 提速 8 倍
3. **选股慢**:完整跑一遍 selector 需要 ~1 小时,但只在 18:30 跑一次,可接受
4. **GitHub Actions 资源**:5 job 并行把 runner 跑 OOM,后端任务加 `continue-on-error: true` 软失败
5. **CI 安全**:别把 token 写进 commit!我的 5 个 GitHub PAT 在这次开发中被泄露,全部手工 revoke 了

---

**源码**:`https://github.com/wadewen1221/StockPicks`
**文档站**:`https://wadewen1221.github.io/StockPicks/`
**💬 站内讨论 / 找一起做的伙伴**:`https://hi.hirey.ai/listing/listing_d03ad5792df6`

如果对你有帮助，来个 star 就好~ ⭐

> 想加策略/因子/前端/测试，欢迎在 Hi 站内联系我，或者直接开 issue / PR。

## 标签
Python / 量化 / 选股 / A股 / Backtrader / 开源