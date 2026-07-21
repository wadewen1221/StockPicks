# 数据更新

本项目需要定期更新股票历史数据和财务数据。

## 数据来源

| 类型 | 数据源 | 更新频率 |
| --- | --- | --- |
| 行情数据 | akshare / 腾讯 / 新浪 | 日度 |
| 财务数据 | akshare / 东方财富 | 季度 |
| 新闻数据 | akshare / 新浪财经 | 小时级 |

## 自动更新

### 通过定时任务 (推荐)

`backend/scheduler.py` 默认每天 16:00 拉取当日数据。

手动触发:

```bash
cd backend
python -m jobs.data_job --update-all
```

### 通过 Docker

```bash
docker-compose exec backend python -m jobs.data_job --update-all
```

## 手动更新 (单独模块)

### 1. 历史 K 线

```bash
python -m jobs.data_job --kline
```

- 来源: akshare / 腾讯
- 输出: `data/historical/{code}.json`
- 单只股票 ~1-2 秒

### 2. 财务数据

```bash
python -m jobs.data_job --fiscal
```

- 来源: akshare
- 输出: `data/fiscal/{code}.json`
- 单只股票 ~3-5 秒

### 3. 行业分类

```bash
python -m jobs.data_job --sectors
```

- 来源: 申万行业
- 输出: `data/sectors.json`

### 4. 新闻

```bash
python -m jobs.news_job --fetch
```

- 输出: `data/news/{date}.json`

## 数据格式

### 历史 K 线 (data/historical/{code}.json)

```json
[
  {
    "date": "2026-07-21",
    "open": 1850.0,
    "high": 1865.0,
    "low": 1845.0,
    "close": 1860.5,
    "volume": 12345678,
    "turnover": 2290000000.0
  }
]
```

### 财务数据 (data/fiscal/{code}.json)

```json
{
  "code": "600519",
  "name": "贵州茅台",
  "roe": 28.5,
  "net_profit_yoy": 15.3,
  "revenue_yoy": 12.8,
  "debt_ratio": 18.5,
  "pe": 25.3,
  "pb": 8.6,
  "update_time": "2026-07-21"
}
```

## 数据规模

| 类型 | 数量 | 大小 |
| --- | --- | --- |
| 历史 K 线 | 5000+ 只 × 60 个月 | ~1.5 GB |
| 财务数据 | 5000+ 只 × 8 季度 | ~50 MB |
| 新闻 | 每天 ~500 条 | ~10 MB/天 |

## ⚠️ 注意事项

!!! warning "不要提交数据到 Git"

    历史数据文件 1.5 GB 不应纳入版本控制。已在 `.gitignore` 排除:

    ```gitignore
    data/historical/*
    !data/historical/.gitkeep
    data/fiscal/*
    !data/fiscal/.gitkeep
    ```

!!! tip "Windows 软链接"

    推荐用 Windows junction 指向共享数据目录:

    ```powershell
    mklink /J D:\stock-picks-v2\data D:\stock-picks\data
    ```

!!! info "首次部署"

    新部署需运行 2-3 小时完整下载一次数据，之后每日增量更新。

## 数据验证

```python
# 验证数据完整性
python -c "
from selector.data_fetcher import DataFetcher
fetcher = DataFetcher()
print(f'历史文件: {fetcher.count_files()}')
print(f'财务文件: {fetcher.fiscal_count_files()}')
# 应输出类似: 历史文件: 5500+
"
```