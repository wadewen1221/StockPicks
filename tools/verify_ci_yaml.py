import yaml
with open(r'D:\StockPicks\.github\workflows\ci.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
print('YAML 解析成功')
print('jobs:', list(data['jobs'].keys()))
for name, job in data['jobs'].items():
    print(f'  - {name}: {job.get("name", name)} ({len(job.get("steps", []))} steps)')