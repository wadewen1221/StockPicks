#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
股票筛选模块 V2 - 基于老版本1398行选股逻辑，集成RSRS和KDJ/RSI/CCI组合筛选
移植自 D:\stock-picks\backend\stock_selector.py
"""

import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict

from config import get_historical_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 基本面数据目录(从老版本兼容 / V2 自有)
import os
_DEFAULT_FISCAL = os.environ.get(
    'STOCK_PICKS_FISCAL',
    str(Path(__file__).parent.parent / 'data' / 'fiscal')
)
_LEGACY_FISCAL = Path('D:/stock-picks/data/fiscal')


def get_fiscal_data_dir() -> Path:
    """获取基本面数据目录(跨平台)"""
    primary = Path(_DEFAULT_FISCAL)

    # Windows: 兼容老项目数据(如存在)
    if os.name == 'nt' and _LEGACY_FISCAL.exists():
        return _LEGACY_FISCAL

    if not primary.exists() and not primary.is_junction():
        try:
            primary.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
    return primary


FISCAL_DATA_DIR = get_fiscal_data_dir()


class LRUCache:
    """带过期时间的LRU缓存"""

    def __init__(self, max_size=200, ttl_seconds=300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}

    def get(self, key):
        if key not in self._cache:
            return None
        # 检查过期
        if time.time() - self._timestamps.get(key, 0) > self.ttl:
            self.delete(key)
            return None
        # 移到末尾（最新使用）
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # 删除最旧的
                oldest = next(iter(self._cache))
                self.delete(oldest)
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def delete(self, key):
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]

    def clear(self):
        self._cache.clear()
        self._timestamps.clear()

    def __len__(self):
        return len(self._cache)

    def size(self):
        return len(self._cache)


class DataFetcher:
    """数据获取器 - V2版本使用本地JSON文件"""

    def __init__(self):
        self.historical_dir = get_historical_dir()
        self._stock_list_cache = None
        self._stock_list_timestamp = 0
        # 使用LRU缓存替代简单字典，控制内存使用
        self._stock_data_cache = LRUCache(max_size=200, ttl_seconds=600)

    def get_stocks_from_historical(self, preload_data=False, max_days=100):
        """从历史数据目录获取所有股票信息（带缓存）

        Args:
            preload_data: 是否预加载历史数据到缓存（耗时较长）
            max_days: 预加载时保留的最大天数
        """
        # 缓存5分钟有效
        if self._stock_list_cache is not None and not preload_data:
            if time.time() - self._stock_list_timestamp < 300:
                return self._stock_list_cache

        stocks = []
        hist_dir = Path(self.historical_dir)

        if not hist_dir.exists():
            logger.warning(f"历史数据目录不存在: {hist_dir}")
            return stocks

        logger.info("开始扫描股票列表...")
        for json_file in hist_dir.glob("*.json"):
            try:
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                data = content.get('data', [])
                if not data:
                    continue

                latest = data[-1]
                prev = data[-2] if len(data) >= 2 else latest

                # 计算涨跌幅
                latest_close = latest.get('close', 0)
                prev_close = prev.get('close', 0)
                if prev_close > 0:
                    change_pct = (latest_close - prev_close) / prev_close * 100
                else:
                    change_pct = 0

                code = content.get('code', json_file.stem)
                stocks.append({
                    '代码': code,
                    '名称': content.get('name', ''),
                    '最新价': latest_close,
                    '涨跌幅': change_pct,
                    '成交量': latest.get('volume', 0),
                    '行业': ''
                })
                # 可选：只缓存最后max_days天数据（大幅减少内存占用）
                if preload_data:
                    recent_data = data[-max_days:] if len(data) > max_days else data
                    self._stock_data_cache.set(code, recent_data)
            except Exception as e:
                logger.warning(f"读取股票文件失败 {json_file}: {e}")
                continue

        self._stock_list_cache = stocks
        self._stock_list_timestamp = time.time()
        logger.info(f"股票列表扫描完成，共 {len(stocks)} 只")
        return stocks

    def preload_candidates_history(self, stocks, min_days=60):
        """预加载候选股票的完整历史数据（并行优化）

        Args:
            stocks: 候选股票列表
            min_days: 最小需要的历史天数

        Returns:
            成功加载历史的股票数量
        """
        # 【修复P1-7】改为多线程并行预加载，避免串行阻塞
        def _load_one(stock):
            code = stock.get('代码', '')
            if not code or self._stock_data_cache.get(code) is not None:
                return False
            hist_data = self.get_stock_historical(code, max_days=min_days)
            return hist_data is not None and len(hist_data) >= min_days

        max_workers = min(16, os.cpu_count() or 8)
        loaded = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_load_one, s) for s in stocks]
            for f in as_completed(futures):
                if f.result():
                    loaded += 1
        return loaded

    def get_stock_historical(self, code, max_days=100):
        """获取单只股票的历史数据（优先从缓存获取，仅保留近期数据）"""
        import json
        # 优先使用缓存
        cached = self._stock_data_cache.get(code)
        if cached is not None:
            return cached[-max_days:] if len(cached) > max_days else cached

        filepath = Path(self.historical_dir) / f"{code}.json"

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
            data = content.get('data', [])
            # 只保留近期数据以节省内存
            recent_data = data[-max_days:] if len(data) > max_days else data
            if recent_data:
                self._stock_data_cache.set(code, recent_data)
            return recent_data
        except Exception as e:
            logger.warning(f"读取历史数据失败 {code}: {e}")
            return None

    def get_hot_sectors(self):
        """获取热门板块 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_hot_sectors() 调用但尚未实现，返回空列表")
        return []

    def get_limit_up_stocks(self):
        """获取涨停股票 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_limit_up_stocks() 调用但尚未实现，返回空列表")
        return []

    def get_hot_search_stocks(self):
        """获取热门搜索股票 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_hot_search_stocks() 调用但尚未实现，返回空列表")
        return []

    def validate_stock_data(self, code):
        """
        验证股票数据质量
        返回: (is_valid, errors)
        """
        errors = []
        filepath = Path(self.historical_dir) / f"{code}.json"

        if not filepath.exists():
            return False, ['文件不存在']

        try:
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)

            # 检查必要字段
            if 'code' not in content:
                errors.append('缺少code字段')
            if 'name' not in content:
                errors.append('缺少name字段')
            if 'data' not in content:
                errors.append('缺少data字段')
                return False, errors

            data = content['data']
            if not data:
                errors.append('历史数据为空')
                return False, errors

            # 检查数据完整性
            required_fields = ['date', 'open', 'high', 'low', 'close', 'volume']
            latest = data[-1]
            for field in required_fields:
                if field not in latest:
                    errors.append(f'最新数据缺少{field}字段')

            # 检查数据一致性
            if len(data) >= 2:
                if data[-1]['date'] == data[-2]['date']:
                    errors.append('存在重复日期数据')

            # 检查涨跌幅计算
            if 'change_pct' in latest and 'close' in latest and len(data) >= 2:
                expected_change = (latest['close'] - data[-2]['close']) / data[-2]['close'] * 100
                if abs(latest.get('change_pct', 0) - expected_change) > 0.1:
                    errors.append(f'涨跌幅可能错误: 记录值{latest.get("change_pct"):.2f}%, 计算值{expected_change:.2f}%')

            return len(errors) == 0, errors

        except json.JSONDecodeError:
            return False, ['JSON格式错误']
        except Exception as e:
            return False, [f'验证异常: {str(e)}']

    def get_data_quality_report(self, sample_size=50):
        """
        生成数据质量报告
        """
        all_stocks = self.get_stocks_from_historical(preload_data=False)
        issues = {'missing_file': [], 'invalid_json': [], 'data_errors': []}

        import random
        sample = random.sample(all_stocks, min(sample_size, len(all_stocks)))

        for s in sample:
            code = s.get('代码', '')
            is_valid, errors = self.validate_stock_data(code)
            if not is_valid:
                for err in errors:
                    if '不存在' in err:
                        issues['missing_file'].append(code)
                    elif 'JSON' in err:
                        issues['invalid_json'].append(code)
                    else:
                        issues['data_errors'].append((code, err))

        return {
            'total_checked': len(sample),
            'issues': issues,
            'quality_score': 100 - (len(issues['missing_file']) + len(issues['invalid_json']) + len(issues['data_errors'])) / len(sample) * 100
        }


