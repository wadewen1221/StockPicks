"""找 akshare 扣非净利润/流通股本"""
import akshare as ak

df = ak.stock_financial_abstract(symbol='000001')
hits = df[df['指标'].astype(str).str.contains('扣|扣非')]
print('扣/扣非 in abstract:')
for _, r in hits.iterrows():
    print(f'  [{r["选项"]}] {r["指标"]}')

# profit_sheet
df2 = ak.stock_profit_sheet_by_report_em(symbol='SZ000001')
print(f'\nprofit_sheet shape: {df2.shape}')
deduct_cols = [c for c in df2.columns if 'DEDUCT' in c.upper()]
print('DEDUCT cols:', deduct_cols)

# 流通股本 - 试 mainstock / 主营
df3 = ak.stock_profit_sheet_by_yearly_em(symbol='SZ000001')
print(f'\nyearly_profit shape: {df3.shape}')

# 找 share_cols
share_cols = [c for c in df2.columns if 'SHARE' in c.upper() or '流通' in c]
print('share cols in profit_sheet:', share_cols)