#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
选股主流程 - 中长线 / 超短线激进 / 超短线稳健 / RSRS 组合
所有函数都是纯函数：接收 fetcher + 参数，返回选股结果列表。

4 套策略：
  1. select_mid_long_term_stocks   - 中长线价值投资（4只）
  2. select_short_term_stocks       - 超短线（3只，激进/稳健可切换）
  3. select_with_rsrs_kdj_cci      - RSRS+KDJ组合（5只，超跌买入）
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Literal, Optional

from ._types import HistData, Indicators, MarketThresholds, StockDataList, StockPick
from .indicators import calculate_advanced_indicators, calculate_rsrs
from .scorer import (
    calculate_mid_long_score_v2,
    calculate_short_term_aggressive,
    calculate_short_term_conservative,
    evaluate_buy_signal,
)

logger = logging.getLogger(__name__)

# 类型别名
Fetcher = Any  # DataFetcher - 故意用 Any 避免循环引用
FiscalFetcher = Any  # FiscalDataFetcher
StrategyType = Literal["aggressive", "conservative"]


def _evaluate_mid_long_candidate(fetcher: Fetcher, stock: StockPick) -> Optional[StockPick]:
    """评估单只股票的中长线价值（用于并行计算）"""
    try:
        code: str = stock.get("代码", "")
        if not code or len(code) != 6:
            return None

        price: float = float(stock.get("最新价", 0))
        if price < 5 or price > 200:
            return None

        volume: float = float(stock.get("成交量", 0))
        if volume < 1e6:
            return None

        change_pct: float = float(stock.get("涨跌幅", 0))
        # 超跌股（如-10%）可能是极佳的买入机会，不应在评估阶段排除
        # 中长线要求：最短120交易日，获取360交易日
        hist_data: Optional[StockDataList] = fetcher.get_stock_historical(code, max_days=360)
        if not hist_data or len(hist_data) < 120:
            return None

        score: int
        details: Dict[str, Any]
        score, details = calculate_mid_long_score_v2(hist_data, stock)
        if score > 0:
            return {
                "code": code,
                "name": stock.get("名称", ""),
                "price": price,
                "change_pct": change_pct,
                "score": score,
                "details": details,
            }
    except Exception:
        pass
    return None


