#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据获取器 - 从本地历史 JSON 文件获取股票数据

数据流向：
    本地 JSON (D:\\stock-picks\\data\\historical\\<code>.json)
        ↓
    DataFetcher.get_stock_historical(code)
        ↓
    DataFetcher.get_stocks_from_historical()
        ↓
    选股引擎 (selector/strategies.py)
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from config import get_historical_dir

from ._types import HistData, StockDataList, StockPick
from .cache import LRUCache

logger = logging.getLogger(__name__)


class DataFetcher:
    """数据获取器 - V2 版本使用本地 JSON 文件

    Attributes:
        historical_dir: 历史数据根目录（默认从 config.get_historical_dir() 读）
        _stock_list_cache: 股票列表缓存（5 分钟 TTL）
        _stock_data_cache: 单只股票历史数据 LRU 缓存（容量 200，TTL 10 分钟）
    """

    def __init__(self, historical_dir: Optional[Union[str, Path]] = None) -> None:
        # 允许测试时传入临时目录，避免依赖真实 D:\\stock-picks 路径
        self.historical_dir: Path = (
            Path(historical_dir) if historical_dir else get_historical_dir()
        )
        self._stock_list_cache: Optional[List[StockPick]] = None
        self._stock_list_timestamp: float = 0.0
        # 使用 LRU 缓存替代简单字典，控制内存使用
        self._stock_data_cache: LRUCache = LRUCache(max_size=200, ttl_seconds=600)

    def get_stocks_from_historical(
        self, preload_data: bool = False, max_days: int = 100
    ) -> List[StockPick]:
        """从历史数据目录获取所有股票信息（带缓存）

        Args:
            preload_data: 是否预加载历史数据到缓存（耗时较长）
            max_days: 预加载时保留的最大天数

        Returns:
            股票列表 [{代码, 名称, 最新价, 涨跌幅, 成交量, 行业}, ...]
        """
        # 缓存5分钟有效
        if self._stock_list_cache is not None and not preload_data:
            if time.time() - self._stock_list_timestamp < 300:
                return self._stock_list_cache

        stocks: List[StockPick] = []
        hist_dir = Path(self.historical_dir)

        if not hist_dir.exists():
            logger.warning(f"历史数据目录不存在: {hist_dir}")
            return stocks

        logger.info("开始扫描股票列表...")
        for json_file in hist_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    content: Dict[str, Any] = json.load(f)

                data: StockDataList = content.get("data", [])
                if not data:
                    continue

                latest: HistData = data[-1]
                prev: HistData = data[-2] if len(data) >= 2 else latest

                # 计算涨跌幅
                latest_close: float = latest.get("close", 0)
                prev_close: float = prev.get("close", 0)
                if prev_close > 0:
                    change_pct: float = (latest_close - prev_close) / prev_close * 100
                else:
                    change_pct = 0.0

                code: str = content.get("code", json_file.stem)
                stocks.append(
                    {
                        "代码": code,
                        "名称": content.get("name", ""),
                        "最新价": latest_close,
                        "涨跌幅": change_pct,
                        "成交量": latest.get("volume", 0),
                        "行业": "",
                    }
                )
                # 可选：只缓存最后max_days天数据（大幅减少内存占用）
                if preload_data:
                    recent_data: StockDataList = (
                        data[-max_days:] if len(data) > max_days else data
                    )
                    self._stock_data_cache.set(code, recent_data)
            except Exception as e:
                logger.warning(f"读取股票文件失败 {json_file}: {e}")
                continue

        self._stock_list_cache = stocks
        self._stock_list_timestamp = time.time()
        logger.info(f"股票列表扫描完成，共 {len(stocks)} 只")
        return stocks

    def preload_candidates_history(
        self, stocks: List[StockPick], min_days: int = 60
    ) -> int:
        """预加载候选股票的完整历史数据（并行优化）

        Args:
            stocks: 候选股票列表
            min_days: 最小需要的历史天数

        Returns:
            成功加载历史的股票数量
        """
        # 【修复P1-7】改为多线程并行预加载，避免串行阻塞
        def _load_one(stock: StockPick) -> bool:
            code: str = stock.get("代码", "")
            if not code or self._stock_data_cache.get(code) is not None:
                return False
            hist_data: Optional[StockDataList] = self.get_stock_historical(
                code, max_days=min_days
            )
            return hist_data is not None and len(hist_data) >= min_days

        max_workers: int = min(16, os.cpu_count() or 8)
        loaded: int = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_load_one, s) for s in stocks]
            for f in as_completed(futures):
                if f.result():
                    loaded += 1
        return loaded

    def get_stock_historical(
        self, code: str, max_days: int = 100
    ) -> Optional[StockDataList]:
        """获取单只股票的历史数据（优先从缓存获取，仅保留近期数据）

        Args:
            code: 股票代码，如 "600519"
            max_days: 最多返回的天数

        Returns:
            历史数据列表 [{date, open, high, low, close, volume, ...}, ...]
            文件不存在或读取失败时返回 None
        """
        # 优先使用缓存
        cached: Optional[StockDataList] = self._stock_data_cache.get(code)
        if cached is not None:
            return cached[-max_days:] if len(cached) > max_days else cached

        filepath: Path = Path(self.historical_dir) / f"{code}.json"

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content: Dict[str, Any] = json.load(f)
            data: StockDataList = content.get("data", [])
            # 只保留近期数据以节省内存
            recent_data: StockDataList = (
                data[-max_days:] if len(data) > max_days else data
            )
            if recent_data:
                self._stock_data_cache.set(code, recent_data)
            return recent_data
        except Exception as e:
            logger.warning(f"读取历史数据失败 {code}: {e}")
            return None

    def get_hot_sectors(self) -> List[Dict[str, Any]]:
        """获取热门板块 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_hot_sectors() 调用但尚未实现，返回空列表")
        return []

    def get_limit_up_stocks(self) -> List[Dict[str, Any]]:
        """获取涨停股票 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_limit_up_stocks() 调用但尚未实现，返回空列表")
        return []

    def get_hot_search_stocks(self) -> List[Dict[str, Any]]:
        """获取热门搜索股票 - V2简化实现【P1-5: 保留接口，标记待实现】"""
        logger.warning("get_hot_search_stocks() 调用但尚未实现，返回空列表")
        return []

    def validate_stock_data(self, code: str) -> Tuple[bool, List[str]]:
        """验证股票数据质量

        Args:
            code: 股票代码

        Returns:
            (is_valid, errors) - is_valid=True 表示数据完整无误
        """
        errors: List[str] = []
        filepath: Path = Path(self.historical_dir) / f"{code}.json"

        if not filepath.exists():
            return False, ["文件不存在"]

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content: Dict[str, Any] = json.load(f)

            # 检查必要字段
            if "code" not in content:
                errors.append("缺少code字段")
            if "name" not in content:
                errors.append("缺少name字段")
            if "data" not in content:
                errors.append("缺少data字段")
                return False, errors

            data: StockDataList = content["data"]
            if not data:
                errors.append("历史数据为空")
                return False, errors

            # 检查数据完整性
            required_fields = ["date", "open", "high", "low", "close", "volume"]
            latest: HistData = data[-1]
            for field in required_fields:
                if field not in latest:
                    errors.append(f"最新数据缺少{field}字段")

            # 检查数据一致性
            if len(data) >= 2:
                if data[-1]["date"] == data[-2]["date"]:
                    errors.append("存在重复日期数据")

            # 检查涨跌幅计算
            if "change_pct" in latest and "close" in latest and len(data) >= 2:
                expected_change: float = (
                    (latest["close"] - data[-2]["close"]) / data[-2]["close"] * 100
                )
                if abs(latest.get("change_pct", 0) - expected_change) > 0.1:
                    errors.append(
                        f"涨跌幅可能错误: 记录值{latest.get('change_pct'):.2f}%, "
                        f"计算值{expected_change:.2f}%"
                    )

            return len(errors) == 0, errors

        except json.JSONDecodeError:
            return False, ["JSON格式错误"]
        except Exception as e:
            return False, [f"验证异常: {str(e)}"]

    def get_data_quality_report(self, sample_size: int = 50) -> Dict[str, Any]:
        """生成数据质量报告

        Args:
            sample_size: 抽样验证的股票数量

        Returns:
            报告 dict: {total_checked, issues, quality_score}
        """
        all_stocks: List[StockPick] = self.get_stocks_from_historical(preload_data=False)
        issues: Dict[str, Any] = {
            "missing_file": [],
            "invalid_json": [],
            "data_errors": [],
        }

        sample: List[StockPick] = random.sample(
            all_stocks, min(sample_size, len(all_stocks))
        )

        for s in sample:
            code: str = s.get("代码", "")
            is_valid: bool
            errors: List[str]
            is_valid, errors = self.validate_stock_data(code)
            if not is_valid:
                for err in errors:
                    if "不存在" in err:
                        issues["missing_file"].append(code)
                    elif "JSON" in err:
                        issues["invalid_json"].append(code)
                    else:
                        issues["data_errors"].append((code, err))

        return {
            "total_checked": len(sample),
            "issues": issues,
            "quality_score": 100
            - (
                len(issues["missing_file"])
                + len(issues["invalid_json"])
                + len(issues["data_errors"])
            )
            / len(sample)
            * 100,
        }