"""
Pytest 共享 fixtures + 路径配置

重要：把 backend/ 加入 sys.path，让 pytest 能 `import selector` / `import config`。
"""
import os
import sys
from pathlib import Path

import pytest

# 把 backend/ 加到 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def sample_hist_data_100():
    """100 天合成历史数据 - 用于快速测试"""
    import random
    random.seed(42)
    price = 10.0
    data = []
    for i in range(100):
        price *= 1 + random.uniform(-0.02, 0.025)
        data.append({
            'date': f'2025-{(i // 30) + 1:02d}-{(i % 30) + 1:02d}',
            'open': price,
            'high': price * 1.01,
            'low': price * 0.99,
            'close': price,
            'volume': 1_000_000,
            'change_pct': random.uniform(-3, 3),
        })
    return data


@pytest.fixture
def sample_hist_data_long():
    """1500 天合成历史数据 - 用于中长线策略"""
    import random
    random.seed(123)
    price = 10.0
    data = []
    for i in range(1500):
        price *= 1 + random.uniform(-0.025, 0.03)
        data.append({
            'date': f'2022-{(i // 30) % 12 + 1:02d}-{(i % 30) + 1:02d}',
            'open': price,
            'high': price * 1.015,
            'low': price * 0.985,
            'close': price,
            'volume': 1_000_000 + i * 1000,
            'change_pct': random.uniform(-5, 5),
        })
    return data


@pytest.fixture
def empty_hist_data():
    """空数据"""
    return []


@pytest.fixture
def short_hist_data():
    """5 天数据 - 数据不足场景"""
    import random
    random.seed(7)
    price = 10.0
    data = []
    for i in range(5):
        price *= 1 + random.uniform(-0.02, 0.025)
        data.append({
            'date': f'2025-01-{i + 1:02d}',
            'open': price,
            'high': price * 1.01,
            'low': price * 0.99,
            'close': price,
            'volume': 1_000_000,
        })
    return data


@pytest.fixture
def real_stock_000001_data():
    """真实股票 000001 历史数据（如果存在）"""
    import json
    from config import get_historical_dir

    data_dir = str(get_historical_dir())
    fp = os.path.join(data_dir, '000001.json')

    if not os.path.exists(fp):
        pytest.skip("000001.json 不存在，跳过真实数据测试")

    with open(fp, 'r', encoding='utf-8') as f:
        content = json.load(f)
    return content.get('data', [])


@pytest.fixture
def monkey_patch_data_dir(tmp_path, monkeypatch):
    """将数据目录重定向到 tmp，避免测试污染真实数据"""
    historical = tmp_path / "historical"
    historical.mkdir()
    fiscal = tmp_path / "fiscal"
    fiscal.mkdir()

    monkeypatch.setenv("STOCK_PICKS_HISTORICAL", str(historical))
    monkeypatch.setenv("STOCK_PICKS_FISCAL", str(fiscal))
    return tmp_path