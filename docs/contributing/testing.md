# 测试指南

项目使用 pytest 单元测试 + mypy 静态类型检查双保险。

## 测试统计

| 指标 | 数值 |
| --- | --- |
| 测试文件 | 8 个 |
| 测试用例 | 87 个 |
| 覆盖率 (selector) | ~85% |
| 运行时间 | ~6 秒 |
| 测试框架 | pytest 7.4+ |
| 类型检查 | mypy |

## 运行测试

```bash
cd backend

# 全部测试
python -m pytest tests/ -v

# 单个文件
python -m pytest tests/test_indicators.py -v

# 单个用例
python -m pytest tests/test_indicators.py::test_calculate_ma -v

# 显示覆盖率
python -m pytest tests/ --cov=selector --cov=config --cov-report=term-missing

# 失败时立即停止
python -m pytest tests/ -x

# 看详细 traceback
python -m pytest tests/ --tb=long
```

## 测试目录

```
backend/tests/
├── __init__.py
├── conftest.py              # 共享 fixture
├── test_cache.py            # 8 用例 - LRU 缓存
├── test_config.py           # 12 用例 - 配置加载
├── test_data_fetcher.py     # 12 用例 - 历史数据获取
├── test_fiscal.py           # 8 用例 - 财务数据
├── test_indicators.py       # 23 用例 - 17 项指标
├── test_scorer.py           # 14 用例 - 5 套打分函数
└── test_split_compat.py     # 10 用例 - 拆分后向后兼容
```

## 测试结构

### 单元测试原则

1. **独立**: 不依赖外部资源 (网络、文件)
2. **快速**: 单个测试 < 100ms
3. **可重复**: 同样输入同样输出
4. **可读**: 测试名 = 测试目的

### 共享 fixture (conftest.py)

```python
import pytest

@pytest.fixture
def sample_hist_data_100():
    """100 日模拟历史数据"""
    return [
        {'date': f'2024-{(i % 30) + 1:02d}-{i % 24 + 1:02d}',
         'open': 100 + i * 0.5,
         'high': 105 + i * 0.5,
         'low': 95 + i * 0.5,
         'close': 102 + i * 0.5,
         'volume': 1000000 + i * 1000}
        for i in range(100)
    ]

@pytest.fixture
def short_hist_data():
    """5 日数据 (短周期测试)"""
    return [
        {'date': f'2024-01-0{i+1}',
         'open': 100 + i, 'high': 105 + i,
         'low': 95 + i, 'close': 102 + i,
         'volume': 1000000}
        for i in range(5)
    ]
```

## 添加测试

### 测试指标函数

```python
def test_calculate_boll_width():
    """布林带宽度"""
    # Arrange
    hist_data = [
        {'close': 100 + i * 0.5}
        for i in range(30)
    ]

    # Act
    width = calculate_boll_width(hist_data)

    # Assert
    assert width is not None
    assert 0 < width < 1
```

### 测试评分函数

```python
def test_evaluate_mid_long_term_returns_valid_score(sample_hist_data_100):
    """中长线评分返回合法分数"""
    stock_data = {'代码': 'TEST001', '名称': '测试股'}

    score_result = evaluate_mid_long_term(stock_data, sample_hist_data_100)

    assert 'total_score' in score_result
    assert 0 <= score_result['total_score'] <= 100
    assert 'indicators' in score_result
```

### 测试向后兼容

```python
def test_split_compat_reexports():
    """V2.1 拆分后公开 API 完全兼容"""
    from stock_selector import (
        StockSelector, calculate_ma, calculate_macd,
        run_comprehensive_strategy
    )

    selector = StockSelector()
    assert hasattr(selector, 'run_comprehensive_strategy')
```

## CI 集成

GitHub Actions 在 PR 时自动跑测试:

```yaml
# .github/workflows/ci.yml
- name: Run pytest
  run: |
    cd backend
    python -m pytest tests/ -v --tb=short
```

## mypy 检查

```bash
cd backend
mypy selector/ config.py --ignore-missing-imports --no-strict-optional
```

期望输出:

```
Success: no issues found in 9 source files
```

### mypy 配置

项目根 `pyproject.toml` (待补):

```toml
[tool.mypy]
python_version = "3.12"
ignore_missing_imports = true
no_strict_optional = true
show_error_codes = true
files = ["selector", "config.py"]
```

## 覆盖率报告

```bash
cd backend
python -m pytest tests/ --cov=selector --cov=config --cov-report=html
# 输出 htmlcov/index.html 可视化报告
```

### 当前覆盖率

| 模块 | 覆盖率 |
| --- | --- |
| `selector/__init__.py` | 100% |
| `selector/cache.py` | 100% |
| `selector/indicators.py` | ~92% |
| `selector/scorer.py` | ~85% |
| `selector/strategies.py` | ~70% |
| `selector/data_fetcher.py` | ~60% (IO 难测) |
| `selector/fiscal.py` | ~65% (IO 难测) |

## 调试失败的测试

```bash
# 1. 看具体失败原因
pytest tests/test_indicators.py::test_x -v --tb=long

# 2. 进入 pdb 调试
pytest tests/test_indicators.py::test_x -v --pdb

# 3. 看打印输出
pytest tests/test_indicators.py::test_x -v -s

# 4. 只跑失败的用例
pytest tests/ --lf
```

## ⚠️ 注意事项

!!! warning "不要在测试中访问真实数据"

    测试用 `tmp_path` fixture 或纯 mock 数据，不要读 `D:/stock-picks/data`。

!!! tip "避免全局状态污染"

    用 `monkeypatch.setattr` 修改变量，而不是直接改模块。

!!! info "CI 环境变量"

    CI 中设置 `STOCK_PICKS_DATA=/tmp/stock-picks-test-data` 避免触碰真实数据。