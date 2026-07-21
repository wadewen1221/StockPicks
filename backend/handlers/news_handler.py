#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
早间资讯Handler - 提供早间财经资讯API
指数数据从本地数据目录读取(默认 : ./data/indices/,Windows 下兼容老项目 D:/stock-picks/data/indices)
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

from handlers.base import BaseHandler
from config import get_data_dir

logger = logging.getLogger(__name__)

# 5个主要指数配置
INDICES = [
    ('sh000001', '上证指数'),
    ('sh000300', '沪深300'),
    ('sh000688', '科创50'),
    ('sz399001', '深证成指'),
    ('sz399006', '创业板指'),
]


def _resolve_indices_dir() -> str:
    """跨平台兼容的指数目录解析"""
    default_indices = str(Path(__file__).parent.parent.parent / 'data' / 'indices')
    primary = Path(os.environ.get('STOCK_PICKS_INDICES', default_indices))
    legacy = Path('D:/stock-picks/data/indices')
    if os.name == 'nt' and legacy.exists():
        return str(legacy)
    if not primary.exists() and not primary.is_junction():
        try:
            primary.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
    return str(primary)


INDICES_DIR = _resolve_indices_dir()


def read_indices_from_file():
    """从文件读取5个主要指数的最新数据"""
    indices_data = []

    for symbol, name in INDICES:
        filepath = os.path.join(INDICES_DIR, f'{symbol}.json')
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                records = data.get('data', [])
                if records:
                    # 取最后一条记录
                    latest = records[-1]
                    prev = records[-2] if len(records) >= 2 else latest

                    close = latest.get('close', 0)
                    prev_close = prev.get('close', close)
                    change = ((close - prev_close) / prev_close * 100) if prev_close and prev_close != 0 else 0

                    indices_data.append({
                        'symbol': symbol,
                        'name': name,
                        'close': round(close, 2),
                        'change': round(change, 2)
                    })
        except Exception as e:
            logger.warning(f"读取指数 {symbol} 失败: {e}")

    return indices_data


class NewsHandler(BaseHandler):
    """早间资讯API"""

    def get(self):
        """
        返回早间资讯数据
        包含：5个指数、热门板块、财经新闻
        """
        try:
            # 读取缓存的新闻数据（板块和新闻）
            data_dir = get_data_dir()
            news_file = os.path.join(data_dir, 'news_cache.json')

            news_cache = {
                'hot_sectors': [],
                'important_news': []
            }

            if os.path.exists(news_file):
                with open(news_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    news_cache['hot_sectors'] = cache_data.get('hot_sectors', [])
                    news_cache['important_news'] = cache_data.get('important_news', [])

            # 从文件读取5个指数数据
            indices = read_indices_from_file()

            # 组装返回数据
            news_data = {
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'indices': indices,
                'hot_sectors': news_cache['hot_sectors'],
                'important_news': news_cache['important_news']
            }

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': news_data
            }, ensure_ascii=False))

        except Exception as e:
            logger.error(f"获取早间资讯失败: {e}")
            self.write(json.dumps({
                'code': 500,
                'message': f'获取早间资讯失败: {str(e)}',
                'data': None
            }, ensure_ascii=False))
