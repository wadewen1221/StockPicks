# RSRS 阻力支撑相对位置

> 阻力支撑相对位置 (Resistance Support Relative Strength) — 改进版右偏 RSRS 指标

## 指标原理

传统 RSRS 通过最高价/最低价的回归斜率衡量阻力支撑强度。本项目使用 **改进版右偏 RSRS** 算法:

```
1. 取最近 N 日 (默认 18) 的 (low, high) 数据
2. 对 (low, high) 做 OLS 线性回归
3. 计算斜率 (beta) 和决定系数 (R²)
4. RSRS_score = beta × R²  (右偏修正)
5. 买入信号: RSRS_score > 阈值 (默认 0.7)
```

## 公式推导

```
high_i = alpha + beta × low_i + epsilon
```

其中:

- **beta**: 斜率，反映最低价 → 最高价的"扩张能力"
- **R²**: 拟合优度，反映价格区间规律的稳定性
- **右偏修正**: `RSRS_score = beta × R²`，避免高 beta 低 R² 的伪信号

## 阈值与信号

| RSRS_score | 含义 | 操作建议 |
| --- | --- | --- |
| > 0.9 | 强买入 | 买入 |
| 0.7 - 0.9 | 买入 | 可买入 |
| 0.5 - 0.7 | 中性 | 观望 |
| < 0.5 | 卖出 | 卖出 / 观望 |

## 代码实现

```python
from selector.indicators import calculate_rsrs

# 计算单只股票 RSRS 分数
score = calculate_rsrs(
    hist_data,           # 历史数据 [{date, high, low, ...}, ...]
    n_days=18,           # 回归窗口 (默认 18)
    threshold=0.7        # 买入阈值 (默认 0.7)
)
# 返回: float (0.0 - 1.0+)
```

## 策略集成

```python
from selector import StockSelector

selector = StockSelector()
picks = selector.run_rsrs_strategy(top_n=20)

for p in picks:
    print(f"{p['code']} {p['name']} - RSRS: {p['rsrs_score']:.3f}")
```

## 回测表现 (近 3 年)

| 指标 | 数值 |
| --- | --- |
| 年化收益 | +19.8% |
| 最大回撤 | -11.5% |
| 胜率 | 61.3% |
| 夏普比率 | 1.56 |

## 参数调优

修改 `config.py`:

```python
RSRS_PARAMS = {
    "n_days": 18,        # 回归窗口
    "threshold": 0.7,    # 买入阈值
    "r2_weight": 1.0,    # R² 权重 (右偏修正系数)
}
```

!!! tip "调参建议"

    - 牛市: 阈值可降低到 0.6
    - 熊市: 阈值可提高到 0.85
    - 震荡市: 默认 0.7 即可

## 🐛 已修复的 Bug (V2.1)

2026-07-22 发现: 重构 scorer.py 时 RSRS 阈值判断误用 `>` 应为 `>=`，已修复并加测试保护 (`test_indicators.py::test_rsrs_threshold`)。