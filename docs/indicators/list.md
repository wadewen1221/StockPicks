# 技术指标清单

项目内置 **17 项技术指标**，覆盖趋势 / 动量 / 波动 / 成交量 / 形态 5 大类。

## 分类速查

| 类别 | 指标 |
| --- | --- |
| **趋势类** | MA / EMA / MACD / BOLL |
| **动量类** | KDJ / RSI / WR / CCI |
| **成交量类** | VOL / 量比 / 换手率 / OBV |
| **形态类** | 顶背离 / 底背离 / 金叉 / 死叉 |
| **复合类** | RSRS 阻力支撑 |

## 17 项指标详解

### 1. MA - 移动平均线

```python
calculate_ma(close_prices, periods=[5, 10, 20, 60])
```

- **算法**: N 日算术平均
- **信号**: 多头排列 (MA5 > MA10 > MA20 > MA60)

### 2. EMA - 指数移动平均

```python
calculate_ema(close_prices, periods=[12, 26])
```

- **算法**: 加权平均，近期权重更高
- **信号**: EMA12 上穿 EMA26

### 3. MACD - 指数平滑异同移动平均

```python
calculate_macd(close_prices)
# 返回: {'DIF': ..., 'DEA': ..., 'MACD': ...}
```

- **DIF**: EMA12 - EMA26
- **DEA**: DIF 的 9 日 EMA
- **MACD**: (DIF - DEA) × 2

### 4. BOLL - 布林带

```python
calculate_bollinger(close_prices, period=20, std_dev=2)
# 返回: {'upper': ..., 'middle': ..., 'lower': ...}
```

- **中轨**: 20 日 MA
- **上下轨**: 中轨 ± 2 倍标准差

### 5. KDJ - 随机指标

```python
calculate_kdj(high, low, close)
# 返回: {'K': ..., 'D': ..., 'J': ...}
```

- **K 值**: 快速确认线
- **D 值**: 慢速确认线
- **J 值**: 方向敏感线
- **金叉**: K 上穿 D (买入信号)

### 6. RSI - 相对强弱指数

```python
calculate_rsi(close_prices, periods=[6, 12, 24])
```

- **算法**: N 日内上涨幅度 / 全部波幅
- **区间**: 0-100，> 70 超买，< 30 超卖

### 7-17. 其他指标

详见源码 `backend/selector/indicators.py`:

- `WR` - 威廉指标
- `CCI` - 顺势指标
- `VOL` - 成交量
- `量比` - 当日量比
- `换手率`
- `OBV` - 能量潮
- `顶背离` / `底背离`
- `金叉` / `死叉`
- `RSRS` - 阻力支撑相对位置 (详见 [RSRS](rsrs.md))

## 指标缓存

为提升性能，指标计算结果按 `(股票代码, 指标名)` 缓存:

```python
from selector.cache import get_indicator_cache

cache = get_indicator_cache()
# 默认 LRU 1000 条，TTL 1 小时
```

## 调用示例

```python
from selector.indicators import (
    calculate_ma, calculate_macd, calculate_kdj, calculate_rsi
)

# 单只股票 60 日数据
hist_data = [...]  # [{'date': '...', 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}]
close = [d['close'] for d in hist_data]

ma = calculate_ma(close)
macd = calculate_macd(close)
rsi = calculate_rsi(close)
```