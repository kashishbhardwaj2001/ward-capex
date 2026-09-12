import re,glob,os,csv,collections
D=os.path.dirname(os.path.abspath(__file__)); PD=os.path.join(D,'pdfs','amc')
WARD={  # legacy-font token -> AMC ward (48 wards). Verified by transliteration.
'htKev':'Ranip','JtmKt':'Vasna','rlftuj':'Nikol','mhœthldh':'Sardarnagar','mh>thldh':'Sardarnagar',
'vtjze':'Paldi','lJhkdÃþht':'Navrangpura','lJhkdvwht':'Navrangpura','htbtuj nt&esK':'Ramol-Hathijan',
'JxJt':'Vatva','&j<us':'Thaltej','atkœFuzt':'Chandkheda','atk>Fuzt':'Chandkheda','JMºttj':'Vastral',
'Mxuzegb':'Stadium','lhtuzt':'Naroda','lJt Jtzs':'Nava Vadaj','lJtJtzs':'Nava Vadaj','mtchb<e':'Sabarmati',
'Ftrzgt':'Khadia','mhmvwh hrFgtj':'Saraspur-Rakhial','mhFus':'Sarkhej','dtu<t':'Gota',
'atkœjtuzegt':'Chandlodiya','ctuzfœuJ':'Bodakdev','RrLzgt ftujtule':'India Colony','jtkCt':'Lambha',
'ytuZJ':'Odhav','CtEÃþht':'Bhaipura','ymthJt':'Asarwa','œtKejebzt':'Danilimda','stu^vwh':'Jodhpur',
'ctvwldh':'Bapunagar','misvwh':'Saijpur','cnuhtbvwht':'Behrampura','ybhtRJtze':'Amraiwadi',
'lthKÃþht':'Naranpura','lthKvwht':'Naranpura','brKldh':'Maninagar','Ntnectd':'Shahibaug',
'NtnÃþh':'Shahpur','Ntnvwh':'Shahpur','rJhtxldh':'Viratnagar','>rhgtÃþh':'Dariapur','œrhgtÃþh':'Dariapur',
'dtub<eÃþh':'Gomtipur','dtub<evwh':'Gomtipur','Dtxjtuzegt':'Ghatlodia','Ftufah':'Khokhra',
'lthtuj':'Narol','bfhct':'Makarba','JusjÃþh':'Vejalpur','Jusjvwh':'Vejalpur','ct5wldh':'Bapunagar',
'S{tkxeldh':'Krantinagar','ftjwvwh':'Kalupur','stbtjvwh':'Jamalpur','rlftujldh':'Nikol',
'ctuvj':'Bopal','dtb<¤':'(gamtal)','rlhK':'Nirnaynagar','rlhKldh':'Nirnaynagar','&fhz':'Thakkarbapanagar',
'&¬hctvtldh':'Thakkarbapanagar','&¬hctvt ldh':'Thakkarbapanagar','ldhJuj':'Nagarvel',
}
DRAIN=('z[ulus','Mxtubo Jtuxh','Mx[tub Jtuxh','z[ulus jtRl','z[ulus jtEl','z[ulus luxJfo')
AMT=re.compile(r'(?:Yt|Y|`|\.)\s*\.?\s*([\d,]+(?:\.\d+)?)\s*(fhtuz|jtF)')
rows=[]
for fn in sorted(glob.glob(os.path.join(PD,'amc_*.txt'))):
    fy=os.path.basename(fn)[4:11]
    txt=open(fn,encoding='utf-8',errors='replace').read()
    # reflow: bullets start with a marker glyph or big indent; join continuation lines
    raw=[l for l in txt.split('\n')]
    paras=[];cur=''
    BUL=re.compile(r'^\s*(?:[GP\u2022\u2726\u2727\u2756\u25a1\u274f\u2666o]|\(\d+\)|\d+[\.\)])\s+|^\s{6,}\S')
    for l in raw:
        if not l.strip():
            if cur: paras.append(cur); cur=''
            continue
        if re.match(r'^\s*(?:[GP\u2022\u2726\u2727\u2756\u25a1\u274f\u2666]|o)\s+',l):
            if cur: paras.append(cur)
            cur=l.strip()
        else:
            cur=(cur+' '+l.strip()).strip()
    if cur: paras.append(cur)
    for ln in paras:
        if not any(d in ln for d in DRAIN): continue
        w=None
        for k in sorted(WARD,key=len,reverse=True):
            if re.search(re.escape(k)+r'\s+Jtuzo',ln): w=WARD[k]; break
        if not w: continue
        m=AMT.search(ln)
        if not m: continue
        v=float(m.group(1).replace(',',''))
        cr=v if m.group(2)=='fhtuz' else v/100
        rows.append(dict(fy=fy,ward=w,rs_crore=round(cr,4),raw=ln.strip()[:140]))
byfy=collections.Counter(r['fy'] for r in rows)
print('ward-level drainage bullets matched, by book FY:',dict(sorted(byfy.items())))
print('total rows',len(rows))
agg=collections.defaultdict(float)
for r in rows: agg[(r['fy'],r['ward'])]+=r['rs_crore']
for fy in sorted(byfy):
    ws={k[1]:v for k,v in agg.items() if k[0]==fy}
    print(f"\n{fy}: {len(ws)} wards, Rs {sum(ws.values()):.2f} cr -> "+', '.join(f"{k} {v:.2f}" for k,v in sorted(ws.items(),key=lambda x:-x[1])[:12]))
with open(os.path.join(D,'amc_ward_drainage_projects.csv'),'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['fy','ward','rs_crore','raw']); w.writeheader(); w.writerows(rows)
