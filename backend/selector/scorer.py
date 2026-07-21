#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打分函数 - 中长线、超短线、RSRS 等综合评分

5 套打分函数：
  1. evaluate_buy_signal            - 超买超卖综合信号 (买入/卖出评分)
  2. evaluate_mid_long_term         - 中长线评分 (V1 简化版)
  3. evaluate_short_term            - 超短线评分 (V1 简化版)
  4. calculate_mid_long_score_v2    - 中长线 V2 (满分 95,五大维度)
  5. calculate_short_term_aggressive - 超短线激进 (满分 100)
  6. calculate_short_term_conservative - 超短线稳健 (满分 85)
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ._types import HistData, Indicators, ScoreResult, StockDataList
from .indicators import (
    calculate_advanced_indicators,
    calculate_kdj_rsi_cci,
    calculate_rsrs,
    calculate_technical_indicators,
)

# 类型别名: market_thresholds 用于市场自适应评分
MarketThresholds = Dict[str, float]


def evaluate_buy_signal(hist_data: StockDataList, stock_info: Dict[str, Any]) -> Dict[str, Any]:
    """超买超卖综合评估（KDJ + RSI + CCI + RSRS）

    Args:
        hist_data: 历史K线列表
        stock_info: 股票基本信息 (来自 get_stocks_from_historical)

    Returns:
        {
            'buy_score': int,         # 买入信号总分
            'sell_score': int,        # 卖出信号总分
            'reasons': List[str],     # 触发原因
            'kdj_rsi_cci': dict,
            'rsrs': dict
        }
    """
    kdj_rsi_cci: Dict[str, Any] = calculate_kdj_rsi_cci(hist_data)
    rsrs: Dict[str, Any] = calculate_rsrs(hist_data)

    buy_score: int = 0
    sell_score: int = 0
    reasons: list[str] = []

    # KDJ 超卖信号
    if kdj_rsi_cci.get("kdj_oversold") and kdj_rsi_cci.get("kdj_golden_cross"):
        buy_score += 20
        reasons.append("KDJ低位金叉")

    # RSI 超卖信号
    if kdj_rsi_cci.get("rsi_oversold"):
        buy_score += 15
        reasons.append("RSI超卖")

    if kdj_rsi_cci.get("rsi_overbought"):
        sell_score += 15
        reasons.append("RSI超买")

    # CCI 超卖信号
    if kdj_rsi_cci.get("cci_oversold"):
        buy_score += 10
        reasons.append("CCI超卖")

    if kdj_rsi_cci.get("cci_overbought"):
        sell_score += 10
        reasons.append("CCI超买")

    # RSRS 信号
    if rsrs.get("signal") == "strong_up":
        buy_score += 15
        reasons.append("RSRS强势向上")
    elif rsrs.get("signal") == "up":
        buy_score += 10

    if rsrs.get("signal") == "strong_down":
        sell_score += 15
        reasons.append("RSRS强势向下")

    return {
        "buy_score": buy_score,
        "sell_score": sell_score,
        "reasons": reasons,
        "kdj_rsi_cci": kdj_rsi_cci,
        "rsrs": rsrs,
    }


