from pathlib import Path
p = Path(r'D:\stock-picks-v2\frontend\package-lock.json')
c = p.read_text(encoding='utf-8')
new_c = c.replace('"name": "StockPicks-frontend"', '"name": "StockPicks-frontend"')
new_c = new_c.replace('StockPicks-frontend/', 'StockPicks-frontend/')
p.write_text(new_c, encoding='utf-8')
print('package-lock.json 已同步')