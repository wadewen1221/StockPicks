#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票筛选模块 V2 - 向后兼容入口

历史：
    原版为单文件 stock_selector.py（约 1700 行），V2 重构后拆为 backend/selector/ 包。
    本文件作为兼容层，从 selector 包重新导出所有公开符号，保证旧 import 语句继续工作：

        from stock_selector import StockSelector        # OK
        from stock_selector import DataFetcher, LRUCache  # OK
        from stock_selector import FiscalDataFetcher     # OK
        from stock_selector import calculate_rsrs        # OK
        from stock_selector import select_mid_long_term_stocks  # OK

新代码请直接 `from selector import ...`，避免此兼容层。
"""
from selector import (
    LRUCache,
    DataFetcher,
    FiscalDataFetcher,
    StockSelector,
    calculate_advanced_indicators,
    calculate_kdj_rsi_cci,
    calculate_mid_long_score_v2,
    calculate_rsrs,
    calculate_short_term_aggressive,
    calculate_short_term_conservative,
    calculate_technical_indicators,
    evaluate_buy_signal,
    evaluate_mid_long_term,
    evaluate_short_term,
    select_mid_long_term_stocks,
    select_short_term_stocks,
    select_with_rsrs_kdj_cci,
)

__all__ = [
    'LRUCache',
    'DataFetcher',
    'FiscalDataFetcher',
    'StockSelector',
    'calculate_advanced_indicators',
    'calculate_kdj_rsi_cci',
    'calculate_mid_long_score_v2',
    calculate_rsrs.__name__,
    'calculate_short_term_aggressive',
    'calculate_short_term_conservative',
    'calculate_technical_indicators',
    'evaluate_buy_signal',
    'evaluate_mid_long_term',
    'evaluate_short_term',
    'select_mid_long_term_stocks',
    'select_short_term_stocks',
    'select_with_rsrs_kdj_cci',
]


if __name__ == '__main__':
    selector = StockSelector()
    print("=== 中长线选股 ===")
    mid_long = selector.select_mid_long_term_stocks(limit=4)
    for s in mid_long:
        print(f"{s['code']} {s['name']}: 评分={s['score']}")

    print("\n=== 超短线激进型 ===")
    short_agg = selector.select_short_term_stocks(limit=3, strategy='aggressive')
    for s in short_agg:
        print(f"{s['code']} {s['name']}: 评分={s['score']}")

    print("\n=== 超短线稳健型 ===")
    short_con = selector.select_short_term_stocks(limit=3, strategy='conservative')
    for s in short_con:
        print(f"{s['code']} {s['name']}: 评分={s['score']}")

    print("\n=== RSRS/KDJ/RSI/CCI组合筛选 ===")
    combo = selector.select_with_rsrs_kdj_cci(limit=5)
    for s in combo:
        print(f"{s['code']} {s['name']}: buy_score={s['buy_score']}")