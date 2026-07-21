"""查找 fiscal.py 和 strategies.py 中所有字段名（中文 key）"""
import re
from pathlib import Path

paths = ['selector/fiscal.py', 'selector/strategies.py', 'selector/scorer.py']
for p in paths:
    if not Path(p).exists():
        continue
    with open(p, encoding='utf-8') as f:
        content = f.read()
    # 中文字段名（引号包围）
    keys = sorted(set(re.findall(r'["\']([^"\']+)["\']\s*:\s*\(?\w', content)))
    print(f'\n=== {p} ===')
    for k in keys:
        if any('\u4e00' <= c <= '\u9fff' for c in k):
            print(f'  {k}')