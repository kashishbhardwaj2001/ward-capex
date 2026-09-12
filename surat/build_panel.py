import re,csv,collections,sys
from parse_v2 import parse
BOOK={'bb2021-22.txt':2022,'bb2022-23.txt':2023,'bb2023-24.txt':2024,'bb2024-25.txt':2025,'bb2025-26.txt':2026,'bb2026_27.txt':2027}
def fy(end): return f"{end-1}-{str(end%100).zfill(2)}"
MEAS=[('act_y3',-3,'actual'),('act_y2',-2,'actual'),('orig_y1',-1,'orig_budget'),
      ('rev_y1',-1,'revised'),('est_comm',0,'est_commissioner'),('est_standing',0,'est_standing'),
      ('est_corp',0,'est_corporation_final')]
out=[]
for fn,e in BOOK.items():
    sch,rows=parse(fn)
    agg=collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rows:
        for col,off,lab in MEAS:
            if r[col]: agg[r['zone']][(fy(e+off),lab)]+=float(r[col])
    for z,d in agg.items():
        for (f,lab),v in d.items():
            out.append(dict(book=f"SMC Budget Book {fy(e)}",zone=z,fy=f,measure=lab,rs_lakh=round(v,2)))
with open('surat_5682_zone_year_panel.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['book','zone','fy','measure','rs_lakh']); w.writeheader(); w.writerows(out)
print('panel rows',len(out))
# pivot of ACTUALS
piv=collections.defaultdict(dict)
for r in out:
    if r['measure']=='actual': piv[r['zone']][r['fy']]=r['rs_lakh']
yrs=sorted({r['fy'] for r in out if r['measure']=='actual'})
print('ACTUAL capital spend on acct 5682 (Rs lakh), by zone x FY')
print(f"{'zone':<12}"+''.join(f"{y:>11}" for y in yrs))
for z in ['HQ','West','Central','North','East-A','East-B','South','South-A','South-B','South-East','South-West']:
    if z in piv: print(f"{z:<12}"+''.join(f"{piv[z].get(y,0):>11.2f}" for y in yrs))
