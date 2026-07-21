"""akshare stock_financial_abstract 字段分析"""
import akshare as ak
df = ak.stock_financial_abstract(symbol='000001')
print(f'总行数: {len(df)}')
print('\n按选项分组:')
for opt in df['选项'].unique():
    sub = df[df['选项'] == opt]
    print(f'\n  [{opt}] ({len(sub)} 项):')
    for ind in sub['指标']:
        print(f'    - {ind}')

# 找老板 7 项
TARGETS = [
    ('营业总收入', '常用指标'),
    ('归母净利润', '常用指标'),
    ('扣非净利润', '常用指标'),
    ('每股净资产', '每股指标'),
    ('资产负债率', '财务风险'),
    ('总股本', '每股指标'),
    ('流通股本', '每股指标'),
]
print('\n=== 老板 7 项指标匹配检查 ===')
for name, expected_opt in TARGETS:
    match = df[(df['指标'] == name)]
    if match.empty:
        # 模糊匹配
        candidates = df[df['指标'].str.contains(name[:2])]
        print(f'  [X] {name}: not found, fuzzy:')
        for _, r in candidates.iterrows():
            print(f'      {r["选项"]} | {r["指标"]}')
    else:
        actual_opt = match.iloc[0]['选项']
        ok = '[OK]' if actual_opt == expected_opt else f'[in {actual_opt}]'
        print(f'  {ok} {name}')