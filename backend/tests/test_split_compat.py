"""
向后兼容性测试 - 确保所有旧 import 路径仍可用
"""
import pytest


class TestOldApiFromStockSelector:
    """从 stock_selector 顶层模块导入（兼容层）"""

    def test_imports_all_classes(self):
        from stock_selector import LRUCache, DataFetcher, FiscalDataFetcher, StockSelector
        assert LRUCache is not None
        assert DataFetcher is not None
        assert FiscalDataFetcher is not None
        assert StockSelector is not None

    def test_imports_all_indicator_functions(self):
        from stock_selector import (
            calculate_technical_indicators,
            calculate_advanced_indicators,
            calculate_rsrs,
            calculate_kdj_rsi_cci,
        )
        assert callable(calculate_technical_indicators)
        assert callable(calculate_advanced_indicators)
        assert callable(calculate_rsrs)
        assert callable(calculate_kdj_rsi_cci)

    def test_imports_all_scorer_functions(self):
        from stock_selector import (
            evaluate_buy_signal,
            evaluate_mid_long_term,
            evaluate_short_term,
            calculate_mid_long_score_v2,
            calculate_short_term_aggressive,
            calculate_short_term_conservative,
        )
        for fn in [evaluate_buy_signal, evaluate_mid_long_term, evaluate_short_term,
                   calculate_mid_long_score_v2, calculate_short_term_aggressive,
                   calculate_short_term_conservative]:
            assert callable(fn)

    def test_imports_all_strategy_functions(self):
        from stock_selector import (
            select_mid_long_term_stocks,
            select_short_term_stocks,
            select_with_rsrs_kdj_cci,
        )
        for fn in [select_mid_long_term_stocks, select_short_term_stocks, select_with_rsrs_kdj_cci]:
            assert callable(fn)

    def test_old_and_new_are_same_object(self):
        """旧 API 与新 API 必须指向同一对象（避免双份定义）"""
        from stock_selector import LRUCache as Old, StockSelector as OldSS
        from selector import LRUCache as New, StockSelector as NewSS
        assert Old is New, "LRUCache 应该是同一个类"
        assert OldSS is NewSS, "StockSelector 应该是同一个类"


class TestSelectorPackageStructure:
    """selector/ 包内模块结构验证"""

    def test_submodules_exist(self):
        from selector import cache, data_fetcher, fiscal, indicators, scorer, strategies
        assert cache.__file__.endswith('cache.py')
        assert data_fetcher.__file__.endswith('data_fetcher.py')
        assert fiscal.__file__.endswith('fiscal.py')
        assert indicators.__file__.endswith('indicators.py')
        assert scorer.__file__.endswith('scorer.py')
        assert strategies.__file__.endswith('strategies.py')

    def test_no_circular_imports(self):
        """不应有循环导入"""
        import importlib
        import sys
        for mod_name in ['selector.cache', 'selector.data_fetcher', 'selector.fiscal',
                         'selector.indicators', 'selector.scorer', 'selector.strategies',
                         'selector']:
            mod = importlib.import_module(mod_name)
            assert mod is not None


class TestStockSelectorFacade:
    """StockSelector 门面类的实例方法代理"""

    def test_facade_instantiation(self):
        from stock_selector import StockSelector
        s = StockSelector()
        assert s.fetcher is not None
        assert s.fiscal_fetcher is not None

    def test_facade_method_proxy_indicators(self, sample_hist_data_100):
        from stock_selector import StockSelector
        s = StockSelector()
        # 所有指标方法都应该能用
        assert s.calculate_technical_indicators(sample_hist_data_100)
        assert s.calculate_advanced_indicators(sample_hist_data_100)
        rsrs = s.calculate_rsrs(sample_hist_data_100)
        assert 'slope' in rsrs
        assert s.calculate_kdj_rsi_cci(sample_hist_data_100)

    def test_facade_method_proxy_scorer(self, sample_hist_data_100):
        from stock_selector import StockSelector
        s = StockSelector()
        # 打分方法应该能用
        buy = s.evaluate_buy_signal(sample_hist_data_100, {'代码': 'TEST'})
        assert 'buy_score' in buy
        score, _ = s.evaluate_mid_long_term({'代码': 'TEST'}, sample_hist_data_100)
        assert isinstance(score, (int, float))
        score, _ = s.evaluate_short_term({'代码': 'TEST'}, sample_hist_data_100)
        assert isinstance(score, (int, float))
        s.calculate_short_term_aggressive(sample_hist_data_100, {'代码': 'TEST'})
        s.calculate_short_term_conservative(sample_hist_data_100, {'代码': 'TEST'})