class FiscalDataFetcher:
    """
    基本面数据获取器 - 从本地财务文件读取数据
    数据来源：D:\\stock-picks\\data\\fiscal\\
    """

    def __init__(self):
        self.fiscal_dir = FISCAL_DATA_DIR
        self._cache = {}  # 缓存财务数据
        self._cache_time = {}
        self.cache_validity = 3600 * 6  # 6小时缓存

    def _is_cache_valid(self, symbol):
        """检查缓存是否有效"""
        if symbol not in self._cache or symbol not in self._cache_time:
            return False
        fpath = os.path.join(self.fiscal_dir, f'{symbol}.json')
        if os.path.exists(fpath):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if file_mtime > self._cache_time[symbol]:
                return False
        return (datetime.now() - self._cache_time[symbol]).total_seconds() < self.cache_validity

    def get_fiscal_data(self, symbol):
        """
        获取股票基本面数据
        返回: dict 包含ROE、净利润增长率、资产负债率等指标
        """
        if self._is_cache_valid(symbol):
            return self._cache[symbol]

        fpath = os.path.join(self.fiscal_dir, f'{symbol}.json')
        if not os.path.exists(fpath):
            return None

        try:
            import json
            with open(fpath, 'r', encoding='utf-8') as f:
                content = json.load(f)

            fiscal_list = content.get('fiscal', [])
            if not fiscal_list:
                return None

            # 按 report_date 降序排列（最新季度排前面）
            fiscal_list = sorted(fiscal_list, key=lambda x: x.get('report_date', ''), reverse=True)
            recent = fiscal_list[:4]  # 取最近4个季度

            def get_q(qidx, field, default=None):
                """取指定季度字段值"""
                if qidx < len(recent):
                    v = recent[qidx].get(field, default)
                    if v is None or v == '' or v == 'None':
                        return default
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return default
                return default

            q0 = recent[0] if recent else {}

            # 计算 ROE = 归母净利润 / 净资产总计
            bps = get_q(0, '每股净资产')
            total_share = get_q(0, '总股本')
            net_assets = bps * total_share if bps and total_share else None
            net_profit = get_q(0, '归母净利润')
            roe = (net_profit / net_assets * 100) if (net_profit and net_assets and net_assets > 0) else None

            # 资产负债率
            debt_ratio = get_q(0, '资产负债率')

            # ST 状态
            stock_name = content.get('name', '')
            import re
            st_pattern = re.compile(r'(ST|S\*ST|\*ST|退市?|暂停上市)', re.IGNORECASE)
            is_st = bool(st_pattern.search(stock_name))

            # 计算净利润同比增长率
            # 按时间降序：q0=最新季度，q1=去年同季度
            def same_period_q1():
                if len(recent) < 2:
                    return None
                q0_period = recent[0].get('period', '')
                q0_year = recent[0].get('year', 0)
                for q in recent[1:]:
                    if q.get('period') == q0_period and q.get('year') == q0_year - 1:
                        return q
                return None

            q1 = same_period_q1()
            net_profit_yoy = None

            if q1:
                np0 = get_q(0, '归母净利润')
                np1_val = q1.get('归母净利润')
                if np1_val and isinstance(np1_val, (int, float)) and np1_val != 0:
                    np1_float = float(np1_val)
                    net_profit_yoy = (np0 - np1_float) / abs(np1_float) * 100

            data = {
                'code': symbol,
                'name': stock_name,
                'roe': roe,
                '净利润': net_profit,
                '资产负债率': debt_ratio,
                '净利润增长率': net_profit_yoy,
                'is_st': is_st,
                'source': 'local_fiscal',
            }

            self._cache[symbol] = data
            self._cache_time[symbol] = datetime.now()
            return data

        except Exception as e:
            logger.warning(f"读取财务文件失败 {symbol}: {e}")
            return None

    def check_financial(self, symbol, stock_type='mid_long'):
        """
        检查股票基本面是否通过筛选
        stock_type: 'mid_long' 中长线
        返回: {'pass': bool, 'score': int, 'reasons': list, 'warnings': list, 'details': dict}
        """
        data = self.get_fiscal_data(symbol)

        if not data:
            return {'pass': False, 'score': 0, 'reasons': ['无财务数据'], 'warnings': [], 'details': {}}

        score = 0
        reasons = []
        warnings = []

        # ST 股票直接淘汰
        if data.get('is_st'):
            return {'pass': False, 'score': 0, 'reasons': ['ST股票'], 'warnings': [], 'details': data}

        # 提取核心指标
        roe = data.get('roe')
        profit_growth = data.get('净利润增长率')

        # 中长线硬性淘汰条件
        if stock_type == 'mid_long':
            if roe is not None and roe < 0:
                return {'pass': False, 'score': 0, 'reasons': [f'ROE为负({roe:.1f}%)'], 'warnings': [], 'details': data}
            if profit_growth is not None and profit_growth < -50:
                return {'pass': False, 'score': 0, 'reasons': [f'净利润增长异常({profit_growth:.1f}%)'], 'warnings': [], 'details': data}

        # ========== 财务评分（CANSLIM风格）==========

        # 1. ROE 评分（15分）
        if roe is not None:
            if roe >= 20:
                score += 15
                reasons.append(f'ROE优秀({roe:.1f}%)')
            elif roe >= 15:
                score += 12
                reasons.append(f'ROE良好({roe:.1f}%)')
            elif roe >= 10:
                score += 8
                reasons.append(f'ROE尚可({roe:.1f}%)')
            elif roe >= 5:
                score += 4
            elif roe >= 0:
                warnings.append(f'ROE偏低({roe:.1f}%)')

        # 2. 净利润增长率（15分）
        if profit_growth is not None:
            if profit_growth >= 100:
                score += 15
                reasons.append(f'净利润爆发增长({profit_growth:.1f}%)')
            elif profit_growth >= 50:
                score += 13
                reasons.append(f'净利润高速增长({profit_growth:.1f}%)')
            elif profit_growth >= 30:
                score += 11
                reasons.append(f'净利润较快增长({profit_growth:.1f}%)')
            elif profit_growth >= 20:
                score += 9
                reasons.append(f'净利润稳健增长({profit_growth:.1f}%)')
            elif profit_growth >= 10:
                score += 6
                reasons.append(f'净利润小幅增长({profit_growth:.1f}%)')
            elif profit_growth >= 0:
                score += 3
            elif profit_growth >= -20:
                warnings.append(f'净利润小幅下滑({profit_growth:.1f}%)')
            else:
                warnings.append(f'净利润下滑较大({profit_growth:.1f}%)')

        # 3. 资产负债率（5分）
        debt_ratio = data.get('资产负债率')
        if debt_ratio is not None:
            if debt_ratio <= 30:
                score += 5
                reasons.append(f'负债率低({debt_ratio:.1f}%)')
            elif debt_ratio <= 50:
                score += 3
                reasons.append(f'负债率适中({debt_ratio:.1f}%)')
            elif debt_ratio <= 70:
                score += 1
            else:
                warnings.append(f'负债率偏高({debt_ratio:.1f}%)')

        # 中长线：总分<15硬淘汰
        if stock_type == 'mid_long' and score < 15:
            return {'pass': False, 'score': score, 'reasons': [f'财务评分过低({score}分)'], 'warnings': warnings, 'details': data}

        return {'pass': True, 'score': score, 'reasons': reasons, 'warnings': warnings, 'details': data}


