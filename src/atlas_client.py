"""
Client-side JavaScript for the atlas, as Python string constants.

No mapping library. The choropleth is hand-projected SVG: equirectangular with a cos(lat)
correction, rescaled to whichever city is active. At city scale (tens of km) the distortion
is far below the ~40 m geometry simplification, and it removes the only dependency the page
would otherwise need. That matters because the page has to work three ways - opened from
disk, served statically, and emailed as a file - and a CDN script fails in the first case.

Two things here exist because of bugs already made once:

  * Every renderer runs at top level. An earlier hand-maintained version had two charts
    accidentally nested inside the table's click handler, so they were blank until a reader
    clicked a row - which nobody does before reading the section a chart belongs to.
  * Metrics that only Bengaluru can compute (drainage share, alignment gap) are filtered
    out of the switcher for the other five cities, and the active metric falls back to
    hazard when switching to a city that cannot show it. Rendering an all-grey map would
    look like a data error rather than a disclosure limit.
"""

APP_JS = r"""
<script>
const D = __DATA__;
const CITIES = D.cities, R = D.R;
const PAL    = ["#eef2f4","#cfe0e8","#a8c8d7","#7aaac2","#4b88a8","#2c6a8c","#1c5d7d"];
const GAPPAL = ["#9b3226","#c06a58","#dda893","#efe7dc","#a9c4b2","#6d9e83","#3d7a5c"];

let cur = "bengaluru", metric = "hz", sel = null, sortK = "hz", sortAsc = false;

/* `rich` metrics need ward-level TOTAL budget, which only Bengaluru publishes. */
const METRICS = {
  hz:    {lab:"Flood hazard",  unit:"",         pal:PAL,    dec:2,
          desc:"standardised share of unit below 5 m above nearest drainage"},
  spk:   {lab:"Drainage ₹/km²", unit:" Cr/km²", pal:PAL, dec:2,
          desc:"stormwater capital per km² over the whole panel"},
  share: {lab:"Drainage share", unit:"%",       pal:PAL,    dec:1, rich:true,
          desc:"drainage as % of the ward's works budget"},
  gap:   {lab:"Alignment gap",  unit:" pp",     pal:GAPPAL, dec:1, rich:true, diverge:true,
          desc:"residual — red = high hazard, low spend"}
};

function vals(c,m){return CITIES[c].features.map(f=>f.properties[m]).filter(v=>v!=null&&isFinite(v));}
function scaleFor(c,m){
  const v=vals(c,m).slice().sort((a,b)=>a-b); if(v.length<2) return null;
  const q=p=>v[Math.max(0,Math.min(v.length-1,Math.floor(p*(v.length-1))))];
  return {lo:v[0],hi:v[v.length-1],brk:[0,1,2,3,4,5,6].map(i=>q(i/7))};
}
function colour(x,sc,m){
  if(x==null||!isFinite(x)||!sc) return "var(--rule-2)";
  const pal=METRICS[m].pal; let i=0; while(i<6 && x>=sc.brk[i+1]) i++;
  return pal[i];
}
function fmt(x,m){
  if(x==null||!isFinite(x)) return "—";
  const M=METRICS[m]; return (x>0&&M.diverge?"+":"")+x.toFixed(M.dec)+M.unit;
}

/* Equirectangular with a cos(lat) correction, rescaled to the active city's bounds. */
function project(c){
  const b=CITIES[c].bounds, W=560;
  const kx=Math.cos((b[1]+b[3])/2*Math.PI/180);
  const dx=(b[2]-b[0])*kx || 1, dy=(b[3]-b[1]) || 1;
  return {W, H:Math.max(180,Math.round(W*dy/dx)),
          px:(lon,lat)=>[(lon-b[0])*kx/dx*W, (b[3]-lat)/dy*Math.max(180,Math.round(W*dy/dx))]};
}
function ring(r,P){
  return r.map((p,i)=>{const a=P.px(p[0],p[1]);
    return (i?"L":"M")+a[0].toFixed(1)+" "+a[1].toFixed(1);}).join("")+"Z";
}
function geo2path(g,P){
  if(!g) return "";
  if(g.type==="Polygon")      return g.coordinates.map(r=>ring(r,P)).join("");
  if(g.type==="MultiPolygon") return g.coordinates.map(poly=>poly.map(r=>ring(r,P)).join("")).join("");
  return "";
}

function draw(){
  const C=CITIES[cur], P=project(cur), sc=scaleFor(cur,metric);
  document.getElementById("map").innerHTML =
    '<svg viewBox="0 0 '+P.W+' '+P.H+'" preserveAspectRatio="xMidYMid meet">'+
    C.features.map((f,i)=>{const v=f.properties[metric];
      return '<path d="'+geo2path(f.geometry,P)+'" fill="'+colour(v,sc,metric)+'" data-i="'+i+'"'+
             (sel===i?' class="sel"':'')+'><title>'+f.properties.nm+': '+fmt(v,metric)+'</title></path>';
    }).join("")+'</svg>';
  document.querySelectorAll("#map path").forEach(p=>p.addEventListener("click",()=>{
    sel=+p.dataset.i; draw(); show(); table();}));
  const M=METRICS[metric];
  document.getElementById("scale").innerHTML = sc
    ? '<span>'+fmt(sc.lo,metric)+'</span><span class="bar" style="background:linear-gradient(90deg,'+
      M.pal.join(",")+')"></span><span>'+fmt(sc.hi,metric)+'</span>'+
      '<span style="flex:0 0 auto;margin-left:8px">'+M.desc+'</span>'
    : '<span>'+C.label+' does not publish this metric</span>';
}

function metricBar(){
  const rich=CITIES[cur].rich;
  document.getElementById("metrics").innerHTML = Object.keys(METRICS)
    .filter(k=>!METRICS[k].rich||rich)
    .map(k=>'<button data-m="'+k+'"'+(metric===k?' class="on"':'')+'>'+METRICS[k].lab+'</button>').join("");
  document.querySelectorAll("#metrics button").forEach(b=>b.addEventListener("click",()=>{
    metric=b.dataset.m; metricBar(); draw(); table();}));
}

function cityBar(){
  document.getElementById("citybar").innerHTML = Object.keys(CITIES).map(k=>{
    const c=CITIES[k];
    return '<button data-c="'+k+'"'+(cur===k?' class="on"':'')+'>'+c.label+
           '<span class="c">'+c.n+' '+c.unitWord+(c.n>1?"s":"")+'</span></button>';}).join("");
  document.querySelectorAll("#citybar button").forEach(b=>b.addEventListener("click",()=>{
    cur=b.dataset.c; sel=null;
    /* re-pick per city, so switching never lands on an empty read-out */
    /* falling back keeps a city that cannot compute a metric from rendering an all-grey
       map, which reads as a data error rather than a disclosure limit */
    if(METRICS[metric].rich && !CITIES[cur].rich) metric="hz";
    if(METRICS[sortK] && METRICS[sortK].rich && !CITIES[cur].rich) sortK="hz";
    sel=defaultSel();
    cityBar(); metricBar(); draw(); show(); table(); meta();}));
}

function meta(){
  const c=CITIES[cur];
  document.getElementById("mapmeta").textContent =
    c.label+" · "+c.n+" "+c.unitWord+"s · FY"+c.fy[0]+"–"+c.fy[1]+
    " · ₹"+c.storm_cr.toLocaleString()+" Cr stormwater";
  document.getElementById("citynote").innerHTML = c.rich
    ? "Bengaluru is the only city publishing ward-level <b>total</b> capital spending alongside "+
      "stormwater, plus census population and an official flood-point inventory — so it is the "+
      "only one with a drainage share, an alignment gap and an equity read-out. The other five "+
      "show what they actually publish, which is why the headline is estimated here."
    : c.label+" publishes stormwater capital by "+c.unitWord+", but not the <b>total</b> "+
      c.unitWord+" budget — so the share and alignment-gap metrics that drive the headline "+
      "cannot be computed for it. Hazard and stormwater spending are shown; the decomposition "+
      "needs Bengaluru's disclosure.";
}

function show(){
  const C=CITIES[cur], el=document.getElementById("readout");
  const head='<span class="eyebrow">'+C.unitWord.toUpperCase()+" READ-OUT</span>";
  if(sel==null){
    el.innerHTML='<div class="ro">'+head+'<p class="note" style="margin-top:14px">Click any '+
      C.unitWord+" on the map, or a row in the table below, to see its figures.</p></div>";
    return;
  }
  const p=C.features[sel].properties, r=[];
  if(p.gap!=null) r.push(["Alignment",'<span class="tag '+(p.gap<0?"under":"over")+'">'+
    (p.gap<0?"UNDER":"OVER")+" by "+Math.abs(p.gap).toFixed(1)+" pp</span>"]);
  r.push(["Flood hazard (z)", p.hz==null?"—":p.hz.toFixed(2)]);
  if(p.hand!=null)     r.push(["Mean HAND", p.hand.toFixed(1)+" m"]);
  if(p.total_cr!=null) r.push(["Total capital", "₹"+p.total_cr.toFixed(1)+" Cr"]);
  r.push(["Stormwater spend", "₹"+p.storm_cr.toFixed(1)+" Cr"]);
  if(p.share!=null)    r.push(["Drainage share", p.share.toFixed(1)+"%"]);
  if(p.spk!=null)      r.push(["Per km²", "₹"+p.spk.toFixed(2)+" Cr/km²"]);
  if(p.area!=null)     r.push(["Area", p.area.toFixed(1)+" km²"]);
  if(p.pop!=null)      r.push(["Population (2011)", p.pop.toLocaleString()]);
  if(p.scst!=null)     r.push(["SC/ST share", p.scst.toFixed(1)+"%"]);
  r.push(["Years observed", p.uy]);
  el.innerHTML='<div class="ro">'+head+"<h3>"+p.nm+"</h3>"+
    '<div class="sub">'+C.label+" · "+C.unitWord+" "+p.u+"</div>"+
    r.map(x=>'<div class="row"><span>'+x[0]+"</span><b>"+x[1]+"</b></div>").join("")+"</div>";
}

function table(){
  const C=CITIES[cur];
  const cols=[["nm",C.unitWord[0].toUpperCase()+C.unitWord.slice(1)],["hz","Hazard"],
              ["storm_cr","Stormwater ₹Cr"],["spk","₹Cr/km²"]]
    .concat(C.rich?[["share","Drainage %"],["gap","Gap pp"],["total_cr","Total ₹Cr"]]:[]);
  const idx=C.features.map((f,i)=>i);
  idx.sort((a,b)=>{
    const x=C.features[a].properties[sortK], y=C.features[b].properties[sortK];
    if(typeof x==="string") return sortAsc?x.localeCompare(y):y.localeCompare(x);
    return sortAsc?((x==null?-1e18:x)-(y==null?-1e18:y)):((y==null?-1e18:y)-(x==null?-1e18:x));});
  document.getElementById("tblwrap").innerHTML=
    '<table id="tbl"><thead><tr>'+cols.map(c=>'<th data-k="'+c[0]+'">'+c[1]+"</th>").join("")+
    "</tr></thead><tbody>"+idx.map(i=>{const p=C.features[i].properties;
      return '<tr data-i="'+i+'"'+(sel===i?' class="sel"':'')+">"+cols.map(c=>{
        const k=c[0], v=p[k];
        if(k==="nm") return "<td>"+v+"</td>";
        if(v==null)  return "<td>—</td>";
        if(k==="gap") return '<td style="color:'+(v<0?"var(--gap)":"var(--good)")+'">'+
                             (v>0?"+":"")+v.toFixed(1)+"</td>";
        return "<td>"+(typeof v==="number"?v.toFixed(k==="hz"||k==="spk"?2:1):v)+"</td>";
      }).join("")+"</tr>";}).join("")+"</tbody></table>";
  document.querySelectorAll("#tbl th").forEach(th=>th.addEventListener("click",()=>{
    const k=th.dataset.k; sortAsc=(k===sortK)?!sortAsc:(k==="nm"); sortK=k; table();}));
  document.querySelectorAll("#tbl tbody tr").forEach(tr=>tr.addEventListener("click",()=>{
    sel=+tr.dataset.i; draw(); show(); table();}));
}

/* Open with the most flood-exposed unit already selected rather than an empty panel. The
   read-out sits beside a tall map, so "click something" leaves a large blank on first
   paint - which is what a reader screenshots and what a link preview captures. */
function defaultSel(){
  const F=CITIES[cur].features;
  let best=null, bv=-Infinity;
  F.forEach((f,i)=>{const v=f.properties.hz; if(v!=null&&isFinite(v)&&v>bv){bv=v;best=i;}});
  return best;
}
sel = defaultSel();

/* every renderer runs at load, at top level - see the module docstring */
cityBar(); metricBar(); draw(); show(); table(); meta();
__CHARTS__
</script>
"""

