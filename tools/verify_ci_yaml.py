import yaml
import os

ROOT = r'D:\stock-picks-v2\.github\workflows'

for fname in os.listdir(ROOT):
    if not fname.endswith('.yml') and not fname.endswith('.yaml'):
        continue
    path = os.path.join(ROOT, fname)
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print(f'OK {fname}')
    print(f'  jobs: {list(data.get("jobs", {}).keys())}')