class StockSelector:
    """股票筛选器 V2 - 增强版"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.fiscal_fetcher = FiscalDataFetcher()  # 基本面数据获取器
        self.evaluations = {}
        # 市场自适应阈值（根据市场波动率动态调整）
        self._market_thresholds = None
        self._thresholds_timestamp = 0

    def _get_market_thresholds(self):
        """
        获取市场自适应阈值
        根据近期市场波动率自动调整评分阈值
        """
        import time
        # 缓存5分钟
        if self._market_thresholds and time.time() - self._thresholds_timestamp < 300:
            return self._market_thresholds

        all_stocks = self.fetcher.get_stocks_from_historical(preload_data=False)
        changes = []
        for s in all_stocks[:200]:  # 采样200只
            change = float(s.get('涨跌幅', 0))
            changes.append(change)

        if changes:
            avg_change = np.mean(changes)
            volatility = np.std(changes)
        else:
            avg_change = 0
            volatility = 0.02

        # 根据波动率调整阈值
        # 高波动市场 -> 收紧阈值（减少假信号）
        # 低波动市场 -> 放宽阈值
        vol_factor = min(max(volatility / 0.03, 0.7), 1.5)  # 0.7-1.5倍调整

        self._market_thresholds = {
            'volatility': volatility,
            'avg_change': avg_change,
            'vol_factor': vol_factor,
            # RSI健康区间（自适应）
            'rsi_oversold': max(25, int(35 * vol_factor)),
            'rsi_overbought': min(80, int(75 / vol_factor)),
            # 成交量放大倍数（自适应）
            'vol_ratio_threshold': max(1.2, 1.5 / vol_factor),
            # 位置评分阈值（自适应）
            'position_low': max(0.15, 0.25 / vol_factor),
            'position_high': min(0.75, 0.65 * vol_factor),
        }
        self._thresholds_timestamp = time.time()

        logger.info(f"市场阈值更新: 波动率={volatility:.3f}, vol_factor={vol_factor:.2f}")
        return self._market_thresholds

    def calculate_technical_indicators(self, hist_data):
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

    def calculate_advanced_indicators(self, hist_data):
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

    # ========== V2 新增指标 ==========

    def calculate_rsrs(self, hist_data, period=18):
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
            # k 就是RSRS值
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

    def calculate_kdj_rsi_cci(self, hist_data):
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
            sma_tp = tp.rolling(14).mean()
            mad = tp.rolling(14).apply(lambda x: np.abs(x - x.mean()).mean())
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

    def evaluate_buy_signal(self, hist_data, stock_info):
        """
        超买超卖综合评估
        返回买卖信号
        """
        kdj_rsi_cci = self.calculate_kdj_rsi_cci(hist_data)
        rsrs = self.calculate_rsrs(hist_data)

        buy_score = 0
        sell_score = 0
        reasons = []

        # KDJ超卖信号
        if kdj_rsi_cci.get('kdj_oversold') and kdj_rsi_cci.get('kdj_golden_cross'):
            buy_score += 20
            reasons.append('KDJ低位金叉')

        # RSI超卖信号
        if kdj_rsi_cci.get('rsi_oversold'):
            buy_score += 15
            reasons.append('RSI超卖')

        if kdj_rsi_cci.get('rsi_overbought'):
            sell_score += 15
            reasons.append('RSI超买')

        # CCI超卖信号
        if kdj_rsi_cci.get('cci_oversold'):
            buy_score += 10
            reasons.append('CCI超卖')

        if kdj_rsi_cci.get('cci_overbought'):
            sell_score += 10
            reasons.append('CCI超买')

        # RSRS信号
        if rsrs.get('signal') == 'strong_up':
            buy_score += 15
            reasons.append('RSRS强势向上')
        elif rsrs.get('signal') == 'up':
            buy_score += 10

        if rsrs.get('signal') == 'strong_down':
            sell_score += 15
            reasons.append('RSRS强势向下')

        return {
            'buy_score': buy_score,
            'sell_score': sell_score,
            'reasons': reasons,
            'kdj_rsi_cci': kdj_rsi_cci,
            'rsrs': rsrs
        }

    # ========== 老版本评分方法 ==========

    def evaluate_mid_long_term(self, stock_data, hist_data):
        """评估中长线投资价值"""
        if not hist_data or len(hist_data) < 60:
            return 0, {}

        indicators = self.calculate_technical_indicators(hist_data)
        if not indicators:
            return 0, {}

        score = 0
        reasons = []

        # 1. 相对低位 (30%)
        position = indicators['position']
        if position < 0.3:
            score += 30
            reasons.append(f"相对低位({position:.1%})")
        elif position < 0.5:
            score += 15

        # 2. 均线多头排列 (20%)
        if indicators['ma5'] > indicators['ma20'] > indicators['ma60']:
            score += 20
            reasons.append("均线多头排列")
        elif indicators['ma20'] > indicators['ma60']:
            score += 10

        # 3. 成交量配合 (20%)
        if indicators['vol_ratio'] > 1.5:
            score += 20
        elif indicators['vol_ratio'] > 1.0:
            score += 10

        # 4. 波动率适中 (15%)
        volatility = indicators['volatility']
        if 0.2 < volatility < 0.5:
            score += 15
        elif volatility < 0.2:
            score += 5

        # 5. 近期表现 (15%)
        change = indicators['change_20d']
        if -10 < change < 20:
            score += 15

        return score, {'indicators': indicators, 'reasons': reasons}

    def evaluate_short_term(self, stock_data, hist_data):
        """评估超短线机会"""
        if not hist_data or len(hist_data) < 5:
            return 0, {}

        indicators = self.calculate_technical_indicators(hist_data)
        if not indicators:
            return 0, {}

        score = 0
        reasons = []

        # 1. 换手率 (25%)
        turnover = stock_data.get('turnover', 0) if isinstance(stock_data, dict) else 0
        if turnover > 15:
            score += 25
        elif turnover > 8:
            score += 15
        elif turnover > 3:
            score += 10

        # 2. 成交量放大 (25%)
        vol_ratio = indicators['vol_ratio']
        if vol_ratio > 3:
            score += 25
        elif vol_ratio > 2:
            score += 20
        elif vol_ratio > 1.5:
            score += 15

        # 3. 价格位置 (20%)
        position = indicators['position']
        if 0.6 < position < 0.9:
            score += 20
        elif position > 0.9:
            score += 10

        # 4. 短期爆发力 (20%)
        change_5d = indicators['change_5d']
        if 5 < change_5d < 15:
            score += 20
        elif change_5d > 0:
            score += 10

        return score, {'indicators': indicators, 'reasons': reasons}

    def calculate_mid_long_score_v2(self, hist_data, stock_info, indicators=None):
        """
        中长线股票优化评分模型 V2
        五大维度综合评分（满分95分）
        """
        if not hist_data or len(hist_data) < 120:
            return 0, {}

        if indicators is None:
            indicators = self.calculate_advanced_indicators(hist_data)
        if not indicators:
            return 0, {}

        # 获取市场自适应阈值
        thresholds = self._get_market_thresholds()

        score = 0
        reasons = []
        details = {}

        # === 趋势指标 (30分) ===
        macd = indicators.get('macd', {})
        macd_score = 0
        if macd.get('golden_cross') and macd.get('dif_above_zero'):
            macd_score = 15
            reasons.append('MACD零轴上方金叉')
        elif macd.get('dif_above_zero'):
            macd_score = 5
        score += macd_score
        details['macd_score'] = macd_score

        ma_score = 0
        if indicators.get('ma_bullish'):
            ma_score = 15
            reasons.append('均线多头排列')
        elif indicators.get('ma_partial_bullish'):
            ma_score = 10
        elif indicators['ma5'] > indicators['ma20']:
            ma_score = 5
        score += ma_score
        details['ma_score'] = ma_score

        # === 动量指标 (25分) - 使用自适应阈值 ===
        rsi = indicators.get('rsi', 50)
        rsi_low = thresholds['rsi_oversold']
        rsi_high = thresholds['rsi_overbought']
        rsi_score = 15 if rsi_low <= rsi <= rsi_high else 10 if rsi_low - 10 <= rsi <= rsi_high + 10 else 5
        if rsi_score >= 10:
            reasons.append(f'RSI健康区间({rsi:.1f})')
        score += rsi_score
        details['rsi_score'] = rsi_score
        details['thresholds_used'] = thresholds  # 记录使用的阈值

        change_20d = indicators.get('change_20d', 0)
        momentum_score = 10 if 0 <= change_20d <= 15 else 5 if -10 <= change_20d < 0 else 3
        score += momentum_score
        details['momentum_score'] = momentum_score

        # === 位置指标 (15分) - 使用自适应阈值 ===
        position = indicators.get('position', 0.5)
        pos_low = thresholds['position_low']
        pos_high = thresholds['position_high']
        position_score = 15 if pos_low <= position <= pos_high else 8 if pos_high < position <= pos_high + 0.15 else 5
        if position_score >= 10:
            reasons.append(f'相对低位({position:.1%})')
        score += position_score
        details['position_score'] = position_score

        # === 量价配合 (15分) - 使用自适应阈值 ===
        vol_ratio = indicators.get('vol_ratio', 1)
        vol_thresh = thresholds['vol_ratio_threshold']
        vol_score = 10 if vol_ratio > vol_thresh * 1.5 else 7 if vol_ratio > vol_thresh else 4
        score += vol_score
        details['vol_score'] = vol_score

        turnover = indicators.get('turnover', 0)
        turnover_score = 5 if turnover > 5 else 3 if turnover > 2 else 0
        score += turnover_score
        details['turnover_score'] = turnover_score

        # === 波动质量 (10分) ===
        volatility = indicators.get('volatility', 0)
        vol_quality_score = 5 if 0.15 <= volatility <= 0.4 else 3
        score += vol_quality_score
        details['volatility_score'] = vol_quality_score

        limit_up_count = indicators.get('limit_up_count_60d', 0)
        limit_gene_score = 5 if limit_up_count >= 2 else 3 if limit_up_count >= 1 else 0
        score += limit_gene_score

        return score, {
            'score': score,
            'reasons': reasons,
            'indicators': indicators,
            'details': details,
            'trend': '上升' if indicators.get('ma_bullish') else '反弹' if indicators.get('ma_partial_bullish') else '震荡'
        }

    def calculate_short_term_aggressive(self, hist_data, stock_info):
        """
        超短线激进型评分模型
        """
        if not hist_data or len(hist_data) < 60:
            return 0, {}

        df = pd.DataFrame(hist_data)
        indicators = self.calculate_advanced_indicators(hist_data)

        score = 0
        reasons = []
        details = {}

        # === 涨停基因 (35分) ===
        today_change = indicators.get('change_pct', 0)
        limit_up_score = 0

        if today_change >= 9.9:
            limit_up_score += 25
            reasons.append('今日涨停')

            consecutive = indicators.get('consecutive_limit_up', 0)
            if consecutive >= 3:
                limit_up_score += 15
                reasons.append(f'{consecutive}连板')
            elif consecutive >= 2:
                limit_up_score += 10
        score += limit_up_score
        details['limit_up_score'] = limit_up_score

        # === 情绪指标 (30分) ===
        turnover = indicators.get('turnover', 0)
        sentiment_score = 20 if turnover > 15 else 15 if turnover > 10 else 8 if turnover > 5 else 0
        score += sentiment_score
        details['sentiment_score'] = sentiment_score

        # === 资金流向 (20分) ===
        vol_ratio = indicators.get('vol_ratio', 1)
        money_score = 12 if vol_ratio > 5 else 10 if vol_ratio > 3 else 6 if vol_ratio > 2 else 3
        score += money_score
        details['money_score'] = money_score

        # === 价格位置 (15分) ===
        position = indicators.get('position', 0.5)
        position_score = 8 if 0.7 <= position <= 0.90 else 6 if 0.5 <= position < 0.7 else 3
        score += position_score
        details['position_score'] = position_score

        return score, {'score': score, 'reasons': reasons, 'indicators': indicators, 'details': details, 'type': '激进型'}

    def calculate_short_term_conservative(self, hist_data, stock_info):
        """
        超短线稳健型评分模型
        """
        if not hist_data or len(hist_data) < 60:
            return 0, {}

        indicators = self.calculate_advanced_indicators(hist_data)

        score = 0
        reasons = []
        details = {}

        # === 低位首板 (30分) ===
        position = indicators.get('position', 0.5)
        position_score = 20 if 0.3 <= position <= 0.55 else 15 if 0.2 <= position < 0.3 else 10
        if position_score >= 15:
            reasons.append(f'低位启动({position:.1%})')
        score += position_score
        details['position_score'] = position_score

        # === 量价配合 (30分) ===
        vol_ratio = indicators.get('vol_ratio', 1)
        vol_score = 20 if 1.5 <= vol_ratio <= 2.5 else 10
        score += vol_score
        details['vol_score'] = vol_score

        turnover = indicators.get('turnover', 0)
        turnover_score = 10 if 5 <= turnover <= 15 else 5
        score += turnover_score
        details['turnover_score'] = turnover_score

        # === 趋势确认 (15分) ===
        trend_score = 15 if indicators.get('ma_bullish') else 10 if indicators.get('ma_partial_bullish') else 5
        score += trend_score
        details['trend_score'] = trend_score

        return score, {'score': score, 'reasons': reasons, 'indicators': indicators, 'details': details, 'type': '稳健型'}

    # ========== 选股入口方法 ==========

    def _evaluate_mid_long_candidate(self, stock):
        """评估单只股票的中长线价值（用于并行计算）"""
        try:
            code = stock.get('代码', '')
            if not code or len(code) != 6:
                return None

            price = float(stock.get('最新价', 0))
            if price < 5 or price > 200:
                return None

            volume = float(stock.get('成交量', 0))
            if volume < 1e6:
                return None

            change_pct = float(stock.get('涨跌幅', 0))
            # 【修复P1-8】移除对大跌股票的错误过滤；
            # 超跌股（如-10%）可能是极佳的买入机会，不应在评估阶段排除
            # 注意：预筛选阶段已过滤了-8%以上的超跌股到candidates_fallen
            # 只有当候选不足时才会从中补充，且这些股票同样参与评分
            # 中长线要求：最短120交易日，获取360交易日
            hist_data = self.fetcher.get_stock_historical(code, max_days=360)
            if not hist_data or len(hist_data) < 120:
                return None

            score, details = self.calculate_mid_long_score_v2(hist_data, stock)
            if score > 0:
                return {
                    'code': code,
                    'name': stock.get('名称', ''),
                    'price': price,
                    'change_pct': change_pct,
                    'score': score,
                    'details': details
                }
        except Exception:
            pass
        return None

    def select_mid_long_term_stocks(self, limit=4):
        """筛选中长线股票（优化版：两阶段加载）"""
        logger.info("开始筛选中长线股票...")

        # 第一阶段：快速扫描股票列表（不加载历史）
        all_stocks = self.fetcher.get_stocks_from_historical(preload_data=False)
        logger.info(f"从历史数据获取到 {len(all_stocks)} 只股票")

        # 第二阶段：快速预筛选（不需要历史数据）
        # 改进：放宽条件，允许大跌股票（可能是买入机会）
        candidates = []
        candidates_fallen = []  # 单独收集大跌股票
        for s in all_stocks:
            code = s.get('代码', '')
            if not code or len(code) != 6:
                continue
            price = float(s.get('最新价', 0))
            if price < 2 or price > 500:  # 放宽价格范围
                continue
            volume = float(s.get('成交量', 0))
            if volume < 5e5:  # 降低成交量门槛
                continue
            change_pct = float(s.get('涨跌幅', 0))
            # 【修复P1-8】大跌股参与评分而非静默丢弃
            # -8%以内的正常股直接进入候选；超跌股(-8%~-15%)收集到候补池
            if change_pct < -15:
                continue  # 超过-15%可能存在基本面问题，过滤掉
            elif change_pct < -8:
                candidates_fallen.append(s)
            else:
                candidates.append(s)

        # 如果正常候选股票不足，考虑加入大跌股票（超跌反弹机会）
        if len(candidates) < limit * 2 and candidates_fallen:
            logger.info(f"候选股票较少({len(candidates)})，加入 {len(candidates_fallen[:20])} 只超跌股票")
            candidates.extend(candidates_fallen[:20])

        logger.info(f"预筛选出 {len(candidates)} 只候选股票，开始预加载历史数据...")

        # 第三阶段：预加载候选股票的历史数据（中长线要求120交易日，获取360交易日）
        self.fetcher.preload_candidates_history(candidates, min_days=120)
        logger.info(f"历史数据加载完成，缓存共 {self.fetcher._stock_data_cache.size()} 只")

        # 第四阶段：并行评估候选股票
        logger.info("开始并行评估...")
        results = []
        max_workers = min(16, os.cpu_count() or 8)

        _filter_stats = {'total': 0, 'ma_fail': 0, 'rsi_fail': 0, 'rsrs_fail': 0, 'ch20_fail': 0, 'ch5_fail': 0, 'score_fail': 0, 'pass': 0}

        def evaluate(s):
            try:
                code = s.get('代码', '')
                hist_data = self.fetcher.get_stock_historical(code, max_days=360)
                if not hist_data or len(hist_data) < 120:
                    return None

                indicators = self.calculate_advanced_indicators(hist_data)
                if not indicators:
                    return None

                # === 硬过滤条件（必须全部满足） ===
                # 1. 均线完全多头排列：SMA5 > SMA20 > SMA60
                if not (indicators['ma5'] > indicators['ma20'] > indicators['ma60']):
                    _filter_stats['ma_fail'] += 1
                    return None

                # 2. RSI 处于健康区间：40 < RSI < 70
                rsi = indicators.get('rsi', 50)
                if not (40 < rsi < 70):
                    _filter_stats['rsi_fail'] += 1
                    return None

                # 3. RSRS 斜率 > 0.95（趋势向上）
                rsrs = self.calculate_rsrs(hist_data)
                rsrs_val = rsrs.get('rsrs', 0)
                if rsrs_val <= 0.95:
                    _filter_stats['rsrs_fail'] += 1
                    return None

                # 4. 20日涨幅 > 0（中期趋势向上）
                change_20d = indicators.get('change_20d', 0)
                if change_20d <= 0:
                    _filter_stats['ch20_fail'] += 1
                    return None

                # 5. 5日涨幅 > 0（短期趋势向上）
                change_5d = indicators.get('change_5d', 0)
                if change_5d <= 0:
                    _filter_stats['ch5_fail'] += 1
                    return None

                # 通过硬过滤后，计算评分（复用已计算的indicators）
                score, details = self.calculate_mid_long_score_v2(hist_data, s, indicators)
                _filter_stats['total'] += 1
                if score > 0:
                    _filter_stats['pass'] += 1
                    return {
                        'code': code,
                        'name': s.get('名称', ''),
                        'price': float(s.get('最新价', 0)),
                        'change_pct': float(s.get('涨跌幅', 0)),
                        'score': score,
                        'details': details
                    }
                _filter_stats['score_fail'] += 1
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(evaluate, s): s for s in candidates}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # 打印过滤统计
        total = _filter_stats['total']
        logger.info(f"硬过滤统计: 总参与评分{total}只, 通过{_filter_stats['pass']}只 "
                    f"(均线{_filter_stats['ma_fail']}, RSI{_filter_stats['rsi_fail']}, "
                    f"RSRS{_filter_stats['rsrs_fail']}, 20日涨幅{_filter_stats['ch20_fail']}, "
                    f"5日涨幅{_filter_stats['ch5_fail']}, 评分{_filter_stats['score_fail']})")

        results.sort(key=lambda x: x['score'], reverse=True)

        # 第五阶段：基本面筛选（ROE/净利润增长/资产负债率/ST过滤）
        logger.info("开始基本面筛选...")
        financial_filtered = []
        fin_filter_stats = {'total': 0, 'st_fail': 0, 'roe_fail': 0, 'profit_fail': 0, 'score_fail': 0, 'pass': 0}

        for r in results:
            fin_filter_stats['total'] += 1
            code = r.get('code', '')

            # 基本面检查
            fin_result = self.fiscal_fetcher.check_financial(code, stock_type='mid_long')

            if not fin_result['pass']:
                reason = fin_result['reasons'][0] if fin_result['reasons'] else '未知原因'
                if 'ST' in reason:
                    fin_filter_stats['st_fail'] += 1
                elif 'ROE' in reason:
                    fin_filter_stats['roe_fail'] += 1
                elif '净利润' in reason:
                    fin_filter_stats['profit_fail'] += 1
                else:
                    fin_filter_stats['score_fail'] += 1
                logger.info(f"基本面淘汰: {code} - {reason}")
                continue

            fin_filter_stats['pass'] += 1
            # 附加基本面数据到结果
            r['financial_score'] = fin_result['score']
            r['financial_reasons'] = fin_result['reasons']
            r['financial_warnings'] = fin_result['warnings']
            r['financial_details'] = fin_result['details']
            financial_filtered.append(r)

        logger.info(f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
                    f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']}, "
                    f"净利润{fin_filter_stats['profit_fail']}, 评分{fin_filter_stats['score_fail']})")

        # 按基本面评分重新排序
        financial_filtered.sort(key=lambda x: (x.get('financial_score', 0), x.get('score', 0)), reverse=True)

        # 第六阶段：行业分散约束
        # 改进：同类行业股票不超过一定比例，避免集中风险
        selected = []
        industry_count = {}  # 统计已选行业数量
        max_per_industry = max(2, limit // 3)  # 每个行业最多选limit/3只，默认为2只

        for r in financial_filtered:
            if len(selected) >= limit:
                break
            # 用股票代码前3位作为伪行业分类（A股行业大致分类）
            pseudo_industry = r['code'][:3]
            count = industry_count.get(pseudo_industry, 0)
            if count < max_per_industry:
                selected.append(r)
                industry_count[pseudo_industry] = count + 1
            elif len(selected) < limit * 0.7:
                # 如果已选够70%，允许超配但标记
                r['overweight'] = True
                selected.append(r)
                industry_count[pseudo_industry] = count + 1

        logger.info(f"筛选出 {len(selected)} 只中长线股票，分布于 {len(industry_count)} 个行业")
        return selected

    def _evaluate_short_term_candidate(self, stock, strategy):
        """评估单只超短线股票（用于并行计算）"""
        try:
            code = stock.get('代码', '')
            if not code or len(code) != 6:
                return None

            # 超短线激进型/稳健型：最短60交易日，获取180交易日
            min_days = 60
            max_days = 180
            hist_data = self.fetcher.get_stock_historical(code, max_days=max_days)
            if not hist_data or len(hist_data) < min_days:
                return None

            if strategy == 'aggressive':
                score, details = self.calculate_short_term_aggressive(hist_data, stock)
            else:
                score, details = self.calculate_short_term_conservative(hist_data, stock)

            if score > 0:
                return {
                    'code': code,
                    'name': stock.get('名称', ''),
                    'price': stock.get('最新价', 0),
                    'change_pct': stock.get('涨跌幅', 0),
                    'score': score,
                    'details': details
                }
        except Exception:
            pass
        return None

    def _evaluate_rsrs_candidate(self, stock):
        """评估单只股票的RSRS买入信号（用于并行计算）"""
        try:
            code = stock.get('代码', '')
            if not code or len(code) != 6:
                return None

            # RSRS组合要求：最短120交易日，获取360交易日
            hist_data = self.fetcher.get_stock_historical(code, max_days=360)
            if not hist_data or len(hist_data) < 120:
                return None

            evaluation = self.evaluate_buy_signal(hist_data, stock)

            if evaluation['buy_score'] >= 30:
                return {
                    'code': code,
                    'name': stock.get('名称', ''),
                    'price': stock.get('最新价', 0),
                    'change_pct': stock.get('涨跌幅', 0),
                    'buy_score': evaluation['buy_score'],
                    'sell_score': evaluation['sell_score'],
                    'reasons': evaluation['reasons'],
                    'kdj_rsi_cci': evaluation['kdj_rsi_cci'],
                    'rsrs': evaluation['rsrs']
                }
        except Exception:
            pass
        return None

    def select_short_term_stocks(self, limit=3, strategy='aggressive'):
        """筛选超短线股票（并行优化版，含基本面筛选）"""
        logger.info(f"开始筛选超短线股票({strategy})...")
        all_stocks = self.fetcher.get_stocks_from_historical()

        candidates = []
        max_workers = min(32, os.cpu_count() or 8)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._evaluate_short_term_candidate, s, strategy): s for s in all_stocks}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    candidates.append(result)

        # 基本面筛选（超短线门槛较低：ROE>0、非ST）
        logger.info(f"技术面候选 {len(candidates)} 只，开始基本面筛选...")
        financial_filtered = []
        fin_filter_stats = {'total': 0, 'st_fail': 0, 'roe_fail': 0, 'pass': 0}

        for r in candidates:
            fin_filter_stats['total'] += 1
            code = r.get('code', '')

            # 基本面检查（超短线使用宽松标准：ROE>0即可通过）
            fin_result = self.fiscal_fetcher.check_financial(code, stock_type='short_term')

            # 超短线宽松逻辑：ROE为负则淘汰，ST直接淘汰
            if not fin_result['pass']:
                reason = fin_result['reasons'][0] if fin_result['reasons'] else '未知'
                if 'ST' in reason:
                    fin_filter_stats['st_fail'] += 1
                elif 'ROE' in reason:
                    fin_filter_stats['roe_fail'] += 1
                logger.info(f"基本面淘汰: {code} - {reason}")
                continue

            fin_filter_stats['pass'] += 1
            r['financial_score'] = fin_result['score']
            r['financial_reasons'] = fin_result['reasons']
            r['financial_details'] = fin_result['details']
            financial_filtered.append(r)

        logger.info(f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
                    f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']})")

        # 按基本面+技术评分排序
        financial_filtered.sort(key=lambda x: (x.get('financial_score', 0), x.get('score', 0)), reverse=True)
        selected = financial_filtered[:limit]

        logger.info(f"筛选出 {len(selected)} 只超短线股票({strategy})")
        return selected

    def select_with_rsrs_kdj_cci(self, limit=5):
        """使用RSRS和KDJ/RSI/CCI组合筛选超跌买入机会（并行优化版，含基本面筛选）"""
        logger.info("开始RSRS/KDJ/RSI/CCI组合筛选...")
        all_stocks = self.fetcher.get_stocks_from_historical()

        candidates = []
        max_workers = min(32, os.cpu_count() or 8)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._evaluate_rsrs_candidate, s): s for s in all_stocks}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    candidates.append(result)

        # 基本面筛选（RSRS策略：ST必须过滤，ROE不能为负）
        logger.info(f"技术面候选 {len(candidates)} 只，开始基本面筛选...")
        financial_filtered = []
        fin_filter_stats = {'total': 0, 'st_fail': 0, 'roe_fail': 0, 'pass': 0}

        for r in candidates:
            fin_filter_stats['total'] += 1
            code = r.get('code', '')

            fin_result = self.fiscal_fetcher.check_financial(code, stock_type='mid_long')

            # RSRS策略：ROE为负直接淘汰，ST也淘汰
            if not fin_result['pass']:
                reason = fin_result['reasons'][0] if fin_result['reasons'] else '未知'
                if 'ST' in reason:
                    fin_filter_stats['st_fail'] += 1
                elif 'ROE' in reason:
                    fin_filter_stats['roe_fail'] += 1
                logger.info(f"基本面淘汰: {code} - {reason}")
                continue

            fin_filter_stats['pass'] += 1
            r['financial_score'] = fin_result['score']
            r['financial_reasons'] = fin_result['reasons']
            r['financial_details'] = fin_result['details']
            financial_filtered.append(r)

        logger.info(f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
                    f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']})")

        financial_filtered.sort(key=lambda x: (x.get('buy_score', 0), x.get('financial_score', 0)), reverse=True)
        selected = financial_filtered[:limit]

        logger.info(f"组合筛选出 {len(selected)} 只股票")
        return selected


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
        print(f"{s['code']} {s['name']}: 买入={s['buy_score']}, 卖出={s['sell_score']}")
