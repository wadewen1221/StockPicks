#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
早间资讯任务 - 每日早上7点更新资讯
使用新浪财经数据源获取指数、板块和新闻
"""

import os
import sys
import logging
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import get_data_dir

logger = logging.getLogger(__name__)


def run_news_update():
    """
    更新早间资讯
    获取上证指数、深证成指、热门板块、财经新闻摘要等资讯
    """
    try:
        import requests

        logger.info("开始更新早间资讯...")

        news_data = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hot_sectors': [],
            'important_news': []
        }

        # 从新浪获取热门板块
        try:
            headers = {
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(
                'https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php?param=class',
                headers=headers,
                timeout=10
            )
            r.encoding = 'gb18030'

            # 解析板块数据
            text = r.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                data = json.loads(json_str)

                sectors = []
                for key, val in data.items():
                    parts = val.split(',')
                    name = parts[1] if len(parts) > 1 else ''
                    change = float(parts[4]) if len(parts) > 4 else 0
                    if name:
                        sectors.append({'name': name, 'change': round(change, 2)})

                # 按涨跌幅排序，取前10
                sectors.sort(key=lambda x: x['change'], reverse=True)
                news_data['hot_sectors'] = sectors[:10]

                logger.info(f"获取到 {len(sectors)} 个板块, 取前10热门")

        except Exception as e:
            logger.warning(f"获取热门板块失败: {e}")

        # 从新浪获取财经新闻
        try:
            headers = {
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(
                'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=10&page=1&r=0.5',
                headers=headers,
                timeout=10
            )
            data = r.json()

            news_list = []
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:10]:
                    title = item.get('title', '')
                    intro = item.get('intro', '')
                    url = item.get('url', '') or item.get('wapurl', '')
                    ctime = item.get('ctime', '')

                    # 转换时间戳
                    news_time = ''
                    if ctime:
                        try:
                            dt = datetime.fromtimestamp(int(ctime))
                            news_time = dt.strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            pass

                    if title and intro:
                        news_list.append({
                            'title': title,
                            'content': intro,
                            'time': news_time,
                            'source': '新浪财经',
                            'url': url
                        })

            news_data['important_news'] = news_list
            logger.info(f"获取到 {len(news_list)} 条财经新闻")

        except Exception as e:
            logger.warning(f"获取新闻失败: {e}")

        # 保存资讯数据
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        news_file = os.path.join(data_dir, 'news_cache.json')
        with open(news_file, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)

        news_count = len(news_data.get('important_news', []))
        sectors_count = len(news_data.get('hot_sectors', []))
        logger.info(f"早间资讯更新完成: 板块 {sectors_count} 个, 新闻 {news_count} 条")

    except Exception as e:
        logger.error(f"早间资讯更新失败: {e}")
        raise


if __name__ == '__main__':
    run_news_update()
