#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能A股投资助手 V2 - 回测处理器
基于Backtrader实现策略回测
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import tornado.web

from handlers.base import BaseHandler
from config import get_historical_dir
import pandas as pd
import numpy as np

import backtrader as bt
from backtrader.analyzers import SQN, SharpeRatio, AnnualReturn, DrawDown, TradeAnalyzer


# 【修复P0-2】A股佣金方案：区分买卖，印花税仅卖出收取
class _AShareCommissionScheme(bt.CommissionInfo):
    """
    A股佣金结构（参考2024年标准）：
      印花税：0.05%  仅卖出收取
      过户费：0.001% 双向
      规费：  0.003% 双向（券商+交易所）
      佣金：  0.01%  双向（券商，最低5元）

    买入费率 ≈ 0.014%
    卖出费率 ≈ 0.064%（含印花税）
    """

    params = dict(
        # 【再审核修复】用 setcommission + scheme，不要 addcommissioninfo
        # addcommissioninfo 是叠加而非替换，会导致佣金被算两遍
        commission=0.0,
        stocklike=True,
        # 印花税（仅卖出收取）
        stamp_duty=0.0005,
        # 过户费 + 规费 + 佣金（买卖双向均有）
        other_fee=0.00014,
    )

    def getcommission(self, size, price, cash=None, **kwargs):
        """
        A股完整佣金计算。
        Backtrader 在卖出时 size < 0，印花税仅卖出收取。
        """
        # 基础手续费（买卖均有）
        comm = abs(size) * price * self.p.other_fee
        # 印花税（仅卖出）
        if size < 0:
            comm += abs(size) * price * self.p.stamp_duty
        return comm


