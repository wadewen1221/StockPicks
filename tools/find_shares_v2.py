"""找 akshare 中股本/总股本/流通股本 - 改用 pandas 显示所有行"""
import akshare as ak
import pandas as pd

pd.set_option('display.max_rows', 200)
pd.set_option('display.max_colwidth', 50)
pd.set_option('display.width', 250)

df = ak.stock_financial_abstract(symbol='000001')
print(f'abstract total rows: {len(df)}')
print(f'columns sample: {list(df.columns[:6])}...')

# 找股本相关
print('\n=== Share-related rows ===')
for _, r in df.iterrows():
    name = str(r['指标'])
    if any(k in name for k in ['股本', '总股', '流通', 'share']):
        # 显示前 3 个季度
        date_cols = list(df.columns[2:5])
        vals = [str(r[c]) for c in date_cols]
        print(f'  [{r["选项"]}] {name}: {dict(zip(date_cols, vals))}')