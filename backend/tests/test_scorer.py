"""
打分函数 - 单元测试
"""
import pytest
from selector import (
    calculate_mid_long_score_v2,
    calculate_short_term_aggressive,
    calculate_short_term_conservative,
    evaluate_buy_signal,
    evaluate_mid_long_term,
    evaluate_short_term,
)


class TestEvaluateBuySignal:
    def test_returns_expected_keys(self, sample_hist_data_100):
        result = evaluate_buy_signal(sample_hist_data_100, {'代码': 'TEST'})
        assert 'buy_score' in result
        assert 'sell_score' in result
        assert 'reasons' in result
        assert 'kdj_rsi_cci' in result
        assert 'rsrs' in result

    def test_scores_non_negative(self, sample_hist_data_100):
        result = evaluate_buy_signal(sample_hist_data_100, {'代码': 'TEST'})
        assert result['buy_score'] >= 0
        assert result['sell_score'] >= 0


class TestEvaluateMidLongTerm:
    def test_returns_score_and_details(self, sample_hist_data_100):
        score, details = evaluate_mid_long_term({'代码': 'TEST'}, sample_hist_data_100)
        assert isinstance(score, (int, float))
        assert 'indicators' in details
        assert 'reasons' in details

    def test_short_data_returns_zero(self, short_hist_data):
        score, _ = evaluate_mid_long_term({'代码': 'TEST'}, short_hist_data)
        assert score == 0


class TestEvaluateShortTerm:
    def test_returns_score_and_details(self, sample_hist_data_100):
        score, details = evaluate_short_term(
            {'代码': 'TEST', 'turnover': 10.0},
            sample_hist_data_100
        )
        assert isinstance(score, (int, float))
        assert 'indicators' in details

    def test_very_short_returns_zero(self):
        data = [{'close': 10, 'volume': 1000, 'open': 10, 'high': 11, 'low': 9, 'date': '2025-01-01'}] * 3
        score, _ = evaluate_short_term({'代码': 'TEST'}, data)
        assert score == 0


class TestCalculateMidLongScoreV2:
    def test_insufficient_data_returns_zero(self, sample_hist_data_100):
        """不足 120 天 -> 0"""
        score, details = calculate_mid_long_score_v2(sample_hist_data_100, {'代码': 'TEST'})
        assert score == 0
        assert details == {}

    def test_long_data_returns_positive(self, sample_hist_data_long):
        """1500 天数据 -> 应有评分"""
        score, details = calculate_mid_long_score_v2(sample_hist_data_long, {'代码': 'TEST'})
        assert score > 0, f"1500 天数据应评分 > 0, 实际 {score}"
        assert 'indicators' in details
        assert 'reasons' in details
        assert 'details' in details

    def test_max_score_below_100(self, sample_hist_data_long):
        """满分模型是 95 分"""
        score, _ = calculate_mid_long_score_v2(sample_hist_data_long, {'代码': 'TEST'})
        assert score <= 100

    def test_real_data_works(self, real_stock_000001_data):
        """真实 000001 数据"""
        if len(real_stock_000001_data) < 120:
            pytest.skip("数据不足 120 天")

        score, details = calculate_mid_long_score_v2(real_stock_000001_data, {'代码': '000001'})
        assert score > 0
        assert 'thresholds_used' in details['details']


class TestCalculateShortTermAggressive:
    def test_returns_tuple(self, sample_hist_data_long):
        score, details = calculate_short_term_aggressive(sample_hist_data_long, {'代码': 'TEST'})
        assert isinstance(score, (int, float))
        assert 'type' in details
        assert details['type'] == '激进型'

    def test_insufficient_data(self, short_hist_data):
        """不足 60 天 -> 0"""
        score, _ = calculate_short_term_aggressive(short_hist_data, {'代码': 'TEST'})
        assert score == 0


class TestCalculateShortTermConservative:
    def test_returns_tuple(self, sample_hist_data_long):
        score, details = calculate_short_term_conservative(sample_hist_data_long, {'代码': 'TEST'})
        assert isinstance(score, (int, float))
        assert 'type' in details
        assert details['type'] == '稳健型'

    def test_insufficient_data(self, short_hist_data):
        """不足 60 天 -> 0"""
        score, _ = calculate_short_term_conservative(short_hist_data, {'代码': 'TEST'})
        assert score == 0