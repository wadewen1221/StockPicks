"""搜索 akshare 所有含 'share' 或 'stock' 的接口"""
import akshare as ak

candidates = [f for f in dir(ak) if 'share' in f.lower() or 'capital' in f.lower()]
print(f'找到 {len(candidates)} 个相关接口:')
for c in candidates[:30]:
    print(f'  {c}')

# 试 stock_share_change / stock_total_share
print('\n=== 试 stock_total_share 等 ===')
for fname in ['stock_share_change', 'stock_share_total', 'stock_capital_flow']:
    try:
        f = getattr(ak, fname)
        df = f()
        print(f'\n{fname}: shape={df.shape}')
        print(df.head(3).to_string()[:300])
    except Exception as e:
        print(f'{fname}: err {str(e)[:80]}')