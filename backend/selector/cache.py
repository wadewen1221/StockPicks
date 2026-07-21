#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LRU 缓存 - 带 TTL 过期

设计要点：
  - 有序字典 + 访问时间戳，O(1) get/set
  - 容量满时淘汰最久未访问的（LRU）
  - 每条记录有 TTL（秒），过期则下次 get 时失效
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Optional

from ._types import CacheKey, CacheValue


class LRUCache:
    """带过期时间的 LRU 缓存"""

    def __init__(self, max_size: int = 200, ttl_seconds: int = 300) -> None:
        self.max_size: int = max_size
        self.ttl: int = ttl_seconds
        self._cache: "OrderedDict[CacheKey, CacheValue]" = OrderedDict()
        self._timestamps: dict[CacheKey, float] = {}

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        if key not in self._cache:
            return None
        # 检查过期
        if time.time() - self._timestamps.get(key, 0) > self.ttl:
            self.delete(key)
            return None
        # 移到末尾（最新使用）
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: CacheKey, value: CacheValue) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # 删除最旧的
                oldest: CacheKey = next(iter(self._cache))
                self.delete(oldest)
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def delete(self, key: CacheKey) -> None:
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()

    def __len__(self) -> int:
        return len(self._cache)

    def size(self) -> int:
        return len(self._cache)