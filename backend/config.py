#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置模块 - 集中管理路径和配置

所有路径都支持环境变量覆盖，便于跨平台部署和 Docker 化。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT: Path = Path(__file__).parent.parent.absolute()

# 数据目录配置 - 支持环境变量(便于跨平台部署)
# 数据优先级: $STOCK_PICKS_DATA > ../data(兼容老项目) > ./backend/data
_default_data: Path = PROJECT_ROOT / "data"
DATA_DIR: Path = Path(os.environ.get("STOCK_PICKS_DATA", str(_default_data)))
HISTORICAL_DATA_DIR: Path = DATA_DIR / "historical"

# 兼容老项目(D:/stock-picks/)路径 - 仅 Windows 平台生效
_LEGACY_ORIG_DATA: Path = Path("D:/stock-picks/data")
_LEGACY_ORIG_HISTORICAL_DIR: Path = _LEGACY_ORIG_DATA / "historical"


def get_data_dir() -> Path:
    """获取数据目录(支持跨平台)"""
    # Windows 上是 junction 链接时 .exists() 可能为 False,但跳过创建
    if not DATA_DIR.exists() and not DATA_DIR.is_junction():
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass  # 串联与现有 junction 的乢突,忽忽
    return DATA_DIR


def get_historical_dir() -> Path:
    """获取历史数据目录 - 跨平台优先级:环境变量 -> 老项目兼容 -> V2 自有

    Returns:
        历史数据目录 Path 对象
    """
    # 2. 兼容老项目数据 (仅 Windows 环境)
    if os.name == "nt" and _LEGACY_ORIG_HISTORICAL_DIR.exists():
        # 老项目数据存在,优先使用它
        return _LEGACY_ORIG_HISTORICAL_DIR

    # 1. 使用主数据目录
    primary: Path = DATA_DIR / "historical"
    if not primary.exists() and not primary.is_junction():
        try:
            primary.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass

    return primary


# 选股结果缓存 - 支持环境变量定制
def get_stock_cache_path() -> Path:
    """获取选股缓存文件路径

    支持通过 STOCK_PICKS_CACHE 环境变量覆盖（便于部署到非默认路径）
    """
    cache_dir: Path = Path(__file__).parent
    cache_file: Path = cache_dir / "stock_cache.json"

    # 支持环境变量覆盖(便于部署到非默认路径)
    custom_path: Optional[str] = os.environ.get("STOCK_PICKS_CACHE")
    if custom_path:
        return Path(custom_path)

    return cache_file


# API配置
API_PORT: int = int(os.environ.get("PORT", 5001))
DEBUG_MODE: bool = os.environ.get("DEBUG", "False").lower() == "true"


def _resolve_cookie_secret() -> Optional[str]:
    """解析 Cookie 密钥 - 必须在主线程启动前调用 main() 中校验"""
    return os.environ.get("COOKIE_SECRET")


# 允许的来源 - 生产环境必须配置具体域名
# 【修复P1-6】生产环境'*'直接抛异常，不再仅warning
ALLOWED_ORIGINS: str = os.environ.get("ALLOWED_ORIGINS", "*")


def validate_production_config() -> None:
    """生产环境配置校验(由 main.py 在启动时调用)"""
    if not _resolve_cookie_secret():
        raise ValueError("COOKIE_SECRET environment variable must be set")
    if ALLOWED_ORIGINS == "*" and not DEBUG_MODE:
        raise ValueError(
            "生产环境禁止 ALLOWED_ORIGINS='*'，请通过环境变量配置具体域名。"
            "示例: ALLOWED_ORIGINS=https://your-domain.com"
        )