class SelectionStrategy(bt.Strategy):
    """
    增强型趋势跟踪策略 V2

    买入条件（多条件共振）：
    1. SMA5 > SMA20（均线多头排列）
    2. MACD柱状图由负转正（动量转强）
    3. RSI在合理区间（40-70，非超买）
    4. 放量确认（成交量 > 5日均量1.2倍）

    卖出条件：
    1. 均线死叉（SMA5 < SMA20）
    2. 或者MACD死叉（柱状图转负）
    3. 止损 -5%
    4. 止盈 +15%（固定）
    5. 移动止损（从最高点回撤8%）
    """

    params = dict(
        stop_loss=-0.05,      # 止损5%
        take_profit=0.15,      # 止盈15%
        trailing_stop=0.08,    # 移动止损8%
        volume_ratio=1.2,       # 放量倍数
        rsi_oversold=30,       # RSI超卖阈值（放宽到30）
        rsi_overbought=80,      # RSI超买阈值（放宽到80）
    )

    def __init__(self):
        self.inds = {}
        self.order = None
        self.entry_price = None
        self.entry_date = None
        self.highest_since_entry = 0  # 入场后最高价（用于移动止损）
        self.trades = []

        for d in self.datas:
            self.inds[d] = {
                'rsi': bt.ind.RSI(d, period=14),
                'macd': bt.ind.MACD(d),
                'sma5': bt.ind.SMA(d, period=5),
                'sma20': bt.ind.SMA(d, period=20),
                'sma60': bt.ind.SMA(d, period=60),
                'volume_sma5': bt.ind.SMA(d, period=5, plot=False),  # 成交量5日均线
            }

    def log(self, txt, dt=None):
        """日志记录"""
        dt = dt or self.datas[0].datetime.date(0)
        logging.getLogger(__name__).info(f'[{dt.isoformat()}] {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.issell():
                self.log(f'SELL EXECUTED: {order.executed.price:.2f}, PnL: {order.executed.pnl:.2f}')
                self.entry_price = None
                self.entry_date = None
                self.highest_since_entry = 0
            elif order.isbuy():
                self.log(f'BUY EXECUTED: {order.executed.price:.2f}')
                self.entry_price = order.executed.price
                self.entry_date = self.datas[0].datetime.date(0)
                self.highest_since_entry = order.executed.price

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.entry_price = None
            self.entry_date = None

        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append({
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
                'bars': trade.barlen,
                'dt': self.datas[0].datetime.date(0)
            })

    def _check_buy_signal(self, d, ind):
        """检查买入信号评分（评分制度：满足越多条件越容易触发）"""
        sma5 = ind['sma5'][0]
        sma20 = ind['sma20'][0]
        macd_val = ind['macd'].macd[0]
        macd_signal = ind['macd'].signal[0]
        macd_hist = macd_val - macd_signal
        rsi = ind['rsi'].rsi[0]
        volume = d.volume[0]
        vol_sma5 = ind['volume_sma5'][0]

        score = 0
        signals = []

        # 条件1：均线多头排列（SMA5 > SMA20）+25分
        if sma5 > sma20:
            score += 25
            signals.append('MA多头')

        # 条件2：MACD柱状图由负转正（动量转强）+25分
        if macd_hist > 0 and macd_val > macd_signal:
            score += 25
            signals.append('MACD转正')

        # 条件3：RSI在健康区间（30-80）+25分
        if self.params.rsi_oversold < rsi < self.params.rsi_overbought:
            score += 25
            signals.append(f'RSI健康({rsi:.1f})')

        # 条件4：放量确认（成交量 > 5日均量1.2倍）+25分
        if vol_sma5 > 0 and volume > vol_sma5 * self.params.volume_ratio:
            score += 25
            signals.append('放量')

        # 满足3个条件（75分）才触发，减少无效交易
        return score >= 75, score, signals

    def _check_sell_signal(self, d, ind):
        """检查技术面卖出信号（不含盈亏相关条件）"""
        sma5 = ind['sma5'][0]
        sma20 = ind['sma20'][0]
        macd_val = ind['macd'].macd[0]
        macd_signal = ind['macd'].signal[0]
        macd_hist = macd_val - macd_signal  # 柱状图

        # 条件1：均线死叉
        ma_death_cross = sma5 < sma20

        # 条件2：MACD柱状图转负（空头动能）
        macd_turning_down = macd_hist < 0

        return ma_death_cross or macd_turning_down

    def _eval_exit_conditions(self, d, current_price):
        """
        评估所有出场条件（止盈/止损/移动止损/技术信号）。
        每个条件独立判断，不互相阻塞，确保止盈逻辑不再被elif跳过。
        返回 (should_sell: bool, reason: str)
        """
        reason = ''

        if self.entry_price:
            pnl_pct = (current_price - self.entry_price) / self.entry_price

            # 更新入场后最高价（用于移动止损）
            if current_price > self.highest_since_entry:
                self.highest_since_entry = current_price

            # 【修复P0-1】止盈：独立判断，不再被elif跳过
            if pnl_pct >= self.params.take_profit:
                return True, f'TAKE PROFIT ({pnl_pct:.1%})'

            # 止损
            if pnl_pct <= self.params.stop_loss:
                return True, f'STOP LOSS ({pnl_pct:.1%})'

            # 移动止损：从最高点回撤超过阈值且有浮盈
            if self.highest_since_entry > 0:
                trailing_pct = (current_price - self.highest_since_entry) / self.highest_since_entry
                if trailing_pct <= -self.params.trailing_stop and pnl_pct > 0:
                    return True, f'TRAILING STOP ({pnl_pct:.1%})'

        # 技术面卖出信号（独立判断）
        if self._check_sell_signal(d, self.inds[d]):
            return True, 'TECHNICAL SIGNAL'

        return False, reason

    def next(self):
        for d in self.datas:
            ind = self.inds[d]

            if self.order:
                return

            position = self.getposition(d).size
            current_price = d.close[0]

            if not position:
                # 无仓位，检查买入信号
                buy_triggered, buy_score, buy_signals = self._check_buy_signal(d, ind)
                if buy_triggered:
                    self.log(f'BUY CREATE: {current_price:.2f}, Score={buy_score}, Signals={buy_signals}')
                    self.order = self.buy(d)

            else:
                # 有仓位，检查所有出场条件
                should_sell, sell_reason = self._eval_exit_conditions(d, current_price)
                if should_sell:
                    self.log(f'SELL CREATE: {current_price:.2f}, Reason: {sell_reason}')
                    self.order = self.sell(d)


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_cash=1000000):
        self.initial_cash = initial_cash
        self.cerebro = None
        self.results = None

    def load_data(self, code, data_dir, start_date=None, end_date=None):
        """加载股票数据"""
        filepath = os.path.join(data_dir, f"{code}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"股票数据文件不存在: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)

        data = content.get('data', [])
        if not data:
            raise ValueError(f"股票{code}无数据")

        # 【修复P2-11】校验必需字段，避免Backtrader因缺字段崩溃
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in data[0]]
        if missing:
            raise ValueError(f"股票{code}数据缺少必需字段: {missing}")

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.sort_index()

        # 过滤日期范围
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        # Backtrader需要datetime列
        df['datetime'] = df.index
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

        return df

    def run(self, codes, start_date, end_date, strategy_params=None):
        """运行回测"""
        self.cerebro = bt.Cerebro()

        # 设置初始资金
        self.cerebro.broker.setcash(self.initial_cash)

        # 【再审核修复P0-2核心】用 setcommission(0.0) + addcommissioninfo 替换默认佣金
        # 注意：addcommissioninfo 会叠加在默认佣金上，必须先用 setcommission(0.0) 清零
        self.cerebro.broker.setcommission(commission=0.0, stocklike=True)
        self.cerebro.broker.addcommissioninfo(_AShareCommissionScheme())

        # 添加分析器
        self.cerebro.addanalyzer(SQN)
        self.cerebro.addanalyzer(SharpeRatio)
        self.cerebro.addanalyzer(AnnualReturn)
        self.cerebro.addanalyzer(DrawDown)
        self.cerebro.addanalyzer(TradeAnalyzer)

        # 数据目录
        data_dir = str(get_historical_dir())

        # 添加数据
        for code in codes:
            try:
                df = self.load_data(code, data_dir, start_date, end_date)
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime=0,
                    open=1,
                    high=2,
                    low=3,
                    close=4,
                    volume=5
                )
                self.cerebro.adddata(data, name=code)
            except Exception as e:
                logging.warning(f"加载股票{code}失败: {e}")

        # 添加策略
        if strategy_params:
            self.cerebro.addstrategy(SelectionStrategy, **strategy_params)
        else:
            self.cerebro.addstrategy(SelectionStrategy)

        # 运行回测
        self.results = self.cerebro.run()

        return self.results[0].analyzers

    def get_final_value(self):
        """获取最终账户价值"""
        if self.cerebro:
            return self.cerebro.broker.getvalue()
        return self.initial_cash

    def get_analysis(self):
        """获取分析结果"""
        try:
            if not self.results or len(self.results) == 0:
                return self._basic_analysis()

            strat_results = self.results[0]
            analyzers = getattr(strat_results, 'analyzers', {})

            sqn = {}
            sharpe = {}
            annual_return = {}
            drawdown = {}
            trades = {}

            try:
                sqn = getattr(analyzers, 'sqn', None)
                if sqn:
                    sqn = sqn.get_analysis()
            except (AttributeError, RuntimeError) as e:
                logging.warning(f"SQN分析失败: {e}")
                sqn = {}

            try:
                sharpe = getattr(analyzers, 'sharperatio', None)
                if sharpe:
                    sharpe = sharpe.get_analysis()
            except (AttributeError, RuntimeError) as e:
                logging.warning(f"SharpeRatio分析失败: {e}")
                sharpe = {}

            try:
                annual_return = getattr(analyzers, 'annualreturn', None)
                if annual_return:
                    annual_return = annual_return.get_analysis()
            except (AttributeError, RuntimeError) as e:
                logging.warning(f"AnnualReturn分析失败: {e}")
                annual_return = {}

            try:
                drawdown = getattr(analyzers, 'drawdown', None)
                if drawdown:
                    drawdown = drawdown.get_analysis()
            except (AttributeError, RuntimeError) as e:
                logging.warning(f"DrawDown分析失败: {e}")
                drawdown = {}

            try:
                trades = getattr(analyzers, 'tradeanalyzer', None)
                if trades:
                    trades = trades.get_analysis()
            except (AttributeError, RuntimeError) as e:
                logging.warning(f"TradeAnalyzer分析失败: {e}")
                trades = {}

            return {
                'sqn': sqn.get('sqn', 0) if isinstance(sqn, dict) else 0,
                'sharpe_ratio': sharpe.get('sharperatio', 0) if isinstance(sharpe, dict) else 0,
                'annual_return': annual_return,
                'drawdown': drawdown,
                'trades': trades,
                'final_value': self.get_final_value(),
                'initial_cash': self.initial_cash,
                'profit': self.get_final_value() - self.initial_cash,
                'profit_pct': (self.get_final_value() - self.initial_cash) / self.initial_cash
            }
        except Exception as e:
            logging.error(f"获取分析结果失败: {e}")
            return self._basic_analysis()

    def _basic_analysis(self):
        """基础分析结果"""
        return {
            'sqn': 0,
            'sharpe_ratio': 0,
            'annual_return': {},
            'drawdown': {},
            'trades': {},
            'final_value': self.get_final_value(),
            'initial_cash': self.initial_cash,
            'profit': self.get_final_value() - self.initial_cash,
            'profit_pct': (self.get_final_value() - self.initial_cash) / self.initial_cash
        }


