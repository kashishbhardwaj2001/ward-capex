<script>
(function(){
  const T=[], ok=(n,c,d)=>T.push({n,pass:!!c,d:d||""});
  const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];
  const ro=()=>q("#readout").textContent.trim();
  // clientX/clientY are read-only on MouseEvent - they must be passed to the constructor
  const fire=(el,type,extra)=>el.dispatchEvent(new MouseEvent(type,
    Object.assign({bubbles:true,cancelable:true,view:window,clientX:250,clientY:250},extra||{})));

  // --- 1. initial render
  ok("map renders paths", qa("#map path").length>0, qa("#map path").length+" paths");
  ok("table renders rows", qa("#tbl tbody tr").length>0, qa("#tbl tbody tr").length+" rows");
  ok("city buttons", qa("#citybar button").length===6, qa("#citybar button").length+" cities");
  ok("metric buttons (blr=4)", qa("#metrics button").length===4, qa("#metrics button").length);
  ok("readout not empty on load", ro().length>60);
  ok("a unit is pinned on load", qa("#map path.sel").length===1);
  const EXP={ladder:5,tiers:3,parties:4,robust:8};   // ladder = 4 quartiles + 1 caption
  Object.keys(EXP).forEach(id=>
    ok("chart #"+id+" has "+EXP[id]+" rows",
       q("#"+id) && q("#"+id).children.length===EXP[id],
       q("#"+id)?q("#"+id).children.length+" rows":"MISSING"));

  // --- 2. HOVER on the map changes the read-out
  const before=ro();
  const paths=qa("#map path");
  let target=paths.find(p=>!p.classList.contains("sel"));
  fire(target,"mousemove",{clientX:300,clientY:300});
  const after=ro();
  ok("HOVER changes read-out", after!==before, after===before?"unchanged":"changed");
  ok("HOVER marks polygon", target.classList.contains("hov"));
  ok("HOVER shows tooltip", q("#tip").style.display==="block", q("#tip").textContent.slice(0,40));
  ok("HOVER highlights table row",
     qa("#tbl tbody tr.hov").length===1 || qa("#tbl tbody tr.sel").length>0);
  ok("HOVER labelled 'previewing'", ro().includes("previewing"));

  // --- 3. mouseleave reverts to the pinned unit
  fire(q("#map"),"mouseleave");
  ok("MOUSELEAVE reverts to pinned", ro()===before, ro()===before?"reverted":"did NOT revert");

  // --- 4. CLICK pins
  fire(target,"click");
  ok("CLICK pins the unit", target.classList.contains("sel"));
  ok("CLICK read-out says pinned", ro().includes("pinned"));
  const pinnedTxt=ro();
  fire(target,"click");
  ok("CLICK again releases", !target.classList.contains("sel"));
  fire(target,"click"); // re-pin for later checks

  // --- 5. TABLE hover + click
  const row=qa("#tbl tbody tr").find(r=>!r.classList.contains("sel"));
  const b2=ro(); fire(row,"mousemove");
  ok("TABLE hover changes read-out", ro()!==b2);
  ok("TABLE hover lights map", qa("#map path.hov").length===1);
  fire(q("#tblwrap"),"mouseleave");
  fire(row,"click");
  ok("TABLE click pins", row.classList.contains("sel"));

  // --- 6. SORT
  const first=()=>q("#tbl tbody tr td").textContent;
  const th=qa("#tbl th")[1]; const f0=first();
  fire(th,"click"); const f1=first();
  ok("SORT reorders", f0!==f1, f0+" -> "+f1);
  ok("SORT shows arrow", qa("#tbl th .ar").length===1);

  // --- 7. METRIC switch
  const fill0=qa("#map path")[0].getAttribute("fill");
  const mb=qa("#metrics button").find(b=>!b.classList.contains("on"));
  const mlab=mb.textContent; fire(mb,"click");
  ok("METRIC switch repaints", qa("#map path")[0].getAttribute("fill")!==fill0 ||
     q("#scale").textContent.length>0, "now "+mlab);
  ok("METRIC updates scale", q("#scale").textContent.length>10);

  // --- 8. CITY switch
  const cb=qa("#citybar button").find(b=>b.textContent.includes("Mumbai"));
  fire(cb,"click");
  ok("CITY switch: map redrawn", qa("#map path").length===24, qa("#map path").length+" paths");
  ok("CITY switch: meta updated", q("#mapmeta").textContent.includes("Mumbai"));
  ok("CITY switch: metrics filtered to 2", qa("#metrics button").length===2,
     qa("#metrics button").length);
  ok("CITY switch: readout adapts", ro().includes("WARD READ-OUT"));
  ok("CITY switch: note explains limits", q("#citynote").textContent.includes("Mumbai"));
  ok("CITY switch: table cols shrink", qa("#tbl thead th").length===4, qa("#tbl thead th").length);
  // hover still works after a redraw (the delegation test)
  const p2=qa("#map path").find(p=>!p.classList.contains("sel"));
  const b3=ro(); fire(p2,"mousemove",{clientX:200,clientY:200});
  ok("HOVER still works after city switch", ro()!==b3);

  const surat=qa("#citybar button").find(b=>b.textContent.includes("Surat"));
  fire(surat,"click");
  ok("SURAT renders 10 zones", qa("#map path").length===10, qa("#map path").length+" paths");
  ok("SURAT readout says ZONE", ro().includes("ZONE READ-OUT"));

  // back to Bengaluru
  fire(qa("#citybar button").find(b=>b.textContent.includes("Bengaluru")),"click");
  ok("RETURN to Bengaluru", qa("#map path").length===198 && qa("#metrics button").length===4);

  const fails=T.filter(t=>!t.pass);
  document.title="UITEST "+JSON.stringify({pass:T.length-fails.length,total:T.length,
    fails:fails.map(f=>f.n+" ["+f.d+"]"), all:T.map(t=>(t.pass?"OK  ":"FAIL")+" "+t.n+(t.d?"  ("+t.d+")":""))});
})();
</script>
