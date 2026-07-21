# 后端 API

所有 API 走 Tornado HTTP 框架，端口 5001，前缀 `/api/`。

## 通用规范

- **Base URL**: `http://localhost:5001/api/`
- **响应格式**: JSON
- **认证**: 暂无需鉴权 (本地部署)
- **错误码**: 200/400/404/500

## 健康检查

### GET /api/health

```bash
curl http://localhost:5001/api/health
```

**响应**:

```json
{
  "status": "ok",
  "data_files": 1500,
  "fiscal_files": 1500,
  "timestamp": "2026-07-21T13:30:00Z"
}
```

## 选股接口

### POST /api/selection/run

触发一次选股计算。

**请求体**:

```json
{
  "strategy": "comprehensive",  // short_term / mid_long_term / comprehensive / rsrs
  "top_n": 20,
  "filters": {
    "exclude_st": true,
    "min_market_cap": 50  // 亿元
  }
}
```

**响应**:

```json
{
  "status": "ok",
  "strategy": "comprehensive",
  "result": [
    {
      "code": "600519",
      "name": "贵州茅台",
      "score": 88.5,
      "indicators": {
        "ma_trend": 92.0,
        "macd_signal": "golden_cross",
        ...
      },
      "financial": {
        "roe": 28.5,
        "pe": 25.3
      },
      "reasons": [
        "MA 多头排列",
        "MACD 金叉",
        "ROE 持续 > 25%"
      ]
    },
    ...
  ]
}
```

### GET /api/selection/cached

读取最近一次缓存的选股结果。

**查询参数**:

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `strategy` | string | 策略名 (可选, 默认 comprehensive) |

## 股票详情

### GET /api/stock/{code}

获取单只股票的详细信息。

**响应**:

```json
{
  "code": "600519",
  "name": "贵州茅台",
  "industry": "白酒",
  "indicators": {
    "close": 1860.5,
    "ma5": 1850.3,
    "ma20": 1820.6,
    "macd": {"DIF": 12.5, "DEA": 10.2, "MACD": 4.6},
    "kdj": {"K": 65.2, "D": 58.4, "J": 78.8},
    "rsi": 62.5,
    "rsrs_score": 0.85
  },
  "financial": {
    "roe": 28.5,
    "pe": 25.3,
    "pb": 8.6,
    "net_profit_yoy": 15.3
  },
  "history": [
    {"date": "2026-07-21", "close": 1860.5, "volume": 12345678}
  ]
}
```

## 回测接口

### POST /api/backtest/run

运行历史回测。

**请求体**:

```json
{
  "strategy": "mid_long_term",
  "start_date": "2023-07-01",
  "end_date": "2026-06-30",
  "initial_capital": 1000000,
  "top_n": 20,
  "rebalance_freq": "monthly"
}
```

**响应**:

```json
{
  "status": "ok",
  "metrics": {
    "annual_return": 0.243,
    "max_drawdown": -0.185,
    "sharpe_ratio": 1.78,
    "win_rate": 0.672
  },
  "equity_curve": [
    {"date": "2023-07-01", "value": 1000000},
    {"date": "2026-06-30", "value": 1850000}
  ]
}
```

## 新闻接口

### GET /api/news/latest

获取最新财经新闻。

**查询参数**:

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `limit` | int | 返回条数 (默认 50) |
| `category` | string | 分类 (可选) |

**响应**:

```json
{
  "status": "ok",
  "news": [
    {
      "title": "...",
      "summary": "...",
      "url": "...",
      "publish_time": "2026-07-21T13:00:00Z",
      "category": "宏观"
    }
  ]
}
```

## 行业接口

### GET /api/sectors

获取行业分类与涨跌幅。

**响应**:

```json
{
  "status": "ok",
  "sectors": [
    {
      "name": "白酒",
      "change_pct": 2.5,
      "leader": "600519",
      "stock_count": 32
    }
  ]
}
```

## 错误响应

```json
{
  "status": "error",
  "error_code": "INVALID_STRATEGY",
  "message": "策略名无效，应为 short_term / mid_long_term / comprehensive / rsrs"
}
```

常见错误码:

| 错误码 | 含义 |
| --- | --- |
| `INVALID_PARAM` | 参数错误 |
| `INVALID_STRATEGY` | 策略名无效 |
| `DATA_NOT_FOUND` | 数据未找到 |
| `INTERNAL_ERROR` | 服务器内部错误 |

## 调用示例

### JavaScript (fetch)

```javascript
const res = await fetch('http://localhost:5001/api/selection/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    strategy: 'comprehensive',
    top_n: 20
  })
});
const data = await res.json();
console.log(data.result);
```

### Python (requests)

```python
import requests

res = requests.post('http://localhost:5001/api/selection/run', json={
    'strategy': 'comprehensive',
    'top_n': 20
})
print(res.json()['result'][:5])
```

### curl

```bash
curl -X POST http://localhost:5001/api/selection/run \
  -H "Content-Type: application/json" \
  -d '{"strategy": "comprehensive", "top_n": 20}'
```