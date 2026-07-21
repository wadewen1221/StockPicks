#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算 - MA/MACD/RSI/BOLL/RSRS/KDJ/CCI 等
"""
import warnings

import numpy as np
import pandas as pd


def calculate_technical_indicators(hist_data):
    """计算基础技术指标"""
    if not hist_data or len(hist_data) < 20:
        return {}

    df = pd.DataFrame(hist_data)
    close = df['close'].values

    ma5 = np.mean(close[-5:])
    ma10 = np.mean(close[-10:])
    ma20 = np.mean(close[-20:])
    ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20

    current_price = close[-1]
    high_250 = np.max(close)
    low_250 = np.min(close)
    position = (current_price - low_250) / (high_250 - low_250) if high_250 != low_250 else 0.5

    vol_ma5 = np.mean(df['volume'].values[-5:])
    vol_ma20 = np.mean(df['volume'].values[-20:])
    vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1

    returns = np.diff(np.log(close))
    volatility = np.std(returns) * np.sqrt(250) if len(returns) > 0 else 0

    change_5d = (close[-1] / close[-6] - 1) * 100 if len(close) >= 6 else 0
    change_20d = (close[-1] / close[-21] - 1) * 100 if len(close) >= 21 else 0

    return {
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'current_price': current_price,
        'position': position,
        'vol_ratio': vol_ratio,
        'volatility': volatility,
        'change_5d': change_5d,
        'change_20d': change_20d,
        'volume': df['volume'].values[-1]
    }


def calculate_advanced_indicators(hist_data):
    """计算高级技术指标"""
    if not hist_data or len(hist_data) < 60:
        return {}

    df = pd.DataFrame(hist_data)
    close = df['close'].values
    volume = df['volume'].values

    indicators = {}

    # === MACD ===
    try:
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = pd.Series(dif).ewm(span=9, adjust=False).mean()
        macd_hist = 2 * (dif - dea)

        indicators['macd'] = {
            'dif': float(dif.iloc[-1]),
            'dea': float(dea.iloc[-1]),
            'hist': float(macd_hist.iloc[-1]),
            'dif_above_zero': dif.iloc[-1] > 0,
            'golden_cross': dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]
        }
    except Exception:
        indicators['macd'] = {'dif': 0, 'dea': 0, 'hist': 0, 'dif_above_zero': False, 'golden_cross': False}

    # === RSI ===
    try:
        delta = pd.Series(close).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        if loss.iloc[-1] == 0 or pd.isna(loss.iloc[-1]):
            indicators['rsi'] = 100.0
        else:
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    except Exception:
        indicators['rsi'] = 50

    # === 布林带 ===
    try:
        ma20_series = pd.Series(close).rolling(20).mean()
        std20 = pd.Series(close).rolling(20).std()
        upper_band = ma20_series + 2 * std20
        lower_band = ma20_series - 2 * std20

        boll_position = (close[-1] - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1]) \
            if upper_band.iloc[-1] != lower_band.iloc[-1] else 0.5

        indicators['bollinger'] = {
            'upper': float(upper_band.iloc[-1]),
            'middle': float(ma20_series.iloc[-1]),
            'lower': float(lower_band.iloc[-1]),
            'position': float(boll_position)
        }
    except Exception:
        indicators['bollinger'] = {'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5}

    # === 均线 ===
    indicators['ma5'] = float(np.mean(close[-5:]))
    indicators['ma10'] = float(np.mean(close[-10:]))
    indicators['ma20'] = float(np.mean(close[-20:]))
    indicators['ma60'] = float(np.mean(close[-60:])) if len(close) >= 60 else indicators['ma20']

    indicators['ma_bullish'] = indicators['ma5'] > indicators['ma10'] > indicators['ma20'] > indicators['ma60']
    indicators['ma_partial_bullish'] = indicators['ma5'] > indicators['ma20'] > indicators['ma60']

    # === 相对位置 ===
    high_250 = np.max(close)
    low_250 = np.min(close)
    indicators['position'] = float((close[-1] - low_250) / (high_250 - low_250)) if high_250 != low_250 else 0.5

    # === 量比 ===
    vol_ma5 = np.mean(volume[-5:])
    vol_ma20 = np.mean(volume[-20:])
    indicators['vol_ratio'] = float(vol_ma5 / vol_ma20) if vol_ma20 > 0 else 1.0

    # === 换手率 ===
    if 'turnover' in df.columns:
        indicators['turnover'] = float(df['turnover'].values[-1])
    else:
        indicators['turnover'] = float(volume[-1] / (close[-1] * 1e8) * 100) if close[-1] > 0 else 0

    # === 波动率 ===
    returns = np.diff(np.log(close))
    indicators['volatility'] = float(np.std(returns) * np.sqrt(250)) if len(returns) > 0 else 0

    # === 近期涨幅 ===
    indicators['change_5d'] = float((close[-1] / close[-6] - 1) * 100) if len(close) >= 6 else 0
    indicators['change_10d'] = float((close[-1] / close[-11] - 1) * 100) if len(close) >= 11 else 0
    indicators['change_20d'] = float((close[-1] / close[-21] - 1) * 100) if len(close) >= 21 else 0

    # === 涨停基因 ===
    if 'change_pct' in df.columns:
        limit_ups = df['change_pct'].values
        indicators['limit_up_count_60d'] = int(sum(1 for c in limit_ups if c >= 9.9))
        consecutive = 0
        for c in reversed(limit_ups):
            if c >= 9.9:
                consecutive += 1
            else:
                break
        indicators['consecutive_limit_up'] = consecutive
    else:
        indicators['limit_up_count_60d'] = 0
        indicators['consecutive_limit_up'] = 0

    # === 今日涨幅 ===
    if 'change_pct' in df.columns:
        indicators['change_pct'] = float(df['change_pct'].values[-1])
    else:
        prev_close = float(df['close'].values[-2]) if len(df) >= 2 else float(df['close'].values[-1])
        curr_close = float(df['close'].values[-1])
        indicators['change_pct'] = float((curr_close - prev_close) / prev_close * 100) if prev_close > 0 else 0

    return indicators


def calculate_rsrs(hist_data, period=18):
    """
    计算RSRS指标（阻力支撑相对强度）
    RSRS = 斜率值，通过N日最高价与最低价的线性回归获得
    斜率 > 0 表示趋势向上，斜率越大趋势越强

    Returns:
        dict: {
            'rsrs': float,        # 当前周期 RSRS 值(同 slope)
            'slope': float,       # 线性回归斜率(供调用方直接使用)
            'rsrs_ma': float,     # RSRS 5 日均值
            'signal': str         # 'strong_up' / 'up' / 'neutral' / 'down' / 'strong_down'
        }
        数据不足时返回带默认值的 dict（避免 NoneType 错误）
    """
    # 默认返回结构 - 包含全部字段，避免上游 .get('slope', 0) 险责
    empty = {
        'rsrs': 1.0,
        'slope': 1.0,
        'rsrs_ma': 1.0,
        'signal': 'neutral',
    }

    if not hist_data or len(hist_data) < period + 1:
        return empty

    df = pd.DataFrame(hist_data)
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values

    results = []
    for i in range(period, len(close)):
        high_n = high[i-period:i]
        low_n = low[i-period:i]

        # 线性回归 y = kx + b, y=最高价, x=最低价
        try:
            x = np.array(low_n)
            y = np.array(high_n)
            if len(x) > 0 and len(y) > 0:
                # 压制 polyfit 的所有警告（低价股数据变化极小时可能触发）
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    k = np.polyfit(x, y, 1)[0]
                results.append(k)
            else:
                results.append(1.0)
        except Exception:
            results.append(1.0)

    if not results:
        return empty

    rsrs_current = results[-1]
    rsrs_ma = np.mean(results[-5:]) if len(results) >= 5 else rsrs_current

    # 信号判断
    signal = 'neutral'
    if rsrs_current > 1.05 and rsrs_ma > 1.0:
        signal = 'strong_up'
    elif rsrs_current > 1.0 and rsrs_ma > 0.98:
        signal = 'up'
    elif rsrs_current < 0.95 and rsrs_ma < 1.0:
        signal = 'down'
    elif rsrs_current < 0.9:
        signal = 'strong_down'

    return {
        'rsrs': float(rsrs_current),
        'slope': float(rsrs_current),  # slope与rsrs相同，都是线性回归斜率
        'rsrs_ma': float(rsrs_ma),
        'signal': signal
    }


def calculate_kdj_rsi_cci(hist_data):
    """
    计算KDJ/RSI/CCI组合指标
    用于超买超卖判断
    """
    if not hist_data or len(hist_data) < 20:
        return {}

    df = pd.DataFrame(hist_data)
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values

    result = {}

    # === KDJ ===
    period = 9
    k_values = []
    d_values = []
    j_values = []

    for i in range(period, len(close)):
        n_high = high[i-period+1:i+1]
        n_low = low[i-period+1:i+1]
        rsv = (close[i] - np.min(n_low)) / (np.max(n_high) - np.min(n_low)) * 100 if np.max(n_high) != np.min(n_low) else 50

        k = 2/3 * 50 + 1/3 * rsv if len(k_values) == 0 else 2/3 * k_values[-1] + 1/3 * rsv
        d = 2/3 * 50 + 1/3 * k if len(d_values) == 0 else 2/3 * d_values[-1] + 1/3 * k
        j = 3 * k - 2 * d

        k_values.append(k)
        d_values.append(d)
        j_values.append(j)

    if k_values:
        result['kdjk'] = k_values[-1]
        result['kdjd'] = d_values[-1]
        result['kdjj'] = j_values[-1]
        result['kdj_oversold'] = k_values[-1] < 20
        result['kdj_overbought'] = k_values[-1] > 80
        # 【修复P0-3】KDJ金叉/死叉信号均补全
        result['kdj_golden_cross'] = len(k_values) >= 2 and k_values[-1] > d_values[-1] and k_values[-2] <= d_values[-2]
        result['kdj_death_cross'] = len(k_values) >= 2 and k_values[-1] < d_values[-1] and k_values[-2] >= d_values[-2]
    else:
        result['kdjk'] = None
        result['kdjd'] = None
        result['kdjj'] = None
        result['kdj_oversold'] = False
        result['kdj_overbought'] = False
        result['kdj_golden_cross'] = False
        result['kdj_death_cross'] = False

    # === RSI ===
    try:
        delta = pd.Series(close).diff()
        gain = delta.where(delta > 0, 0).rolling(6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(6).mean()

        # 安全计算RSI，处理零除情况
        rsi_6_val = 50
        if not (pd.isna(gain.iloc[-1]) or pd.isna(loss.iloc[-1])):
            if loss.iloc[-1] == 0:
                rsi_6_val = 100 if gain.iloc[-1] > 0 else 50
            elif gain.iloc[-1] == 0 and loss.iloc[-1] > 0:
                rsi_6_val = 0
            else:
                rs = gain.iloc[-1] / loss.iloc[-1]
                rsi_6_val = 100 - (100 / (1 + rs))
        result['rsi_6'] = rsi_6_val

        gain12 = delta.where(delta > 0, 0).rolling(12).mean()
        loss12 = (-delta.where(delta < 0, 0)).rolling(12).mean()

        rsi_12_val = 50
        if not (pd.isna(gain12.iloc[-1]) or pd.isna(loss12.iloc[-1])):
            if loss12.iloc[-1] == 0:
                rsi_12_val = 100 if gain12.iloc[-1] > 0 else 50
            elif gain12.iloc[-1] == 0 and loss12.iloc[-1] > 0:
                rsi_12_val = 0
            else:
                rs12 = gain12.iloc[-1] / loss12.iloc[-1]
                rsi_12_val = 100 - (100 / (1 + rs12))
        result['rsi_12'] = rsi_12_val
    except Exception:
        # 【修复P2-9】RSI计算失败时返回None，与RSI=50（中性正常值）区分
        result['rsi_6'] = None
        result['rsi_12'] = None

    # 【修复P2-9】RSI超买超卖（双周期），安全处理None
    rsi_6 = result['rsi_6']
    rsi_12 = result['rsi_12']
    result['rsi_oversold'] = rsi_6 is not None and rsi_6 < 30
    result['rsi_overbought'] = rsi_6 is not None and rsi_6 > 70
    result['rsi_oversold_12'] = rsi_12 is not None and rsi_12 < 30
    result['rsi_overbought_12'] = rsi_12 is not None and rsi_12 > 70

    # === CCI ===
    try:
        tp = (high + low + close) / 3
        sma_tp = pd.Series(tp).rolling(14).mean()
        mad = pd.Series(tp).rolling(14).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - sma_tp) / (0.015 * mad)
        cci_val = cci.iloc[-1]
        if pd.isna(cci_val):
            result['cci'] = np.nan
            result['cci_calculation_failed'] = True
        else:
            result['cci'] = float(cci_val)
            result['cci_calculation_failed'] = False
    except Exception:
        result['cci'] = np.nan
        result['cci_calculation_failed'] = True

    result['cci_oversold'] = result['cci'] < -100
    result['cci_overbought'] = result['cci'] > 100

    return result