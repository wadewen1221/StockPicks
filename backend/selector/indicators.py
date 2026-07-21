#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算 - MA/MACD/RSI/BOLL/RSRS/KDJ/CCI 等

所有函数都是"纯函数"——输入 hist_data，输出指标 dict，便于测试和组合。
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from ._types import HistData, Indicators, StockDataList

# ================== 基础技术指标 ==================


def calculate_technical_indicators(hist_data: StockDataList) -> Indicators:
    """计算基础技术指标 (MA / 均线位置 / 量比 / 波动率 / 近期涨幅)

    Args:
        hist_data: 历史K线列表，按日期正序，至少 20 根

    Returns:
        {ma5, ma10, ma20, ma60, current_price, position, vol_ratio,
         volatility, change_5d, change_20d, volume} - 数据不足时返回 {}
    """
    if not hist_data or len(hist_data) < 20:
        return {}

    df = pd.DataFrame(hist_data)
    close: np.ndarray = df["close"].values

    ma5: float = float(np.mean(close[-5:]))
    ma10: float = float(np.mean(close[-10:]))
    ma20: float = float(np.mean(close[-20:]))
    ma60: float = float(np.mean(close[-60:])) if len(close) >= 60 else ma20

    current_price: float = float(close[-1])
    high_250: float = float(np.max(close))
    low_250: float = float(np.min(close))
    position: float = (
        (current_price - low_250) / (high_250 - low_250)
        if high_250 != low_250
        else 0.5
    )

    vol_ma5: float = float(np.mean(df["volume"].values[-5:]))
    vol_ma20: float = float(np.mean(df["volume"].values[-20:]))
    vol_ratio: float = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0

    returns: np.ndarray = np.diff(np.log(close))
    volatility: float = (
        float(np.std(returns) * np.sqrt(250)) if len(returns) > 0 else 0.0
    )

    change_5d: float = (
        float((close[-1] / close[-6] - 1) * 100) if len(close) >= 6 else 0.0
    )
    change_20d: float = (
        float((close[-1] / close[-21] - 1) * 100) if len(close) >= 21 else 0.0
    )

    return {
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "current_price": current_price,
        "position": position,
        "vol_ratio": vol_ratio,
        "volatility": volatility,
        "change_5d": change_5d,
        "change_20d": change_20d,
        "volume": float(df["volume"].values[-1]),
    }


# ================== 高级技术指标 ==================


