"""找 akshare 中股本/总股本/流通股本 接口"""
import akshare as ak
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# 1. abstract 接口 - 找股本相关
df = ak.stock_financial_abstract(symbol='000001')
print(f'abstract 总行数: {len(df)}')
print('\n股本/总股本/流通相关:')
for _, r in df.iterrows():
    name = str(r['指标'])
    if any(k in name for k in ['股本', '总股', '流通']):
        date_col = df.columns[2]
        v = r[date_col]
        print(f'  [{r["选项"]}] {name} ({date_col}): {v}')

# 2. 尝试 stock_a_indicator_ths / stock_balance_sheet
print('\n\n=== 试其他接口 ===')
for fname in ['stock_zh_a_spot_em', 'stock_individual_spot_xq']:
    try:
        if fname == 'stock_zh_a_spot_em':
            f = getattr(ak, fname)()
        else:
            f = getattr(ak, fname)
            df = f(symbol='000001')
        print(f'\n{fname}:')
        if isinstance(df, pd.DataFrame) and not df.empty:
            print('columns:', list(df.columns))
            for c in df.columns:
                if 'share' in c.lower() or '股本' in c:
                    print(f'  {c}: {df.iloc[0][c] if len(df) > 0 else None}')
        else:
            print('  empty')
    except Exception as e:
        print(f'{fname}: err {str(e)[:100]}')