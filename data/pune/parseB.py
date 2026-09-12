import pandas as pd, re, openpyxl, unicodedata
YEARS = {
 '2016-17':('xl/2016-2017_SC.xlsx','CapitalListA'),
 '2017-18':('xl/2017-2018_SC.xlsx','A_Capital_List'),
 '2018-19':('xl/2018-2019_SC.xlsx','A_Capital_List'),
 '2019-20':('xl/2019-2020_SC.xlsx','A_Capital_List'),
 '2020-21':('xl/2020-2021_SC.xlsx','A_Capital_List'),
 '2021-22':('xl/2021-2022_SC.xlsx','list21'),
 '2022-23':('xl/2022-2023_MC.xlsx','A_List'),
 '2023-24':('xl/2023-2024_SC.xlsx','A_List'),
 '2024-25':('xl/2024-2025_SC.xlsx','A_List'),
 '2025-26':('xl/2025-2026_SC.xlsx','listA'),
}
CODE = re.compile(r'^([A-Z]{2}\d{2}[A-Z]\d+)\s*/\s*([A-Z]+\d*)\s*-\s*(\d+)')
rows=[]; log=[]
for fy,(f,sheet) in YEARS.items():
    df=pd.read_excel(f,sheet_name=sheet,header=None,dtype=object)
    # locate header rows: a row containing 'code' and 'कामाचे नाव'
    hdrs=[]
    for r in range(len(df)):
        vals=[str(v).strip() for v in df.iloc[r].tolist()]
        if 'code' in vals and 'कामाचे नाव' in vals:
            m={}
            for c,v in enumerate(vals):
                if v=='code': m['code']=c
                elif v=='ward': m['ward']=c
                elif v=='कामाचे नाव': m['name']=c
                elif v=='प्रकल्पीय रक्कम': m['proj']=c
                elif v=='तरतूद': m['prov']=c
            hdrs.append((r,m))
    n_all=0; n_sw=0
    for i,(hr,m) in enumerate(hdrs):
        end = hdrs[i+1][0] if i+1<len(hdrs) else len(df)
        for r in range(hr+1,end):
            cv=df.iat[r,m['code']]
            if not isinstance(cv,str): continue
            mm=CODE.match(cv.strip())
            if not mm: continue
            n_all+=1
            acct,lst,seq=mm.groups()
            prov=pd.to_numeric(df.iat[r,m['prov']],errors='coerce') if 'prov' in m else None
            proj=pd.to_numeric(df.iat[r,m['proj']],errors='coerce') if 'proj' in m else None
            nm=df.iat[r,m['name']] if 'name' in m else None
            wd=df.iat[r,m['ward']] if 'ward' in m else None
            rows.append(dict(fy=fy,sheet=sheet,row=r,code=cv.strip(),account_code=acct,list_no=lst,seq=int(seq),
                             ward_col=(None if wd is None or str(wd)=='nan' else str(wd).strip()),
                             work_name=(re.sub(r'\s+',' ',nm).strip() if isinstance(nm,str) else None),
                             project_cost_rs=(None if proj is None or pd.isna(proj) else float(proj)),
                             provision_rs=(None if prov is None or pd.isna(prov) else float(prov))))
            if acct=='CE20E101': n_sw+=1
    log.append(dict(fy=fy,sheet=sheet,n_header_blocks=len(hdrs),n_coded_rows=n_all,n_stormwater=n_sw))
out=pd.DataFrame(rows); out.to_csv('pune_capital_list_all.csv',index=False)
sw=out[out.account_code=='CE20E101'].copy(); sw.to_csv('pune_stormwater_projects_raw.csv',index=False)
print(pd.DataFrame(log).to_string(index=False))
print('\nstormwater rows total:',len(sw))
print(sw.groupby('fy').agg(n=('code','size'),rs_cr=('provision_rs',lambda s:round(s.sum()/1e7,2)),
                           ward_col_filled=('ward_col',lambda s:s.notna().sum())).to_string())
print('\nlist_no values for stormwater:',sorted(sw.list_no.unique()))
