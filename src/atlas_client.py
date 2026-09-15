"""
Client-side JavaScript for the atlas, as Python string constants.

No mapping library. The choropleth is hand-projected SVG: equirectangular with a cos(lat)
correction, rescaled to whichever city is active. At city scale (tens of km) the distortion
is far below the ~40 m geometry simplification, and it removes the only dependency the page
would otherwise need. That matters because the page has to work three ways - opened from
disk, served statically, and emailed as a file - and a CDN script fails in the first case.

INTERACTION MODEL. Two pieces of state, not one:

    pinned  what the reader clicked, and what the read-out returns to
    hov     what the cursor is currently over

and the read-out shows `hov ?? pinned`. A first version had only a click handler, so moving
the cursor across 198 wards did nothing at all and the map looked broken - the polygons
changed their stroke on CSS :hover, which promised interactivity the JS never delivered.
Hover-to-preview with click-to-pin is what that stroke was implicitly advertising.

The same pairing drives the table, so hovering a row highlights its polygon and vice versa;
the two views are one selection, not two.

Three bugs already made once, which is why the code looks the way it does:

  * Every renderer runs at top level. An earlier hand-maintained version had two charts
    accidentally nested inside the table's click handler, so they were blank until a reader
    clicked a row - which nobody does before reading the section a chart belongs to.
  * Metrics only Bengaluru can compute (drainage share, alignment gap) are filtered out of
    the switcher for the other five cities, and the active metric falls back to hazard when
    switching to a city that cannot show it. An all-grey map reads as a data error rather
    than a disclosure limit.
  * Listeners are attached with delegation on stable containers rather than re-bound to
    every path and row after each redraw. draw() and table() both replace their innerHTML,
    so per-node listeners die on every repaint and silently stop working.
"""

