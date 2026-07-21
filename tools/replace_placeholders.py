#!/usr/bin/env python3
"""
替换项目中的占位符:
  - wadewen1221  -> wadewen1221
  - StockPicks -> StockPicks
  - github.com/wadewen1221/StockPicks -> github.com/wadewen1221/StockPicks
"""
import os
import sys
from pathlib import Path

ROOT = Path(r'D:\StockPicks')

REPLACEMENTS = [
    ('wadewen1221/StockPicks', 'wadewen1221/StockPicks'),
    ('wadewen1221', 'wadewen1221'),
    ('StockPicks', 'StockPicks'),
]

# 文件扩展名白名单
EXT_WHITELIST = {'.md', '.yml', '.yaml', '.json', '.py', '.txt', '.bat', '.toml', '.cfg', '.ini', '.html'}
# 排除目录
EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'site', 'data', 'logs', 'dist', '.pytest_cache', '.mypy_cache', 'static', 'templates'}
# 排除文件名
EXCLUDE_FILES = {'CLAUDE.md', 'DEPLOY.md', 'requirements.txt', '生产部署方案：.txt', 'package-lock.json'}

count_modified = 0
files_changed = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    # 排除目录
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for fname in filenames:
        if fname in EXCLUDE_FILES:
            continue
        fpath = Path(dirpath) / fname
        if fpath.suffix.lower() not in EXT_WHITELIST:
            continue
        try:
            content = fpath.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        new_content = content
        for old, new in REPLACEMENTS:
            new_content = new_content.replace(old, new)
        if new_content != content:
            fpath.write_text(new_content, encoding='utf-8')
            count_modified += 1
            files_changed.append(fpath.relative_to(ROOT))

print(f'已修改 {count_modified} 个文件:')
for f in files_changed:
    print(f'  - {f}')