def evaluate_mid_long_term(
    stock_data_or_hist: Any,
    hist_data_or_stock: Any = None,
) -> Tuple[int, ScoreResult]:
    """评估中长线投资价值（V1 简化版,满分 100）

    为了向后兼容，同时支持两种调用顺序：
        - 旧 API: evaluate_mid_long_term(stock_data, hist_data)
        - 新 API: evaluate_mid_long_term(hist_data) 或 evaluate_mid_long_term(hist_data, stock_data)
    内部按“哪个是 list”自动判断。

    Args:
        stock_data_or_hist: 股票基本信息 dict 或历史数据 list
        hist_data_or_stock: 反之（可选）

    Returns:
        (score, result_dict) - score 是 0-100 的评分
    """
    # 参数顺序智能判定
    if isinstance(stock_data_or_hist, list):
        hist_data: StockDataList = stock_data_or_hist
        stock_data: Optional[Dict[str, Any]] = hist_data_or_stock
    elif isinstance(hist_data_or_stock, list):
        hist_data = hist_data_or_stock
        stock_data = stock_data_or_hist
    else:
        return 0, {}

    if not hist_data or len(hist_data) < 60:
        return 0, {}

    indicators: Indicators = calculate_technical_indicators(hist_data)
    if not indicators:
        return 0, {}

    score: int = 0
    reasons: list[str] = []

    # 1. 相对低位 (30%)
    position: float = indicators["position"]
    if position < 0.3:
        score += 30
        reasons.append(f"相对低位({position:.1%})")
    elif position < 0.5:
        score += 15

    # 2. 均线多头排列 (20%)
    if indicators["ma5"] > indicators["ma20"] > indicators["ma60"]:
        score += 20
        reasons.append("均线多头排列")
    elif indicators["ma20"] > indicators["ma60"]:
        score += 10

    # 3. 成交量配合 (20%)
    if indicators["vol_ratio"] > 1.5:
        score += 20
    elif indicators["vol_ratio"] > 1.0:
        score += 10

    # 4. 波动率适中 (15%)
    volatility: float = indicators["volatility"]
    if 0.2 < volatility < 0.5:
        score += 15
    elif volatility < 0.2:
        score += 5

    # 5. 近期表现 (15%)
    change: float = indicators["change_20d"]
    if -10 < change < 20:
        score += 15

    return score, {"indicators": indicators, "reasons": reasons}


def evaluate_short_term(
    stock_data_or_hist: Any,
    hist_data_or_stock: Any = None,
) -> Tuple[int, ScoreResult]:
    """评估超短线机会（V1 简化版,满分 90）

    同时支持两种调用顺序：
        - 旧 API: evaluate_short_term(stock_data, hist_data)
        - 新 API: evaluate_short_term(hist_data) 或 evaluate_short_term(hist_data, stock_data)

    Args:
        stock_data_or_hist: 股票基本信息 dict 或历史数据 list
        hist_data_or_stock: 反之（可选）

    Returns:
        (score, result_dict) - score 是 0-90 的评分
    """
    # 参数顺序智能判定
    if isinstance(stock_data_or_hist, list):
        hist_data: StockDataList = stock_data_or_hist
        stock_data: Dict[str, Any] = hist_data_or_stock or {}
    elif isinstance(hist_data_or_stock, list):
        hist_data = hist_data_or_stock
        stock_data = stock_data_or_hist if isinstance(stock_data_or_hist, dict) else {}
    else:
        return 0, {}

    if not hist_data or len(hist_data) < 5:
        return 0, {}

    indicators: Indicators = calculate_technical_indicators(hist_data)
    if not indicators:
        return 0, {}

    score: int = 0
    reasons: list[str] = []

    # 1. 换手率 (25%)
    turnover: float = stock_data.get("turnover", 0) if isinstance(stock_data, dict) else 0.0
    if turnover > 15:
        score += 25
    elif turnover > 8:
        score += 15
    elif turnover > 3:
        score += 10

    # 2. 成交量放大 (25%)
    vol_ratio: float = indicators["vol_ratio"]
    if vol_ratio > 3:
        score += 25
    elif vol_ratio > 2:
        score += 20
    elif vol_ratio > 1.5:
        score += 15

    # 3. 价格位置 (20%)
    position: float = indicators["position"]
    if 0.6 < position < 0.9:
        score += 20
    elif position > 0.9:
        score += 10

    # 4. 短期爆发力 (20%)
    change_5d: float = indicators["change_5d"]
    if 5 < change_5d < 15:
        score += 20
    elif change_5d > 0:
        score += 10

    return score, {"indicators": indicators, "reasons": reasons}