def select_mid_long_term_stocks(
    fetcher: Fetcher,
    fiscal_fetcher: FiscalFetcher,
    limit: int = 4,
    market_thresholds: Optional[MarketThresholds] = None,
) -> List[StockPick]:
    """筛选中长线股票（优化版：两阶段加载 + 并行评估 + 基本面筛选）

    Args:
        fetcher: DataFetcher 实例
        fiscal_fetcher: FiscalDataFetcher 实例
        limit: 返回股票数量（默认 4）
        market_thresholds: 市场自适应阈值（透传给 calculate_mid_long_score_v2）

    Returns:
        选股结果列表，按 (financial_score, score) 降序
    """
    logger.info("开始筛选中长线股票...")

    # 第一阶段：快速扫描股票列表（不加载历史）
    all_stocks: List[StockPick] = fetcher.get_stocks_from_historical(preload_data=False)
    logger.info(f"从历史数据获取到 {len(all_stocks)} 只股票")

    # 第二阶段：快速预筛选（不需要历史数据）
    candidates: List[StockPick] = []
    candidates_fallen: List[StockPick] = []
    for s in all_stocks:
        code: str = s.get("代码", "")
        if not code or len(code) != 6:
            continue
        price: float = float(s.get("最新价", 0))
        if price < 2 or price > 500:
            continue
        volume: float = float(s.get("成交量", 0))
        if volume < 5e5:
            continue
        change_pct: float = float(s.get("涨跌幅", 0))
        if change_pct < -15:
            continue
        elif change_pct < -8:
            candidates_fallen.append(s)
        else:
            candidates.append(s)

    if len(candidates) < limit * 2 and candidates_fallen:
        logger.info(f"候选股票较少({len(candidates)})，加入 {len(candidates_fallen[:20])} 只超跌股票")
        candidates.extend(candidates_fallen[:20])

    logger.info(f"预筛选出 {len(candidates)} 只候选股票，开始预加载历史数据...")

    # 第三阶段：预加载候选股票的历史数据
    fetcher.preload_candidates_history(candidates, min_days=120)
    logger.info(f"历史数据加载完成，缓存共 {fetcher._stock_data_cache.size()} 只")

    # 第四阶段：并行评估候选股票（硬过滤 + 评分）
    logger.info("开始并行评估...")
    results: List[StockPick] = []
    max_workers: int = min(16, os.cpu_count() or 8)

    _filter_stats: Dict[str, int] = {
        "total": 0,
        "ma_fail": 0,
        "rsi_fail": 0,
        "rsrs_fail": 0,
        "ch20_fail": 0,
        "ch5_fail": 0,
        "score_fail": 0,
        "pass": 0,
    }

    def evaluate(s: StockPick) -> Optional[StockPick]:
        try:
            code: str = s.get("代码", "")
            hist_data: Optional[StockDataList] = fetcher.get_stock_historical(code, max_days=360)
            if not hist_data or len(hist_data) < 120:
                return None

            indicators: Indicators = calculate_advanced_indicators(hist_data)
            if not indicators:
                return None

            # 硬过滤：均线完全多头排列
            if not (indicators["ma5"] > indicators["ma20"] > indicators["ma60"]):
                _filter_stats["ma_fail"] += 1
                return None

            rsi: float = indicators.get("rsi", 50.0)
            if not (40 < rsi < 70):
                _filter_stats["rsi_fail"] += 1
                return None

            rsrs: Dict[str, Any] = calculate_rsrs(hist_data)
            rsrs_val: float = rsrs.get("rsrs", 0.0)
            if rsrs_val <= 0.95:
                _filter_stats["rsrs_fail"] += 1
                return None

            change_20d: float = indicators.get("change_20d", 0.0)
            if change_20d <= 0:
                _filter_stats["ch20_fail"] += 1
                return None

            change_5d: float = indicators.get("change_5d", 0.0)
            if change_5d <= 0:
                _filter_stats["ch5_fail"] += 1
                return None

            score: int
            details: Dict[str, Any]
            score, details = calculate_mid_long_score_v2(
                hist_data, s, indicators, market_thresholds
            )
            _filter_stats["total"] += 1
            if score > 0:
                _filter_stats["pass"] += 1
                return {
                    "code": code,
                    "name": s.get("名称", ""),
                    "price": float(s.get("最新价", 0)),
                    "change_pct": float(s.get("涨跌幅", 0)),
                    "score": score,
                    "details": details,
                }
            _filter_stats["score_fail"] += 1
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(evaluate, s): s for s in candidates}
        for future in as_completed(futures):
            result: Optional[StockPick] = future.result()
            if result:
                results.append(result)

    total: int = _filter_stats["total"]
    logger.info(
        f"硬过滤统计: 总参与评分{total}只, 通过{_filter_stats['pass']}只 "
        f"(均线{_filter_stats['ma_fail']}, RSI{_filter_stats['rsi_fail']}, "
        f"RSRS{_filter_stats['rsrs_fail']}, 20日涨幅{_filter_stats['ch20_fail']}, "
        f"5日涨幅{_filter_stats['ch5_fail']}, 评分{_filter_stats['score_fail']})"
    )

    results.sort(key=lambda x: x["score"], reverse=True)

    # 第五阶段：基本面筛选
    logger.info("开始基本面筛选...")
    financial_filtered: List[StockPick] = []
    fin_filter_stats: Dict[str, int] = {
        "total": 0,
        "st_fail": 0,
        "roe_fail": 0,
        "profit_fail": 0,
        "score_fail": 0,
        "pass": 0,
    }

    for r in results:
        fin_filter_stats["total"] += 1
        fin_code: str = r.get("code", "")

        fin_result: Dict[str, Any] = fiscal_fetcher.check_financial(
            fin_code, stock_type="mid_long"
        )

        if not fin_result["pass"]:
            reason: str = (
                fin_result["reasons"][0] if fin_result["reasons"] else "未知原因"
            )
            if "ST" in reason:
                fin_filter_stats["st_fail"] += 1
            elif "ROE" in reason:
                fin_filter_stats["roe_fail"] += 1
            elif "净利润" in reason:
                fin_filter_stats["profit_fail"] += 1
            else:
                fin_filter_stats["score_fail"] += 1
            logger.info(f"基本面淘汰: {fin_code} - {reason}")
            continue

        fin_filter_stats["pass"] += 1
        r["financial_score"] = fin_result["score"]
        r["financial_reasons"] = fin_result["reasons"]
        r["financial_warnings"] = fin_result["warnings"]
        r["financial_details"] = fin_result["details"]
        financial_filtered.append(r)

    logger.info(
        f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
        f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']}, "
        f"净利润{fin_filter_stats['profit_fail']}, 评分{fin_filter_stats['score_fail']})"
    )

    financial_filtered.sort(
        key=lambda x: (x.get("financial_score", 0), x.get("score", 0)), reverse=True
    )

    # 第六阶段：行业分散约束
    selected: List[StockPick] = []
    industry_count: Dict[str, int] = {}
    max_per_industry: int = max(2, limit // 3)

    for r in financial_filtered:
        if len(selected) >= limit:
            break
        pseudo_industry: str = r["code"][:3]
        count: int = industry_count.get(pseudo_industry, 0)
        if count < max_per_industry:
            selected.append(r)
            industry_count[pseudo_industry] = count + 1
        elif len(selected) < limit * 0.7:
            r["overweight"] = True
            selected.append(r)
            industry_count[pseudo_industry] = count + 1

    logger.info(
        f"筛选出 {len(selected)} 只中长线股票，分布于 {len(industry_count)} 个行业"
    )
    return selected


def _evaluate_short_term_candidate(
    fetcher: Fetcher, stock: StockPick, strategy: StrategyType
) -> Optional[StockPick]:
    """评估单只超短线股票（用于并行计算）"""
    try:
        code: str = stock.get("代码", "")
        if not code or len(code) != 6:
            return None

        min_days: int = 60
        max_days: int = 180
        hist_data: Optional[StockDataList] = fetcher.get_stock_historical(
            code, max_days=max_days
        )
        if not hist_data or len(hist_data) < min_days:
            return None

        if strategy == "aggressive":
            score: int
            details: Dict[str, Any]
            score, details = calculate_short_term_aggressive(hist_data, stock)
        else:
            score, details = calculate_short_term_conservative(hist_data, stock)

        if score > 0:
            return {
                "code": code,
                "name": stock.get("名称", ""),
                "price": stock.get("最新价", 0),
                "change_pct": stock.get("涨跌幅", 0),
                "score": score,
                "details": details,
            }
    except Exception:
        pass
    return None


def select_short_term_stocks(
    fetcher: Fetcher,
    fiscal_fetcher: FiscalFetcher,
    limit: int = 3,
    strategy: StrategyType = "aggressive",
) -> List[StockPick]:
    """筛选超短线股票（并行优化版 + 基本面筛选）

    Args:
        fetcher: DataFetcher 实例
        fiscal_fetcher: FiscalDataFetcher 实例
        limit: 返回股票数量（默认 3）
        strategy: 'aggressive' 激进型 / 'conservative' 稳健型

    Returns:
        选股结果列表，按 (financial_score, score) 降序
    """
    logger.info(f"开始筛选超短线股票({strategy})...")
    all_stocks: List[StockPick] = fetcher.get_stocks_from_historical()

    candidates: List[StockPick] = []
    max_workers: int = min(32, os.cpu_count() or 8)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_evaluate_short_term_candidate, fetcher, s, strategy): s
            for s in all_stocks
        }
        for future in as_completed(futures):
            result: Optional[StockPick] = future.result()
            if result:
                candidates.append(result)

    logger.info(f"技术面候选 {len(candidates)} 只，开始基本面筛选...")
    financial_filtered: List[StockPick] = []
    fin_filter_stats: Dict[str, int] = {
        "total": 0,
        "st_fail": 0,
        "roe_fail": 0,
        "pass": 0,
    }

    for r in candidates:
        fin_filter_stats["total"] += 1
        _code: str = r.get("code", "")

        fin_result: Dict[str, Any] = fiscal_fetcher.check_financial(
            _code, stock_type="short_term"
        )

        if not fin_result["pass"]:
            reason: str = fin_result["reasons"][0] if fin_result["reasons"] else "未知"
            if "ST" in reason:
                fin_filter_stats["st_fail"] += 1
            elif "ROE" in reason:
                fin_filter_stats["roe_fail"] += 1
            logger.info(f"基本面淘汰: {_code} - {reason}")
            continue

        fin_filter_stats["pass"] += 1
        r["financial_score"] = fin_result["score"]
        r["financial_reasons"] = fin_result["reasons"]
        r["financial_details"] = fin_result["details"]
        financial_filtered.append(r)

    logger.info(
        f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
        f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']})"
    )

    financial_filtered.sort(
        key=lambda x: (x.get("financial_score", 0), x.get("score", 0)), reverse=True
    )
    selected: List[StockPick] = financial_filtered[:limit]

    logger.info(f"筛选出 {len(selected)} 只超短线股票({strategy})")
    return selected