APP_JS = r"""
<script>
const D = __DATA__;
const CITIES = D.cities, R = D.R;
const PAL    = ["#eef2f4","#cfe0e8","#a8c8d7","#7aaac2","#4b88a8","#2c6a8c","#1c5d7d"];
const GAPPAL = ["#9b3226","#c06a58","#dda893","#efe7dc","#a9c4b2","#6d9e83","#3d7a5c"];

let cur = "bengaluru", metric = "hz";
let pinned = null, hov = null;
let sortK = "hz", sortAsc = false;
const active = () => (hov !== null ? hov : pinned);

/* `rich` metrics need ward-level TOTAL budget, which only Bengaluru publishes. */
const METRICS = {
  hz:    {lab:"Flood hazard",  unit:"",         pal:PAL,    dec:2,
          desc:"standardised share of unit below 5 m above nearest drainage"},
  spk:   {lab:"Drainage ₹/km²", unit:" Cr/km²", pal:PAL, dec:2,
          desc:"stormwater capital per km² over the whole panel"},
  share: {lab:"Drainage share", unit:"%",       pal:PAL,    dec:1, rich:true,
          desc:"drainage as % of the ward's works budget"},
  gap:   {lab:"Alignment gap",  unit:" pp",     pal:GAPPAL, dec:1, rich:true, diverge:true,
          desc:"residual - red = high hazard, low spend"}
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
  if(x==null||!isFinite(x)) return "-";
  const M=METRICS[m]; return (x>0&&M.diverge?"+":"")+x.toFixed(M.dec)+M.unit;
}

/* Equirectangular with a cos(lat) correction, rescaled to the active city's bounds. */
function project(c){
  const b=CITIES[c].bounds, W=560;
  const kx=Math.cos((b[1]+b[3])/2*Math.PI/180);
  const dx=(b[2]-b[0])*kx || 1, dy=(b[3]-b[1]) || 1;
  const H=Math.max(180,Math.round(W*dy/dx));
  return {W,H,px:(lon,lat)=>[(lon-b[0])*kx/dx*W,(b[3]-lat)/dy*H]};
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

/* ------------------------------------------------------------------ map */
function draw(){
  const C=CITIES[cur], P=project(cur), sc=scaleFor(cur,metric);
  document.getElementById("map").innerHTML =
    '<svg viewBox="0 0 '+P.W+' '+P.H+'" preserveAspectRatio="xMidYMid meet" role="img" '+
    'aria-label="Choropleth of '+C.label+' by '+METRICS[metric].lab+'">'+
    C.features.map((f,i)=>{const v=f.properties[metric];
      return '<path d="'+geo2path(f.geometry,P)+'" fill="'+colour(v,sc,metric)+'" data-i="'+i+'" '+
             'tabindex="0" role="button" aria-label="'+f.properties.nm+', '+fmt(v,metric)+'">'+
             '</path>';}).join("")+'</svg>';
  paint();
  const M=METRICS[metric];
  document.getElementById("scale").innerHTML = sc
    ? '<span>'+fmt(sc.lo,metric)+'</span><span class="bar" style="background:linear-gradient(90deg,'+
      M.pal.join(",")+')"></span><span>'+fmt(sc.hi,metric)+'</span>'+
      '<span style="flex:0 0 auto;margin-left:8px">'+M.desc+'</span>'
    : '<span>'+C.label+' does not publish this metric</span>';
}

/* Highlighting is separate from drawing: moving the cursor must not rebuild 198 SVG paths
   on every mousemove. draw() lays the geometry down once; paint() only swaps classes. */
function paint(){
  const a=active();
  document.querySelectorAll("#map path").forEach(p=>{
    const i=+p.dataset.i;
    p.classList.toggle("sel", i===pinned);
    p.classList.toggle("hov", i===hov && i!==pinned);
  });
  document.querySelectorAll("#tbl tbody tr").forEach(tr=>{
    const i=+tr.dataset.i;
    tr.classList.toggle("sel", i===pinned);
    tr.classList.toggle("hov", i===a && i!==pinned);
  });
}

function tip(ev,i){
  const el=document.getElementById("tip");
  if(i===null){el.style.display="none";return;}
  const p=CITIES[cur].features[i].properties;
  el.innerHTML='<b>'+p.nm+'</b><span>'+METRICS[metric].lab+' '+fmt(p[metric],metric)+'</span>';
  el.style.display="block";
  const pad=14, w=el.offsetWidth, h=el.offsetHeight;
  let x=ev.clientX+pad, y=ev.clientY+pad;
  if(x+w>window.innerWidth-8)  x=ev.clientX-w-pad;
  if(y+h>window.innerHeight-8) y=ev.clientY-h-pad;
  el.style.left=x+"px"; el.style.top=y+"px";
}

/* ------------------------------------------------------------------ read-out */
function show(){
  const C=CITIES[cur], el=document.getElementById("readout"), i=active();
  const head='<span class="eyebrow">'+C.unitWord.toUpperCase()+" READ-OUT</span>";
  if(i===null||!C.features[i]){
    el.innerHTML='<div class="ro">'+head+'<p class="note" style="margin-top:14px">Hover any '+
      C.unitWord+" on the map to preview it; click to keep it.</p></div>";
    return;
  }
  const p=C.features[i].properties, r=[];
  if(p.gap!=null) r.push(["Alignment",'<span class="tag '+(p.gap<0?"under":"over")+'">'+
    (p.gap<0?"UNDER":"OVER")+" by "+Math.abs(p.gap).toFixed(1)+" pp</span>"]);
  r.push(["Flood hazard (z)", p.hz==null?"-":p.hz.toFixed(2)]);
  if(p.hand!=null)     r.push(["Mean HAND", p.hand.toFixed(1)+" m"]);
  if(p.total_cr!=null) r.push(["Total capital", "₹"+p.total_cr.toFixed(1)+" Cr"]);
  r.push(["Stormwater spend", "₹"+p.storm_cr.toFixed(1)+" Cr"]);
  if(p.share!=null)    r.push(["Drainage share", p.share.toFixed(1)+"%"]);
  if(p.spk!=null)      r.push(["Per km²", "₹"+p.spk.toFixed(2)+" Cr/km²"]);
  if(p.area!=null)     r.push(["Area", p.area.toFixed(1)+" km²"]);
  if(p.pop!=null)      r.push(["Population (2011)", p.pop.toLocaleString()]);
  if(p.scst!=null)     r.push(["SC/ST share", p.scst.toFixed(1)+"%"]);
  r.push(["Years observed", p.uy]);
  const state = hov!==null && hov!==pinned
    ? '<span class="pill">previewing</span>'
    : (pinned!==null ? '<span class="pill pin">pinned</span>' : "");
  el.innerHTML='<div class="ro">'+head+state+"<h3>"+p.nm+"</h3>"+
    '<div class="sub">'+C.label+" · "+C.unitWord+" "+p.u+"</div>"+
    r.map(x=>'<div class="row"><span>'+x[0]+"</span><b>"+x[1]+"</b></div>").join("")+"</div>";
}

/* ------------------------------------------------------------------ table */
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
    '<table id="tbl"><thead><tr>'+cols.map(c=>{
      const on=c[0]===sortK;
      return '<th data-k="'+c[0]+'" tabindex="0" aria-sort="'+(on?(sortAsc?"ascending":"descending"):"none")+
             '">'+c[1]+(on?'<span class="ar">'+(sortAsc?"▲":"▼")+"</span>":"")+"</th>";}).join("")+
    "</tr></thead><tbody>"+idx.map(i=>{const p=C.features[i].properties;
      return '<tr data-i="'+i+'">'+cols.map(c=>{
        const k=c[0], v=p[k];
        if(k==="nm") return "<td>"+v+"</td>";
        if(v==null)  return "<td>-</td>";
        if(k==="gap") return '<td style="color:'+(v<0?"var(--gap)":"var(--good)")+'">'+
                             (v>0?"+":"")+v.toFixed(1)+"</td>";
        return "<td>"+(typeof v==="number"?v.toFixed(k==="hz"||k==="spk"?2:1):v)+"</td>";
      }).join("")+"</tr>";}).join("")+"</tbody></table>";
  /* the dropdown's closed label: "198 wards" / "15 zones" */
  const cnt=document.getElementById("tblcount");
  if(cnt) cnt.textContent=C.features.length+" "+C.unitWord+(C.features.length===1?"":"s");
  paint();
}

/* ------------------------------------------------------------------ events
   Delegated on containers that survive a repaint. draw() and table() replace their
   innerHTML wholesale, so listeners bound to individual paths or rows would be destroyed
   on the first redraw and every interaction would silently stop working. */
const mapBox = document.getElementById("map");
mapBox.addEventListener("mousemove", e=>{
  const t=e.target.closest("path");
  const i=t?+t.dataset.i:null;
  if(i!==hov){hov=i; paint(); show();}
  tip(e,i);
});
mapBox.addEventListener("mouseleave", ()=>{hov=null; paint(); show(); tip(null,null);});
mapBox.addEventListener("click", e=>{
  const t=e.target.closest("path"); if(!t) return;
  const i=+t.dataset.i;
  pinned = (pinned===i ? null : i);   /* clicking the pinned unit again releases it */
  paint(); show();
});
mapBox.addEventListener("keydown", e=>{
  const t=e.target.closest("path"); if(!t) return;
  if(e.key==="Enter"||e.key===" "){e.preventDefault(); pinned=+t.dataset.i; paint(); show();}
});
mapBox.addEventListener("focusin", e=>{
  const t=e.target.closest("path"); if(!t) return;
  hov=+t.dataset.i; paint(); show();
});

const tblBox = document.getElementById("tblwrap");
tblBox.addEventListener("mousemove", e=>{
  const tr=e.target.closest("tbody tr");
  const i=tr?+tr.dataset.i:null;
  if(i!==hov){hov=i; paint(); show();}
});
tblBox.addEventListener("mouseleave", ()=>{hov=null; paint(); show();});
tblBox.addEventListener("click", e=>{
  const th=e.target.closest("th");
  if(th){const k=th.dataset.k; sortAsc=(k===sortK)?!sortAsc:(k==="nm"); sortK=k; table(); return;}
  const tr=e.target.closest("tbody tr"); if(!tr) return;
  const i=+tr.dataset.i;
  pinned = (pinned===i ? null : i);
  paint(); show();
});
tblBox.addEventListener("keydown", e=>{
  const th=e.target.closest("th");
  if(th&&(e.key==="Enter"||e.key===" ")){
    e.preventDefault(); const k=th.dataset.k;
    sortAsc=(k===sortK)?!sortAsc:(k==="nm"); sortK=k; table();}
});

document.getElementById("metrics").addEventListener("click", e=>{
  const b=e.target.closest("button"); if(!b) return;
  metric=b.dataset.m; metricBar(); draw(); table();
});
document.getElementById("citysel").addEventListener("change", e=>{
  cur=e.target.value; hov=null;
  /* falling back keeps a city that cannot compute a metric from rendering an all-grey map */
  if(METRICS[metric].rich && !CITIES[cur].rich) metric="hz";
  if(METRICS[sortK] && METRICS[sortK].rich && !CITIES[cur].rich) sortK="hz";
  pinned=defaultSel();
  cityBar(); metricBar(); draw(); show(); table(); meta();
});

/* ------------------------------------------------------------------ chrome */
function metricBar(){
  const rich=CITIES[cur].rich;
  document.getElementById("metrics").innerHTML = Object.keys(METRICS)
    .filter(k=>!METRICS[k].rich||rich)
    .map(k=>'<button data-m="'+k+'"'+(metric===k?' class="on"':'')+
            ' aria-pressed="'+(metric===k)+'">'+METRICS[k].lab+"</button>").join("");
}
function cityBar(){
  const sel=document.getElementById("citysel");
  sel.innerHTML = Object.keys(CITIES).map(k=>{
    const c=CITIES[k];
    return '<option value="'+k+'"'+(cur===k?" selected":"")+">"+c.label+
           " - "+c.n+" "+c.unitWord+(c.n>1?"s":"")+"</option>";}).join("");
  sel.value=cur;
  const c=CITIES[cur];
  document.getElementById("cityhint").textContent =
    "FY"+c.fy[0]+"–"+c.fy[1]+" · ₹"+c.storm_cr.toLocaleString()+" Cr stormwater"+
    (c.rich?" · full decomposition":" · hazard + spending only");
}
function meta(){
  const c=CITIES[cur];
  document.getElementById("mapmeta").textContent =
    c.label+" · "+c.n+" "+c.unitWord+"s · FY"+c.fy[0]+"–"+c.fy[1]+
    " · ₹"+c.storm_cr.toLocaleString()+" Cr stormwater";
  document.getElementById("citynote").innerHTML = c.rich
    ? "Bengaluru is the only city publishing ward-level <b>total</b> capital spending alongside "+
      "stormwater, plus census population and an official flood-point inventory - so it is the "+
      "only one with a drainage share, an alignment gap and an equity read-out. The other five "+
      "show what they actually publish, which is why the headline is estimated here."
    : c.label+" publishes stormwater capital by "+c.unitWord+", but not the <b>total</b> "+
      c.unitWord+" budget - so the share and alignment-gap metrics that drive the headline "+
      "cannot be computed for it. Hazard and stormwater spending are shown; the decomposition "+
      "needs Bengaluru's disclosure.";
}

/* Open with the most flood-exposed unit pinned rather than an empty panel: the read-out
   sits beside a tall map, so "click something" leaves a large blank on first paint, which
   is what a thumbnail and a shared-link preview both capture. */
function defaultSel(){
  const F=CITIES[cur].features; let best=null,bv=-Infinity;
  F.forEach((f,i)=>{const v=f.properties.hz; if(v!=null&&isFinite(v)&&v>bv){bv=v;best=i;}});
  return best;
}
pinned = defaultSel();

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
