#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LRU 缓存 - 带 TTL 过期
"""
import time
from collections import OrderedDict


class LRUCache:
    """带过期时间的 LRU 缓存"""

    def __init__(self, max_size=200, ttl_seconds=300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}

    def get(self, key):
        if key not in self._cache:
            return None
        # 检查过期
        if time.time() - self._timestamps.get(key, 0) > self.ttl:
            self.delete(key)
            return None
        # 移到末尾（最新使用）
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # 删除最旧的
                oldest = next(iter(self._cache))
                self.delete(oldest)
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def delete(self, key):
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]

    def clear(self):
        self._cache.clear()
        self._timestamps.clear()

    def __len__(self):
        return len(self._cache)

    def size(self):
        return len(self._cache)