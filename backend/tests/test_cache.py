"""
LRU 缓存 - 单元测试
"""
import time

import pytest
from selector import LRUCache


class TestLRUCache:
    def test_basic_set_get(self):
        cache = LRUCache(max_size=3, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        assert cache.get('a') == 1
        assert cache.get('b') == 2
        assert cache.get('nonexistent') is None

    def test_size_tracking(self):
        cache = LRUCache(max_size=3, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        assert cache.size() == 2
        assert len(cache) == 2

    def test_lru_eviction(self):
        """超出 max_size 时，淘汰最久未使用"""
        cache = LRUCache(max_size=2, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        # a 应被淘汰
        assert cache.get('a') is None
        assert cache.get('b') == 2
        assert cache.get('c') == 3

    def test_update_existing_key(self):
        cache = LRUCache(max_size=3, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('a', 100)
        assert cache.get('a') == 100
        assert cache.size() == 1

    def test_ttl_expiration(self):
        """TTL 到期后值应失效"""
        cache = LRUCache(max_size=3, ttl_seconds=1)
        cache.set('a', 1)
        assert cache.get('a') == 1
        time.sleep(1.1)
        assert cache.get('a') is None

    def test_delete(self):
        cache = LRUCache(max_size=3, ttl_seconds=10)
        cache.set('a', 1)
        cache.delete('a')
        assert cache.get('a') is None
        assert cache.size() == 0

    def test_clear(self):
        cache = LRUCache(max_size=3, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.clear()
        assert cache.size() == 0

    def test_lru_order_update(self):
        """get 操作应更新 LRU 顺序"""
        cache = LRUCache(max_size=2, ttl_seconds=10)
        cache.set('a', 1)
        cache.set('b', 2)
        # 访问 a，使其变为最新
        cache.get('a')
        # 添加 c，应淘汰 b（而不是 a）
        cache.set('c', 3)
        assert cache.get('a') == 1
        assert cache.get('b') is None
        assert cache.get('c') == 3