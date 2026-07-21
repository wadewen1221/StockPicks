#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基本面数据获取器 - 从本地财务文件读取数据

CANSLIM 风格评分（C=Current 净利润, A=Annual 增长, etc）
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def get_fiscal_data_dir() -> Path:
    """获取基本面数据目录(跨平台)

    优先级:
        1. 环境变量 STOCK_PICKS_FISCAL
        2. <项目根>/data/fiscal
        3. Windows + 老项目 D:/stock-picks/data/fiscal (向后兼容)
    """
    primary = Path(
        os.environ.get(
            "STOCK_PICKS_FISCAL",
            str(Path(__file__).parent.parent / "data" / "fiscal"),
        )
    )
    legacy = Path("D:/stock-picks/data/fiscal")

    # Windows: 兼容老项目数据(如存在)
    if os.name == "nt" and legacy.exists():
        return legacy

    if not primary.exists() and not primary.is_junction():
        try:
            primary.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
    return primary


class FiscalDataFetcher:
    """基本面数据获取器 - 从本地财务文件读取数据

    Attributes:
        fiscal_dir: 财务 JSON 文件目录
        _cache: 财务数据缓存 {symbol: data}
        _cache_time: 缓存时间戳 {symbol: datetime}
        cache_validity: 缓存有效期（秒），默认 6 小时
    """

    def __init__(self, fiscal_dir: Optional[Union[str, Path]] = None) -> None:
        # 允许测试时传入临时目录
        self.fiscal_dir: Path = (
            Path(fiscal_dir) if fiscal_dir else get_fiscal_data_dir()
        )
        self._cache: Dict[str, Dict[str, Any]] = {}  # 缓存财务数据
        self._cache_time: Dict[str, datetime] = {}
        self.cache_validity: int = 3600 * 6  # 6小时缓存

    def _is_cache_valid(self, symbol: str) -> bool:
        """检查缓存是否有效

        当文件比缓存更新时也认为失效（强制重读）
        """
        if symbol not in self._cache or symbol not in self._cache_time:
            return False
        fpath: Path = self.fiscal_dir / f"{symbol}.json"
        if fpath.exists():
            file_mtime: datetime = datetime.fromtimestamp(fpath.stat().st_mtime)
            if file_mtime > self._cache_time[symbol]:
                return False
        return (
            datetime.now() - self._cache_time[symbol]
        ).total_seconds() < self.cache_validity

    def get_fiscal_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本面数据

        Args:
            symbol: 股票代码，如 "600519"

        Returns:
            dict 包含 ROE、净利润增长率、资产负债率等指标；文件不存在时返回 None
            {
              'code', 'name', 'roe', '净利润', '资产负债率', '净利润增长率', 'is_st', 'source'
            }
        """
        if self._is_cache_valid(symbol):
            return self._cache[symbol]

        fpath: Path = self.fiscal_dir / f"{symbol}.json"
        if not fpath.exists():
            return None

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content: Dict[str, Any] = json.load(f)

            fiscal_list: List[Dict[str, Any]] = content.get("fiscal", [])
            if not fiscal_list:
                return None

            # 按 report_date 降序排列（最新季度排前面）
            fiscal_list = sorted(
                fiscal_list,
                key=lambda x: x.get("report_date", ""),
                reverse=True,
            )
            recent: List[Dict[str, Any]] = fiscal_list[:4]  # 取最近4个季度

            def get_q(qidx: int, field: str, default: Optional[float] = None) -> Optional[float]:
                """取指定季度字段值（自动转 float，处理 'None'/'' 等脏数据）"""
                if qidx < len(recent):
                    v: Any = recent[qidx].get(field, default)
                    if v is None or v == "" or v == "None":
                        return default
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return default
                return default

            # 计算 ROE = 归母净利润 / 净资产总计
            bps: Optional[float] = get_q(0, "每股净资产")
            total_share: Optional[float] = get_q(0, "总股本")
            net_assets: Optional[float] = (
                bps * total_share if bps and total_share else None
            )
            net_profit: Optional[float] = get_q(0, "归母净利润")
            roe: Optional[float] = (
                (net_profit / net_assets * 100)
                if (net_profit and net_assets and net_assets > 0)
                else None
            )

            # 资产负债率
            debt_ratio: Optional[float] = get_q(0, "资产负债率")

            # ST 状态
            stock_name: str = content.get("name", "")
            st_pattern = re.compile(r"(ST|S\*ST|\*ST|退市?|暂停上市)", re.IGNORECASE)
            is_st: bool = bool(st_pattern.search(stock_name))

            # 计算净利润同比增长率
            # 按时间降序：q0=最新季度，q1=去年同季度
            def same_period_q1() -> Optional[Dict[str, Any]]:
                if len(recent) < 2:
                    return None
                q0_period: str = recent[0].get("period", "")
                q0_year: int = recent[0].get("year", 0)
                for q in recent[1:]:
                    if q.get("period") == q0_period and q.get("year") == q0_year - 1:
                        return q
                return None

            q1: Optional[Dict[str, Any]] = same_period_q1()
            net_profit_yoy: Optional[float] = None

            if q1:
                np0: Optional[float] = get_q(0, "归母净利润")
                np1_val: Any = q1.get("归母净利润")
                if (
                    np1_val
                    and isinstance(np1_val, (int, float))
                    and np1_val != 0
                ):
                    np1_float: float = float(np1_val)
                    net_profit_yoy = (np0 - np1_float) / abs(np1_float) * 100

            data: Dict[str, Any] = {
                "code": symbol,
                "name": stock_name,
                "roe": roe,
                "净利润": net_profit,
                "资产负债率": debt_ratio,
                "净利润增长率": net_profit_yoy,
                "is_st": is_st,
                "source": "local_fiscal",
            }

            self._cache[symbol] = data
            self._cache_time[symbol] = datetime.now()
            return data

        except Exception as e:
            logger.warning(f"读取财务文件失败 {symbol}: {e}")
            return None

    def check_financial(
        self, symbol: str, stock_type: str = "mid_long"
    ) -> Dict[str, Any]:
        """检查股票基本面是否通过筛选

        Args:
            symbol: 股票代码
            stock_type: 'mid_long' 中长线 / 其他（短线不查财务）

        Returns:
            {
              'pass': bool,           # 是否通过
              'score': int,           # CANSLIM 财务评分（满分 35）
              'reasons': list,        # 加分理由
              'warnings': list,       # 风险提示
              'details': dict         # 原始财务数据
            }
        """
        data: Optional[Dict[str, Any]] = self.get_fiscal_data(symbol)

        if not data:
            return {
                "pass": False,
                "score": 0,
                "reasons": ["无财务数据"],
                "warnings": [],
                "details": {},
            }

        score: int = 0
        reasons: List[str] = []
        warnings: List[str] = []

        # ST 股票直接淘汰
        if data.get("is_st"):
            return {
                "pass": False,
                "score": 0,
                "reasons": ["ST股票"],
                "warnings": [],
                "details": data,
            }

        # 提取核心指标
        roe: Optional[float] = data.get("roe")
        profit_growth: Optional[float] = data.get("净利润增长率")

        # 中长线硬性淘汰条件
        if stock_type == "mid_long":
            if roe is not None and roe < 0:
                return {
                    "pass": False,
                    "score": 0,
                    "reasons": [f"ROE为负({roe:.1f}%)"],
                    "warnings": [],
                    "details": data,
                }
            if profit_growth is not None and profit_growth < -50:
                return {
                    "pass": False,
                    "score": 0,
                    "reasons": [f"净利润增长异常({profit_growth:.1f}%)"],
                    "warnings": [],
                    "details": data,
                }

        # ========== 财务评分（CANSLIM风格）==========
        # 1. ROE 评分（15分）
        if roe is not None:
            if roe >= 20:
                score += 15
                reasons.append(f"ROE优秀({roe:.1f}%)")
            elif roe >= 15:
                score += 12
                reasons.append(f"ROE良好({roe:.1f}%)")
            elif roe >= 10:
                score += 8
                reasons.append(f"ROE尚可({roe:.1f}%)")
            elif roe >= 5:
                score += 4
            elif roe >= 0:
                warnings.append(f"ROE偏低({roe:.1f}%)")

        # 2. 净利润增长率（15分）
        if profit_growth is not None:
            if profit_growth >= 100:
                score += 15
                reasons.append(f"净利润爆发增长({profit_growth:.1f}%)")
            elif profit_growth >= 50:
                score += 13
                reasons.append(f"净利润高速增长({profit_growth:.1f}%)")
            elif profit_growth >= 30:
                score += 11
                reasons.append(f"净利润较快增长({profit_growth:.1f}%)")
            elif profit_growth >= 20:
                score += 9
                reasons.append(f"净利润稳健增长({profit_growth:.1f}%)")
            elif profit_growth >= 10:
                score += 6
                reasons.append(f"净利润小幅增长({profit_growth:.1f}%)")
            elif profit_growth >= 0:
                score += 3
            elif profit_growth >= -20:
                warnings.append(f"净利润小幅下滑({profit_growth:.1f}%)")
            else:
                warnings.append(f"净利润下滑较大({profit_growth:.1f}%)")

        # 3. 资产负债率（5分）
        debt_ratio: Optional[float] = data.get("资产负债率")
        if debt_ratio is not None:
            if debt_ratio <= 30:
                score += 5
                reasons.append(f"负债率低({debt_ratio:.1f}%)")
            elif debt_ratio <= 50:
                score += 3
                reasons.append(f"负债率适中({debt_ratio:.1f}%)")
            elif debt_ratio <= 70:
                score += 1
            else:
                warnings.append(f"负债率偏高({debt_ratio:.1f}%)")

        # 中长线：总分<15硬淘汰
        if stock_type == "mid_long" and score < 15:
            return {
                "pass": False,
                "score": score,
                "reasons": [f"财务评分过低({score}分)"],
                "warnings": warnings,
                "details": data,
            }

        return {
            "pass": True,
            "score": score,
            "reasons": reasons,
            "warnings": warnings,
            "details": data,
        }