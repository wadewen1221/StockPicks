#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
选股+自动回测定时任务
每日收盘后运行选股策略，然后对选出的股票进行回测

V2版本: 使用移植自老版本的stock_selector逻辑，集成RSRS和KDJ/RSI/CCI组合筛选
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backtest import BacktestEngine
from config import get_data_dir, get_stock_cache_path


def convert_to_python_types(obj):
    """递归转换numpy类型为Python原生类型"""
    if isinstance(obj, dict):
        return {k: convert_to_python_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_python_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_python_types(item) for item in obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        val = float(obj)
        # 处理 NaN 和 Inf
        if val != val:  # NaN check (NaN != NaN)
            return None
        if val == float('inf'):
            return None
        if val == float('-inf'):
            return None
        return val
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float):
        # Python float NaN/Inf
        if obj != obj:  # NaN
            return None
        if obj == float('inf') or obj == float('-inf'):
            return None
        return obj
    else:
        return obj

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_stock_selection():
    """
    运行选股策略 - 使用V2版本的stock_selector

    包含:
    - 中长线选股 (均线多头/MACD金叉/RSI位置)
    - 超短线激进型选股 (换手率/成交量放大/价格位置)
    - 超短线稳健型选股
    - RSRS/KDJ/RSI/CCI组合筛选 (V2新增)
    """
    try:
        from stock_selector import StockSelector

        selector = StockSelector()
        result = {
            'mid_long': [],
            'short_term': [],       # 兼容前端：使用激进型
            'short_term_aggressive': [],
            'short_term_conservative': [],
            'rsrs_kdj_cci': [],
            'selection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 1. 中长线选股
        logger.info("[选股] 开始中长线选股...")
        try:
            mid_long = selector.select_mid_long_term_stocks(limit=4)
            for s in mid_long:
                result['mid_long'].append({
                    'code': s['code'],
                    'name': s['name'],
                    'price': s.get('price', 0),
                    'change_pct': s.get('change_pct', 0),
                    'score': s.get('score', 0)
                })
            logger.info(f"[选股] 中长线完成，选出 {len(mid_long)} 只")
        except Exception as e:
            logger.error(f"[选股] 中长线选股失败: {e}")

        # 2. 超短线激进型选股
        logger.info("[选股] 开始超短线激进型选股...")
        try:
            short_agg = selector.select_short_term_stocks(limit=3, strategy='aggressive')
            for s in short_agg:
                stock_info = {
                    'code': s['code'],
                    'name': s['name'],
                    'price': s.get('price', 0),
                    'change_pct': s.get('change_pct', 0),
                    'score': s.get('score', 0)
                }
                result['short_term_aggressive'].append(stock_info)
                result['short_term'].append(stock_info)  # 兼容前端
            logger.info(f"[选股] 超短线激进型完成，選出 {len(short_agg)} 只")
        except Exception as e:
            logger.error(f"[选股] 超短线激进型选股失败: {e}")

        # 3. 超短线稳健型选股
        logger.info("[选股] 开始超短线稳健型选股...")
        try:
            short_con = selector.select_short_term_stocks(limit=3, strategy='conservative')
            for s in short_con:
                result['short_term_conservative'].append({
                    'code': s['code'],
                    'name': s['name'],
                    'price': s.get('price', 0),
                    'change_pct': s.get('change_pct', 0),
                    'score': s.get('score', 0)
                })
            logger.info(f"[选股] 超短线稳健型完成，選出 {len(short_con)} 只")
        except Exception as e:
            logger.error(f"[选股] 超短线稳健型选股失败: {e}")

        # 4. RSRS/KDJ/RSI/CCI组合筛选 (V2新增)
        logger.info("[选股] 开始RSRS/KDJ/RSI/CCI组合筛选...")
        try:
            combo = selector.select_with_rsrs_kdj_cci(limit=5)
            for s in combo:
                result['rsrs_kdj_cci'].append({
                    'code': s['code'],
                    'name': s['name'],
                    'price': s.get('price', 0),
                    'change_pct': s.get('change_pct', 0),
                    'buy_score': s.get('buy_score', 0),
                    'sell_score': s.get('sell_score', 0),
                    'reasons': s.get('reasons', []),
                    'kdj_rsi_cci': s.get('kdj_rsi_cci', {}),
                    'rsrs': s.get('rsrs', {})
                })
            logger.info(f"[选股] RSRS/KDJ/RSI/CCI组合筛选完成，選出 {len(combo)} 只")
        except Exception as e:
            logger.error(f"[选股] RSRS/KDJ/RSI/CCI组合筛选失败: {e}")

        return result

    except Exception as e:
        logger.error(f"[选股] 选股任务失败: {e}")
        return None


def run_backtest_on_stocks(stock_list, initial_cash=1000000, strategy_type='mid_long'):
    """对选出的股票进行回测"""
    if not stock_list:
        return []

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    results = []
    for stock in stock_list:
        code = stock.get('code')
        if not code:
            continue

        try:
            logger.info(f"[回测] {strategy_type}: {code} {stock.get('name', '')}")
            engine = BacktestEngine(initial_cash=initial_cash)
            engine.run([code], start_date, end_date)
            analysis = engine.get_analysis()

            backtest_result = {
                'final_value': analysis.get('final_value', 0),
                'profit_pct': analysis.get('profit_pct', 0),
                'sqn': analysis.get('sqn', 0),
                'sharpe_ratio': analysis.get('sharpe_ratio', 0),
                'max_drawdown': analysis.get('drawdown', {}).get('max', {}).get('drawdown', 0),
                'total_trades': analysis.get('trades', {}).get('total', {}).get('total', 0),
            }
            stock['backtest'] = backtest_result
            logger.info(f"  最终价值: {analysis.get('final_value', 0):.2f}, 收益: {analysis.get('profit_pct', 0)*100:.2f}%")
            results.append(backtest_result)
        except Exception as e:
            logger.error(f"  回测失败: {e}")
            stock['backtest'] = {'error': str(e)}

    return results


def run_stock_selection_and_backtest():
    """
    选股+自动回测主流程

    流程:
    1. 运行V2版本选股策略
    2. 对选出的股票进行回测
    3. 保存结果到缓存
    """
    output_file = str(get_stock_cache_path())

    # 运行选股
    selection_result = run_stock_selection()
    if not selection_result:
        logger.error("选股失败，退出")
        return

    # 对中长线股票进行回测
    if selection_result.get('mid_long'):
        run_backtest_on_stocks(
            selection_result['mid_long'],
            initial_cash=1000000,
            strategy_type='mid_long'
        )

    # 对超短线激进型进行回测
    if selection_result.get('short_term_aggressive'):
        run_backtest_on_stocks(
            selection_result['short_term_aggressive'],
            initial_cash=500000,
            strategy_type='short_term_aggressive'
        )

    # 对超短线稳健型进行回测
    if selection_result.get('short_term_conservative'):
        run_backtest_on_stocks(
            selection_result['short_term_conservative'],
            initial_cash=500000,
            strategy_type='short_term_conservative'
        )

    # RSRS/KDJ/RSI/CCI组合暂不参与回测(短期择时策略)

    # 保存结果（先转换numpy类型为Python原生类型）
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(convert_to_python_types(selection_result), f, ensure_ascii=False, indent=2)

    logger.info(f"选股+回测完成，结果已保存到 {output_file}")
    return selection_result


if __name__ == '__main__':
    run_stock_selection_and_backtest()
