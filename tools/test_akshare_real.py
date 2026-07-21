"""真实跑 fiscal_job (akshare 兜底)"""
import os
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime

# 让 fiscal_job 用临时目录
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

with tempfile.TemporaryDirectory() as tmp:
    fiscal_dir = Path(tmp) / 'fiscal'
    hist_dir = Path(tmp) / 'historical'
    fiscal_dir.mkdir()
    hist_dir.mkdir()
    (hist_dir / '000001.json').write_text(
        json.dumps({'code': '000001', 'name': '平安银行'}), encoding='utf-8'
    )

    from jobs import fiscal_job as fj
    fj.FISCAL_DIR = fiscal_dir
    fj.HISTORICAL_DIR = hist_dir
    fj.LOCK_DIR = fiscal_dir / '.locks'
    fj.LOCK_DIR.mkdir(parents=True, exist_ok=True)

    # 模拟 5 月 → 2026Q1 + 2025Q4
    stats = fj.run_fiscal_update(
        current_date=datetime(2026, 5, 10),
        codes=['000001'],
    )
    print(f'\n>>> stats: {stats}')

    fp = fiscal_dir / '000001.json'
    if fp.exists():
        d = json.loads(fp.read_text(encoding='utf-8'))
        print(f'>>> saved {len(d["fiscal"])} records:')
        for r in d['fiscal']:
            print(f'  {r["report_date"]}: {list(r.keys())}')
            for k, v in r.items():
                print(f'    {k}: {v}')