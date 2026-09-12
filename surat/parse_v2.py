import re,sys,csv,collections
DIG={'!':'1','Z':'2','#':'3','$':'4','5':'5','&':'6','*':'7','(':'8',')':'9','_':'0'}
dec=lambda s:''.join(DIG.get(c,c) for c in s)
ZONE={'C[0 SJF8;"':'HQ','J[:8 hMG':'West','[g8=, hMG':'Central','GMY" hMG':'North',
 '.:8 hMG v¹V[':'East-A','.:8 hMG v¹AL':'East-B','FpY hMG v V[':'South-A',
 'FpY hMG v AL':'South-B','FpY hMG':'South','FpY >:8 hMG':'South-East','FpY J[:8 hMG':'South-West'}
SRCMAP={'S[POP':'KP','Z[POP':'RevP'}
NUM=re.compile(r'\d[\d,]*\.\d\d'); SRCRE=re.compile(r'(S\[POP|U.F\\POP|Z\[POP)')
LBL='JM8Z 0=[G[H ,F.G'
COLS=['act_y3','act_y2','orig_y1','rev_y1','est_comm','est_standing','est_corp']
def zone_of(h):
    for k in sorted(ZONE,key=len,reverse=True):
        if k in h: return ZONE[k]
def anchors(page):
    for ln in page.split('\n'):
        if 'SlDxGZ' in ln:
            t=[(m.group(),m.end()) for m in re.finditer(r'\S+',ln)]
            yrs=[e for w,e in t if re.fullmatch(r'\d{4}-\d{2}',w)]
            d={w:e for w,e in t}
            if len(yrs)>=4 and 'zL' in d and ':YFP;P' in d and 'DPGP5FP' in d:
                return [yrs[0]+1,yrs[1]+1,yrs[2]+1,yrs[3]+1,d['zL']+1,d[':YFP;P']+1,d['DPGP5FP']+1]
    return None
def parse(fn):
    pages=open(fn,encoding='utf-8',errors='replace').read().split('\f')
    sch=collections.OrderedDict()
    for i,p in enumerate(pages,1):
        for m in re.finditer(r'lX0I\],\s*v?\s*(5P![P!Z#$5&*()_]*)\s+S\[5L\[?8,\s*BR"+\s*([^\n(`]*)',p[:1200]):
            s=dec(m.group(1).replace('P','.')); z=zone_of(m.group(2))
            if s.count('.')==2 and z: sch.setdefault(s,{'zone':z,'pages':[]})['pages'].append(i)
    rows=[]
    for s,v in sch.items():
        for pno in v['pages']:
            pg=pages[pno-1]; anc=anchors(pg)
            if not anc: continue
            centre=head=''
            for ln in pg.split('\n'):
                mc=re.match(r'\s*(\d\d/\d\d)\s+(\S.*)',ln)
                if mc and 'lJEFU' in ln: centre=mc.group(1)+' '+mc.group(2).strip()
                mh=re.search(r'\b(C-\d{3})\b',ln)
                if mh: head=mh.group(1)
                if ' 5682 ' not in ln or LBL not in ln: continue
                ms=SRCRE.search(ln)
                vals=dict.fromkeys(COLS,'')
                for m in NUM.finditer(ln[ln.index('5682')+4:]):
                    e=m.end()+ln.index('5682')+4
                    d=[abs(e-a) for a in anc]; j=d.index(min(d))
                    if min(d)<=4: vals[COLS[j]]=m.group().replace(',','')
                rows.append(dict(file=fn,sch=s,zone=v['zone'],page=pno,centre=centre,
                    proj_head=head,acct='5682',src=SRCMAP.get(ms.group(1),'GrantP') if ms else '',**vals))
    return sch,rows
if __name__=='__main__':
    allr=[]
    for fn in sys.argv[1:]:
        sch,rows=parse(fn); allr+=rows
        agg=collections.defaultdict(float)
        for r in rows:
            if r['est_corp']: agg[r['zone']]+=float(r['est_corp'])
        print('####',fn,'schedules',len(sch),'rows',len(rows))
        for z in sorted(agg): print(f"   {z:<11}{agg[z]:>10.2f}")
        print(f"   {'TOTAL':<11}{sum(agg.values()):>10.2f}")
    with open('surat_5682_projectlevel.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allr[0].keys())); w.writeheader(); w.writerows(allr)
    print('wrote surat_5682_projectlevel.csv rows=',len(allr))
