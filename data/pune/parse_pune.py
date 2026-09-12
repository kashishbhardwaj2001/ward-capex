"""PMC (Pune) budget extractor.
Structure A: ward-office x department x year (4 tables/yr)
Structure B: project-level capital list, stormwater dept CE20E101, prabhag from Marathi text
"""
import pandas as pd, re, openpyxl, json

YEARS = {  # fiscal year -> (local file, sheet-name suffix, source url)
 '2016-17':('xl/2016-2017_SC.xlsx','16'),
 '2017-18':('xl/2017-2018_MC.xlsx','1718'),
 '2018-19':('xl/2018-2019_SC.xlsx','1819'),
 '2019-20':('xl/2019-2020_SC.xlsx','1920'),
 '2020-21':('xl/2020-2021_SC.xlsx','2021'),
 '2021-22':('xl/2021-2022_SC.xlsx','2122'),
 '2022-23':('xl/2022-2023_MC.xlsx','2223'),
 '2023-24':('xl/2023-2024_SC.xlsx','2324'),
 '2024-25':('xl/2024-2025_SC.xlsx','2425'),
 '2025-26':('xl/2025-2026_SC.xlsx','2526'),
}
HDR_RE = re.compile(r'^\s*([A-Z]{2}\d{2}[A-Z]\d+)\s*/\s*([WC])(\d)\s*-?\s*$')
SLOT = {'2':'Roads','1':'Electrical','4':'Buildings','5':'Slum','6':'WaterSupply','7':'Sewerage_foul'}

rows=[]; log=[]
for fy,(f,suf) in YEARS.items():
    wb=openpyxl.load_workbook(f,read_only=True); names=wb.sheetnames; wb.close()
    for kind in ['WardOfficePlan','WardOfficeNonPlan','CitizensPlan','CitizensNonPlan']:
        sheet=next((n for n in names if n.lower()==(kind+suf).lower()),None)
        if sheet is None:
            log.append(dict(fy=fy,table=kind,sheet=None,n_wardoffices=0,note='sheet absent')); continue
        df=pd.read_excel(f,sheet_name=sheet,header=None,dtype=object)
        hdr=colmap=None
        for i in range(min(25,len(df))):
            cm={c:HDR_RE.match(str(v)).groups() for c,v in df.iloc[i].items() if HDR_RE.match(str(v))}
            if len(cm)>=4: hdr,colmap=i,cm; break
        if hdr is None:
            log.append(dict(fy=fy,table=kind,sheet=sheet,n_wardoffices=0,note='no header')); continue
        first=min(colmap)
        namecol=next((c for c in range(first-1,-1,-1)
                      if df.iloc[hdr+1:hdr+30,c].astype(str).str.contains('क्षेत्रीय').any()),None)
        # data block: contiguous ward-office rows; grand-total row name STARTS with क्षेत्रीय
        blk=[]
        for r in range(hdr+1,min(hdr+40,len(df))):
            nm=df.iat[r,namecol]
            if not isinstance(nm,str) or 'क्षेत्रीय' not in nm:
                if blk: break
                continue
            nm=re.sub(r'\s+',' ',nm).strip()
            if nm.startswith('क्षेत्रीय'): break     # grand total
            blk.append((r,nm))
        # Sr. column = column left of namecol whose block values are 1..N ints
        srcol=None
        for c in range(namecol-1,-1,-1):
            v=pd.to_numeric(pd.Series([df.iat[r,c] for r,_ in blk]),errors='coerce')
            if v.notna().all() and list(v.astype(int))==list(range(1,len(blk)+1)): srcol=c; break
        for r,nm in blk:
            wn=df.iat[r,0]
            for c,(code,W,slot) in colmap.items():
                v=pd.to_numeric(df.iat[r,c],errors='coerce')
                rows.append(dict(fy=fy,table=kind,sheet=sheet,
                                 sr=(int(df.iat[r,srcol]) if srcol is not None else None),
                                 col0_wardnumbers=(str(wn) if wn is not None and str(wn)!='nan' else None),
                                 ward_office=nm,account_code=code,dept=SLOT[slot],
                                 amount_lakh=(None if pd.isna(v) else float(v))))
        log.append(dict(fy=fy,table=kind,sheet=sheet,n_wardoffices=len(blk),
                        note=','.join(sorted({c for c,_,_ in colmap.values()}))))
out=pd.DataFrame(rows); out.to_csv('pune_wardoffice_dept_year.csv',index=False)
pd.DataFrame(log).to_csv('pune_structureA_sheetlog.csv',index=False)
print(pd.DataFrame(log).to_string(index=False))
print('\nrows:',len(out))
print('\nRs lakh by FY x table:')
print(out.pivot_table(index='fy',columns='table',values='amount_lakh',aggfunc='sum').round(1).to_string())
print('\nWardOfficePlan (capital) Rs lakh, FY x dept:')
p=out[out.table=='WardOfficePlan'].pivot_table(index='fy',columns='dept',values='amount_lakh',aggfunc='sum')
print(p.round(1).to_string())
