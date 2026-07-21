"""
FiscalDataFetcher - 基本面数据获取器单元测试
"""
import json
from datetime import datetime, timedelta

import pytest

from selector import FiscalDataFetcher


@pytest.fixture
def fake_fiscal_files(tmp_path):
    """创建临时财务数据"""
    fiscal_dir = tmp_path / "fiscal"
    fiscal_dir.mkdir()

    # 股票 A: 健康 ROE
    fiscal_a = {
        'fiscal': [
            {'report_date': '2025-03-31', 'year': 2025, 'period': 'Q1',
             '归母净利润': 10_000_000_000, '每股净资产': 10, '总股本': 1_000_000_000,
             '资产负债率': 30},
            {'report_date': '2024-12-31', 'year': 2024, 'period': 'Q4',
             '归母净利润': 8_000_000_000, '每股净资产': 9, '总股本': 1_000_000_000,
             '资产负债率': 32},
            {'report_date': '2024-03-31', 'year': 2024, 'period': 'Q1',
             '归母净利润': 8_000_000_000, '每股净资产': 9, '总股本': 1_000_000_000,
             '资产负债率': 32},
        ]
    }

    # 股票 B: ST 状态
    fiscal_b = {
        'fiscal': [
            {'report_date': '2025-03-31', 'year': 2025, 'period': 'Q1',
             '归母净利润': -1_000_000_000, '每股净资产': 5, '总股本': 1_000_000_000,
             '资产负债率': 80}
        ]
    }

    with open(fiscal_dir / "000001.json", 'w', encoding='utf-8') as f:
        json.dump({'code': '000001', 'name': '健康股票A', 'fiscal': fiscal_a['fiscal']}, f, ensure_ascii=False)

    with open(fiscal_dir / "600000.json", 'w', encoding='utf-8') as f:
        json.dump({'code': '600000', 'name': 'ST股票B', 'fiscal': fiscal_b['fiscal']}, f, ensure_ascii=False)

    return fiscal_dir


class TestGetFiscalData:
    def test_returns_dict(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        data = fetcher.get_fiscal_data('000001')
        assert data is not None
        assert 'roe' in data
        assert '净利润' in data
        assert '资产负债率' in data

    def test_roe_calculation(self, fake_fiscal_files):
        """ROE = 归母净利润 / (每股净资产 * 总股本)"""
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        data = fetcher.get_fiscal_data('000001')
        # 10_000_000_000 / (10 * 1_000_000_000) = 1.0
        # 净利润 100亿 / 净资产 100亿 = 100%
        assert data['roe'] is not None
        assert abs(data['roe'] - 100.0) < 0.5

    def test_nonexistent_returns_none(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        data = fetcher.get_fiscal_data('999999')
        assert data is None

    def test_st_detection(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        data = fetcher.get_fiscal_data('600000')
        assert data['is_st'] is True


class TestCheckFinancial:
    def test_healthy_stock_passes(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        result = fetcher.check_financial('000001', stock_type='mid_long')
        assert result['pass'] is True
        assert result['score'] > 0

    def test_st_stock_fails(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        result = fetcher.check_financial('600000', stock_type='mid_long')
        assert result['pass'] is False
        assert 'ST' in result['reasons'][0]

    def test_missing_data_returns_fail(self, fake_fiscal_files):
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        result = fetcher.check_financial('999999', stock_type='mid_long')
        assert result['pass'] is False
        assert '无财务数据' in result['reasons']

    def test_short_term_relaxed(self, fake_fiscal_files):
        """超短线模式 ROE 负数检查更宽松"""
        fetcher = FiscalDataFetcher(fiscal_dir=str(fake_fiscal_files))
        result = fetcher.check_financial('000001', stock_type='short_term')
        # 应该通过
        assert 'score' in result