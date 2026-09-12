import openpyxl,re,collections,csv
CODE=re.compile(r'^([A-Z]{2}\d{2}[A-Z]\d{3})/(S?[A-Z]+\d+)-(\d+\+?)$')
PRAB=re.compile(r'प्र(?:भाग)?\s*\.?\s*क्र\s*\.?\s*([0-9०-९]+)')
ZONE=re.compile(r'झोन\s*क्र\s*\.?\s*([0-9०-९]+)')
def dv(s): return int(''.join(str('०१२३४५६७८९'.index(c)) if c in '०१२३४५६७८९' else c for c in s))
def num(s):
    try: return float(s)
    except: return None
def parse(f,sh):
    wb=openpyxl.load_workbook(f,read_only=True,data_only=True)
    rows=[[('' if c is None else str(c).strip()) for c in r] for r in wb[sh].iter_rows(values_only=True)]
    wb.close()
    out=[]
    for r in rows:
        ci=None
        for i,c in enumerate(r):
            if CODE.match(c): ci=i;break
        if ci is None: continue
        m=CODE.match(r[ci])
        ward=r[ci+1] if ci+1<len(r) else ''
        rest=r[ci+1:]
        # name = longest non-numeric string
        cand=[c for c in rest if len(c)>12 and num(c) is None]
        name=max(cand,key=len) if cand else ''
        nums=[num(c) for c in rest if num(c) is not None]
        amt=nums[-1] if nums else None
        out.append((m.group(1),m.group(2),m.group(3),ward,name,amt))
    return out
SH={'2016-17':('xl/1617_1.xlsx','CapitalListA'),'2017-18':('xl/1718_2.xlsx','A_Capital_List'),
 '2018-19':('xl/1819_2.xlsx','A_Capital_List'),'2019-20':('xl/1920_1.xlsx','A_Capital_List'),
 '2020-21':('xl/2021_1.xlsx','A_Capital_List'),'2021-22':('xl/2122_1.xlsx','list21'),
 '2022-23':('xl/2223_1.xlsx','A_List'),'2023-24':('xl/2324_1.xlsx','A_List'),
 '2024-25':('xl/2425_1.xlsx','A_List'),'2025-26':('xl/2526_1.xlsx','listA')}
w=csv.writer(open('pmc_swd_projects.csv','w',newline=''))
w.writerow(['year','acct_code','list_code','sn','ward_col','prabhag_from_text','zone_from_text','provision_rs','work_name'])
print(f"{'yr':8}{'allrows':>8}{'wardcol':>8}{'SWD n':>7}{'SWD Rs cr':>11}{'prabhag':>9}{'zone':>6}{'neither':>8}")
for yr,(f,sh) in SH.items():
    rec=parse(f,sh)
    swd=[x for x in rec if x[0]=='CE20E101']
    tot=sum(x[5] or 0 for x in swd)
    p=z=n=0
    for a,l,s,wd,nm,am in swd:
        mp=PRAB.search(nm); mz=ZONE.search(nm)
        pv = dv(wd.split('.')[0]) if re.match(r'^\d+(\.0)?$',wd) else (dv(mp.group(1)) if mp else '')
        zv = dv(mz.group(1)) if mz else ''
        if pv!='': p+=1
        elif zv!='': z+=1
        else: n+=1
        w.writerow([yr,a,l,s,wd,pv,zv,am,nm])
    wc=sum(1 for x in rec if x[3] not in ('','_','None'))
    print(f"{yr:8}{len(rec):>8}{wc:>8}{len(swd):>7}{tot/1e7:>11.2f}{p:>9}{z:>6}{n:>8}")
