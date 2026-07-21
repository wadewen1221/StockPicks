#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能A股投资助手 V2 - 定时任务调度器

任务安排:
- 交易日17:30: 下载历史数据
- 交易日18:30: 三步法选股 + 自动回测
- 每天07:00: 早间资讯更新
"""

import os
import sys
import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def _get_last_n_trading_days(n=5):
    """获取最近n个交易日的日期（跳过周末），按时间顺序排列（从老到新）"""
    from datetime import datetime, timedelta
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime('%Y-%m-%d'))
        d -= timedelta(days=1)
    dates.reverse()  # 翻转成 chronological order
    return dates


def _run_data_update():
    """下载历史数据任务 - 检查并补齐最近5个交易日的缺损数据"""
    trading_days = _get_last_n_trading_days(5)
    logger.info(f"[数据更新] 开始下载历史数据，检查日期: {trading_days}")

    from jobs.data_job import run_data_update
    result = run_data_update(target_date=trading_days)

    logger.info("[数据更新] 历史数据更新完成")

    # 同时更新5个主要指数数据
    _run_index_update()

    return result


def _run_index_update():
    """更新5个主要指数的历史数据"""
    import requests
    import json
    from datetime import datetime
    import os
    from pathlib import Path

    # 跨平台兼容: 主数据目录 / data/indices
    # Windows 老项目兼容: D:/stock-picks/data/indices
    _default_indices = str(Path(__file__).parent.parent / 'data' / 'indices')
    _primary_indices = Path(os.environ.get('STOCK_PICKS_INDICES', _default_indices))
    _legacy_indices = Path('D:/stock-picks/data/indices')

    if os.name == 'nt' and _legacy_indices.exists():
        INDICES_DIR = str(_legacy_indices)
    else:
        if not _primary_indices.exists() and not _primary_indices.is_junction():
            try:
                _primary_indices.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                pass
        INDICES_DIR = str(_primary_indices)

    HEADERS = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    indices = [
        ('sh000001', '上证指数'),
        ('sh000300', '沪深300'),
        ('sh000688', '科创50'),
        ('sz399001', '深证成指'),
        ('sz399006', '创业板指'),
    ]

    logger.info("[指数更新] 开始更新5个主要指数...")

    for symbol, name in indices:
        try:
            filepath = os.path.join(INDICES_DIR, f'{symbol}.json')
            if not os.path.exists(filepath):
                logger.warning(f"[指数更新] {symbol} 文件不存在，跳过")
                continue

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            existing_records = {d['date']: d for d in data.get('data', [])}
            last_date = max(existing_records.keys()) if existing_records else None

            if not last_date:
                logger.warning(f"[指数更新] {symbol} 无现有记录，跳过")
                continue

            today = datetime.now().strftime('%Y-%m-%d')
            if last_date >= today:
                logger.info(f"[指数更新] {symbol} 数据已是最新 ({last_date})")
                continue

            # 从新浪获取最新数据
            url = f'https://quotes.sina.cn/cn/api/jsonp.php/var%20__{symbol}=/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=100'
            r = requests.get(url, headers=HEADERS, timeout=10)

            text = r.text
            start = text.find('[')
            end = text.rfind(']') + 1
            if start == -1 or end == 0:
                continue

            new_data = json.loads(text[start:end])

            new_count = 0
            for item in new_data:
                day = item.get('day', '')
                if day and day > last_date and day not in existing_records:
                    existing_records[day] = {
                        'date': day,
                        'open': float(item.get('open', 0)),
                        'close': float(item.get('close', 0)),
                        'high': float(item.get('high', 0)),
                        'low': float(item.get('low', 0)),
                        'amount': float(item.get('volume', 0))
                    }
                    new_count += 1

            if new_count > 0:
                sorted_records = sorted(existing_records.values(), key=lambda x: x['date'])
                data['data'] = sorted_records
                data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"[指数更新] {symbol} 完成: 新增 {new_count} 条，总计 {len(sorted_records)} 条")
            else:
                logger.info(f"[指数更新] {symbol} 无新增数据")

        except Exception as e:
            logger.error(f"[指数更新] {symbol} 失败: {e}")

    logger.info("[指数更新] 5个主要指数更新完成")


def _run_stock_selection():
    """选股+自动回测任务"""
    try:
        logger.info("[选股回测] 开始选股...")
        from jobs.selector_job import run_stock_selection_and_backtest
        run_stock_selection_and_backtest()
        logger.info("[选股回测] 选股+回测完成")
    except Exception as e:
        logger.error(f"[选股回测] 失败: {e}")


def _run_news_update():
    """早间资讯更新任务"""
    try:
        logger.info("[资讯更新] 开始更新早间资讯...")
        from jobs.news_job import run_news_update
        run_news_update()
        logger.info("[资讯更新] 早间资讯更新完成")
    except Exception as e:
        logger.error(f"[资讯更新] 失败: {e}")


def _run_fiscal_update():
    """季度财务数据补全任务（5/9/11 月 10 号 02:00 触发）

    数据源：baostock（主）→ akshare（兜底）
    """
    logger.info("[财务更新] 开始季度财务数据补全")
    try:
        from jobs.fiscal_job import run_fiscal_update as _run
        stats = _run()
        logger.info(f"[财务更新] 完成: {stats}")
    except Exception as e:
        logger.error(f"[财务更新] 失败: {e}", exc_info=True)


def _check_and_trigger_immediate_run(scheduler):
    """如果现在是交易日且在17:30-19:00延迟期内，触发数据更新任务"""
    now = datetime.now()

    # 检查是否是交易日（周一到周五）
    if now.weekday() >= 5:
        return

    # 检查是否在17:30-19:00延迟期内（1.5小时窗口）
    # 17:30之后且19:00之前才触发
    if now.hour < 17:
        return
    if now.hour == 17 and now.minute < 30:
        return
    if now.hour >= 19:
        logger.info(f"[启动检查] 已超过19:00延迟期，今日数据更新任务已完成，不再触发")
        return

    # 直接触发更新任务（任务内部会检查每只股票每个日期，缺失就补）
    logger.info(f"[启动检查] 处于交易日17:30-19:00延迟期，触发数据更新任务")
    scheduler.modify_job('data_update', next_run_time=now)


def start_scheduler():
    """启动定时任务调度器"""
    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

    # 任务1: 交易日17:30 - 下载历史数据
    scheduler.add_job(
        _run_data_update,
        CronTrigger(hour=17, minute=30, timezone='Asia/Shanghai'),
        id='data_update',
        name='历史数据更新',
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60
    )
    logger.info("调度任务已注册: 交易日17:30 (历史数据下载)")

    # 任务2: 交易日18:30 - 选股+回测
    scheduler.add_job(
        _run_stock_selection,
        CronTrigger(hour=18, minute=30, timezone='Asia/Shanghai'),
        id='stock_selection',
        name='三步法选股+回测',
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60  # 允许最多延迟60秒执行，避免因系统负载波动导致任务被跳过
    )
    logger.info("调度任务已注册: 交易日18:30 (三步法选股+回测)")

    # 任务3: 每天07:00 - 早间资讯
    scheduler.add_job(
        _run_news_update,
        CronTrigger(hour=7, minute=0, timezone='Asia/Shanghai'),
        id='news_update',
        name='早间资讯更新',
        coalesce=True,
        max_instances=1
    )
    logger.info("调度任务已注册: 每天07:00 (早间资讯更新)")

    # 任务4: 每年 5/9/11 月 10 号 02:00 - 季度财务数据补全
    #   5月：补一季报 + 上年度年报
    #   9月：补半年报
    #   11月：补三季报
    scheduler.add_job(
        _run_fiscal_update,
        CronTrigger(month='5,9,11', day=10, hour=2, minute=0, timezone='Asia/Shanghai'),
        id='fiscal_update',
        name='季度财务数据补全',
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600  # 允许最多延迟1小时，避免深夜任务被跳过
    )
    logger.info("调度任务已注册: 每年5/9/11月10号 02:00 (季度财务数据补全)")

    # 注意: 每周日20:00周报任务已取消

    scheduler.start()
    logger.info("定时任务调度器已启动")

    # 如果现在是交易日且在17:30-19:00延迟期内，立即触发一次数据更新
    _check_and_trigger_immediate_run(scheduler)

    return scheduler


if __name__ == '__main__':
    scheduler = start_scheduler()
    try:
        while True:
            import time
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
