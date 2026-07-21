"""Stock Picks V2 - 类型定义集中地

目的：让 selector/ 包内所有模块共享一组清晰的类型别名，避免到处写 Dict[str, Any]。
约定：
    HistData      - 一根 K 线 {date, open, high, low, close, volume, ...}
    StockDataList - 一只股票的历史数据 = List[HistData]
    Indicators    - 17 种技术指标字典
    ScoreResult   - 打分结果

加新类型前请先在这里定义，不要在函数签名里凭空写 Dict[str, Any]。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 基础数据结构
# ============================================================

# 单根 K 线（来自 akshare / 新浪 / 腾讯 的 JSON）
# 常见字段：date, open, high, low, close, volume, amount, turnover
HistData = Dict[str, Any]

# 一只股票的完整历史 = List[HistData]，按日期正序
StockDataList = List[HistData]

# ============================================================
# 指标 / 打分
# ============================================================

# 17 种技术指标的扁平 dict
# 常见 key: ma5, ma10, ma20, ma60, macd, macd_signal, macd_hist, kdj_k, kdj_d, kdj_j,
#           rsi6, rsi12, rsi24, cci, boll_upper, boll_mid, boll_lower, rsrs, rsrs_slope, rsrs_ma
# 内部子结构: indicators['macd'] = {dif, dea, hist, dif_above_zero, golden_cross}
#          indicators['bollinger'] = {upper, middle, lower, position}
Indicators = Dict[str, Any]

# 打分函数返回：总评分 + 评级
# 形如: {"score": 85.5, "rating": "强烈推荐", "details": {...}}
ScoreResult = Dict[str, Any]

# 单只股票的选股信号
# 形如: {"code": "600519", "name": "贵州茅台", "score": 85.5, "price": 1680.0, ...}
StockPick = Dict[str, Any]

# ============================================================
# 缓存 / 任务
# ============================================================

# LRU 缓存节点
CacheKey = str
CacheValue = Any

# APScheduler 任务 ID
JobId = str

# ============================================================
# 财务 / 基本面
# ============================================================

# 财务数据单条记录
# 形如: {"date": "2024Q3", "roe": 18.5, "net_profit": 1234567, ...}
FiscalRecord = Dict[str, Any]

# 财务历史 = List[FiscalRecord]
FiscalDataList = List[FiscalRecord]

__all__ = [
    "HistData",
    "StockDataList",
    "Indicators",
    "ScoreResult",
    "StockPick",
    "CacheKey",
    "CacheValue",
    "JobId",
    "FiscalRecord",
    "FiscalDataList",
    "MarketThresholds",
]

# ============================================================
# 市场自适应阈值 (用于 calculate_mid_long_score_v2)
# ============================================================

# 形如: {"vol_factor": 1.0, "rsi_oversold": 35, "rsi_overbought": 75, ...}
# 由 StockSelector._get_market_thresholds() 根据市场波动率动态生成
MarketThresholds = Dict[str, float]