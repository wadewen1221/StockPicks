#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试优化后的智能股票分析"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from handlers.selection_handler import StockAnalysisHandler
from config import get_historical_dir
import tornado.ioloop
import tornado.web

class MockHandler(StockAnalysisHandler):
    """模拟Handler用于测试"""
    def __init__(self):
        self._written_data = None

    def write(self, chunk):
        self._written_data = json.loads(chunk)

def test_analysis():
    """测试智能股票分析"""
    test_stocks = ['002685', '688110', '300263']

    print("=" * 70)
    print("优化后的智能股票分析测试")
    print("=" * 70)

    for code in test_stocks:
        print(f"\n股票: {code}")
        try:
            handler = MockHandler()
            handler.get(code)

            if handler._written_data and handler._written_data.get('code') == 0:
                data = handler._written_data['data']
                print(f"  推荐: {data.get('recommendation')}")
                print(f"  买入评分: {data.get('buy_score')}, 卖出评分: {data.get('sell_score')}")
                print(f"  趋势评分: {data.get('trend_score')}/100 ({data.get('trend_level')})")
                print(f"  市场环境: {data.get('market_env')} (置信度: {data.get('market_confidence')}%)")
                print(f"  买卖时机: {data.get('timing_signal')} - {data.get('timing_desc')}")
                print(f"  当前位置: {data.get('price_position')}")
                print(f"  描述: {data.get('recommendation_desc')[:50]}...")
            else:
                print(f"  错误: {handler._written_data}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  异常: {e}")

if __name__ == '__main__':
    test_analysis()