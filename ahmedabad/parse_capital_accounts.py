import re,glob,os,csv
D=os.path.dirname(os.path.abspath(__file__)); PD=os.path.join(D,'pdfs','amc')
NUM=r'-?[\d,]+\.\d\d'
# layout A: <n>*4  CODE  NAME  <n>*2-3      layout B: CODE NAME <n>*6-7
A=re.compile(r'^\s*((?:'+NUM+r'\s+){4})(\d{5})\s+(.*?)\s+((?:'+NUM+r'\s*){2,3})$')
B=re.compile(r'^\s*(\d{5})\s+(.*?)\s+((?:'+NUM+r'\s*){6,7})$')
DEPT=re.compile(r'^\s*(\d{3})\s+(\S.*?)\s*$')
DEPT_TOT_A=re.compile(r'^\s*((?:'+NUM+r'\s+){4})(\d{3})\s+(.*?)(?:v|\s)S\],?\s+((?:'+NUM+r'\s*){2,3})$')
DEPT_TOT_B=re.compile(r'^\s*(\d{3})\s+(.*?)v?S\],?\s+((?:'+NUM+r'\s*){6,7})$')
DRAIN={'64507':'Drainage - General','64509':'Storm Water Drain - General',
       '64510':'Drainage pipe line - prevent water-logging','64511':'100% cost drainage pipe line soc/GHB',
       '64513':'25% cost drainage pipe line soc/GHB','64514':'15% cost drainage pipe line soc/GHB',
       '64518':'Drainage Project','64519':'Kharicut Canal','64505':'STP Vasna/Pirana',
       '78313':'Drainage facility in chalis & slums'}
DEPTN={'952':'Drainage Project','962':'Zonal Capital Works','325':'Branch Sewage Pumping Station',
       '326':'Drainage Line','951':'Water Project','967':'JNNURM Project','219':'Slum Upgradation Project'}
rows=[]
for fn in sorted(glob.glob(os.path.join(PD,'amc_*.txt'))):
    fy=os.path.basename(fn)[4:11]; y1=int(fy[:4])
    cur_dept=''
    for ln in open(fn,encoding='utf-8',errors='replace'):
        ln=ln.rstrip('\n')
        md=re.match(r'^\s*(\d{3})\s+([^\d].*)$',ln)
        if md and not re.search(NUM,ln): cur_dept=md.group(1)
        m=A.match(ln); code=name=None
        if m: nums=re.findall(NUM,m.group(1))+re.findall(NUM,m.group(4)); code=m.group(2); name=m.group(3)
        else:
            m=B.match(ln)
            if m: nums=re.findall(NUM,m.group(3)); code=m.group(1); name=m.group(2)
        if code and code in DRAIN and len(nums)>=6:
            v=[x.replace(',','') for x in nums]
            rows.append(dict(fy=fy,dept=cur_dept,dept_name=DEPTN.get(cur_dept,''),acct=code,
                acct_name=DRAIN[code],
                act_y3=v[0],act_y2=v[1],orig_y1=v[2],rev_y1=v[3],
                est_comm=v[4],est_standing=v[5],est_board=v[6] if len(v)>6 else '',
                fy_act_y3=f"{y1-3}-{str((y1-2)%100).zfill(2)}",fy_act_y2=f"{y1-2}-{str((y1-1)%100).zfill(2)}",
                fy_y1=f"{y1-1}-{str(y1%100).zfill(2)}"))
        # dept totals
        mt=DEPT_TOT_A.match(ln)
        lay='A'
        if not mt: mt=DEPT_TOT_B.match(ln); lay='B'
        if mt:
            if lay=='A': dep=mt.group(2); nums=re.findall(NUM,mt.group(1))+re.findall(NUM,mt.group(4))
            else: dep=mt.group(1); nums=re.findall(NUM,mt.group(3))
            if dep in ('952','962','951') and len(nums)>=6:
                v=[x.replace(',','') for x in nums]
                rows.append(dict(fy=fy,dept=dep,dept_name=DEPTN.get(dep,''),acct='TOTAL',
                    acct_name=DEPTN.get(dep,'')+' - department total',
                    act_y3=v[0],act_y2=v[1],orig_y1=v[2],rev_y1=v[3],
                    est_comm=v[4],est_standing=v[5],est_board=v[6] if len(v)>6 else '',
                    fy_act_y3=f"{y1-3}-{str((y1-2)%100).zfill(2)}",fy_act_y2=f"{y1-2}-{str((y1-1)%100).zfill(2)}",
                    fy_y1=f"{y1-1}-{str(y1%100).zfill(2)}"))
with open(os.path.join(D,'amc_capital_drainage_accounts.csv'),'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('rows',len(rows))
# print dept 952 & 962 totals
print(f"\n{'book FY':<9}{'dept':<6}{'act y-3':>12}{'act y-2':>12}{'orig y-1':>12}{'rev y-1':>12}{'comm y':>12}{'std y':>12}{'board y':>12}")
for r in rows:
    if r['acct']=='TOTAL' and r['dept'] in ('952','962'):
        print(f"{r['fy']:<9}{r['dept']:<6}{r['act_y3']:>12}{r['act_y2']:>12}{r['orig_y1']:>12}{r['rev_y1']:>12}{r['est_comm']:>12}{r['est_standing']:>12}{r['est_board'] or '-':>12}")
