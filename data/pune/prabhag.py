import pandas as pd, re
sw=pd.read_csv('pune_stormwater_projects_raw.csv')
DEV='०१२३४५६७८९'; TR=str.maketrans(DEV,'0123456789')
# प्रभाग क्र. / प्रभाग क्रं. / प्रभाग क्रमांक / प्र.क्र.  + number (ASCII or Devanagari) + optional sub-letter
PRABHAG_RE = re.compile(
 r'(?:प्रभाग|प्र\.)\s*(?:क्र(?:\.|ं\.?|मांक)?)\s*\.?\s*'
 r'([0-9०-९]{1,2})\s*([अआबकडईइ])?'
)
CONT_RE = re.compile(r'(?:,|व|आणि|ते)\s*([0-9०-९]{1,2})\s*([अआबकडईइ])?')
def extract(t):
    if not isinstance(t,str): return []
    out=[]
    for m in PRABHAG_RE.finditer(t):
        n=int(m.group(1).translate(TR)); out.append((n,m.group(2)))
    return out
sw['prabhag_list']=sw.work_name.apply(extract)
sw['prabhag_nums']=sw.prabhag_list.apply(lambda L:sorted({n for n,_ in L}))
sw['n_prabhag']=sw.prabhag_nums.apply(len)
sw['prabhag_primary']=sw.prabhag_nums.apply(lambda L:L[0] if L else None)
sw['prabhag_sub']=sw.prabhag_list.apply(lambda L:L[0][1] if L and L[0][1] else None)
# ward column parse
def wardcol(v):
    if not isinstance(v,str): return (None,None)
    m=re.match(r'^\s*(\d{1,3})\s*([A-Za-z])?\s*$',v)
    return (int(m.group(1)),m.group(2)) if m else (None,v.strip())
sw['ward_col_num']=sw.ward_col.apply(lambda v:wardcol(v)[0])
sw['ward_col_sub']=sw.ward_col.apply(lambda v:wardcol(v)[1])
sw.to_csv('pune_stormwater_projects.csv',index=False)
g=sw.groupby('fy').agg(n=('code','size'),
    rs_cr=('provision_rs',lambda s:round(s.sum()/1e7,2)),
    with_prabhag_text=('n_prabhag',lambda s:(s>0).sum()),
    with_ward_col=('ward_col_num',lambda s:s.notna().sum()),
    any_ward=('code','size'))
g['any_ward']=sw.assign(k=(sw.n_prabhag>0)|sw.ward_col_num.notna()).groupby('fy').k.sum()
g['pct_geocodable']=(100*g.any_ward/g.n).round(0)
print(g.to_string())
print('\nprabhag number range per fy (from text):')
for fy,s in sw.groupby('fy'):
    nums=sorted({n for L in s.prabhag_nums for n in L})
    wc=sorted({int(x) for x in s.ward_col_num.dropna()})
    print(f'{fy}: text n={len(nums)} min={min(nums) if nums else None} max={max(nums) if nums else None} | ward_col n={len(wc)} max={max(wc) if wc else None}')
print('\nsample rows:')
for _,r in sw[sw.n_prabhag>0].head(8).iterrows():
    print(f'{r.fy} {r.code} ward_col={r.ward_col} prabhag={r.prabhag_nums}{r.prabhag_sub or ""} Rs{r.provision_rs:,.0f} | {str(r.work_name)[:80]}')
print('\nrows WITHOUT any ward info:',int((~((sw.n_prabhag>0)|sw.ward_col_num.notna())).sum()))
for _,r in sw[~((sw.n_prabhag>0)|sw.ward_col_num.notna())].head(5).iterrows():
    print('  ',r.fy,r.code,str(r.work_name)[:90])