CHART_JS = r"""
/* --- hazard validation ladder --- */
const vd=R.validation||[];
if(vd.length){
  const key=("density" in vd[0])?"density":("d" in vd[0]?"d":Object.keys(vd[0])[1]);
  const qk =("quartile" in vd[0])?"quartile":("q" in vd[0]?"q":Object.keys(vd[0])[0]);
  const vm=Math.max.apply(null,vd.map(v=>+v[key]))||1;
  document.getElementById("ladder").innerHTML=vd.map(v=>
    '<div class="r"><span class="q">'+v[qk]+'</span><span class="t"><i style="width:'+
    (+v[key]/vm*100)+'%"></i></span><span class="v">'+(+v[key]).toFixed(2)+"</span></div>").join("")+
    '<div class="r" style="margin-top:4px"><span class="q"></span><span class="t" '+
    'style="background:none;color:var(--ink-3);font-size:11px;font-family:\'IBM Plex Mono\',monospace">'+
    "observed flood points per km²</span><span class=\"v\"></span></div>";
}

/* --- tagging tiers --- */
const T=R.meta.tiers, tm=Math.max.apply(null,T.map(t=>t.pct))||1;
document.getElementById("tiers").innerHTML=T.map(t=>
  '<div class="city"><span class="nm">'+t.t+'</span><span class="track"><i class="pos" style="width:'+
  (t.pct/tm*46)+'%"></i></span><span class="v">'+t.pct.toFixed(1)+
  '% <span style="color:var(--ink-3)">₹'+t.cr.toLocaleString()+" Cr</span></span></div>").join("");

/* --- mean hazard by councillor party --- */
const parties=R.parties||[];
if(parties.length){
  const pmax=Math.max.apply(null,parties.map(p=>Math.abs(p.hz)))||1;
  document.getElementById("parties").innerHTML=parties.map(p=>{
    const neg=p.hz<0, w=Math.abs(p.hz)/pmax*46;
    return '<div class="city"><span class="nm">'+p.p+
      ' <span style="color:var(--ink-3);font-size:11px">n='+p.n+'</span></span>'+
      '<span class="track"><span class="zero"></span><i style="'+
      (neg?"right:50%;":"left:50%;right:auto;")+"width:"+w+"%;background:"+
      (neg?"var(--water)":"var(--gap)")+'"></i></span><span class="v">'+
      (p.hz>0?"+":"")+p.hz.toFixed(2)+"</span></div>";}).join("");
}

/* --- robustness arms --- */
const RB=R.robust||[];
if(RB.length){
  const rmax=Math.max.apply(null,RB.map(x=>Math.abs(x.beta)))||1;
  document.getElementById("robust").innerHTML=RB.map(x=>{
    const sig=x.cluster_p<0.05;
    return '<div class="city"><span class="nm" style="width:150px">'+x.arm+"</span>"+
      '<span class="track"><span class="zero"></span><i style="left:50%;right:auto;width:'+
      (Math.abs(x.beta)/rmax*46)+"%;background:"+(sig?"var(--good)":"var(--rule)")+'"></i></span>'+
      '<span class="v">'+(x.beta>0?"+":"")+x.beta.toFixed(3)+' <span style="color:'+
      (sig?"var(--good)":"var(--ink-3)")+'">p='+x.cluster_p.toFixed(3)+"</span></span></div>";
  }).join("");
}
"""
