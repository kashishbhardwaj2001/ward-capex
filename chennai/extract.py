import re,subprocess,sys,os,csv
W=re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
YR=re.compile(r'(19|20)\d\d-(19|20)\d\d')
def pagelines(pdf):
    xml=subprocess.run(['pdftotext','-bbox-layout',pdf,'-'],capture_output=True,text=True).stdout
    for pi,pg in enumerate(xml.split('<page ')[1:],1):
        b={}
        for xm,ym,xM,yM,w in W.findall(pg):
            b.setdefault(round(float(ym)/2.0),[]).append((float(xm),float(xM),w))
        yield pi,[sorted(b[k]) for k in sorted(b)]
def extract(pdf):
    out=[];bounds=None;years=None
    for pg,lines in pagelines(pdf):
        for ws in lines:
            toks=[w for _,_,w in ws]
            ys=[(a+b)/2 for a,b,w in ws if YR.fullmatch(w)]
            yl=[w for w in toks if YR.fullmatch(w)]
            if len(ys)==4:                      # year header row -> column centres
                years=yl
                mid=[(ys[i]+ys[i+1])/2 for i in range(3)]
                bounds=[ys[0]-(ys[1]-ys[0])*0.7]+mid+[ys[3]+(ys[3]-ys[2])*0.7]
            if not bounds or len(ws)<4: continue
            z,f,c=ws[0][2],ws[1][2],ws[2][2]
            if not (re.fullmatch(r'N[A-Q]',z) and re.fullmatch(r'\d\d-\d\d-\d\d',f)
                    and re.fullmatch(r'\d{3}-\d{2}-\d{2}-\d{2}',c)): continue
            vals=['']*4; head=[]
            for a,b,w in ws[3:]:
                if re.fullmatch(r'-?[\d,]+(\.\d+)?',w) and b>bounds[0]:
                    for k in range(4):
                        if bounds[k]<b<=bounds[k+1]: vals[k]=w.replace(',',''); break
                else: head.append(w)
            out.append([os.path.basename(pdf),pg,z,c,' '.join(head),'|'.join(years)]+vals)
    return out
if __name__=='__main__':
    allr=[]
    for pdf in sys.argv[1:]:
        r=extract(pdf); allr+=r
        sw=[x for x in r if x[3]=='412-40-11-00']
        print(f"{pdf}: zonerows={len(r)} pages={min(x[1] for x in r) if r else '-'}-{max(x[1] for x in r) if r else '-'} SWDzones={len(sw)} yearcols={sw[0][5] if sw else ''}")
    with open('gcc_zone_capital_all.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow(['book','page','zone','dp_code','account_head','year_cols','col1_actuals','col2_BE','col3_RE','col4_BE']); w.writerows(allr)
    print("rows written:",len(allr))
