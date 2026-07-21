#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能A股投资助手 V2 - 指标图表处理器
整合stockstats + finta + Bokeh可视化
"""

import os
import re
import json
import logging
import traceback
import hashlib
from datetime import datetime, timedelta

import tornado.web
import pandas as pd
import numpy as np
import stockstats
from finta import TA

from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.palettes import Category10, Category20
from bokeh.models import DatetimeTickFormatter, HoverTool

from handlers.base import BaseHandler
from config import get_historical_dir

# 图表缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
CACHE_TTL_HOURS = 24  # 缓存24小时

os.makedirs(CACHE_DIR, exist_ok=True)


def _get_chart_cache_path(code):
    """获取图表缓存文件路径"""
    return os.path.join(CACHE_DIR, f'{code}_chart_cache.json')


def _is_cache_valid(code, data_update_time):
    """检查缓存是否有效"""
    cache_path = _get_chart_cache_path(code)
    if not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # 检查缓存是否过期
        cached_at = cache_data.get('cached_at', '')
        if cached_at:
            cached_time = datetime.fromisoformat(cached_at)
            age = datetime.now() - cached_time
            if age.total_seconds() > CACHE_TTL_HOURS * 3600:
                return False

        # 检查数据是否已更新（数据更新时间晚于缓存时间）
        cache_data_time = cache_data.get('data_update_time', '')
        if data_update_time and cache_data_time:
            if data_update_time > cache_data_time:
                return False

        return True
    except Exception:
        return False


def _save_chart_cache(code, data_update_time, chart_data):
    """保存图表到缓存"""
    cache_path = _get_chart_cache_path(code)
    try:
        cache_data = {
            'code': code,
            'cached_at': datetime.now().isoformat(),
            'data_update_time': data_update_time,
            'script': chart_data['script'],
            'div': chart_data['div'],
            'indicators': chart_data['indicators'],
            'dates': chart_data['dates'],
            'close_prices': chart_data['close_prices']
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
        logging.info(f"图表缓存已保存: {code}")
    except Exception as e:
        logging.warning(f"保存图表缓存失败: {e}")


def _load_chart_cache(code):
    """从缓存加载图表数据"""
    cache_path = _get_chart_cache_path(code)
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return {
            'script': cache_data['script'],
            'div': cache_data['div'],
            'indicators': cache_data['indicators'],
            'dates': cache_data['dates'],
            'close_prices': cache_data['close_prices']
        }
    except Exception:
        return None

# 指标配置 - 17种指标定义
INDICATORS_CONFIG = [
    {
        "id": "kdj",
        "title": "KDJ指标",
        "desc": "随机指标(KDJ)通过特定周期内的最高价、最低价和收盘价计算K、D、J值，用于判断超买超卖",
        "lines": ["kdjk", "kdjd", "kdjj"],
        "colors": [Category10[3][0], Category10[3][1], Category10[3][2]],
        "labels": ["K", "D", "J"]
    },
    {
        "id": "macd",
        "title": "MACD指标",
        "desc": "平滑异同移动平均线，用于判断趋势方向和动量",
        "lines": ["macd", "macds", "macdh"],
        "colors": [Category10[3][0], Category10[3][1], Category10[3][2]],
        "labels": ["MACD", "Signal", "Histogram"]
    },
    {
        "id": "boll",
        "title": "布林带指标",
        "desc": "布林线指标(BOLL)由中轨和上下轨组成，用于判断价格通道和超买超卖",
        "lines": ["boll", "boll_ub", "boll_lb"],
        "colors": [Category10[3][0], Category10[3][1], Category10[3][2]],
        "labels": ["BOLL", "Upper", "Lower"]
    },
    {
        "id": "rsi",
        "title": "RSI指标",
        "desc": "相对强弱指数(RSI)，0-100波动，>70超买，<30超卖",
        "lines": ["rsi_6", "rsi_12"],
        "colors": [Category10[3][0], Category10[3][1]],
        "labels": ["RSI(6)", "RSI(12)"]
    },
    {
        "id": "cci",
        "title": "CCI指标",
        "desc": "顺势指标(CCI)，>100超买，<-100超卖",
        "lines": ["cci", "cci_20"],
        "colors": [Category10[3][0], Category10[3][1]],
        "labels": ["CCI(14)", "CCI(20)"]
    },
    {
        "id": "wr",
        "title": "威廉指标",
        "desc": "威廉指数(WR)，>80超卖，<20超买",
        "lines": ["wr_10", "wr_6"],
        "colors": [Category10[3][0], Category10[3][1]],
        "labels": ["WR(10)", "WR(6)"]
    },
    {
        "id": "atr",
        "title": "ATR指标",
        "desc": "均幅指标(ATR)，衡量市场波动性",
        "lines": ["atr"],
        "colors": [Category10[3][0]],
        "labels": ["ATR"]
    },
    {
        "id": "trix",
        "title": "TRIX指标",
        "desc": "三重指数平滑移动平均线，用于判断趋势",
        "lines": ["trix", "trix_9_sma"],
        "colors": [Category10[3][0], Category10[3][1]],
        "labels": ["TRIX", "TRIX SMA"]
    },
    {
        "id": "dma",
        "title": "DMA指标",
        "desc": "平行线差指标，用于判断短期趋势",
        "lines": ["dma"],
        "colors": [Category10[3][0]],
        "labels": ["DMA"]
    },
    {
        "id": "dmi",
        "title": "DMI指标",
        "desc": "动向指数，包含+DI和ADX用于判断趋势强度",
        "lines": ["pdi", "adx"],
        "colors": [Category10[3][0], Category10[3][2]],
        "labels": ["+DI", "ADX"]
    },
    {
        "id": "adxr",
        "title": "ADXR指标",
        "desc": "平均趋向指数的平滑版本，用于判断趋势强度",
        "lines": ["adxr"],
        "colors": [Category10[3][0]],
        "labels": ["ADXR"]
    },
    {
        "id": "vr",
        "title": "VR指标",
        "desc": "成交量变异率，用于判断量能变化趋势",
        "lines": ["vr"],
        "colors": [Category10[3][0]],
        "labels": ["VR"]
    },
    {
        "id": "ppo",
        "title": "PPO指标",
        "desc": "价格动量振荡器，与MACD类似但以百分比计算",
        "lines": ["ppo", "ppos", "ppoh"],
        "colors": [Category10[3][0], Category10[3][1], Category10[3][2]],
        "labels": ["PPO", "Signal", "Histogram"]
    },
    {
        "id": "cr",
        "title": "CR指标",
        "desc": "能量潮指标，通过最高价、最低价和收盘价判断资金流向",
        "lines": ["cr", "cr-ma1", "cr-ma2", "cr-ma3"],
        "colors": [Category10[3][0], Category10[3][1], Category10[3][2], '#FF6B6B'],
        "labels": ["CR", "MA1", "MA2", "MA3"]
    },
    {
        "id": "mfi",
        "title": "MFI指标",
        "desc": "资金流量指标，结合价格和成交量的超买超卖指标",
        "lines": ["mfi"],
        "colors": [Category10[3][0]],
        "labels": ["MFI"]
    },
    {
        "id": "tema",
        "title": "TEMA指标",
        "desc": "三重指数移动平均线，减少移动平均的滞后性",
        "lines": ["tema"],
        "colors": [Category10[3][0]],
        "labels": ["TEMA"]
    },
    {
        "id": "kama",
        "title": "KAMA指标",
        "desc": "考夫曼自适应移动平均线，能根据市场波动性自动调整",
        "lines": ["kama"],
        "colors": [Category10[3][0]],
        "labels": ["KAMA"]
    }
]


def load_stock_historical(code, data_dir):
    """加载股票历史数据"""
    filepath = os.path.join(data_dir, f"{code}.json")
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)

        data = content.get('data', [])
        if not data:
            return None

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index()

        # 确保列名正确
        df = df.rename(columns={
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'volume': 'volume'
        })

        return df
    except Exception as e:
        logging.error(f"加载股票数据失败 {code}: {e}")
        return None


def calculate_indicators(df):
    """使用stockstats计算所有技术指标"""
    try:
        # 使用stockstats计算
        stockStat = stockstats.StockDataFrame.retype(df)

        indicators = {}

        # KDJ
        try:
            indicators['kdjk'] = stockStat['kdjk'].values
            indicators['kdjd'] = stockStat['kdjd'].values
            indicators['kdjj'] = stockStat['kdjj'].values
        except Exception as e:
            logging.warning(f"KDJ计算失败: {e}")

        # MACD
        try:
            indicators['macd'] = stockStat['macd'].values
            indicators['macds'] = stockStat['macds'].values
            indicators['macdh'] = stockStat['macdh'].values
        except Exception as e:
            logging.warning(f"MACD计算失败: {e}")

        # BOLL
        try:
            indicators['boll'] = stockStat['boll'].values
            indicators['boll_ub'] = stockStat['boll_ub'].values
            indicators['boll_lb'] = stockStat['boll_lb'].values
        except Exception as e:
            logging.warning(f"BOLL计算失败: {e}")

        # RSI
        try:
            indicators['rsi_6'] = stockStat['rsi_6'].values
            indicators['rsi_12'] = stockStat['rsi_12'].values
        except Exception as e:
            logging.warning(f"RSI计算失败: {e}")

        # CCI
        try:
            indicators['cci'] = stockStat['cci'].values
            indicators['cci_20'] = stockStat['cci_20'].values
        except Exception as e:
            logging.warning(f"CCI计算失败: {e}")

        # WR
        try:
            indicators['wr_10'] = stockStat['wr_10'].values
            indicators['wr_6'] = stockStat['wr_6'].values
        except Exception as e:
            logging.warning(f"WR计算失败: {e}")

        # ATR
        try:
            indicators['atr'] = stockStat['atr'].values
        except Exception as e:
            logging.warning(f"ATR计算失败: {e}")

        # TRIX
        try:
            indicators['trix'] = stockStat['trix'].values
            indicators['trix_9_sma'] = stockStat['trix_9_sma'].values
        except Exception as e:
            logging.warning(f"TRIX计算失败: {e}")

        # DMA
        try:
            indicators['dma'] = stockStat['dma'].values
        except Exception as e:
            logging.warning(f"DMA计算失败: {e}")

        # DMI
        try:
            indicators['pdi'] = stockStat['pdi'].values
            indicators['mdi'] = stockStat['mdi'].values
            indicators['adx'] = stockStat['adx'].values
        except Exception as e:
            logging.warning(f"DMI计算失败: {e}")

        # ADXR
        try:
            indicators['adxr'] = stockStat['adxr'].values
        except Exception as e:
            logging.warning(f"ADXR计算失败: {e}")

        # VR
        try:
            indicators['vr'] = stockStat['vr'].values
        except Exception as e:
            logging.warning(f"VR计算失败: {e}")

        # PPO
        try:
            indicators['ppo'] = stockStat['ppo'].values
            indicators['ppos'] = stockStat['ppos'].values
            indicators['ppoh'] = stockStat['ppoh'].values
        except Exception as e:
            logging.warning(f"PPO计算失败: {e}")

        # CR
        try:
            indicators['cr'] = stockStat['cr'].values
            indicators['cr-ma1'] = stockStat['cr-ma1'].values
            indicators['cr-ma2'] = stockStat['cr-ma2'].values
            indicators['cr-ma3'] = stockStat['cr-ma3'].values
        except Exception as e:
            logging.warning(f"CR计算失败: {e}")

        # MFI
        try:
            indicators['mfi'] = stockStat['mfi'].values
        except Exception as e:
            logging.warning(f"MFI计算失败: {e}")

        # TEMA
        try:
            indicators['tema'] = stockStat['tema'].values
        except Exception as e:
            logging.warning(f"TEMA计算失败: {e}")

        # KAMA
        try:
            indicators['kama'] = stockStat['kama'].values
        except Exception as e:
            logging.warning(f"KAMA计算失败: {e}")

        return indicators
    except Exception as e:
        logging.error(f"指标计算失败: {e}")
        return {}


def calculate_finta_indicators(df):
    """使用finta计算额外指标"""
    try:
        # 重命名列以适应finta
        df_finta = df.copy()
        df_finta.columns = [c.lower() for c in df_finta.columns]

        indicators = {}

        # RSI
        try:
            indicators['rsi_14'] = TA.RSI(df_finta, period=14).values
        except Exception as e:
            logging.warning(f"finta RSI失败: {e}")

        # SMA
        try:
            indicators['sma_20'] = TA.SMA(df_finta, period=20).values
            indicators['sma_60'] = TA.SMA(df_finta, period=60).values
        except Exception as e:
            logging.warning(f"finta SMA失败: {e}")

        # EMA
        try:
            indicators['ema_12'] = TA.EMA(df_finta, period=12).values
            indicators['ema_26'] = TA.EMA(df_finta, period=26).values
        except Exception as e:
            logging.warning(f"finta EMA失败: {e}")

        # ATR
        try:
            indicators['atr_14'] = TA.ATR(df_finta, period=14).values
        except Exception as e:
            logging.warning(f"finta ATR失败: {e}")

        # ADX
        try:
            indicators['adx_14'] = TA.ADX(df_finta, period=14).values
        except Exception as e:
            logging.warning(f"finta ADX失败: {e}")

        # OBV
        try:
            indicators['obv'] = TA.OBV(df_finta).values
        except Exception as e:
            logging.warning(f"finta OBV失败: {e}")

        return indicators
    except Exception as e:
        logging.error(f"finta指标计算失败: {e}")
        return {}


class IndicatorsHandler(BaseHandler):
    """获取单只股票的技术指标图表"""

    def initialize(self):
        self.data_dir = str(get_historical_dir())

    def get(self, code):
        """返回Bokeh图表嵌入代码"""
        # 验证股票代码格式，防止路径遍历
        if not _validate_stock_code(code):
            self.write(json.dumps({'code': 400, 'message': '无效的股票代码', 'data': None}))
            return

        try:
            # 获取数据更新时间用于缓存验证
            data_update_time = None
            try:
                with open(os.path.join(self.data_dir, f"{code}.json"), 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    data_update_time = content.get('update_date', '')
                    stock_name = content.get('name', code)
            except:
                pass

            # 检查缓存
            if _is_cache_valid(code, data_update_time):
                cached = _load_chart_cache(code)
                if cached:
                    logging.info(f"图表缓存命中: {code}")
                    self.write(json.dumps({
                        'code': 0,
                        'message': 'success',
                        'data': cached,
                        'cached': True
                    }))
                    return

            # 加载数据
            df = load_stock_historical(code, self.data_dir)
            if df is None:
                self.write(json.dumps({'code': 404, 'message': '股票数据不存在', 'data': None}))
                return

            # 计算最近300天数据
            df = df.tail(300)

            # 获取股票名称
            stock_name = code
            try:
                with open(os.path.join(self.data_dir, f"{code}.json"), 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    stock_name = content.get('name', code)
            except:
                pass

            # 计算指标
            indicators = calculate_indicators(df)
            finta_indicators = calculate_finta_indicators(df)

            # 生成K线+成交量图表
            charts = []

            # 1. K线图
            p_candle = figure(
                width=1400, height=400,
                x_axis_type="datetime",
                toolbar_location="above",
                title=f"{stock_name} ({code})"
            )
            p_candle.title.text_font_size = "14pt"
            p_candle.xaxis.formatter = DatetimeTickFormatter(
                days="%Y-%m-%d"
            )

            # 准备数据
            dates = df.index.tolist()
            opens = df['open'].tolist()
            closes = df['close'].tolist()
            highs = df['high'].tolist()
            lows = df['low'].tolist()

            # 绘制K线（使用日线）
            for i in range(len(dates)):
                # 涨跌颜色：红涨绿跌（中国A股标准）
                if closes[i] >= opens[i]:
                    fill_color = '#EE0000'  # 红色上涨
                    line_color = '#EE0000'
                else:
                    fill_color = '#00AA00'  # 绿色下跌
                    line_color = '#00AA00'

                d = dates[i]
                body_width = pd.Timedelta(days=0.3)

                # 绘制影线（上下影线）：从低点到高点
                p_candle.line(
                    [d, d], [lows[i], highs[i]],
                    line_color=line_color, line_width=1
                )
                # 绘制蜡烛体
                p_candle.quad(
                    left=d - body_width,
                    right=d + body_width,
                    top=max(opens[i], closes[i]),
                    bottom=min(opens[i], closes[i]),
                    fill_color=fill_color,
                    line_color=line_color, line_width=0.5
                )

            charts.append(p_candle)

            # 2. 成交量
            p_vol = figure(
                width=1400, height=100,
                x_axis_type="datetime",
                toolbar_location="above"
            )
            p_vol.xaxis.formatter = DatetimeTickFormatter(
                days="%Y-%m-%d"
            )
            p_vol.vbar(
                df.index, 0.5, df['volume'] * 0.0001,
                fill_color=['#EE0000' if df['close'].iloc[i] >= df['open'].iloc[i] else '#00AA00'
                           for i in range(len(df))]
            )
            charts.append(p_vol)

            # 3. 按指标配置生成图表（只显示前6个常用指标以提升性能）
            # KDJ, MACD, BOLL, RSI, CCI, WR 是最常用的指标
            for config in INDICATORS_CONFIG[:6]:
                chart_lines = []
                for idx, line_key in enumerate(config['lines']):
                    if line_key in indicators and len(indicators[line_key]) > 0:
                        chart_lines.append((line_key, config['labels'][idx] if idx < len(config['labels']) else line_key))

                if not chart_lines:
                    continue

                p = figure(
                    width=1400, height=120,
                    x_axis_type="datetime",
                    toolbar_location="above"
                )
                p.xaxis.formatter = DatetimeTickFormatter(
                    days="%Y-%m-%d"
                )

                dates = df.index.values
                for i, (line_key, label) in enumerate(chart_lines):
                    if line_key in indicators:
                        p.line(
                            dates,
                            _clean_nan(indicators[line_key]),
                            color=config['colors'][i % len(config['colors'])],
                            legend_label=label,
                            line_width=1.5
                        )

                p.legend.location = "top_left"
                p.legend.click_policy = "hide"
                charts.append(p)

            # 生成嵌入代码
            gp = gridplot([[c] for c in charts], toolbar_location="above")
            script, div = components(gp)

            chart_data = {
                'script': script,
                'div': div,
                'indicators': {k: _clean_nan(v).tolist()[-20:]
                              for k, v in {**indicators, **finta_indicators}.items()},
                'dates': df.index.strftime('%Y-%m-%d').tolist()[-20:],
                'close_prices': df['close'].values[-20:].tolist()
            }

            # 保存缓存（异步进行，不阻塞响应）
            _save_chart_cache(code, data_update_time, chart_data)

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': chart_data,
                'cached': False
            }))

        except Exception as e:
            logging.error(f"指标图表生成失败: {e}")
            logging.debug(traceback.format_exc())
            self.write(json.dumps({'code': 500, 'message': f'生成失败: {str(e)}', 'data': None}))


class IndicatorListHandler(BaseHandler):
    """获取支持的指标列表"""

    def get(self):
        self.write(json.dumps({
            'code': 0,
            'message': 'success',
            'data': INDICATORS_CONFIG
        }))


def _validate_stock_code(code):
    """验证股票代码格式，防止路径遍历攻击"""
    # A股股票代码格式：6位数字
    pattern = r'^\d{6}$'
    if re.match(pattern, code):
        return True
    return False


def _clean_nan(arr):
    """清理NaN和Inf值"""
    arr = np.array(arr, dtype=float)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return arr
