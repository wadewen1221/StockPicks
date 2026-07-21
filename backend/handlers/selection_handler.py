#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
选股处理器 - 提供API接口触发V2版本选股
"""

import json
import logging

import tornado.ioloop
from handlers.base import BaseHandler
from config import get_historical_dir

logger = logging.getLogger(__name__)


class SelectionHandler(BaseHandler):
    """触发选股并返回结果"""

    def get(self):
        """运行选股（中长线+超短线+RSRS组合）"""
        try:
            from jobs.selector_job import run_stock_selection_and_backtest

            logger.info("手动触发选股任务...")
            # 在executor中运行CPU密集型任务，避免阻塞事件循环
            def run_in_executor():
                return run_stock_selection_and_backtest()

            def on_complete(result):
                if result:
                    self.write({
                        'code': 0,
                        'message': 'success',
                        'data': result
                    })
                else:
                    self.set_status(500)
                    self.write({
                        'code': 500,
                        'message': '选股失败',
                        'data': None
                    })

            def on_error(error):
                logger.error(f"选股API失败: {error}")
                self.set_status(500)
                self.write({
                    'code': 500,
                    'message': f'选股失败: {str(error)}',
                    'data': None
                })

            def _done_callback(future):
                exc = future.exception()
                if exc is None:
                    on_complete(future.result())
                else:
                    on_error(exc)

            executor = tornado.ioloop.IOLoop.current().run_in_executor(None, run_in_executor)
            executor.add_done_callback(_done_callback)

        except Exception as e:
            logger.error(f"选股API失败: {e}")
            self.set_status(500)
            self.write({
                'code': 500,
                'message': f'选股失败: {str(e)}',
                'data': None
            })


class SelectionOnlyHandler(BaseHandler):
    """仅运行选股（不进行回测）"""

    def get(self):
        """仅运行选股，不回测"""
        try:
            from jobs.selector_job import run_stock_selection

            logger.info("手动触发选股任务（仅选股）...")

            def run_in_executor():
                return run_stock_selection()

            def on_complete(result):
                if result:
                    self.write({
                        'code': 0,
                        'message': 'success',
                        'data': result
                    })
                else:
                    self.set_status(500)
                    self.write({
                        'code': 500,
                        'message': '选股失败',
                        'data': None
                    })

            def on_error(error):
                logger.error(f"选股API失败: {error}")
                self.set_status(500)
                self.write({
                    'code': 500,
                    'message': f'选股失败: {str(error)}',
                    'data': None
                })

            def _done_callback(future):
                exc = future.exception()
                if exc is None:
                    on_complete(future.result())
                else:
                    on_error(exc)

            executor = tornado.ioloop.IOLoop.current().run_in_executor(None, run_in_executor)
            executor.add_done_callback(_done_callback)

        except Exception as e:
            logger.error(f"选股API失败: {e}")
            self.set_status(500)
            self.write({
                'code': 500,
                'message': f'选股失败: {str(e)}',
                'data': None
            })


def rsrs_signal_text(signal):
    """RSRS信号中文描述"""
    return {
        'strong_up': '强势向上',
        'up': '向上',
        'neutral': '中性',
        'down': '向下',
        'strong_down': '强势向下'
    }.get(signal, '未知')


class StockAnalysisHandler(BaseHandler):
    """单只股票综合分析"""

    def get(self, code):
        """分析单只股票的买卖点"""
        import os
        import pandas as pd
        import math
        from stock_selector import StockSelector

        def safe_val(v):
            """转换NaN和None为有效值"""
            if v is None:
                return None
            if isinstance(v, float) and math.isnan(v):
                return None
            if hasattr(v, 'item'):
                v = v.item()
                if isinstance(v, float) and math.isnan(v):
                    return None
            return v

        if not code or len(code) != 6 or not code.isdigit():
            self.write(json.dumps({'code': 400, 'message': '无效的股票代码', 'data': None}))
            return

        try:
            data_dir = str(get_historical_dir())
            filepath = os.path.join(data_dir, f"{code}.json")

            if not os.path.exists(filepath):
                self.write(json.dumps({'code': 404, 'message': '股票数据不存在', 'data': None}))
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)

            name = content.get('name', code)
            hist_data = content.get('data', [])

            if not hist_data or len(hist_data) < 60:
                self.write(json.dumps({'code': 400, 'message': '数据不足无法分析', 'data': None}))
                return

            # 计算指标
            selector = StockSelector()
            kdj_rsi_cci = selector.calculate_kdj_rsi_cci(hist_data)
            rsrs = selector.calculate_rsrs(hist_data)

            # 计算买卖评分和建议
            buy_score = 0
            sell_score = 0
            buy_signals = []
            sell_signals = []

            # KDJ分析
            k = safe_val(kdj_rsi_cci.get('kdjk', 0)) or 0
            d = safe_val(kdj_rsi_cci.get('kdjd', 0)) or 0
            j = safe_val(kdj_rsi_cci.get('kdjj', 0)) or 0

            if kdj_rsi_cci.get('kdj_oversold'):
                buy_score += 20
                buy_signals.append({'indicator': 'KDJ', 'signal': '超卖', 'value': f'K={k:.1f} D={d:.1f} J={j:.1f}', 'action': '买入时机'})
            if kdj_rsi_cci.get('kdj_overbought'):
                sell_score += 20
                sell_signals.append({'indicator': 'KDJ', 'signal': '超买', 'value': f'K={k:.1f} D={d:.1f} J={j:.1f}', 'action': '注意风险'})
            if kdj_rsi_cci.get('kdj_golden_cross'):
                buy_score += 15
                buy_signals.append({'indicator': 'KDJ', 'signal': '金叉', 'value': 'K线上穿D线', 'action': '买入信号'})
            if kdj_rsi_cci.get('kdj_death_cross'):
                sell_score += 15
                sell_signals.append({'indicator': 'KDJ', 'signal': '死叉', 'value': 'K线下穿D线', 'action': '卖出信号'})

            # RSI分析（双周期共振）
            rsi_6 = safe_val(kdj_rsi_cci.get('rsi_6', 0)) or 0
            rsi_12 = safe_val(kdj_rsi_cci.get('rsi_12', 0)) or 0
            rsi_6_oversold = kdj_rsi_cci.get('rsi_oversold', False)
            rsi_6_overbought = kdj_rsi_cci.get('rsi_overbought', False)
            rsi_12_oversold = kdj_rsi_cci.get('rsi_oversold_12', False)
            rsi_12_overbought = kdj_rsi_cci.get('rsi_overbought_12', False)

            # RSI6超买超卖信号
            if rsi_6_oversold:
                buy_score += 10
                buy_signals.append({'indicator': 'RSI(6)', 'signal': '超卖', 'value': f'RSI={rsi_6:.1f}', 'action': '短期超卖反弹概率大'})
            if rsi_6_overbought:
                sell_score += 10
                sell_signals.append({'indicator': 'RSI(6)', 'signal': '超买', 'value': f'RSI={rsi_6:.1f}', 'action': '短期注意回调风险'})

            # RSI12超买超卖信号（权重略低）
            if rsi_12_oversold:
                buy_score += 5
                buy_signals.append({'indicator': 'RSI(12)', 'signal': '超卖', 'value': f'RSI={rsi_12:.1f}', 'action': '中期超卖反弹概率大'})
            if rsi_12_overbought:
                sell_score += 5
                sell_signals.append({'indicator': 'RSI(12)', 'signal': '超买', 'value': f'RSI={rsi_12:.1f}', 'action': '中期注意回调风险'})

            # CCI分析
            cci = safe_val(kdj_rsi_cci.get('cci', 0)) or 0
            if kdj_rsi_cci.get('cci_oversold'):
                buy_score += 10
                buy_signals.append({'indicator': 'CCI', 'signal': '超卖', 'value': f'CCI={cci:.1f}', 'action': '低位反弹信号'})
            if kdj_rsi_cci.get('cci_overbought'):
                sell_score += 10
                sell_signals.append({'indicator': 'CCI', 'signal': '超买', 'value': f'CCI={cci:.1f}', 'action': '高位回落风险'})

            # RSRS分析（独家指标，提高权重）
            rsrs_val = safe_val(rsrs.get('rsrs', 0)) or 0
            rsrs_signal = rsrs.get('signal', 'neutral')
            rsrs_slope = safe_val(rsrs.get('slope', rsrs.get('rsrs', 0))) or 0

            if rsrs_signal == 'strong_up':
                buy_score += 20  # 提高权重：15 -> 20
                buy_signals.append({'indicator': 'RSRS', 'signal': '强势向上', 'value': f'斜率={rsrs_slope:.4f}', 'action': '趋势强劲向上'})
            elif rsrs_signal == 'up':
                buy_score += 15  # 提高权重：10 -> 15
                buy_signals.append({'indicator': 'RSRS', 'signal': '向上', 'value': f'斜率={rsrs_slope:.4f}', 'action': '趋势向上'})
            elif rsrs_signal == 'strong_down':
                sell_score += 20  # 提高权重：15 -> 20
                sell_signals.append({'indicator': 'RSRS', 'signal': '强势向下', 'value': f'斜率={rsrs_slope:.4f}', 'action': '趋势强劲向下'})
            elif rsrs_signal == 'down':
                sell_score += 15  # 提高权重：10 -> 15
                sell_signals.append({'indicator': 'RSRS', 'signal': '向下', 'value': f'斜率={rsrs_slope:.4f}', 'action': '趋势向下'})

            # ===== 新增优化1: 趋势强度评分 =====
            trend_score = 0  # 0-100
            trend_level = 'neutral'

            # 计算均线（从历史数据）
            closes = [d.get('close', 0) for d in hist_data]
            if len(closes) >= 60:
                sma60 = sum(closes[-60:]) / 60
            elif len(closes) >= 20:
                sma60 = sum(closes[-20:]) / 20
            else:
                sma60 = closes[-1] if closes else 0

            if len(closes) >= 20:
                sma20 = sum(closes[-20:]) / 20
            else:
                sma20 = closes[-1] if closes else 0

            if len(closes) >= 5:
                sma5 = sum(closes[-5:]) / 5
            else:
                sma5 = closes[-1] if closes else 0

            # 均线多头排列程度
            if sma5 > sma20 > 0:
                trend_score += 30
                if sma20 > sma60 > 0:
                    trend_score += 20  # 完全多头排列

            # RSI健康区间（40-60最佳，既不超买也不超卖）
            if 40 <= rsi_6 <= 60:
                trend_score += 25
            elif 30 <= rsi_6 < 40 or 60 < rsi_6 <= 70:
                trend_score += 15

            # MACD状态（如果可用）
            macd_val = safe_val(kdj_rsi_cci.get('macd', 0))
            macd_signal = safe_val(kdj_rsi_cci.get('macds', 0))
            if macd_val and macd_signal:
                macd_hist = macd_val - macd_signal
                if macd_hist > 0:
                    trend_score += 15

            # 趋势级别判定
            if trend_score >= 60:
                trend_level = 'strong_up'
            elif trend_score >= 40:
                trend_level = 'up'
            elif trend_score <= 20:
                trend_level = 'down'
            elif trend_score <= 35:
                trend_level = 'weak'

            # ===== 新增优化2: 市场环境判断 =====
            market_env = 'volatile'  # 默认震荡
            env_confidence = 0

            # 基于RSRS判断市场环境
            if rsrs_signal in ['strong_up', 'up']:
                market_env = 'uptrend'
                env_confidence = 70 if rsrs_signal == 'strong_up' else 55
            elif rsrs_signal in ['strong_down', 'down']:
                market_env = 'downtrend'
                env_confidence = 70 if rsrs_signal == 'strong_down' else 55

            # 基于KDJ判断
            if kdj_rsi_cci.get('kdj_overbought') and kdj_rsi_cci.get('kdj_golden_cross'):
                if market_env == 'volatile':
                    market_env = 'uptrend'
                    env_confidence = max(env_confidence, 60)

            if market_env == 'volatile' and trend_score >= 60:
                market_env = 'uptrend'
                env_confidence = 65
            elif market_env == 'volatile' and trend_score <= 25:
                market_env = 'downtrend'
                env_confidence = 65

            # ===== 新增优化3: 买卖时机信号 =====
            timing_signal = 'neutral'  # 默认观望
            timing_desc = ''

            # 买入时机：RSI < 30 或 (RSI < 40 且 趋势向上)
            if rsi_6 < 30:
                timing_signal = 'buy'
                timing_desc = f'超卖区域(RSI={rsi_6:.1f})，反弹概率大'
            elif rsi_6 < 40 and trend_level in ['strong_up', 'up']:
                timing_signal = 'buy'
                timing_desc = f'RSI偏低({rsi_6:.1f})且趋势向好，可关注'
            elif rsi_6 < 40:
                timing_signal = 'watch'
                timing_desc = f'RSI偏低({rsi_6:.1f})，等待更多确认'

            # 卖出时机：RSI > 70 或 (RSI > 60 且 趋势向下)
            elif rsi_6 > 80:
                timing_signal = 'sell'
                timing_desc = f'严重超买(RSI={rsi_6:.1f})，注意风险'
            elif rsi_6 > 70:
                timing_signal = 'sell'
                timing_desc = f'超买区域(RSI={rsi_6:.1f})，建议减仓'
            elif rsi_6 > 60 and trend_level in ['down', 'weak']:
                timing_signal = 'sell'
                timing_desc = f'RSI偏高({rsi_6:.1f})且趋势向下，注意风险'

            # 当前位置评估（相对高低点）
            price_position = 'middle'  # 默认中间位置
            if rsi_6 < 30:
                price_position = 'low'
            elif rsi_6 > 70:
                price_position = 'high'

            # 数据质量检查 - 核心指标必须有效，辅助指标可失败
            data_quality = {
                'kdj_valid': kdj_rsi_cci.get('kdjk') is not None and not pd.isna(kdj_rsi_cci.get('kdjk')),
                'rsi_valid': rsi_6 >= 0 and rsi_6 <= 100,  # RSI有效范围0-100，0是有效值（极端下跌）
                'cci_valid': not kdj_rsi_cci.get('cci_calculation_failed', False) and cci is not None and not pd.isna(cci),
                'rsrs_valid': rsrs_val > 0 and rsrs_val != 1.0,  # 1.0是默认值，表示计算失败
                'overall': True
            }
            # 核心指标（KDJ+RSI，至少一个有效）必须有效，RSRS和CCI是辅助指标
            data_quality['overall'] = data_quality['kdj_valid'] and data_quality['rsi_valid']

            # ===== 综合建议 - 整合趋势、市场环境、择时信号 =====
            signal_strength = max(buy_score, sell_score)
            signal_type = '买入' if buy_score >= sell_score else '卖出'

            # 综合研判：结合评分、趋势、市场环境
            if not data_quality['overall']:
                recommendation = '数据不足'
                recommendation_desc = '部分指标数据计算失败，建议更换股票或等待数据完善后再分析。'
            elif timing_signal == 'buy' and buy_score >= 25:
                recommendation = '建议买入'
                recommendation_desc = f'买入时机成熟（{timing_desc}），综合评分买入{buy_score}分/卖出{sell_score}分，市场环境为{market_env}，趋势评分{trend_score}/100。'
            elif timing_signal == 'sell' and sell_score >= 25:
                recommendation = '注意风险'
                recommendation_desc = f'卖出信号明确（{timing_desc}），综合评分卖出{sell_score}分/买入{buy_score}分，市场环境为{market_env}，趋势评分{trend_score}/100。'
            elif buy_score >= 40 and sell_score <= 20:
                recommendation = '强烈建议买入'
                recommendation_desc = f'买入信号显著强（买入{buy_score}分 vs 卖出{sell_score}分），多指标共振，建议积极关注。'
            elif sell_score >= 40 and buy_score <= 20:
                recommendation = '强烈建议卖出'
                recommendation_desc = f'卖出信号显著强（卖出{sell_score}分 vs 买入{buy_score}分），建议减仓或离场。'
            elif buy_score >= 30 and buy_score > sell_score + 10:
                recommendation = '建议买入'
                recommendation_desc = f'买入信号偏强（买入{buy_score}分 vs 卖出{sell_score}分），{"多指标共振。" if buy_score >= 35 else "部分指标向好，可择机关注。"}'
            elif sell_score >= 30 and sell_score > buy_score + 10:
                recommendation = '注意风险'
                recommendation_desc = f'卖出信号偏强（卖出{sell_score}分 vs 买入{buy_score}分），建议谨慎操作，考虑逢高减仓。'
            elif buy_score >= 20 or rsrs_signal in ['strong_up', 'up']:
                recommendation = '密切关注'
                recommendation_desc = f'存在部分买入信号（买入{buy_score}分），市场环境为{market_env}，趋势评分{trend_score}/100。建议等待更强确认信号。'
            elif sell_score >= 20 or rsrs_signal in ['strong_down', 'down']:
                recommendation = '谨慎关注'
                recommendation_desc = f'存在部分风险信号（卖出{sell_score}分），市场环境为{market_env}，趋势评分{trend_score}/100。建议保持谨慎。'
            else:
                recommendation = '观望等待'
                recommendation_desc = f'指标处于中性区域（买入{buy_score}分 vs 卖出{sell_score}分），市场环境为{market_env}，趋势评分{trend_score}/100，没有明显方向信号。'

            # 获取最新价格和涨跌幅
            # ‌仍 P0 修复: 使用昨收价计算涨跌幅,而不是开盘价
            latest = hist_data[-1]
            prev = hist_data[-2] if len(hist_data) >= 2 else latest
            latest_close = latest.get('close', 0)
            prev_close = prev.get('close', 0)

            # 优先级: 1) API 返回的 change_pct 字段 2) 本地用昨收价计计算
            cached_change_pct = latest.get('change_pct')
            if cached_change_pct is not None and isinstance(cached_change_pct, (int, float)):
                change_pct = float(cached_change_pct)
            else:
                change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close > 0 else 0

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': {
                    'code': code,
                    'name': name,
                    'price': latest_close,
                    'change_pct': change_pct,
                    'buy_score': buy_score,
                    'sell_score': sell_score,
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals,
                    'recommendation': recommendation,
                    'recommendation_desc': recommendation_desc,
                    'data_quality': data_quality,
                    # 新增优化字段
                    'trend_score': trend_score,           # 趋势强度 0-100
                    'trend_level': trend_level,          # 趋势级别: strong_up/up/neutral/down/weak
                    'market_env': market_env,            # 市场环境: uptrend/downtrend/volatile
                    'market_confidence': env_confidence,  # 市场判断置信度
                    'timing_signal': timing_signal,       # 买卖时机: buy/sell/watch/neutral
                    'timing_desc': timing_desc,          # 时机描述
                    'price_position': price_position,     # 当前位置: high/middle/low
                    'indicators': {
                        'kdj': {'k': k, 'd': d, 'j': j},
                        'rsi': {'value': rsi_6, 'rsi_6': rsi_6, 'rsi_12': rsi_12},
                        'cci': {'value': cci},
                        'rsrs': {'value': rsrs_val, 'slope': rsrs_slope, 'signal': rsrs_signal, 'ma': rsrs.get('rsrs_ma', 0)},
                        'macd': None, 'macds': None, 'macdh': None,
                        'boll': None, 'boll_ub': None, 'boll_lb': None
                    }
                }
            }))

        except Exception as e:
            logger.error(f"股票分析失败: {e}")
            self.write(json.dumps({'code': 500, 'message': f'分析失败: {str(e)}', 'data': None}))
