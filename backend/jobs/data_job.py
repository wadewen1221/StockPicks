#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史数据下载任务 V2 - 高效版（移植自D:/stock-picks/backend/fill_jun01_v2.py）
"""

import json
import os
import sys
import time
import threading
import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 历史数据目录 - 使用config中的路径配置
from config import get_historical_dir
HISTORICAL_DATA_DIR = str(get_historical_dir())
os.makedirs(HISTORICAL_DATA_DIR, exist_ok=True)

# 腾讯 API
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.qq.com/'}

# 高效版核心参数
FETCH_CONCURRENCY = 30
WRITE_CONCURRENCY = 20
BATCH_SUBMIT = 200
BATCH_DELAY = 0.05  # 每批提交后延迟（秒）
PER_REQUEST_DELAY = 0.01  # 每个请求后额外延迟，防止瞬时并发过高

# ---------- 全局 HTTP Session（连接复用） ----------
_session_lock = threading.Lock()
_global_session = None

def _get_session():
    """获取全局复用的 requests.Session（线程安全）"""
    global _global_session
    if _global_session is None:
        with _session_lock:
            if _global_session is None:
                s = requests.Session()
                from requests.adapters import HTTPAdapter
                # 连接池大小 = 并发数，避免连接耗尽或被限流
                adapter = HTTPAdapter(pool_connections=FETCH_CONCURRENCY,
                                     pool_maxsize=FETCH_CONCURRENCY * 2,
                                     max_retries=0)  # 重试由代码控制，不在这里
                s.mount('https://', adapter)
                s.mount('http://', adapter)
                s.headers.update(HEADERS)
                _global_session = s
    return _global_session

# 线程安全计数器
_progress_lock = threading.Lock()
_counters = {'done': 0, 'ok': 0, 'fail': 0, 'written': 0}

# 文件锁目录（防止不同进程同时写入同一文件）
LOCK_DIR = os.path.join(HISTORICAL_DATA_DIR, '.locks')
os.makedirs(LOCK_DIR, exist_ok=True)


def _acquire_file_lock(lock_path, timeout=30):
    """
    获取文件锁（跨平台实现）
    使用 O_CREAT | O_EXCL 确保原子性创建锁文件
    """
    start_time = time.time()
    while True:
        try:
            # O_CREAT | O_EXCL 确保原子性 - 如果文件存在会报错
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            # 锁已存在，等待
            if time.time() - start_time > timeout:
                return None
            time.sleep(0.1)
        except Exception:
            if time.time() - start_time > timeout:
                return None
            time.sleep(0.1)


def _release_file_lock(lock_path):
    """释放文件锁"""
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass


def _fetch_with_retry(url, timeout=8, max_retries=3, backoff_base=1.5):
    """带指数退避重试的HTTP GET（使用全局Session）"""
    session = _get_session()
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
            # 429 或 5xx 需要重试
            if r.status_code in (429, 502, 503, 504):
                wait = backoff_base ** attempt
                time.sleep(wait)
                continue
            return r
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError) as e:
            wait = backoff_base ** attempt
            time.sleep(wait)
    return None


def fetch_target_date_kline(code, target_date):
    """获取单只股票目标日期的K线数据（前复权日K），带重试"""
    if code.startswith('9'):
        sym = f'bj{code}'
    elif code.startswith(('6', '5')):
        sym = f'sh{code}'
    else:
        sym = f'sz{code}'

    url = (f'https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get'
           f'?_var=kline_dayfqk&param={sym},day,,{target_date},3,fqk')

    try:
        r = _fetch_with_retry(url, timeout=8, max_retries=3)
        if r is None or r.status_code != 200:
            return None
        text = r.text
        if '=' not in text:
            return None
        json_str = text[text.index('=') + 1:]
        data = json.loads(json_str)
        sym_data = data.get('data', {})
        if not isinstance(sym_data, dict):
            return None
        sym_info = sym_data.get(sym, {})
        if not isinstance(sym_info, dict):
            return None
        qfqday = sym_info.get('qfqday') or []
        day = sym_info.get('day') or []
        raw = qfqday if (isinstance(qfqday, list) and len(qfqday) > 0) else (day if (isinstance(day, list) and len(day) > 0) else [])
        for d in raw:
            if len(d) < 6 or d[0] != target_date:
                continue
            vol = float(d[5]) * (1 if code.startswith('688') else 100)
            return {'date': target_date, 'open': float(d[1]), 'close': float(d[2]),
                    'high': float(d[3]), 'low': float(d[4]), 'volume': vol}
    except Exception:
        return None
    return None


def write_single_date(code, kline, target_date):
    """更新单只股票单个日期（带文件锁防止并发写入）"""
    filepath = os.path.join(HISTORICAL_DATA_DIR, f'{code}.json')
    lock_path = os.path.join(LOCK_DIR, f'{code}.lock')

    try:
        # 获取文件锁
        if not _acquire_file_lock(lock_path, timeout=30):
            logger.warning(f'获取锁失败 {code}，跳过')
            return False

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['data'] = [k for k in data['data'] if k['date'] != target_date]
        data['data'].append(kline)
        data['data'].sort(key=lambda x: x['date'])
        data['update_date'] = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=False)
        return True
    except Exception as e:
        logger.error(f'写入失败 {code} ({filepath}): {e}')
        return False
    finally:
        _release_file_lock(lock_path)


def _run_single_date_update(target_date):
    """单日期更新（核心高效逻辑）"""
    global _counters
    _counters = {'done': 0, 'ok': 0, 'fail': 0, 'skip': 0, 'written': 0}

    t0 = datetime.now()
    logger.info(f'[{t0}] 启动{target_date}数据补齐（高效版）')

    # 扫描文件，检查哪些需要更新
    all_files = os.listdir(HISTORICAL_DATA_DIR)
    target_codes = [fname[:-5] for fname in all_files if fname.endswith('.json')]

    # 快速检查：跳过已有目标日期数据的股票
    codes_needs_update = []
    for fname in all_files:
        if not fname.endswith('.json'):
            continue
        code = fname[:-5]
        filepath = os.path.join(HISTORICAL_DATA_DIR, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            dates = [k['date'] for k in data.get('data', [])]
            if target_date not in dates:
                codes_needs_update.append(code)
            else:
                with _progress_lock:
                    _counters['skip'] += 1
        except:
            codes_needs_update.append(code)

    logger.info(f'总股票: {len(target_codes)} 只，已跳过: {_counters["skip"]} 只，待更新: {len(codes_needs_update)} 只')
    if not codes_needs_update:
        return

    # 第一阶段：多线程获取（只获取需要更新的）
    results = {}
    BATCH = BATCH_SUBMIT

    with ThreadPoolExecutor(max_workers=FETCH_CONCURRENCY) as ex:
        for i in range(0, len(codes_needs_update), BATCH):
            batch = codes_needs_update[i:i + BATCH]
            futures = {ex.submit(fetch_target_date_kline, code, target_date): code for code in batch}

            for future in as_completed(futures):
                code = futures[future]
                with _progress_lock:
                    _counters['done'] += 1
                result = future.result()
                if result:
                    results[code] = result
                    with _progress_lock:
                        _counters['ok'] += 1
                else:
                    with _progress_lock:
                        _counters['fail'] += 1

                done = _counters['done']
                if done % 500 == 0 or done == len(codes_needs_update):
                    elapsed = (datetime.now() - t0).total_seconds()
                    speed = done / elapsed * 60 if elapsed > 0 else 0
                    logger.info(f'  已获取{done}/{len(codes_needs_update)}  成功{_counters["ok"]}  跳过{_counters["skip"]}  速度≈{speed:.0f}只/分')
                time.sleep(PER_REQUEST_DELAY)
            time.sleep(BATCH_DELAY)

    fetch_time = (datetime.now() - t0).total_seconds()
    logger.info(f'获取完毕，耗时{fetch_time:.0f}秒，成功:{_counters["ok"]} 失败:{_counters["fail"]} 跳过:{_counters["skip"]}')

    if not results:
        logger.warning('没有获取到任何数据')
        return

    # 第二阶段：多线程写入
    t1 = datetime.now()
    written, write_fail = 0, []

    with ThreadPoolExecutor(max_workers=WRITE_CONCURRENCY) as ex:
        write_futures = {ex.submit(write_single_date, code, kline, target_date): code for code, kline in results.items()}
        for future in as_completed(write_futures):
            code = write_futures[future]
            if future.result():
                written += 1
            else:
                write_fail.append(code)
            wc = written + len(write_fail)
            if wc % 500 == 0 or wc == len(results):
                logger.info(f'  写入进度: {wc}/{len(results)}')

    write_time = (datetime.now() - t1).total_seconds()
    total_time = (datetime.now() - t0).total_seconds()
    logger.info(f'完成！总股票{len(target_codes)}只  跳过{_counters["skip"]}只  获取{len(results)}只  写入{written}只  失败{len(write_fail)}只  总耗时{total_time:.0f}秒')


def update_stocks_incremental(target_dates):
    """增量更新股票历史数据"""
    if isinstance(target_dates, str):
        target_dates = [target_dates]
    for td in target_dates:
        _run_single_date_update(td)
    return True


def _get_stock_list():
    """从历史数据目录获取股票代码列表"""
    try:
        codes = [f[:-5] for f in os.listdir(HISTORICAL_DATA_DIR) if f.endswith('.json')]
        logger.info(f'从目录获取到 {len(codes)} 只股票')
        return [{'code': c} for c in codes]
    except Exception as e:
        logger.error(f'获取股票列表失败: {e}')
        return []


def _fetch_full_history(code):
    """获取单只股票完整历史数据，带重试"""
    if code.startswith('9'):
        sym = f'bj{code}'
    elif code.startswith(('6', '5')):
        sym = f'sh{code}'
    else:
        sym = f'sz{code}'

    url = (f'https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get'
           f'?_var=kline_dayfqk&param={sym},day,,,2500,fqk')

    try:
        r = _fetch_with_retry(url, timeout=10, max_retries=3)
        if r is None or r.status_code != 200:
            return None
        text = r.text
        if '=' not in text:
            return None
        json_str = text[text.index('=') + 1:]
        data = json.loads(json_str)
        sym_data = data.get('data', {})
        if not isinstance(sym_data, dict):
            return None
        sym_info = sym_data.get(sym, {})
        if not isinstance(sym_info, dict):
            return None
        qfqday = sym_info.get('qfqday') or []
        day = sym_info.get('day') or []
        raw = qfqday if (isinstance(qfqday, list) and len(qfqday) > 0) else (day if (isinstance(day, list) and len(day) > 0) else [])
        records = []
        for d in raw:
            if len(d) < 6:
                continue
            vol = float(d[5]) * (1 if code.startswith('688') else 100)
            records.append({'date': d[0], 'open': float(d[1]), 'close': float(d[2]),
                           'high': float(d[3]), 'low': float(d[4]), 'volume': vol})
        return records if records else None
    except Exception:
        return None


def _save_full_history(code, hist_data, name=None):
    """保存完整历史数据（带文件锁防止并发写入）"""
    filepath = os.path.join(HISTORICAL_DATA_DIR, f'{code}.json')
    lock_path = os.path.join(LOCK_DIR, f'{code}.lock')

    try:
        if not _acquire_file_lock(lock_path, timeout=30):
            logger.warning(f'获取锁失败 {code}，跳过')
            return False

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'code': code, 'name': name, 'update_date': datetime.now().isoformat(),
                       'data': hist_data}, f, ensure_ascii=False, indent=False)
        return True
    except Exception as e:
        logger.error(f'写入失败 {code} ({filepath}): {e}')
        return False
    finally:
        _release_file_lock(lock_path)


def download_all_stocks(progress_callback=None):
    """全量下载所有股票历史数据"""
    global _counters
    _counters = {'done': 0, 'ok': 0, 'fail': 0}

    t0 = datetime.now()
    logger.info(f'[{t0}] 启动全量历史数据下载')

    stocks = _get_stock_list()
    if not stocks:
        logger.error('获取股票列表失败')
        return False

    to_download = [s for s in stocks if not os.path.exists(os.path.join(HISTORICAL_DATA_DIR, f"{s['code']}.json"))]
    logger.info(f'共{len(stocks)}只股票，待下载{len(to_download)}只')

    if not to_download:
        return True

    results = {}
    with ThreadPoolExecutor(max_workers=FETCH_CONCURRENCY) as ex:
        for i in range(0, len(to_download), BATCH_SUBMIT):
            batch = to_download[i:i + BATCH_SUBMIT]
            futures = {ex.submit(_fetch_full_history, s['code']): s for s in batch}
            for future in as_completed(futures):
                s = futures[future]
                code = s['code']
                name = s.get('name', code)
                with _progress_lock:
                    _counters['done'] += 1
                data = future.result()
                if data:
                    results[code] = (data, name)
                    with _progress_lock:
                        _counters['ok'] += 1
                else:
                    with _progress_lock:
                        _counters['fail'] += 1
                done = _counters['done']
                if done % 500 == 0 or done == len(to_download):
                    elapsed = (datetime.now() - t0).total_seconds()
                    speed = done / elapsed * 60 if elapsed > 0 else 0
                    logger.info(f'  已处理{done}/{len(to_download)}  成功{_counters["ok"]}  速度≈{speed:.0f}只/分')
            time.sleep(BATCH_DELAY)

    written = 0
    with ThreadPoolExecutor(max_workers=WRITE_CONCURRENCY) as ex:
        write_futures = {ex.submit(_save_full_history, code, data[0], data[1]): code for code, data in results.items()}
        for future in as_completed(write_futures):
            if future.result():
                written += 1

    total_time = (datetime.now() - t0).total_seconds()
    logger.info(f'全量下载完成！成功{written}只  耗时{total_time:.0f}秒')
    return True


def run_data_update(target_date=None):
    """更新股票历史数据"""
    try:
        logger.info('=' * 50)
        logger.info('开始更新A股历史数据...')
        logger.info('=' * 50)

        if target_date:
            if isinstance(target_date, str):
                target_date = [target_date]
            update_stocks_incremental(target_date)
        else:
            download_all_stocks()

        logger.info('历史数据更新完成！')
        return True
    except Exception as e:
        logger.error(f'历史数据更新失败: {e}')
        raise


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        run_data_update(target_date=target)
    else:
        run_data_update()
