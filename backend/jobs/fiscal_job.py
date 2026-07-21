#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
季度财务数据下载任务 V2

功能：
  - 主源：baostock（稳定免费）
  - 兜底：akshare（覆盖更全）
  - 范围：所有 A 股（5000+）
  - 触发：5/9/11 月 10 号 02:00（每年 3 次）
    * 5 月：年报 + 一季报补全
    * 9 月：半年报补全
    * 11 月：三季报补全

设计要点：
  - 只下载缺失的 report_date（不重复）
  - 文件锁防并发写
  - 复用 selector/fiscal.py 的 FiscalDataFetcher 数据格式
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# 直接复用 selector/fiscal.py 的路径解析（已支持 STOCK_PICKS_FISCAL 环境变量 + 老项目兼容）
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from selector.fiscal import get_fiscal_data_dir  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

FISCAL_DIR: Path = get_fiscal_data_dir()
FISCAL_DIR.mkdir(parents=True, exist_ok=True)

# 历史数据目录（用于获取股票代码列表 + 名称）
HISTORICAL_DIR: Path = Path(os.environ.get(
    "STOCK_PICKS_DATA",
    str(Path(__file__).parent.parent.parent / "data" / "historical")
))

# 并发控制
WORKERS = 20            # 股票并发数
INNER_WORKERS = 50      # 单股票内部季度并发数（baostock 每线程独立连接）
FILE_LOCK_TIMEOUT = 30  # 文件锁超时秒数

# 线程本地 baostock 连接
_tls = threading.local()


# ============================================================
# 季度日期生成
# ============================================================

# A 股财报披露季度及对应截止日
QUARTER_END_DATES = {
    1: "03-31",   # 一季报
    2: "06-30",   # 半年报
    3: "09-30",   # 三季报
    4: "12-31",   # 年报
}


