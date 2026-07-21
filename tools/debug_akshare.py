"""直接 debug fetch_from_akshare"""
import os, sys, tempfile, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
from jobs.fiscal_job import fetch_from_akshare

records = fetch_from_akshare('000001', [(2026, 1), (2025, 4)])
print('Returned records:')
for rp, rec in records.items():
    print(f'  {rp}:')
    for k, v in rec.items():
        print(f'    {k}: {v}')