#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 calculate_rsrs() 修复 - 确认所有返回路径都有 'slope' 字段
"""
import sys
sys.path.insert(0, '.')

from stock_selector import StockSelector
import random

selector = StockSelector()

# 测试 1: 正常数据
random.seed(42)
price = 10.0
fake_data = []
for i in range(100):
    price *= 1 + random.uniform(-0.02, 0.025)
    high = price * 1.01
    low = price * 0.99
    fake_data.append({
        'date': f'2025-{i//30+1:02d}-{i%30+1:02d}',
        'open': price, 'high': high, 'low': low,
        'close': price, 'volume': 1000000
    })

result = selector.calculate_rsrs(fake_data)
print('Test 1 - 正常数据 (100 天):')
print(f'  keys: {list(result.keys())}')
print(f'  rsrs: {result.get("rsrs"):.4f}')
print(f'  slope: {result.get("slope"):.4f}')
print(f'  rsrs_ma: {result.get("rsrs_ma"):.4f}')
print(f'  signal: {result.get("signal")}')
print(f'  RESULT: {"PASS" if "slope" in result else "FAIL"}')
print()

# 测试 2: 数据不足
result_short = selector.calculate_rsrs(fake_data[:5])
print('Test 2 - 数据不足 (5 天):')
print(f'  keys: {list(result_short.keys())}')
print(f'  slope: {result_short.get("slope")}')
print(f'  RESULT: {"PASS" if "slope" in result_short else "FAIL"}')
print()

# 测试 3: 空数据
result_empty = selector.calculate_rsrs([])
print('Test 3 - 空数据:')
print(f'  keys: {list(result_empty.keys())}')
print(f'  slope: {result_empty.get("slope")}')
print(f'  RESULT: {"PASS" if "slope" in result_empty else "FAIL"}')
print()

# 测试 4: 真实股票数据（000001 平安银行）
import os
import json
from config import get_historical_dir

data_dir = str(get_historical_dir())
filepath = os.path.join(data_dir, '000001.json')
if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = json.load(f)
    hist_data = content.get('data', [])
    if len(hist_data) >= 60:
        result_real = selector.calculate_rsrs(hist_data)
        print(f'Test 4 - 真实数据 000001 ({len(hist_data)} 天):')
        print(f'  keys: {list(result_real.keys())}')
        print(f'  slope: {result_real.get("slope"):.4f}')
        print(f'  signal: {result_real.get("signal")}')
        print(f'  RESULT: {"PASS" if "slope" in result_real else "FAIL"}')
    else:
        print(f'Test 4 - 跳过: 000001 数据不足 ({len(hist_data)} 天)')
else:
    print('Test 4 - 跳过: 000001.json 不存在')

print()
print('=== 全部修复验证完成 ===')