def get_target_quarters(current_date: Optional[datetime] = None) -> List[Tuple[int, int]]:
    """根据当前日期返回本次下载应补的 (year, quarter) 列表

    规则：
      - 5 月 10 号: 触发当年的 (year, 1) 一季报 + 上年的 (year-1, 4) 年报
      - 9 月 10 号: 触发当年的 (year, 2) 半年报
      - 11 月 10 号: 触发当年的 (year, 3) 三季报
      - 其他月份（手动调用）：返回最近一个未完成披露的季度
    """
    now = current_date or datetime.now()
    month = now.month
    year = now.year

    if month == 5:
        return [(year, 1), (year - 1, 4)]
    elif month == 9:
        return [(year, 2)]
    elif month == 11:
        return [(year, 3)]
    else:
        # 手动调用兜底：返回上一季度
        last_q = ((month - 1) // 3) or 4
        if last_q == 4:
            return [(year - 1, 4)]
        return [(year, last_q)]


def _fmt_date(year: int, quarter: int) -> str:
    """(year, quarter) → 'YYYY-MM-DD'"""
    return f"{year}-{QUARTER_END_DATES[quarter]}"


# ============================================================
# baostock 数据源
# ============================================================

def _baocode(code: str) -> str:
    """A 股代码 → baostock 格式（sh/sz/bj）"""
    if code[0] in "569":
        return "sh." + code
    elif code[0] in "02":
        return "sz." + code
    elif code.startswith("8") or code.startswith("4"):
        return "bj." + code
    return "sz." + code


def _bs():
    """线程本地 baostock 连接（每线程独立 login）"""
    if not hasattr(_tls, "bs"):
        import baostock as bs
        bs.login()
        _tls.bs = bs
    return _tls.bs


def _query_bs(code: str, year: int, quarter: int, tbl: str) -> Dict[str, dict]:
    """baostock 单表查询，返回 {statDate: row}"""
    bs = _bs()
    fn_map = {
        "profit": bs.query_profit_data,
        "balance": bs.query_balance_data,
        "dupont": bs.query_dupont_data,
    }
    fn = fn_map[tbl]
    rs = fn(code=code, year=str(year), quarter=str(quarter))
    rows = {}
    while rs.next():
        r = dict(zip(rs.fields, rs.get_row_data()))
        rows[r.get("statDate", "")] = r
    return rows


def _parse_bs_records(
    tbl_rows: Dict[Tuple[int, int], Dict[str, Dict[str, dict]]],
    year: int,
    quarter: int,
) -> Optional[dict]:
    """把 baostock 三表合并成单条 fiscal 记录

    Args:
        tbl_rows: {(year, quarter): {tbl_name: {statDate: row}}}
        year, quarter: 当前处理的季度
    """
    rp = _fmt_date(year, quarter)
    yq_tables = tbl_rows.get((year, quarter), {})
    prows = yq_tables.get("profit", {}).get(rp)
    if not prows:
        return None

    bdata = yq_tables.get("balance", {}).get(rp, {})
    drows = yq_tables.get("dupont", {}).get(rp, {})

    def _f(v):
        if not v:
            return None
        try:
            return round(float(v), 4)
        except (ValueError, TypeError):
            return None

    net_profit = _f(prows.get("netProfit"))
    mb_revenue = _f(prows.get("MBRevenue"))
    total_share = _f(prows.get("totalShare"))
    liqa_share = _f(prows.get("liqaShare"))
    debt_ratio = _f(bdata.get("liabilityToAsset"))

    total_rev = round(mb_revenue * 1e6, 4) if mb_revenue else None

    naps = None
    if net_profit and total_share:
        try:
            if total_share > 0:
                naps = round(net_profit / total_share, 4)
        except Exception:
            pass

    rec = {
        "report_date": rp,
        "year": year,
        "period": QUARTER_END_DATES[quarter],
        "营业总收入": total_rev,
        "归母净利润": net_profit,
        "每股净资产": naps,
        "资产负债率": round(debt_ratio * 100, 4) if debt_ratio else None,
        "总股本": _f(total_share),
        "流通股本": _f(liqa_share),
    }
    return {k: v for k, v in rec.items() if v is not None}


def fetch_from_baostock(
    code: str,
    targets: List[Tuple[int, int]],
) -> Dict[str, dict]:
    """从 baostock 拉一只股票的多个季度数据，返回 {report_date: record}"""
    bcode = _baocode(code)
    records: Dict[str, dict] = {}

    # 每只股票内部每季度三表并发
    with ThreadPoolExecutor(max_workers=INNER_WORKERS) as ex:
        futs = {}
        for y, q in targets:
            for tbl in ("profit", "balance", "dupont"):
                futs[ex.submit(_query_bs, bcode, y, q, tbl)] = (y, q, tbl)

        # {(year, quarter, tbl): {statDate: row}}
        tbl_rows: Dict[Tuple[int, int, str], Dict[str, dict]] = {}
        for fu in as_completed(futs):
            try:
                rows = fu.result()
                tbl_rows[futs[fu]] = rows
            except Exception as e:
                logger.debug(f"baostock {code} {futs[fu]} 异常: {e}")

    # 按 (year, quarter) 合并三表
    for y, q in targets:
        # 重组为 {(year, quarter): {tbl: {date: row}}}
        # _parse_bs_records 只关心三个表，需传入 {(y, q): {"profit": {}, "balance": {}, "dupont": {}}}
        yq_tables: Dict[Tuple[int, int], Dict[str, Dict[str, dict]]] = {}
        for (yy, qq, tbl), rows in tbl_rows.items():
            if (yy, qq) == (y, q):
                yq_tables.setdefault((y, q), {})[tbl] = rows

        rec = _parse_bs_records(yq_tables, y, q)
        if rec:
            records[rec["report_date"]] = rec

    return records


# ============================================================
# akshare 兜底（老板 7 项财务指标全覆盖）
# ============================================================

# akshare 抽象指标接口 -> 老板 7 项字段映射
# 来源：ak.stock_financial_abstract(symbol=code) 返回 DataFrame
#   columns: ['选项', '指标', 'YYYYMMDD', ...] (所有季度作为列)
AKSHARE_ABSTRACT_MAP = {
    "营业总收入": ("常用指标", "营业总收入"),
    "归母净利润": ("常用指标", "归母净利润"),
    "扣非净利润": ("常用指标", "扣非净利润"),  # 备用，实测 abstract 中未必含
    "每股净资产": ("每股指标", "每股净资产"),
    "资产负债率": ("财务风险", "资产负债率"),
    # 总股本/流通股本 走 balance 接口
    # 扣非净利润 备选走 stock_profit_sheet_by_report_em 的 DEDUCT_PARENT_NETPROFIT
}


def fetch_from_akshare(
    code: str,
    targets: List[Tuple[int, int]],
) -> Dict[str, dict]:
    """从 akshare 拉指定季度的财务数据（兜底数据源）

    两个接口：
      1. stock_financial_abstract - 一次返回所有季度，拿 5 个常用指标
      2. stock_balance_sheet_by_report_em - 拿 SHARE_CAPITAL (总股本)
    流通股本：akshare 无直接接口，留空（依赖 baostock 或后续接其他数据源）
    """
    try:
        import akshare as ak
    except ImportError:
        logger.debug("akshare 未安装，跳过")
        return {}

    target_dates = {_fmt_date(y, q) for y, q in targets}
    records: Dict[str, dict] = {}

    # ---- 接口 1: stock_financial_abstract ----
    # akshare 抽象指标中日期列格式: '20251231'
    target_date_compact = {
        _fmt_date(y, q).replace("-", "") for y, q in targets
    }

    try:
        df_abstract = ak.stock_financial_abstract(symbol=code)
    except Exception as e:
        logger.debug(f"akshare abstract {code} 异常: {e}")
        df_abstract = None

    if df_abstract is not None and not df_abstract.empty:
        # 为每个目标季度收集数据
        per_quarter: Dict[str, dict] = {d: {} for d in target_dates}

        for field_name, (expected_opt, indicator) in AKSHARE_ABSTRACT_MAP.items():
            rows = df_abstract[df_abstract["指标"] == indicator]
            if rows.empty:
                continue
            row = rows.iloc[0]
            for dc in target_date_compact:
                if dc not in df_abstract.columns:
                    continue
                v = row.get(dc)
                if v is None or (isinstance(v, float) and v != v):  # NaN
                    continue
                # 转回标准日期格式
                rp = f"{dc[:4]}-{dc[4:6]}-{dc[6:8]}"
                if rp in per_quarter:
                    try:
                        per_quarter[rp][field_name] = round(float(v), 4)
                    except (ValueError, TypeError):
                        pass

        # ---- 接口 2: stock_balance_sheet_by_report_em 拿总股本 ----
        try:
            market_prefix = (
                "sh" if code[0] in "569"
                else "sz" if code[0] in "02"
                else "bj"
            )
            df_bs = ak.stock_balance_sheet_by_report_em(
                symbol=f"{market_prefix}{code}"
            )
            if df_bs is not None and not df_bs.empty and "SHARE_CAPITAL" in df_bs.columns:
                # 按 REPORT_DATE 匹配
                for _, row in df_bs.iterrows():
                    rd = row.get("REPORT_DATE")
                    if rd is None:
                        continue
                    # datetime -> 'YYYY-MM-DD'
                    if hasattr(rd, "strftime"):
                        rd_str = rd.strftime("%Y-%m-%d")
                    else:
                        rd_str = str(rd)[:10]
                    if rd_str in per_quarter:
                        sc = row.get("SHARE_CAPITAL")
                        if sc is not None and not (isinstance(sc, float) and sc != sc):
                            try:
                                per_quarter[rd_str]["总股本"] = round(float(sc), 0)
                            except (ValueError, TypeError):
                                pass
        except Exception as e:
            logger.debug(f"akshare balance {code} 异常: {e}")

        # ---- 接口 3: stock_profit_sheet_by_report_em 补扣非净利润 ----
        # abstract 表中未必含扣非净利润，profit_sheet 一定有 DEDUCT_PARENT_NETPROFIT
        if any("扣非净利润" not in r for r in per_quarter.values()):
            try:
                market_prefix = (
                    "sh" if code[0] in "569"
                    else "sz" if code[0] in "02"
                    else "bj"
                )
                df_ps = ak.stock_profit_sheet_by_report_em(
                    symbol=f"{market_prefix}{code}"
                )
                if df_ps is not None and not df_ps.empty and "DEDUCT_PARENT_NETPROFIT" in df_ps.columns:
                    for _, row in df_ps.iterrows():
                        rd = row.get("REPORT_DATE")
                        if rd is None:
                            continue
                        rd_str = rd.strftime("%Y-%m-%d") if hasattr(rd, "strftime") else str(rd)[:10]
                        if rd_str in per_quarter and "扣非净利润" not in per_quarter[rd_str]:
                            v = row.get("DEDUCT_PARENT_NETPROFIT")
                            if v is not None and not (isinstance(v, float) and v != v):
                                try:
                                    per_quarter[rd_str]["扣非净利润"] = round(float(v), 4)
                                except (ValueError, TypeError):
                                    pass
            except Exception as e:
                logger.debug(f"akshare profit_sheet {code} 异常: {e}")

        # 过滤空记录
        for rp, rec in per_quarter.items():
            if rec:
                rec["report_date"] = rp
                # year/period 推断
                parts = rp.split("-")
                rec["year"] = int(parts[0])
                rec["period"] = f"{parts[1]}-{parts[2]}"
                records[rp] = rec

    return records


# ============================================================
# 文件锁 + 写入
# ============================================================

LOCK_DIR: Path = FISCAL_DIR / ".locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)


def _acquire_file_lock(lock_path: Path, timeout: int = FILE_LOCK_TIMEOUT) -> bool:
    start = time.time()
    while True:
        try:
            lock_path.touch(exist_ok=False)
            return True
        except FileExistsError:
            if time.time() - start > timeout:
                return False
            time.sleep(0.1)
        except Exception:
            if time.time() - start > timeout:
                return False
            time.sleep(0.1)


def _load_name(code: str) -> str:
    """从 historical 加载股票名称"""
    hp = HISTORICAL_DIR / f"{code}.json"
    if hp.exists():
        try:
            return json.loads(hp.read_text(encoding="utf-8")).get("name", code)
        except Exception:
            pass
    return code


def _existing_dates(code: str) -> Set[str]:
    """读取现有 fiscal 文件中已存在的 report_date 集合"""
    fp = FISCAL_DIR / f"{code}.json"
    if not fp.exists():
        return set()
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        return {q["report_date"] for q in d.get("fiscal", [])}
    except Exception:
        return set()


def _save(code: str, records: Dict[str, dict]) -> int:
    """合并写入，新增条数"""
    if not records:
        return 0
    fpath = FISCAL_DIR / f"{code}.json"
    lock_path = LOCK_DIR / f"{code}.lock"
    if not _acquire_file_lock(lock_path):
        logger.warning(f"{code} 文件锁超时，跳过")
        return 0
    try:
        if fpath.exists():
            fd = json.loads(fpath.read_text(encoding="utf-8"))
        else:
            fd = {
                "code": code,
                "name": _load_name(code),
                "update_date": "",
                "fiscal": [],
            }

        exist = {q["report_date"] for q in fd.get("fiscal", [])}
        added = 0
        for rp, rec in records.items():
            if rp not in exist:
                fd["fiscal"].append(rec)
                added += 1

        if added:
            fd["update_date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            fpath.write_text(
                json.dumps(fd, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        return added
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


# ============================================================
# 股票列表 + 主入口
# ============================================================

def get_codes() -> List[str]:
    """获取所有 A 股代码（从 historical 目录读）"""
    if not HISTORICAL_DIR.exists():
        logger.warning(f"历史数据目录不存在: {HISTORICAL_DIR}")
        return []
    return sorted(
        f.stem
        for f in HISTORICAL_DIR.iterdir()
        if f.suffix == ".json" and f.stem.isdigit()
    )


def run_fiscal_update(
    current_date: Optional[datetime] = None,
    codes: Optional[List[str]] = None,
) -> Dict[str, int]:
    """季度财务数据补全主入口

    Args:
        current_date: 当前日期（用于决定下载哪个季度；测试时传固定值）
        codes: 股票代码列表（None = 自动获取）

    Returns:
        {"total_added": N, "errors": M, "skipped": K}
    """
    targets = get_target_quarters(current_date)
    logger.info(
        f"目标季度: {[(y, q, _fmt_date(y, q)) for y, q in targets]} "
        f"数据源: baostock → akshare 兜底"
    )

    if codes is None:
        codes = get_codes()
    logger.info(f"待处理股票: {len(codes)} 只")

    stats = {"total_added": 0, "errors": 0, "skipped": 0}
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {
            ex.submit(_process_one, code, targets): code for code in codes
        }
        for i, fu in enumerate(as_completed(futures), 1):
            code = futures[fu]
            try:
                added = fu.result()
                stats["total_added"] += added
                if added == 0:
                    stats["skipped"] += 1
            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"[{i}/{len(codes)}] {code} 异常: {e}")

            if i % 100 == 0 or i == len(codes):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0
                logger.info(
                    f"进度: {i}/{len(codes)} "
                    f"新增 {stats['total_added']} "
                    f"跳过 {stats['skipped']} "
                    f"失败 {stats['errors']} "
                    f"速度 {rate:.1f} 只/s"
                )

    elapsed = time.time() - t0
    logger.info(
        f"完成: 新增 {stats['total_added']} 条, "
        f"跳过 {stats['skipped']}, 失败 {stats['errors']}, "
        f"耗时 {elapsed:.1f}s"
    )
    return stats


def _process_one(code: str, targets: List[Tuple[int, int]]) -> int:
    """单股票处理：baostock → akshare 兜底 → 写入

    字段合并策略：
      1. baostock 拉一轮（可能在某些字段上有缺失）
      2. akshare 拉一轮（覆盖全字段，作为补集/追加）
      3. 以 bs_records 为底，akshare 只补 baostock 缺失的字段
    """
    target_dates = {_fmt_date(y, q) for y, q in targets}

    # 1. baostock 主源
    bs_records = fetch_from_baostock(code, targets)
    # 仅保留本次目标季度（防御性过滤）
    bs_records = {rp: r for rp, r in bs_records.items() if rp in target_dates}

    # 2. akshare 全面补全（以“字段集”为补集，不以“季度”为单位）
    #    - 为所有目标季度调用，akshare 返回全字段
    #    - 只补 baostock 缺的字段，不覆盖 baostock 已有的字段
    aks_records = fetch_from_akshare(code, targets)
    for rp, aks_rec in aks_records.items():
        if rp not in target_dates:
            continue
        existing_rec = bs_records.get(rp, {})
        # akshare 提供但 baostock 未给的字段
        for k, v in aks_rec.items():
            if k not in existing_rec:
                existing_rec[k] = v
        bs_records.setdefault(rp, existing_rec)
        bs_records[rp] = existing_rec

    # 3. 写入
    return _save(code, bs_records)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="季度财务数据补全")
    parser.add_argument(
        "--month", type=int, default=None,
        help="模拟当前月份（1-12），用于测试不同月份触发的季度",
    )
    parser.add_argument(
        "--codes", type=str, default=None,
        help="指定股票代码列表（逗号分隔），否则全部",
    )
    args = parser.parse_args()

    current = datetime.now()
    if args.month:
        current = current.replace(month=args.month)
    code_list = args.codes.split(",") if args.codes else None

    run_fiscal_update(current_date=current, codes=code_list)