def _evaluate_rsrs_candidate(
    fetcher: Fetcher, stock: StockPick
) -> Optional[Dict[str, Any]]:
    """评估单只股票的 RSRS 买入信号（用于并行计算）"""
    try:
        code: str = stock.get("代码", "")
        if not code or len(code) != 6:
            return None

        hist_data: Optional[StockDataList] = fetcher.get_stock_historical(
            code, max_days=360
        )
        if not hist_data or len(hist_data) < 120:
            return None

        evaluation: Dict[str, Any] = evaluate_buy_signal(hist_data, stock)

        if evaluation["buy_score"] >= 30:
            return {
                "code": code,
                "name": stock.get("名称", ""),
                "price": stock.get("最新价", 0),
                "change_pct": stock.get("涨跌幅", 0),
                "buy_score": evaluation["buy_score"],
                "sell_score": evaluation["sell_score"],
                "reasons": evaluation["reasons"],
                "kdj_rsi_cci": evaluation["kdj_rsi_cci"],
                "rsrs": evaluation["rsrs"],
            }
    except Exception:
        pass
    return None


def select_with_rsrs_kdj_cci(
    fetcher: Fetcher, fiscal_fetcher: FiscalFetcher, limit: int = 5
) -> List[Dict[str, Any]]:
    """使用 RSRS + KDJ/RSI/CCI 组合筛选超跌买入机会

    Args:
        fetcher: DataFetcher 实例
        fiscal_fetcher: FiscalDataFetcher 实例
        limit: 返回股票数量（默认 5）

    Returns:
        选股结果列表，按 (buy_score, financial_score) 降序
    """
    logger.info("开始RSRS/KDJ/RSI/CCI组合筛选...")
    all_stocks: List[StockPick] = fetcher.get_stocks_from_historical()

    candidates: List[Dict[str, Any]] = []
    max_workers: int = min(32, os.cpu_count() or 8)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_evaluate_rsrs_candidate, fetcher, s): s
            for s in all_stocks
        }
        for future in as_completed(futures):
            result: Optional[Dict[str, Any]] = future.result()
            if result:
                candidates.append(result)

    logger.info(f"技术面候选 {len(candidates)} 只，开始基本面筛选...")
    financial_filtered: List[Dict[str, Any]] = []
    fin_filter_stats: Dict[str, int] = {
        "total": 0,
        "st_fail": 0,
        "roe_fail": 0,
        "pass": 0,
    }

    for r in candidates:
        fin_filter_stats["total"] += 1
        _code: str = r.get("code", "")

        fin_result: Dict[str, Any] = fiscal_fetcher.check_financial(
            _code, stock_type="mid_long"
        )

        if not fin_result["pass"]:
            reason: str = fin_result["reasons"][0] if fin_result["reasons"] else "未知"
            if "ST" in reason:
                fin_filter_stats["st_fail"] += 1
            elif "ROE" in reason:
                fin_filter_stats["roe_fail"] += 1
            logger.info(f"基本面淘汰: {_code} - {reason}")
            continue

        fin_filter_stats["pass"] += 1
        r["financial_score"] = fin_result["score"]
        r["financial_reasons"] = fin_result["reasons"]
        r["financial_details"] = fin_result["details"]
        financial_filtered.append(r)

    logger.info(
        f"基本面筛选: 参与{fin_filter_stats['total']}只, 通过{fin_filter_stats['pass']}只 "
        f"(ST{fin_filter_stats['st_fail']}, ROE{fin_filter_stats['roe_fail']})"
    )

    financial_filtered.sort(
        key=lambda x: (x.get("buy_score", 0), x.get("financial_score", 0)),
        reverse=True,
    )
    selected: List[Dict[str, Any]] = financial_filtered[:limit]

    logger.info(f"组合筛选出 {len(selected)} 只股票")
    return selected