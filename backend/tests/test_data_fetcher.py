"""
DataFetcher - 数据获取器单元测试（使用临时目录避免污染真实数据）
"""
import json
import os
from pathlib import Path

import pytest

from selector import DataFetcher
from config import get_historical_dir


@pytest.fixture
def fake_stock_files(tmp_path):
    """创建临时历史数据目录 + 2 个测试股票文件"""
    hist_dir = tmp_path / "historical"
    hist_dir.mkdir()

    # 股票 A: 100 天上升趋势
    price_a = 10.0
    data_a = []
    for i in range(100):
        price_a *= 1.005  # 0.5% 每日增长
        data_a.append({
            'date': f'2025-{(i//30)+1:02d}-{(i%30)+1:02d}',
            'open': price_a * 0.99,
            'high': price_a * 1.02,
            'low': price_a * 0.98,
            'close': price_a,
            'volume': 1_000_000 + i * 1000,
            'change_pct': 0.5,
        })

    # 股票 B: 100 天下降趋势
    price_b = 50.0
    data_b = []
    for i in range(100):
        price_b *= 0.995
        data_b.append({
            'date': f'2025-{(i//30)+1:02d}-{(i%30)+1:02d}',
            'open': price_b * 1.01,
            'high': price_b * 1.02,
            'low': price_b * 0.98,
            'close': price_b,
            'volume': 5_000_000,
            'change_pct': -0.5,
        })

    # 写入文件
    with open(hist_dir / "000001.json", 'w', encoding='utf-8') as f:
        json.dump({'code': '000001', 'name': '股票A', 'data': data_a}, f, ensure_ascii=False)

    with open(hist_dir / "600519.json", 'w', encoding='utf-8') as f:
        json.dump({'code': '600519', 'name': '股票B', 'data': data_b}, f, ensure_ascii=False)

    return hist_dir


class TestGetStocksFromHistorical:
    def test_returns_list(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        # 强制重新加载（绕过 5min 缓存）
        fetcher._stock_list_cache = None
        stocks = fetcher.get_stocks_from_historical(preload_data=False)
        assert isinstance(stocks, list)
        assert len(stocks) == 2

    def test_stock_has_required_fields(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        fetcher._stock_list_cache = None
        stocks = fetcher.get_stocks_from_historical(preload_data=False)
        for s in stocks:
            assert '代码' in s
            assert '名称' in s
            assert '最新价' in s
            assert '涨跌幅' in s

    def test_caching_works(self, fake_stock_files):
        """两次调用应返回同一对象（5min 缓存）"""
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        fetcher._stock_list_cache = None
        s1 = fetcher.get_stocks_from_historical(preload_data=False)
        s2 = fetcher.get_stocks_from_historical(preload_data=False)
        assert s1 is s2


class TestGetStockHistorical:
    def test_returns_data(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        data = fetcher.get_stock_historical('000001', max_days=200)
        assert data is not None
        assert len(data) == 100

    def test_returns_none_for_nonexistent(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        data = fetcher.get_stock_historical('999999', max_days=200)
        assert data is None

    def test_max_days_truncates(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        data = fetcher.get_stock_historical('000001', max_days=30)
        assert len(data) == 30


class TestValidateStockData:
    def test_valid_stock(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        is_valid, errors = fetcher.validate_stock_data('000001')
        assert is_valid
        assert errors == []

    def test_missing_file(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        is_valid, errors = fetcher.validate_stock_data('999999')
        assert not is_valid
        assert '不存在' in errors[0]


class TestGetDataQualityReport:
    def test_report_structure(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        fetcher._stock_list_cache = None
        report = fetcher.get_data_quality_report(sample_size=2)
        assert 'total_checked' in report
        assert 'issues' in report
        assert 'quality_score' in report
        assert report['total_checked'] == 2


class TestStubFunctionsReturnEmpty:
    """占位接口应返回空列表，不抛异常"""

    def test_get_hot_sectors(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        assert fetcher.get_hot_sectors() == []

    def test_get_limit_up_stocks(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        assert fetcher.get_limit_up_stocks() == []

    def test_get_hot_search_stocks(self, fake_stock_files):
        fetcher = DataFetcher(historical_dir=str(fake_stock_files))
        assert fetcher.get_hot_search_stocks() == []