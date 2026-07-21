import yaml
for f in ['.github/workflows/main-ci.yml', '.github/workflows/pages.yml']:
    with open(f, 'rb') as fp:
        data = fp.read()
    print(f'=== {f} ===')
    print(f'  size: {len(data)} bytes')
    print(f'  has BOM: {data[:3] == bytes([0xEF, 0xBB, 0xBF])}')
    print(f'  has CR: {bytes([0x0D]) in data}')
    try:
        parsed = yaml.safe_load(data)
        print(f'  YAML OK. top-level keys: {list(parsed.keys())}')
        print(f'  name field: {parsed.get("name")!r}')
    except Exception as e:
        print(f'  YAML PARSE ERR: {e}')
