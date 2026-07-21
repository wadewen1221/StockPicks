#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试评分制度回测策略"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from handlers.backtest_handler import BacktestEngine
from config import get_historical_dir
import json

def test_backtest():
    """测试一批股票的回测"""
    test_stocks = ['002685', '688110', '603275', '300263', '000001', '600519']
    all_results = []

    print("=" * 60)
    print("评分制度回测策略测试")
    print("=" * 60)

    for code in test_stocks:
        print(f"\n测试股票: {code}")
        try:
            engine = BacktestEngine(initial_cash=1000000)
            results = engine.run([code], '2024-01-01', '2025-06-01')
            analysis = engine.get_analysis()

            trades = analysis.get('trades', {})
            total_trades = trades.get('total', {}).get('total', 0) if isinstance(trades, dict) else 0

            print(f"  总收益率: {analysis.get('profit_pct', 0)*100:.2f}%")
            print(f"  SQN: {analysis.get('sqn', 0):.2f}")
            print(f"  交易次数: {total_trades}")
            print(f"  最终价值: {analysis.get('final_value', 0):.2f}")

            all_results.append({
                'code': code,
                'profit_pct': analysis.get('profit_pct', 0) * 100,
                'sqn': analysis.get('sqn', 0),
                'trades': total_trades,
                'final_value': analysis.get('final_value', 0)
            })
        except Exception as e:
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({'code': code, 'error': str(e)})

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    successful = [r for r in all_results if 'error' not in r]
    with_trades = [r for r in successful if r.get('trades', 0) > 0]

    print(f"测试股票数: {len(test_stocks)}")
    print(f"成功回测: {len(successful)}")
    print(f"有交易的股票: {len(with_trades)} / {len(successful)}")

    if with_trades:
        print("\n有交易的股票:")
        for r in with_trades:
            print(f"  {r['code']}: {r['trades']}笔交易, 收益率{r['profit_pct']:.2f}%, SQN={r['sqn']:.2f}")
    else:
        print("\n警告: 所有股票均无交易！")

if __name__ == '__main__':
    test_backtest()