def calculate_advanced_indicators(hist_data: StockDataList) -> Indicators:
    """计算高级技术指标 (MACD/RSI/BOLL/均线形态/换手率/涨停基因)

    Args:
        hist_data: 历史K线列表，至少 60 根

    Returns:
        包含 macd/rsi/bollinger/ma*/position/vol_ratio/turnover/volatility/change_*
        和 涨停基因 (limit_up_count_60d/consecutive_limit_up) 的 dict
    """
    if not hist_data or len(hist_data) < 60:
        return {}

    df = pd.DataFrame(hist_data)
    close: np.ndarray = df["close"].values
    volume: np.ndarray = df["volume"].values

    indicators: Indicators = {}

    # === MACD ===
    try:
        ema12: pd.Series = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26: pd.Series = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif: pd.Series = ema12 - ema26
        dea: pd.Series = pd.Series(dif).ewm(span=9, adjust=False).mean()
        macd_hist: pd.Series = 2 * (dif - dea)

        indicators["macd"] = {
            "dif": float(dif.iloc[-1]),
            "dea": float(dea.iloc[-1]),
            "hist": float(macd_hist.iloc[-1]),
            "dif_above_zero": bool(dif.iloc[-1] > 0),
            "golden_cross": bool(
                dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]
            ),
        }
    except Exception:
        indicators["macd"] = {
            "dif": 0.0,
            "dea": 0.0,
            "hist": 0.0,
            "dif_above_zero": False,
            "golden_cross": False,
        }

    # === RSI ===
    try:
        delta: pd.Series = pd.Series(close).diff()
        gain: pd.Series = delta.where(delta > 0, 0).rolling(14).mean()
        loss: pd.Series = (-delta.where(delta < 0, 0)).rolling(14).mean()
        if loss.iloc[-1] == 0 or pd.isna(loss.iloc[-1]):
            indicators["rsi"] = 100.0
        else:
            rs: pd.Series = gain / loss
            rsi: pd.Series = 100 - (100 / (1 + rs))
            indicators["rsi"] = (
                float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
            )
    except Exception:
        indicators["rsi"] = 50.0

    # === 布林带 ===
    try:
        ma20_series: pd.Series = pd.Series(close).rolling(20).mean()
        std20: pd.Series = pd.Series(close).rolling(20).std()
        upper_band: pd.Series = ma20_series + 2 * std20
        lower_band: pd.Series = ma20_series - 2 * std20

        boll_position: float = (
            (close[-1] - lower_band.iloc[-1])
            / (upper_band.iloc[-1] - lower_band.iloc[-1])
            if upper_band.iloc[-1] != lower_band.iloc[-1]
            else 0.5
        )

        indicators["bollinger"] = {
            "upper": float(upper_band.iloc[-1]),
            "middle": float(ma20_series.iloc[-1]),
            "lower": float(lower_band.iloc[-1]),
            "position": float(boll_position),
        }
    except Exception:
        indicators["bollinger"] = {
            "upper": 0.0,
            "middle": 0.0,
            "lower": 0.0,
            "position": 0.5,
        }

    # === 均线 ===
    indicators["ma5"] = float(np.mean(close[-5:]))
    indicators["ma10"] = float(np.mean(close[-10:]))
    indicators["ma20"] = float(np.mean(close[-20:]))
    indicators["ma60"] = (
        float(np.mean(close[-60:])) if len(close) >= 60 else indicators["ma20"]
    )

    indicators["ma_bullish"] = bool(
        indicators["ma5"] > indicators["ma10"] > indicators["ma20"] > indicators["ma60"]
    )
    indicators["ma_partial_bullish"] = bool(
        indicators["ma5"] > indicators["ma20"] > indicators["ma60"]
    )

    # === 相对位置 ===
    high_250: float = float(np.max(close))
    low_250: float = float(np.min(close))
    indicators["position"] = float(
        (close[-1] - low_250) / (high_250 - low_250) if high_250 != low_250 else 0.5
    )

    # === 量比 ===
    vol_ma5: float = float(np.mean(volume[-5:]))
    vol_ma20: float = float(np.mean(volume[-20:]))
    indicators["vol_ratio"] = float(vol_ma5 / vol_ma20) if vol_ma20 > 0 else 1.0

    # === 换手率 ===
    if "turnover" in df.columns:
        indicators["turnover"] = float(df["turnover"].values[-1])
    else:
        indicators["turnover"] = (
            float(volume[-1] / (close[-1] * 1e8) * 100) if close[-1] > 0 else 0.0
        )

    # === 波动率 ===
    returns: np.ndarray = np.diff(np.log(close))
    indicators["volatility"] = (
        float(np.std(returns) * np.sqrt(250)) if len(returns) > 0 else 0.0
    )

    # === 近期涨幅 ===
    indicators["change_5d"] = (
        float((close[-1] / close[-6] - 1) * 100) if len(close) >= 6 else 0.0
    )
    indicators["change_10d"] = (
        float((close[-1] / close[-11] - 1) * 100) if len(close) >= 11 else 0.0
    )
    indicators["change_20d"] = (
        float((close[-1] / close[-21] - 1) * 100) if len(close) >= 21 else 0.0
    )

    # === 涨停基因 ===
    if "change_pct" in df.columns:
        limit_ups: np.ndarray = df["change_pct"].values
        indicators["limit_up_count_60d"] = int(sum(1 for c in limit_ups if c >= 9.9))
        consecutive: int = 0
        for c in reversed(limit_ups):
            if c >= 9.9:
                consecutive += 1
            else:
                break
        indicators["consecutive_limit_up"] = consecutive
    else:
        indicators["limit_up_count_60d"] = 0
        indicators["consecutive_limit_up"] = 0

    # === 今日涨幅 ===
    if "change_pct" in df.columns:
        indicators["change_pct"] = float(df["change_pct"].values[-1])
    else:
        prev_close: float = (
            float(df["close"].values[-2]) if len(df) >= 2 else float(df["close"].values[-1])
        )
        curr_close: float = float(df["close"].values[-1])
        indicators["change_pct"] = (
            float((curr_close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        )

    return indicators


# ================== RSRS 阻力支撑相对强度 ==================


def calculate_rsrs(hist_data: StockDataList, period: int = 18) -> Dict[str, Any]:
    """计算 RSRS 指标（阻力支撑相对强度）

    RSRS = 斜率值，通过 N 日最高价与最低价的线性回归获得
    斜率 > 0 表示趋势向上，斜率越大趋势越强

    Args:
        hist_data: 历史K线列表，至少 period+1 根
        period: 回归窗口（默认 18）

    Returns:
        {
            'rsrs': float,        # 当前周期 RSRS 值(同 slope)
            'slope': float,       # 线性回归斜率(供调用方直接使用)
            'rsrs_ma': float,     # RSRS 5 日均值
            'signal': str         # 'strong_up' / 'up' / 'neutral' / 'down' / 'strong_down'
        }
        数据不足时返回带默认值的 dict（避免 NoneType 错误）
    """
    # 默认返回结构 - 包含全部字段，避免上游 .get('slope', 0) 险责
    empty: Dict[str, Any] = {
        "rsrs": 1.0,
        "slope": 1.0,
        "rsrs_ma": 1.0,
        "signal": "neutral",
    }

    if not hist_data or len(hist_data) < period + 1:
        return empty

    df = pd.DataFrame(hist_data)
    close: np.ndarray = df["close"].values
    high: np.ndarray = df["high"].values
    low: np.ndarray = df["low"].values

    results: list[float] = []
    for i in range(period, len(close)):
        high_n: np.ndarray = high[i - period : i]
        low_n: np.ndarray = low[i - period : i]

        # 线性回归 y = kx + b, y=最高价, x=最低价
        try:
            x: np.ndarray = np.array(low_n)
            y: np.ndarray = np.array(high_n)
            if len(x) > 0 and len(y) > 0:
                # 压制 polyfit 的所有警告（低价股数据变化极小时可能触发）
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    k: float = float(np.polyfit(x, y, 1)[0])
                results.append(k)
            else:
                results.append(1.0)
        except Exception:
            results.append(1.0)

    if not results:
        return empty

    rsrs_current: float = results[-1]
    rsrs_ma: float = float(np.mean(results[-5:])) if len(results) >= 5 else rsrs_current

    # 信号判断
    signal: str = "neutral"
    if rsrs_current > 1.05 and rsrs_ma > 1.0:
        signal = "strong_up"
    elif rsrs_current > 1.0 and rsrs_ma > 0.98:
        signal = "up"
    elif rsrs_current < 0.95 and rsrs_ma < 1.0:
        signal = "down"
    elif rsrs_current < 0.9:
        signal = "strong_down"

    return {
        "rsrs": float(rsrs_current),
        "slope": float(rsrs_current),  # slope与rsrs相同，都是线性回归斜率
        "rsrs_ma": float(rsrs_ma),
        "signal": signal,
    }


# ================== KDJ / RSI / CCI 组合 ==================


def calculate_kdj_rsi_cci(hist_data: StockDataList) -> Dict[str, Any]:
    """计算 KDJ / RSI / CCI 组合指标（用于超买超卖判断）

    Args:
        hist_data: 历史K线列表，至少 20 根

    Returns:
        {
            'kdjk','kdjd','kdjj': float,           # KDJ 三个值
            'kdj_oversold','kdj_overbought': bool, # KDJ 超买超卖
            'kdj_golden_cross','kdj_death_cross': bool,
            'rsi_6','rsi_12': float,               # RSI 双周期
            'rsi_oversold','rsi_overbought': bool,
            'rsi_oversold_12','rsi_overbought_12': bool,
            'cci': float,
            'cci_oversold','cci_overbought': bool,
            'cci_calculation_failed': bool
        }
        数据不足时返回 {}
    """
    if not hist_data or len(hist_data) < 20:
        return {}

    df = pd.DataFrame(hist_data)
    close: np.ndarray = df["close"].values
    high: np.ndarray = df["high"].values
    low: np.ndarray = df["low"].values

    result: Dict[str, Any] = {}

    # === KDJ ===
    period: int = 9
    k_values: list[float] = []
    d_values: list[float] = []
    j_values: list[float] = []

    for i in range(period, len(close)):
        n_high: np.ndarray = high[i - period + 1 : i + 1]
        n_low: np.ndarray = low[i - period + 1 : i + 1]
        rsv: float = (
            (close[i] - np.min(n_low)) / (np.max(n_high) - np.min(n_low)) * 100
            if np.max(n_high) != np.min(n_low)
            else 50.0
        )

        k: float = (
            2 / 3 * 50 + 1 / 3 * rsv
            if len(k_values) == 0
            else 2 / 3 * k_values[-1] + 1 / 3 * rsv
        )
        d: float = (
            2 / 3 * 50 + 1 / 3 * k
            if len(d_values) == 0
            else 2 / 3 * d_values[-1] + 1 / 3 * k
        )
        j: float = 3 * k - 2 * d

        k_values.append(k)
        d_values.append(d)
        j_values.append(j)

    if k_values:
        result["kdjk"] = float(k_values[-1])
        result["kdjd"] = float(d_values[-1])
        result["kdjj"] = float(j_values[-1])
        result["kdj_oversold"] = bool(k_values[-1] < 20)
        result["kdj_overbought"] = bool(k_values[-1] > 80)
        # 【修复P0-3】KDJ金叉/死叉信号均补全
        result["kdj_golden_cross"] = bool(
            len(k_values) >= 2
            and k_values[-1] > d_values[-1]
            and k_values[-2] <= d_values[-2]
        )
        result["kdj_death_cross"] = bool(
            len(k_values) >= 2
            and k_values[-1] < d_values[-1]
            and k_values[-2] >= d_values[-2]
        )
    else:
        result["kdjk"] = None
        result["kdjd"] = None
        result["kdjj"] = None
        result["kdj_oversold"] = False
        result["kdj_overbought"] = False
        result["kdj_golden_cross"] = False
        result["kdj_death_cross"] = False

    # === RSI ===
    try:
        delta: pd.Series = pd.Series(close).diff()
        gain: pd.Series = delta.where(delta > 0, 0).rolling(6).mean()
        loss: pd.Series = (-delta.where(delta < 0, 0)).rolling(6).mean()

        # 安全计算RSI，处理零除情况
        rsi_6_val: float = 50.0
        if not (pd.isna(gain.iloc[-1]) or pd.isna(loss.iloc[-1])):
            if loss.iloc[-1] == 0:
                rsi_6_val = 100.0 if gain.iloc[-1] > 0 else 50.0
            elif gain.iloc[-1] == 0 and loss.iloc[-1] > 0:
                rsi_6_val = 0.0
            else:
                rs: float = gain.iloc[-1] / loss.iloc[-1]
                rsi_6_val = 100.0 - (100.0 / (1 + rs))
        result["rsi_6"] = rsi_6_val

        gain12: pd.Series = delta.where(delta > 0, 0).rolling(12).mean()
        loss12: pd.Series = (-delta.where(delta < 0, 0)).rolling(12).mean()

        rsi_12_val: float = 50.0
        if not (pd.isna(gain12.iloc[-1]) or pd.isna(loss12.iloc[-1])):
            if loss12.iloc[-1] == 0:
                rsi_12_val = 100.0 if gain12.iloc[-1] > 0 else 50.0
            elif gain12.iloc[-1] == 0 and loss12.iloc[-1] > 0:
                rsi_12_val = 0.0
            else:
                rs12: float = gain12.iloc[-1] / loss12.iloc[-1]
                rsi_12_val = 100.0 - (100.0 / (1 + rs12))
        result["rsi_12"] = rsi_12_val
    except Exception:
        # 【修复P2-9】RSI计算失败时返回None，与RSI=50（中性正常值）区分
        result["rsi_6"] = None
        result["rsi_12"] = None

    # 【修复P2-9】RSI超买超卖（双周期），安全处理None
    rsi_6: Optional[float] = result["rsi_6"]
    rsi_12: Optional[float] = result["rsi_12"]
    result["rsi_oversold"] = rsi_6 is not None and rsi_6 < 30
    result["rsi_overbought"] = rsi_6 is not None and rsi_6 > 70
    result["rsi_oversold_12"] = rsi_12 is not None and rsi_12 < 30
    result["rsi_overbought_12"] = rsi_12 is not None and rsi_12 > 70

    # === CCI ===
    try:
        tp: np.ndarray = (high + low + close) / 3
        sma_tp: pd.Series = pd.Series(tp).rolling(14).mean()
        mad: pd.Series = pd.Series(tp).rolling(14).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        cci: pd.Series = (tp - sma_tp) / (0.015 * mad)
        cci_val: Any = cci.iloc[-1]
        if pd.isna(cci_val):
            result["cci"] = np.nan
            result["cci_calculation_failed"] = True
        else:
            result["cci"] = float(cci_val)
            result["cci_calculation_failed"] = False
    except Exception:
        result["cci"] = np.nan
        result["cci_calculation_failed"] = True

    cci_now: float = result["cci"]
    result["cci_oversold"] = bool(cci_now < -100) if not pd.isna(cci_now) else False
    result["cci_overbought"] = bool(cci_now > 100) if not pd.isna(cci_now) else False

    return result