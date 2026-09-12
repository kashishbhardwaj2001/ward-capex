import re,glob,os,csv
D=os.path.dirname(os.path.abspath(__file__))
PD=os.path.join(D,'pdfs','amc')
GD=str.maketrans('૦૧૨૩૪૫૬૭૮૯','0123456789')
LEG={'bæg':'Central','W•th':'North','W¥th':'North','>rûtK':'South','ÃËJo':'East','vrùb':'West','vr©b':'West','lJt':'New'}
UNI={'મ ય':'Central','ઉ ર':'North','દ  ણ':'South','ૂવ':'East','પ  મ':'West'}
N=r'([\d,]+\.\d\d)'
# Legacy-font row: "<zone words> Ítul [fwj]  n n n n n"
ROW_LEG=re.compile(r'^\s*([^\d]{0,28}?)\s*Ítul\s*(fwj)?\s+'+r'\s+'.join([N]*5)+r'\s*$')
SPL=re.compile(r'^\s*Special Project by Zone\s+'+r'\s+'.join([N]*5)+r'\s*$')
TOT=re.compile(r'^\s*fwj\s+'+r'\s+'.join([N]*5)+r'\s*$')
GN=r'([૦-૯,]+\.[૦-૯]{2})'
ROW_UNI=re.compile(r'^\s*([^૦-૯]{0,28}?)\s*ઝોન\s+'+r'\s+'.join([GN]*5)+r'\s*$')
def lz(raw):
    return ' '.join(LEG.get(p,p) for p in raw.split()).replace('New West','New West')
def uz(raw):
    k=re.sub(r'\s+','',raw)
    return {'મય':'Central','ઉર':'North','દણ':'South','ૂવ':'East','પૂવ':'East','પમ':'West',
            'ઉરપમ':'North West','દણપમ':'South West'}.get(k,k)
rows=[]
for fn in sorted(glob.glob(os.path.join(PD,'amc_*.txt'))):
    fy=os.path.basename(fn)[4:11]
    lines=open(fn,encoding='utf-8',errors='replace').read().split('\n')
    cur=None
    for i,ln in enumerate(lines):
        m=ROW_LEG.match(ln); uni=False
        if not m:
            m=ROW_UNI.match(ln); uni=bool(m)
        if m:
            g=list(m.groups())
            if uni: name=uz(g[0]); vals=[x.translate(GD) for x in g[1:6]]
            else:   name=lz(g[0]); vals=g[2:7]
            if 'Ítul' in name or 'ઝોન' in name or not name: continue
            ctx='\n'.join(lines[max(0,i-14):i])
            unit='crore' if ('fhtuz{tk' in ctx or 'fhtuzbtk' in ctx or 'કરોડમ' in ctx) else ('lakh' if ('÷t¾{tk' in ctx or 'jtFbtk' in ctx) else '?')
            cur=dict(fy=fy,zone=name,unit=unit,line=i+1,base_road=vals[0],base_water=vals[1],
                     base_drainage=vals[2],base_bldg=vals[3],base_total=vals[4],
                     spl_drainage='',spl_total='',tot_drainage='',tot_total='')
            rows.append(cur); continue
        if cur:
            m2=SPL.match(ln)
            if m2: cur['spl_drainage'],cur['spl_total']=m2.group(3),m2.group(5); continue
            m3=TOT.match(ln)
            if m3: cur['tot_drainage'],cur['tot_total']=m3.group(3),m3.group(5); cur=None
# carry unit forward within a year
byfy={}
for r in rows: byfy.setdefault(r['fy'],[]).append(r)
for fy,rs in byfy.items():
    u=next((x['unit'] for x in rs if x['unit']!='?'),'?')
    for x in rs:
        if x['unit']=='?': x['unit']=u
    for x in rs:
        d=float(x['tot_drainage'] or x['base_drainage']); t=float(x['tot_total'] or x['base_total'])
        if x['unit']=='lakh': d/=100; t/=100
        x['drain_crore']=round(d,4); x['total_crore']=round(t,4)
ORD=['Central','North','South','East','West','North West','South West','New West','Zone/Head Office']
print(f"{'FY':<9}"+''.join(f"{z[:9]:>11}" for z in ORD[:8])+f"{'CITY':>11}")
print('--- DRAINAGE allocation (Rs crore) ---')
for fy in sorted(byfy):
    d={r['zone']:r['drain_crore'] for r in byfy[fy]}
    print(f"{fy:<9}"+''.join(f"{d.get(z,float('nan')):>11.2f}" for z in ORD[:8])+f"{sum(d.values()):>11.2f}")
print('--- TOTAL zone allocation (Rs crore) ---')
for fy in sorted(byfy):
    d={r['zone']:r['total_crore'] for r in byfy[fy]}
    print(f"{fy:<9}"+''.join(f"{d.get(z,float('nan')):>11.2f}" for z in ORD[:8])+f"{sum(d.values()):>11.2f}")
with open(os.path.join(D,'amc_zone_year_drainage.csv'),'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('rows',len(rows),'->',os.path.join(D,'amc_zone_year_drainage.csv'))