def calculate_mid_long_score_v2(
    hist_data: StockDataList,
    stock_info: Dict[str, Any],
    indicators: Optional[Indicators] = None,
    market_thresholds: Optional[MarketThresholds] = None,
) -> Tuple[int, ScoreResult]:
    """中长线股票优化评分模型 V2（五大维度,满分 95 分）

    维度：
        - 趋势指标 (30): MACD + 均线
        - 动量指标 (25): RSI + 近期涨幅
        - 位置指标 (15): 相对 250 日位置
        - 量价配合 (15): 量比 + 换手率
        - 波动质量 (10): 波动率 + 涨停基因

    Args:
        hist_data: 历史K线列表
        stock_info: 股票基本信息
        indicators: 预计算的指标(可选,避免重复算)
        market_thresholds: 市场自适应阈值 dict(由调用方传入,避免函数变成隐藏的IO调用)

    Returns:
        (score, result_dict)
    """
    if not hist_data or len(hist_data) < 120:
        return 0, {}

    if indicators is None:
        indicators = calculate_advanced_indicators(hist_data)
    if not indicators:
        return 0, {}

    # 默认阈值(无 market_thresholds 参数时使用)
    if market_thresholds is None:
        market_thresholds = {
            "vol_factor": 1.0,
            "rsi_oversold": 35.0,
            "rsi_overbought": 75.0,
            "vol_ratio_threshold": 1.5,
            "position_low": 0.25,
            "position_high": 0.75,
        }

    score: int = 0
    reasons: list[str] = []
    details: Dict[str, Any] = {}

    # === 趋势指标 (30分) ===
    macd: Dict[str, Any] = indicators.get("macd", {})
    macd_score: int = 0
    if macd.get("golden_cross") and macd.get("dif_above_zero"):
        macd_score = 15
        reasons.append("MACD零轴上方金叉")
    elif macd.get("dif_above_zero"):
        macd_score = 5
    score += macd_score
    details["macd_score"] = macd_score

    ma_score: int = 0
    if indicators.get("ma_bullish"):
        ma_score = 15
        reasons.append("均线多头排列")
    elif indicators.get("ma_partial_bullish"):
        ma_score = 10
    elif indicators["ma5"] > indicators["ma20"]:
        ma_score = 5
    score += ma_score
    details["ma_score"] = ma_score

    # === 动量指标 (25分) - 使用自适应阈值 ===
    rsi: float = indicators.get("rsi", 50.0)
    rsi_low: float = market_thresholds["rsi_oversold"]
    rsi_high: float = market_thresholds["rsi_overbought"]
    rsi_score: int = (
        15
        if rsi_low <= rsi <= rsi_high
        else 10
        if rsi_low - 10 <= rsi <= rsi_high + 10
        else 5
    )
    if rsi_score >= 10:
        reasons.append(f"RSI健康区间({rsi:.1f})")
    score += rsi_score
    details["rsi_score"] = rsi_score
    details["thresholds_used"] = market_thresholds  # 记录使用的阈值

    change_20d: float = indicators.get("change_20d", 0.0)
    momentum_score: int = 10 if 0 <= change_20d <= 15 else 5 if -10 <= change_20d < 0 else 3
    score += momentum_score
    details["momentum_score"] = momentum_score

    # === 位置指标 (15分) - 使用自适应阈值 ===
    position: float = indicators.get("position", 0.5)
    pos_low: float = market_thresholds["position_low"]
    pos_high: float = market_thresholds["position_high"]
    position_score: int = (
        15
        if pos_low <= position <= pos_high
        else 8
        if pos_high < position <= pos_high + 0.15
        else 5
    )
    if position_score >= 10:
        reasons.append(f"相对低位({position:.1%})")
    score += position_score
    details["position_score"] = position_score

    # === 量价配合 (15分) - 使用自适应阈值 ===
    vol_ratio: float = indicators.get("vol_ratio", 1.0)
    vol_thresh: float = market_thresholds["vol_ratio_threshold"]
    vol_score: int = 10 if vol_ratio > vol_thresh * 1.5 else 7 if vol_ratio > vol_thresh else 4
    score += vol_score
    details["vol_score"] = vol_score

    turnover: float = indicators.get("turnover", 0.0)
    turnover_score: int = 5 if turnover > 5 else 3 if turnover > 2 else 0
    score += turnover_score
    details["turnover_score"] = turnover_score

    # === 波动质量 (10分) ===
    volatility: float = indicators.get("volatility", 0.0)
    vol_quality_score: int = 5 if 0.15 <= volatility <= 0.4 else 3
    score += vol_quality_score
    details["volatility_score"] = vol_quality_score

    limit_up_count: int = indicators.get("limit_up_count_60d", 0)
    limit_gene_score: int = 5 if limit_up_count >= 2 else 3 if limit_up_count >= 1 else 0
    score += limit_gene_score

    return score, {
        "score": score,
        "reasons": reasons,
        "indicators": indicators,
        "details": details,
        "trend": "上升" if indicators.get("ma_bullish") else "反弹" if indicators.get("ma_partial_bullish") else "震荡",
    }