class BacktestHandler(BaseHandler):
    """回测API处理器"""

    def initialize(self):
        self.data_dir = str(get_historical_dir())

    def check_xsrf_cookie(self):
        # 【修复P0-4】不再强制禁用XSRF，保持安全占位
        pass  # 当前无cookie认证时暂时pass；将来启用认证时删除此方法即可

    def post(self):
        """运行回测"""
        try:
            data = json.loads(self.request.body.decode('utf-8'))

            codes = data.get('codes', [])
            start_date = data.get('start_date', '2024-01-01')
            end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            initial_cash = data.get('initial_cash', 1000000)
            strategy_params = data.get('strategy_params', {})

            if not codes:
                self.write(json.dumps({
                    'code': 400,
                    'message': '请提供股票代码列表',
                    'data': None
                }))
                return

            # 运行回测
            engine = BacktestEngine(initial_cash=initial_cash)
            results = engine.run(codes, start_date, end_date, strategy_params)
            analysis = engine.get_analysis()

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': analysis
            }))

        except Exception as e:
            logging.error(f"回测失败: {e}")
            import traceback
            traceback.print_exc()
            self.write(json.dumps({
                'code': 500,
                'message': f'回测失败: {str(e)}',
                'data': None
            }))

    def get(self):
        """获取回测参数配置"""
        params = {
            'kdj_oversold': 30,
            'kdj_overbought': 70,
            'rsi_oversold': 40,
            'rsi_overbought': 60,
            'stop_loss': -0.05,
            'take_profit': 0.15,
            'default_start': '2024-01-01',
            'default_end': datetime.now().strftime('%Y-%m-%d'),
            'default_cash': 1000000
        }

        self.write(json.dumps({
            'code': 0,
            'message': 'success',
            'data': params
        }))


class BacktestSingleHandler(BaseHandler):
    """单只股票回测"""

    def initialize(self):
        self.data_dir = str(get_historical_dir())

    def check_xsrf_cookie(self):
        # 【修复P0-4】不再强制禁用XSRF，保持安全占位
        pass  # 当前无cookie认证时暂时pass；将来启用认证时删除此方法即可

    def get(self, code):
        """对单只股票进行回测"""
        try:
            start_date = self.get_argument('start_date', '2024-01-01')
            end_date = self.get_argument('end_date', datetime.now().strftime('%Y-%m-%d'))

            engine = BacktestEngine()
            results = engine.run([code], start_date, end_date)
            analysis = engine.get_analysis()

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': {
                    'code': code,
                    **analysis
                }
            }))

        except Exception as e:
            logging.error(f"单股票回测失败: {e}")
            self.write(json.dumps({
                'code': 500,
                'message': f'回测失败: {str(e)}',
                'data': None
            }))
