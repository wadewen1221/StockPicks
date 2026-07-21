#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能 A 股选股器 V2 - 模块化入口

模块拆分：
    cache.py         - LRU 缓存
    data_fetcher.py  - 历史数据获取
    fiscal.py        - 基本面财务数据
    indicators.py    - 技术指标计算（MA/MACD/RSRS/KDJ/RSI/CCI 等）
    scorer.py        - 打分函数（多策略评分）
    strategies.py    - 选股主流程

StockSelector 门面类聚合以上模块，提供向后兼容的单一入口。
"""
from .cache import LRUCache
from .data_fetcher import DataFetcher
from .fiscal import FiscalDataFetcher
from .indicators import (
    calculate_advanced_indicators,
    calculate_kdj_rsi_cci,
    calculate_rsrs,
    calculate_technical_indicators,
)
from .scorer import (
    calculate_mid_long_score_v2,
    calculate_short_term_aggressive,
    calculate_short_term_conservative,
    evaluate_buy_signal,
    evaluate_mid_long_term,
    evaluate_short_term,
)
from .strategies import (
    select_mid_long_term_stocks,
    select_short_term_stocks,
    select_with_rsrs_kdj_cci,
)

__all__ = [
    'LRUCache',
    'DataFetcher',
    'FiscalDataFetcher',
    'calculate_technical_indicators',
    'calculate_advanced_indicators',
    'calculate_rsrs',
    'calculate_kdj_rsi_cci',
    'evaluate_buy_signal',
    'evaluate_mid_long_term',
    'evaluate_short_term',
    'calculate_mid_long_score_v2',
    'calculate_short_term_aggressive',
    'calculate_short_term_conservative',
    'select_mid_long_term_stocks',
    'select_short_term_stocks',
    'select_with_rsrs_kdj_cci',
]


class StockSelector:
    """
    选股器门面类 - 向后兼容旧 API

    内部聚合 DataFetcher / FiscalDataFetcher，所有实例方法
    委托到独立模块的纯函数。
    """

    def __init__(self):
        self.fetcher = DataFetcher()
        self.fiscal_fetcher = FiscalDataFetcher()
        self.evaluations = {}
        # 市场自适应阈值（根据市场波动率动态调整）
        self._market_thresholds = None
        self._thresholds_timestamp = 0

    # ========== 指标 ==========

    def calculate_technical_indicators(self, hist_data):
        return calculate_technical_indicators(hist_data)

    def calculate_advanced_indicators(self, hist_data):
        return calculate_advanced_indicators(hist_data)

    def calculate_rsrs(self, hist_data, period=18):
        return calculate_rsrs(hist_data, period)

    def calculate_kdj_rsi_cci(self, hist_data):
        return calculate_kdj_rsi_cci(hist_data)

    # ========== 打分 ==========

    def evaluate_buy_signal(self, hist_data, stock_info):
        return evaluate_buy_signal(hist_data, stock_info)

    def evaluate_mid_long_term(self, stock_data, hist_data):
        return evaluate_mid_long_term(stock_data, hist_data)

    def evaluate_short_term(self, stock_data, hist_data):
        return evaluate_short_term(stock_data, hist_data)

    def calculate_mid_long_score_v2(self, hist_data, stock_info, indicators=None):
        return calculate_mid_long_score_v2(
            hist_data, stock_info, indicators,
            market_thresholds=self._get_market_thresholds()
        )

    def calculate_short_term_aggressive(self, hist_data, stock_info):
        return calculate_short_term_aggressive(hist_data, stock_info)

    def calculate_short_term_conservative(self, hist_data, stock_info):
        return calculate_short_term_conservative(hist_data, stock_info)

    # ========== 主流程 ==========

    def select_mid_long_term_stocks(self, limit=4):
        return select_mid_long_term_stocks(self.fetcher, self.fiscal_fetcher, limit)

    def select_short_term_stocks(self, limit=3, strategy='aggressive'):
        return select_short_term_stocks(self.fetcher, self.fiscal_fetcher, limit, strategy)

    def select_with_rsrs_kdj_cci(self, limit=5):
        return select_with_rsrs_kdj_cci(self.fetcher, self.fiscal_fetcher, limit)

    # ========== 市场阈值（StockSelector 内部状态）==========

    def _get_market_thresholds(self):
        """
        获取市场自适应阈值 - 根据近期市场波动率自动调整评分阈值。
        """
        import time

        # 缓存5分钟
        if self._market_thresholds and time.time() - self._thresholds_timestamp < 300:
            return self._market_thresholds

        import numpy as np
        all_stocks = self.fetcher.get_stocks_from_historical(preload_data=False)
        changes = []
        for s in all_stocks[:200]:
            change = float(s.get('涨跌幅', 0))
            changes.append(change)

        if changes:
            avg_change = np.mean(changes)
            volatility = np.std(changes)
        else:
            avg_change = 0
            volatility = 0.02

        vol_factor = min(max(volatility / 0.03, 0.7), 1.5)

        self._market_thresholds = {
            'volatility': volatility,
            'avg_change': avg_change,
            'vol_factor': vol_factor,
            'rsi_oversold': max(25, int(35 * vol_factor)),
            'rsi_overbought': min(80, int(75 / vol_factor)),
            'vol_ratio_threshold': max(1.2, 1.5 / vol_factor),
            'position_low': max(0.15, 0.25 / vol_factor),
            'position_high': min(0.85, 0.75 * vol_factor),
        }
        self._thresholds_timestamp = time.time()
        return self._market_thresholds