def calculate_short_term_aggressive(
    hist_data: StockDataList, stock_info: Dict[str, Any]
) -> Tuple[int, ScoreResult]:
    """超短线激进型评分模型（追涨停,满分 100）

    维度:
        - 涨停基因 (35): 今日涨停 + 连板
        - 情绪指标 (30): 换手率
        - 资金流向 (20): 量比
        - 价格位置 (15): 相对位置

    Args:
        hist_data: 历史K线列表
        stock_info: 股票基本信息

    Returns:
        (score, result_dict)
    """
    if not hist_data or len(hist_data) < 60:
        return 0, {}

    indicators: Indicators = calculate_advanced_indicators(hist_data)

    score: int = 0
    reasons: list[str] = []
    details: Dict[str, Any] = {}

    # === 涨停基因 (35分) ===
    today_change: float = indicators.get("change_pct", 0.0)
    limit_up_score: int = 0

    if today_change >= 9.9:
        limit_up_score += 25
        reasons.append("今日涨停")

        consecutive: int = indicators.get("consecutive_limit_up", 0)
        if consecutive >= 3:
            limit_up_score += 15
            reasons.append(f"{consecutive}连板")
        elif consecutive >= 2:
            limit_up_score += 10
    score += limit_up_score
    details["limit_up_score"] = limit_up_score

    # === 情绪指标 (30分) ===
    turnover: float = indicators.get("turnover", 0.0)
    sentiment_score: int = 20 if turnover > 15 else 15 if turnover > 10 else 8 if turnover > 5 else 0
    score += sentiment_score
    details["sentiment_score"] = sentiment_score

    # === 资金流向 (20分) ===
    vol_ratio: float = indicators.get("vol_ratio", 1.0)
    money_score: int = 12 if vol_ratio > 5 else 10 if vol_ratio > 3 else 6 if vol_ratio > 2 else 3
    score += money_score
    details["money_score"] = money_score

    # === 价格位置 (15分) ===
    position: float = indicators.get("position", 0.5)
    position_score: int = 8 if 0.7 <= position <= 0.90 else 6 if 0.5 <= position < 0.7 else 3
    score += position_score
    details["position_score"] = position_score

    return (
        score,
        {
            "score": score,
            "reasons": reasons,
            "indicators": indicators,
            "details": details,
            "type": "激进型",
        },
    )


def calculate_short_term_conservative(
    hist_data: StockDataList, stock_info: Dict[str, Any]
) -> Tuple[int, ScoreResult]:
    """超短线稳健型评分模型（低吸反弹,满分 85）

    维度:
        - 低位首板 (30): 相对位置
        - 量价配合 (30): 量比 + 换手率
        - 趋势确认 (15): 均线形态

    Args:
        hist_data: 历史K线列表
        stock_info: 股票基本信息

    Returns:
        (score, result_dict)
    """
    if not hist_data or len(hist_data) < 60:
        return 0, {}

    indicators: Indicators = calculate_advanced_indicators(hist_data)

    score: int = 0
    reasons: list[str] = []
    details: Dict[str, Any] = {}

    # === 低位首板 (30分) ===
    position: float = indicators.get("position", 0.5)
    position_score: int = 20 if 0.3 <= position <= 0.55 else 15 if 0.2 <= position < 0.3 else 10
    if position_score >= 15:
        reasons.append(f"低位启动({position:.1%})")
    score += position_score
    details["position_score"] = position_score

    # === 量价配合 (30分) ===
    vol_ratio: float = indicators.get("vol_ratio", 1.0)
    vol_score: int = 20 if 1.5 <= vol_ratio <= 2.5 else 10
    score += vol_score
    details["vol_score"] = vol_score

    turnover: float = indicators.get("turnover", 0.0)
    turnover_score: int = 10 if 5 <= turnover <= 15 else 5
    score += turnover_score
    details["turnover_score"] = turnover_score

    # === 趋势确认 (15分) ===
    trend_score: int = 15 if indicators.get("ma_bullish") else 10 if indicators.get("ma_partial_bullish") else 5
    score += trend_score
    details["trend_score"] = trend_score

    return (
        score,
        {
            "score": score,
            "reasons": reasons,
            "indicators": indicators,
            "details": details,
            "type": "稳健型",
        },
    )