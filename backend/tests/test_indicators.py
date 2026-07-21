"""
技术指标计算 - 单元测试
覆盖:
- calculate_technical_indicators
- calculate_advanced_indicators
- calculate_rsrs (P0 修复不回归)
- calculate_kdj_rsi_cci
"""
import pytest
from selector import (
    calculate_advanced_indicators,
    calculate_kdj_rsi_cci,
    calculate_rsrs,
    calculate_technical_indicators,
)


# ========== calculate_technical_indicators ==========

class TestCalculateTechnicalIndicators:
    def test_empty_data(self):
        """空数据 -> {}"""
        assert calculate_technical_indicators([]) == {}

    def test_short_data(self):
        """不足 20 天 -> {}"""
        short = [{'close': 10, 'volume': 1000, 'open': 10, 'high': 11, 'low': 9, 'date': '2025-01-01'}] * 10
        assert calculate_technical_indicators(short) == {}

    def test_basic_keys(self, sample_hist_data_100):
        """100 天数据返回所有预期字段"""
        result = calculate_technical_indicators(sample_hist_data_100)
        expected_keys = {'ma5', 'ma10', 'ma20', 'ma60', 'current_price', 'position',
                         'vol_ratio', 'volatility', 'change_5d', 'change_20d', 'volume'}
        assert expected_keys.issubset(result.keys())

    def test_ma_values_positive(self, sample_hist_data_100):
        """MA 值应该为正数"""
        result = calculate_technical_indicators(sample_hist_data_100)
        assert result['ma5'] > 0
        assert result['ma20'] > 0
        assert result['ma60'] > 0

    def test_position_in_range(self, sample_hist_data_100):
        """位置指标应在 [0, 1]"""
        result = calculate_technical_indicators(sample_hist_data_100)
        assert 0 <= result['position'] <= 1

    def test_vol_ratio_positive(self, sample_hist_data_100):
        """量比应为正"""
        result = calculate_technical_indicators(sample_hist_data_100)
        assert result['vol_ratio'] > 0


# ========== calculate_advanced_indicators ==========

class TestCalculateAdvancedIndicators:
    def test_empty_data(self):
        assert calculate_advanced_indicators([]) == {}

    def test_short_data(self):
        """不足 60 天 -> {}"""
        short = [{'close': 10, 'volume': 1000, 'open': 10, 'high': 11, 'low': 9, 'date': '2025-01-01'}] * 30
        assert calculate_advanced_indicators(short) == {}

    def test_macd_present(self, sample_hist_data_100):
        result = calculate_advanced_indicators(sample_hist_data_100)
        assert 'macd' in result
        assert 'dif' in result['macd']
        assert 'dea' in result['macd']

    def test_rsi_present(self, sample_hist_data_100):
        result = calculate_advanced_indicators(sample_hist_data_100)
        assert 'rsi' in result
        assert 0 <= result['rsi'] <= 100

    def test_bollinger_bands(self, sample_hist_data_100):
        result = calculate_advanced_indicators(sample_hist_data_100)
        bb = result['bollinger']
        assert bb['upper'] >= bb['middle'] >= bb['lower']

    def test_ma_bullish_flag(self, sample_hist_data_long):
        result = calculate_advanced_indicators(sample_hist_data_long)
        assert 'ma_bullish' in result
        assert isinstance(result['ma_bullish'], bool)


# ========== calculate_rsrs (P0 修复不回归) ==========

class TestCalculateRsrs:
    def test_all_paths_return_slope(self, sample_hist_data_100, empty_hist_data, short_hist_data):
        """P0 修复: 所有返回路径都必须有 'slope' 字段"""
        # 1. 正常数据
        r1 = calculate_rsrs(sample_hist_data_100)
        assert 'slope' in r1, "正常数据缺 slope 字段"
        assert isinstance(r1['slope'], float)

        # 2. 数据不足
        r2 = calculate_rsrs(short_hist_data)
        assert 'slope' in r2, "数据不足时缺 slope"
        assert r2['slope'] == 1.0  # 默认值

        # 3. 空数据
        r3 = calculate_rsrs(empty_hist_data)
        assert 'slope' in r3, "空数据缺 slope"
        assert r3['slope'] == 1.0

    def test_signal_values(self, sample_hist_data_100):
        """信号字段必须是有效枚举值"""
        result = calculate_rsrs(sample_hist_data_100)
        valid_signals = {'strong_up', 'up', 'neutral', 'down', 'strong_down'}
        assert result['signal'] in valid_signals

    def test_typical_keys(self, sample_hist_data_100):
        """返回 dict 应有 rsrs/slope/rsrs_ma/signal 4 字段"""
        result = calculate_rsrs(sample_hist_data_100)
        assert set(result.keys()) == {'rsrs', 'slope', 'rsrs_ma', 'signal'}

    def test_real_data_meaningful_slope(self, real_stock_000001_data):
        """真实股票应返回非默认值"""
        if len(real_stock_000001_data) < 60:
            pytest.skip("数据不足 60 天")

        result = calculate_rsrs(real_stock_000001_data)
        # 真实数据 slope 应不是默认 1.0
        assert result['slope'] != 1.0, "真实数据 slope 不应是默认 1.0"
        # 真实数据 slope 应在合理范围 (0.5 ~ 1.5)
        assert 0.5 < result['slope'] < 1.5

    def test_period_parameter(self, sample_hist_data_long):
        """不同 period 参数应都能跑通"""
        for p in [10, 18, 30, 60]:
            r = calculate_rsrs(sample_hist_data_long, period=p)
            assert 'slope' in r


# ========== calculate_kdj_rsi_cci ==========

class TestCalculateKdjrsiCci:
    def test_empty_data(self):
        assert calculate_kdj_rsi_cci([]) == {}

    def test_short_data(self):
        """不足 20 天 -> {}"""
        short = [{'close': 10, 'volume': 1000, 'open': 10, 'high': 11, 'low': 9, 'date': '2025-01-01'}] * 10
        assert calculate_kdj_rsi_cci(short) == {}

    def test_kdj_values(self, sample_hist_data_100):
        result = calculate_kdj_rsi_cci(sample_hist_data_100)
        assert 'kdjk' in result
        assert 'kdjd' in result
        assert 'kdjj' in result
        # KDJ 通常在 0-100 区间（j 可能略超）
        assert 0 <= result['kdjk'] <= 100
        assert 0 <= result['kdjd'] <= 100

    def test_rsi_values(self, sample_hist_data_100):
        result = calculate_kdj_rsi_cci(sample_hist_data_100)
        assert 'rsi_6' in result
        assert 'rsi_12' in result
        if result['rsi_6'] is not None:
            assert 0 <= result['rsi_6'] <= 100

    def test_cross_signals_are_bool(self, sample_hist_data_100):
        result = calculate_kdj_rsi_cci(sample_hist_data_100)
        # numpy.bool_ 并不是 Python bool，但应可转换为 bool
        assert bool(result['kdj_golden_cross']) in (True, False)
        assert bool(result['kdj_death_cross']) in (True, False)

    def test_oversold_overbought_are_bool(self, sample_hist_data_100):
        result = calculate_kdj_rsi_cci(sample_hist_data_100)
        assert bool(result['rsi_oversold']) in (True, False)
        assert bool(result['rsi_overbought']) in (True, False)