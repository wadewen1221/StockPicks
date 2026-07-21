# 选股模块 API

> `backend/selector/` 模块 — V2.1 拆分后的核心代码

## 模块概览

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `__init__.py` | 162 | `StockSelector` 门面类 |
| `_types.py` | 80 | 共享类型别名 |
| `cache.py` | 55 | LRU 缓存 |
| `data_fetcher.py` | 244 | 历史 K 线获取 |
| `fiscal.py` | 241 | 财务数据获取 |
| `indicators.py` | 366 | 17 项技术指标 |
| `scorer.py` | 363 | 5 套打分函数 |
| `strategies.py` | 393 | 4 套选股策略 |

## StockSelector 门面

```python
from selector import StockSelector

selector = StockSelector()  # 默认读 D:/stock-picks/data

# 自定义数据目录
selector = StockSelector(
    historical_dir='/custom/path',
    fiscal_dir='/custom/path/fiscal'
)

# 运行策略
picks = selector.run_short_term_strategy(top_n=20)
picks = selector.run_mid_long_term_strategy(top_n=20)
picks = selector.run_comprehensive_strategy(top_n=20)
picks = selector.run_rsrs_strategy(top_n=20)
```

## 核心函数 API

### 指标函数

```python
from selector.indicators import (
    calculate_ma,       # MA 移动平均
    calculate_ema,      # EMA 指数移动平均
    calculate_macd,     # MACD
    calculate_boll,     # 布林带
    calculate_kdj,      # KDJ 随机指标
    calculate_rsi,      # RSI 相对强弱
    calculate_rsrs,     # RSRS 阻力支撑
    # ... 17 个指标
)

# 统一签名
def calc(hist_data: List[Dict]) -> Union[float, Dict, None]:
    """计算技术指标

    Args:
        hist_data: 历史 K 线数据
            [{date, open, high, low, close, volume}, ...]

    Returns:
        单值指标返回 float
        多值指标返回 dict (如 MACD 返回 {DIF, DEA, MACD})
        数据不足返回 None
    """
```

### 评分函数

```python
from selector.scorer import (
    evaluate_short_term,
    evaluate_mid_long_term,
    evaluate_comprehensive,
    evaluate_capital_flow,
    evaluate_valuation,
)

# 智能参数顺序 - 向后兼容
result = evaluate_mid_long_term(
    hist_data,            # 必填
    stock_data=None       # 可选
)
# 也兼容旧调用: evaluate_mid_long_term(stock_data, hist_data)
```

### 策略函数

```python
from selector.strategies import (
    run_short_term_strategy,
    run_mid_long_term_strategy,
    run_comprehensive_strategy,
    run_rsrs_strategy,
)

picks = run_comprehensive_strategy(
    fetcher=selector.fetcher,
    fiscal_fetcher=selector.fiscal_fetcher,
    top_n=20
)
```

## 类型别名 (`_types.py`)

```python
from selector._types import (
    HistData,           # 单根 K 线 Dict
    StockDataList,      # 历史数据 List
    Indicators,         # 指标 Dict
    ScoreResult,        # 评分结果 Dict
    StockPick,          # 选股结果 Dict
    CacheKey,
    CacheValue,
    FiscalRecord,
    FiscalDataList,
    MarketThresholds,
)
```

## DataFetcher 数据获取

```python
from selector.data_fetcher import DataFetcher

fetcher = DataFetcher()  # 默认目录
fetcher = DataFetcher(historical_dir='/custom/path')

# 获取单只股票历史
hist = fetcher.fetch('600519', days=120)
# 返回: [{date, open, high, low, close, volume}, ...]

# 批量获取
all_data = fetcher.fetch_batch(['600519', '000001'], days=60)

# 文件统计
count = fetcher.count_files()  # 1500+
```

## FiscalDataFetcher 财务数据

```python
from selector.fiscal import FiscalDataFetcher

fiscal = FiscalDataFetcher()
fiscal = FiscalDataFetcher(fiscal_dir='/custom/path/fiscal')

# 获取单只股票财务
data = fiscal.fetch('600519')
# 返回: {roe, pe, pb, net_profit_yoy, ...}

# 批量
all_fiscal = fiscal.fetch_batch(['600519', '000001'])
```

## Cache 缓存

```python
from selector.cache import get_indicator_cache

cache = get_indicator_cache()
# 默认 LRU 1000 条, TTL 1 小时

# 使用
cache.set('600519.ma', ma_values)
values = cache.get('600519.ma')

# 清除
cache.clear()
```

## 向后兼容

V2.1 拆分后保留 100% 向后兼容:

```python
# 旧代码 (V2.0) 仍可运行
from stock_selector import (
    StockSelector,
    calculate_ma,
    calculate_macd,
    run_comprehensive_strategy,
    # 全部 19 个公开符号
)
```

`stock_selector.py` 是 79 行的兼容层，从新模块 re-export。

## 异常处理

```python
from selector.exceptions import (
    DataNotFoundError,
    InvalidParamError,
    StrategyError,
)

try:
    picks = selector.run_comprehensive_strategy(top_n=20)
except DataNotFoundError as e:
    print(f"数据缺失: {e}")
except InvalidParamError as e:
    print(f"参数错误: {e}")
```