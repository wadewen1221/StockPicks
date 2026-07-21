#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fiscal_job 测试 - 不依赖真实网络，用 monkeypatch 模拟 baostock/akshare

覆盖：
  - 季度选择（5/9/11 月）
  - 单股票处理流程（mock 数据源）
  - 文件锁 + 写入逻辑
  - 增量下载（不重复写入已存在的 report_date）
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


# 避免测试时启动 scheduler
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs import fiscal_job


@pytest.fixture
def temp_dirs(monkeypatch):
    """临时 fiscal / historical 目录"""
    with tempfile.TemporaryDirectory() as tmp:
        fiscal_dir = Path(tmp) / "fiscal"
        hist_dir = Path(tmp) / "historical"
        fiscal_dir.mkdir()
        hist_dir.mkdir()
        monkeypatch.setattr(fiscal_job, "FISCAL_DIR", fiscal_dir)
        monkeypatch.setattr(fiscal_job, "HISTORICAL_DIR", hist_dir)
        monkeypatch.setattr(fiscal_job, "LOCK_DIR", fiscal_dir / ".locks")
        fiscal_job.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        yield fiscal_dir, hist_dir


# ============================================================
# 季度选择测试
# ============================================================

class TestQuarterSelection:
    def test_may_triggers_q1_and_prev_year_q4(self):
        """5 月应该下载当年一季报 + 上年年报"""
        targets = fiscal_job.get_target_quarters(datetime(2026, 5, 10))
        assert targets == [(2026, 1), (2025, 4)]

    def test_september_triggers_q2(self):
        """9 月应该下载当年半年报"""
        targets = fiscal_job.get_target_quarters(datetime(2026, 9, 10))
        assert targets == [(2026, 2)]

    def test_november_triggers_q3(self):
        """11 月应该下载当年三季报"""
        targets = fiscal_job.get_target_quarters(datetime(2026, 11, 10))
        assert targets == [(2026, 3)]

    def test_other_month_fallback(self):
        """非 5/9/11 月兜底：上一季度"""
        targets = fiscal_job.get_target_quarters(datetime(2026, 7, 1))
        assert (2026, 2) in targets


# ============================================================
# 日期格式化
# ============================================================

class TestDateFormat:
    def test_q1_2026(self):
        assert fiscal_job._fmt_date(2026, 1) == "2026-03-31"

    def test_q4_2025(self):
        assert fiscal_job._fmt_date(2025, 4) == "2025-12-31"

    def test_q2_q3(self):
        assert fiscal_job._fmt_date(2026, 2) == "2026-06-30"
        assert fiscal_job._fmt_date(2026, 3) == "2026-09-30"


# ============================================================
# 单股票处理（mock 数据源）
# ============================================================

def _mock_baostock_records(code, targets):
    """模拟 baostock 返回一组完整数据"""
    out = {}
    for y, q in targets:
        rp = fiscal_job._fmt_date(y, q)
        out[rp] = {
            "report_date": rp,
            "year": y,
            "period": fiscal_job.QUARTER_END_DATES[q],
            "营业总收入": 1e9,
            "归母净利润": 1e8,
            "每股净资产": 1.5,
            "资产负债率": 45.0,
            "总股本": 1e8,
            "流通股本": 9e7,
        }
    return out


class TestProcessOne:
    def test_baostock_only_writes_new_records(self, temp_dirs):
        """baostock 返回的数据应被写入；已存在的 report_date 不重复"""
        fiscal_dir, _ = temp_dirs

        # 预置一条已有记录（2025Q4）
        existing = {
            "code": "000001",
            "name": "平安银行",
            "update_date": "",
            "fiscal": [{
                "report_date": "2025-12-31",
                "year": 2025,
                "period": "12-31",
                "营业总收入": 999.0,  # 故意不同，应保留
            }],
        }
        (fiscal_dir / "000001.json").write_text(
            json.dumps(existing, ensure_ascii=False), encoding="utf-8"
        )

        targets = [(2026, 1), (2025, 4)]
        with patch.object(
            fiscal_job, "fetch_from_baostock",
            side_effect=lambda c, t: _mock_baostock_records(c, t),
        ), patch.object(fiscal_job, "fetch_from_akshare", return_value={}):
            added = fiscal_job._process_one("000001", targets)

        # 2025Q4 已存在（不应再加），2026Q1 应新增
        assert added == 1

        saved = json.loads((fiscal_dir / "000001.json").read_text(encoding="utf-8"))
        dates = {q["report_date"] for q in saved["fiscal"]}
        assert "2025-12-31" in dates
        assert "2026-03-31" in dates
        # 已有记录未被覆盖
        original = next(q for q in saved["fiscal"] if q["report_date"] == "2025-12-31")
        assert original["营业总收入"] == 999.0

    def test_akshare_fills_baostock_gap(self, temp_dirs):
        """baostock 缺的季度，akshare 应兜底"""
        fiscal_dir, _ = temp_dirs

        targets = [(2026, 2)]
        bs_only_q1 = _mock_baostock_records("000001", [(2026, 1)])
        # bs 返回 Q1（不是 Q2），akshare 应补 Q2
        aks_only_q2 = _mock_baostock_records("000001", [(2026, 2)])

        with patch.object(
            fiscal_job, "fetch_from_baostock", return_value=bs_only_q1
        ), patch.object(
            fiscal_job, "fetch_from_akshare", return_value=aks_only_q2
        ):
            added = fiscal_job._process_one("000001", targets)

        assert added == 1  # 只新增了 Q2
        saved = json.loads((fiscal_dir / "000001.json").read_text(encoding="utf-8"))
        assert len(saved["fiscal"]) == 1
        assert saved["fiscal"][0]["report_date"] == "2026-06-30"


# ============================================================
# get_codes 测试
# ============================================================

class TestGetCodes:
    def test_reads_all_stock_files(self, temp_dirs):
        _, hist_dir = temp_dirs
        for code in ["000001", "600519", "300750"]:
            (hist_dir / f"{code}.json").write_text(
                json.dumps({"code": code, "name": f"股票{code}"}),
                encoding="utf-8",
            )
        # 非数字文件名应忽略
        (hist_dir / "README.json").write_text("{}", encoding="utf-8")

        codes = fiscal_job.get_codes()
        assert sorted(codes) == ["000001", "300750", "600519"]

    def test_empty_dir_returns_empty_list(self, temp_dirs):
        assert fiscal_job.get_codes() == []


# ============================================================
# 文件锁测试
# ============================================================

class TestFileLock:
    def test_acquire_release(self, temp_dirs):
        fiscal_dir, _ = temp_dirs
        lock_path = fiscal_dir / "test.lock"
        assert fiscal_job._acquire_file_lock(lock_path, timeout=2)
        assert lock_path.exists()
        lock_path.unlink()
        # 第二次应能再获取
        assert fiscal_job._acquire_file_lock(lock_path, timeout=2)