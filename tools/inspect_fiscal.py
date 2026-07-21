"""检查现有 fiscal 文件结构"""
import json
import os
from pathlib import Path

# 老板老项目 fiscal 目录（D:/stock-picks/data/fiscal/）
LEGACY = Path('D:/stock-picks/data/fiscal')
V2 = Path(os.environ.get('STOCK_PICKS_FISCAL', 'D:/stock-picks-v2/backend/data/fiscal'))

import os
V2 = Path(os.environ.get('STOCK_PICKS_FISCAL', str(V2)))

for label, base in [('legacy D:/stock-picks/data/fiscal', LEGACY), ('v2', V2)]:
    if not base.exists():
        print(f'\n{label}: NOT FOUND')
        continue
    files = list(base.glob('*.json'))
    if not files:
        print(f'\n{label}: EMPTY')
        continue
    print(f'\n=== {label} ({len(files)} files) ===')
    for fp in files[:3]:
        with open(fp, encoding='utf-8') as fh:
            d = json.load(fh)
        if d.get('fiscal'):
            rec = d['fiscal'][0]
            print(f'  {fp.name} ({d.get("name","")}):')
            print(f'    fields ({len(rec)}): {list(rec.keys())}')
            print(f'    sample:')
            for k, v in rec.items():
                print(f'      {k}: {v}')
            break