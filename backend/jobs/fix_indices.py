#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
补齐指数历史数据 - 使用新浪财经接口
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def load_existing_data(filepath):
    """加载现有数据"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_data(filepath, data):
    """保存数据"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sina_index_data(symbol, count=100):
    """
    从新浪获取指数历史数据
    symbol: 如 'sh000001', 'sz399001'
    count: 获取最近N条数据
    """
    url = f'https://quotes.sina.cn/cn/api/jsonp.php/var%20__{symbol}=/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={count}'

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        text = r.text

        # 解析JSON数据
        start = text.find('[')
        end = text.rfind(']') + 1
        if start == -1 or end == 0:
            return []

        data = json.loads(text[start:end])
        return data
    except Exception as e:
        logger.warning(f"获取 {symbol} 失败: {e}")
        return []


def fix_index(symbol, data_dir):
    """修复单个指数数据"""
    filepath = os.path.join(data_dir, f'{symbol}.json')

    # 加载现有数据
    existing_data = load_existing_data(filepath)
    if not existing_data:
        logger.warning(f"{symbol} 文件不存在或数据为空")
        return False

    existing_records = {d['date']: d for d in existing_data.get('data', [])}
    logger.info(f"{symbol} 现有 {len(existing_records)} 条记录")

    # 检查是否需要更新
    existing_dates = sorted(existing_records.keys())
    if existing_dates:
        last_date = existing_dates[-1]
        today = datetime.now().strftime('%Y-%m-%d')

        if last_date >= today:
            logger.info(f"{symbol} 数据已是最新 ({last_date})")
            return True

        logger.info(f"{symbol} 需要补齐: {last_date} -> {today}")
    else:
        logger.warning(f"{symbol} 无现有记录")
        return False

    # 从新浪获取最新数据
    # 新浪每次最多获取100条，我们需要更多天数
    all_new_data = []

    # 计算需要获取的天数（考虑到周末，每天可能没有数据）
    last_dt = datetime.strptime(last_date, '%Y-%m-%d')
    days_needed = (datetime.now() - last_dt).days + 10  # 多取几天确保够用

    # 分批获取，每批100条
    for i in range(0, days_needed, 80):  # 每次请求100条，但取80天左右的数据
        batch_data = get_sina_index_data(symbol, count=100)
        if not batch_data:
            break

        for item in batch_data:
            day = item.get('day', '')
            if day and day > last_date:
                all_new_data.append({
                    'date': day,
                    'open': float(item.get('open', 0)),
                    'close': float(item.get('close', 0)),
                    'high': float(item.get('high', 0)),
                    'low': float(item.get('low', 0)),
                    'amount': float(item.get('volume', 0))
                })

        # 如果数据不够，继续获取
        if len(batch_data) < 100:
            break

    if not all_new_data:
        logger.info(f"{symbol} 没有获取到新数据")
        return False

    # 去重并按日期排序
    seen = set()
    unique_data = []
    for item in all_new_data:
        if item['date'] not in seen:
            seen.add(item['date'])
            unique_data.append(item)
    unique_data.sort(key=lambda x: x['date'])

    # 添加新数据
    new_count = 0
    for item in unique_data:
        if item['date'] not in existing_records:
            existing_records[item['date']] = item
            new_count += 1

    if new_count == 0:
        logger.info(f"{symbol} 没有新增数据")
        return True

    # 按日期排序并保存
    sorted_records = sorted(existing_records.values(), key=lambda x: x['date'])
    existing_data['data'] = sorted_records
    existing_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_data(filepath, existing_data)

    logger.info(f"{symbol} 完成: 新增 {new_count} 条，总计 {len(sorted_records)} 条")
    return True


def main():
    import os
    from pathlib import Path

    # 跨平台兼容
    default_indices_dir = str(Path(__file__).parent.parent.parent / 'data' / 'indices')
    primary_indices_dir = Path(os.environ.get('STOCK_PICKS_INDICES', default_indices_dir))
    legacy_indices_dir = Path('D:/stock-picks/data/indices')

    if os.name == 'nt' and legacy_indices_dir.exists():
        indices_dir = str(legacy_indices_dir)
    else:
        if not primary_indices_dir.exists() and not primary_indices_dir.is_junction():
            try:
                primary_indices_dir.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                pass
        indices_dir = str(primary_indices_dir)

    indices = [
        'sh000001',  # 上证指数
        'sh000300',  # 沪深300
        'sh000688',  # 科创50
        'sz399001',  # 深证成指
        'sz399006',  # 创业板指
    ]

    logger.info("开始补齐指数历史数据...")

    for symbol in indices:
        logger.info(f"处理 {symbol}...")
        try:
            fix_index(symbol, indices_dir)
        except Exception as e:
            logger.error(f"处理 {symbol} 失败: {e}")

    logger.info("全部完成!")


if __name__ == '__main__':
    main()
