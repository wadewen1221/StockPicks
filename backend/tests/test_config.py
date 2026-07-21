"""
config.py - 配置模块单元测试
"""
import os
from pathlib import Path

import pytest


class TestGetDataDir:
    def test_default_returns_pathlib(self, monkeypatch):
        monkeypatch.delenv('STOCK_PICKS_DATA', raising=False)
        from config import get_data_dir
        result = get_data_dir()
        assert isinstance(result, Path)

    def test_env_var_override(self, monkeypatch, tmp_path):
        """$STOCK_PICKS_DATA 应优先"""
        custom = tmp_path / "custom_data"
        monkeypatch.setenv('STOCK_PICKS_DATA', str(custom))
        # 重新导入以应用 env
        import importlib
        import config as cfg
        importlib.reload(cfg)
        assert cfg.get_data_dir() == custom
        # 还原
        monkeypatch.delenv('STOCK_PICKS_DATA')

    def test_creates_dir_if_missing(self, monkeypatch, tmp_path):
        """目录不存在时自动创建"""
        target = tmp_path / "new_data_dir"
        monkeypatch.setenv('STOCK_PICKS_DATA', str(target))
        import importlib
        import config as cfg
        importlib.reload(cfg)
        result = cfg.get_data_dir()
        assert target.exists()
        assert result == target


class TestGetHistoricalDir:
    def test_returns_path(self, monkeypatch):
        from config import get_historical_dir
        result = get_historical_dir()
        assert isinstance(result, Path)
        assert 'historical' in str(result).lower() or result.name == 'historical'


class TestGetStockCachePath:
    def test_default(self, monkeypatch):
        monkeypatch.delenv('STOCK_PICKS_CACHE', raising=False)
        from config import get_stock_cache_path
        result = get_stock_cache_path()
        assert result.name == 'stock_cache.json'

    def test_env_override(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom_cache.json"
        monkeypatch.setenv('STOCK_PICKS_CACHE', str(custom))
        from config import get_stock_cache_path
        result = get_stock_cache_path()
        assert result == custom


class TestApiConfig:
    def test_default_port(self, monkeypatch):
        monkeypatch.delenv('PORT', raising=False)
        import importlib
        import config as cfg
        importlib.reload(cfg)
        assert cfg.API_PORT == 5001

    def test_custom_port(self, monkeypatch):
        monkeypatch.setenv('PORT', '8080')
        import importlib
        import config as cfg
        importlib.reload(cfg)
        assert cfg.API_PORT == 8080


class TestProductionValidation:
    def test_missing_cookie_secret_raises(self, monkeypatch):
        """生产模式但没设 COOKIE_SECRET 应抛异常"""
        monkeypatch.delenv('COOKIE_SECRET', raising=False)
        # 直接修改模块值（不 reload，避免 reload 重读常量）
        import config as cfg
        monkeypatch.setattr(cfg, 'DEBUG_MODE', False)
        monkeypatch.setattr(cfg, 'ALLOWED_ORIGINS', 'https://example.com')
        with pytest.raises(ValueError, match='COOKIE_SECRET'):
            cfg.validate_production_config()

    def test_wildcard_origins_in_prod_raises(self, monkeypatch):
        """生产模式 ALLOWED_ORIGINS='*' 应抛异常"""
        monkeypatch.setenv('COOKIE_SECRET', 'test-secret-1234567890')
        import config as cfg
        monkeypatch.setattr(cfg, 'DEBUG_MODE', False)
        monkeypatch.setattr(cfg, 'ALLOWED_ORIGINS', '*')
        with pytest.raises(ValueError, match='ALLOWED_ORIGINS'):
            cfg.validate_production_config()

    def test_debug_mode_allows_wildcard(self, monkeypatch):
        """DEBUG 模式允许通配符"""
        monkeypatch.setenv('COOKIE_SECRET', 'test-secret-1234567890')
        import config as cfg
        monkeypatch.setattr(cfg, 'DEBUG_MODE', True)
        monkeypatch.setattr(cfg, 'ALLOWED_ORIGINS', '*')
        # 不应抛异常
        cfg.validate_production_config()

    def test_production_with_specific_origin_ok(self, monkeypatch):
        """生产模式配具体域名 - OK"""
        monkeypatch.setenv('COOKIE_SECRET', 'test-secret-1234567890')
        import config as cfg
        monkeypatch.setattr(cfg, 'DEBUG_MODE', False)
        monkeypatch.setattr(cfg, 'ALLOWED_ORIGINS', 'https://my-stock-app.com')
        # 不应抛异常
        cfg.validate_production_config()