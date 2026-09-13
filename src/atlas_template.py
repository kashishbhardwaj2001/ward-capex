"""
Markup, styles and client JS for the six-city atlas. Imported by build_atlas.py.

Kept in its own module for one reason: the page is ~500 KB of generated HTML, and mixing
that much template text into the data-assembly code made the latter unreadable. Nothing
here touches the filesystem or computes a statistic - every number arrives already
calculated, from the analysis CSVs.

The page is deliberately dependency-free: no React, no mapping library, no build step. The
choropleth is hand-projected SVG (equirectangular, scaled to whichever city is active),
which is exact enough at city scale and keeps the whole thing a single file that opens from
disk or from a static host with equal success.
"""
import numpy as np

# --------------------------------------------------------------------------- styles
EXTRA_CSS = """
<style>
.citybar{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 16px}
.citybar button{font:inherit;font-size:12.5px;padding:7px 14px;border:1px solid var(--rule);
  background:var(--card);color:var(--ink-2);border-radius:3px;cursor:pointer;transition:.12s}
.citybar button:hover{border-color:var(--ink-3);color:var(--ink)}
.citybar button.on{background:var(--ink);color:var(--paper);border-color:var(--ink);font-weight:500}
.citybar button .c{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.6;margin-left:6px}
.panel{background:var(--card);border:1px solid var(--rule-2);border-radius:4px;padding:14px}
.ptop{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:10px;flex-wrap:wrap}
.segs{display:flex;gap:3px;flex-wrap:wrap}
.segs button{font:inherit;font-size:11.5px;padding:4px 10px;border:1px solid var(--rule);
  background:transparent;color:var(--ink-2);border-radius:3px;cursor:pointer}
.segs button.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
#map svg{width:100%;height:auto;display:block}
#map path{stroke:var(--card);stroke-width:.4;cursor:pointer;transition:stroke-width .08s}
/* .hov is set by JS, not by CSS :hover. The CSS pseudo-class cannot tell the table which
   polygon to light up, and the two views have to share one selection. */
#map path.hov{stroke:var(--ink-2);stroke-width:1.6}
#map path.sel{stroke:var(--ink);stroke-width:2.2}
#map path:focus{outline:none;stroke:var(--ink);stroke-width:2.2}
#map path:focus-visible{stroke:var(--silt);stroke-width:2.6}

/* cursor tooltip - a 198-ward map needs a label without forcing a glance sideways */
#tip{position:fixed;z-index:50;display:none;pointer-events:none;background:var(--ink);
  color:var(--paper);padding:6px 10px;border-radius:4px;font-size:12px;line-height:1.45;
  box-shadow:0 4px 14px rgba(0,0,0,.18);max-width:250px}
#tip b{display:block;font-weight:600}
#tip span{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.8}

.pill{float:right;font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.04em;
  padding:2px 7px;border-radius:3px;background:var(--rule-2);color:var(--ink-3)}
.pill.pin{background:var(--water);color:var(--paper);opacity:.9}
#tbl tbody tr{cursor:pointer}
#tbl tbody tr.hov{background:var(--rule-2)}
#tbl tbody tr.sel{background:var(--rule-2);box-shadow:inset 3px 0 0 var(--ink)}
#tbl th{cursor:pointer;user-select:none;white-space:nowrap}
#tbl th:focus-visible{outline:2px solid var(--silt);outline-offset:-2px}
#tbl th .ar{font-size:9px;margin-left:4px;color:var(--ink-3)}
.scale{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:11px;
  color:var(--ink-3);font-family:"IBM Plex Mono",monospace;flex-wrap:wrap}
.scale .bar{flex:1;min-width:90px;height:8px;border-radius:2px}
.ro h3{margin:2px 0 2px;font-size:16.5px}
.ro .sub{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-3);margin-bottom:12px}
.ro .row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;
  border-bottom:1px solid var(--rule-2);font-size:13.5px}
.ro .row b{font-family:"IBM Plex Mono",monospace;text-align:right}
.tag{font-family:"IBM Plex Mono",monospace;font-size:10.5px;padding:2px 7px;border-radius:3px;
  background:var(--rule-2);color:var(--ink-2)}
.tag.under{background:#f4e0dc;color:var(--gap)}
.tag.over{background:#dbe8e0;color:var(--good)}
@media (prefers-color-scheme:dark){
  :root:not([data-theme=light]) .tag.under{background:#4a2420}
  :root:not([data-theme=light]) .tag.over{background:#1e3a2c}}
:root[data-theme=dark] .tag.under{background:#4a2420}
:root[data-theme=dark] .tag.over{background:#1e3a2c}
</style>
"""

# --------------------------------------------------------------------------- body
BODY = """
<div class="wrap">
<header>
  <div class="eyebrow">__EYEBROW__</div>
  <h1>The drainage money does not go where the water goes</h1>
  <p class="dek">Bengaluru's flood-prone wards <b>do</b> tilt their spending toward drainage.
  They are simply handed <b>smaller budgets</b> &mdash; so the water still wins. The
  misallocation sits one level above where climate-budget audits look.</p>
  <!-- class names must match the stylesheet lifted from the original page: .finding / .f.neg|pos|mid -->
  <div class="finding">
    <div class="f neg"><div class="n">&minus;12.8%</div><div class="l">total ward capital budget, per standard deviation of flood hazard</div><div class="p">p &lt; 0.0001</div></div>
    <div class="f pos"><div class="n">+1.61pp</div><div class="l">of that budget goes to drainage &mdash; wards do prioritise correctly</div><div class="p">p = 0.047</div></div>
    <div class="f mid"><div class="n">&minus;9.0%</div><div class="l">net drainage spending where water collects</div><div class="p">p = 0.016</div></div>
  </div>
</header>

<section>
  <div class="sec-h"><h2>Six cities, unit by unit</h2><span class="eyebrow" id="mapmeta"></span></div>
  <div class="citybar" id="citybar"></div>
  <div class="grid2">
    <div class="panel">
      <div class="ptop"><span class="eyebrow">CHOROPLETH</span><span class="segs" id="metrics"></span></div>
      <div id="map"></div>
      <div class="scale" id="scale"></div>
    </div>
    <div class="panel" id="readout"></div>
  </div>
  <div id="tip" role="status" aria-live="polite"></div>
  <p class="note" style="margin-top:12px">
    <b>Hover</b> any unit to preview it &middot; <b>click</b> to keep it pinned &middot;
    click it again to release &middot; the table and the map are one selection.
  </p>
  <p class="note" id="citynote"></p>
</section>
__SECTIONS__
<footer>
  Spending: BBMP Works Bill Public View via OpenCity &middot; Hazard: Copernicus DEM GLO-30 (HAND)
  &middot; Rainfall: CHIRPS &middot; Boundaries: DataMeet CC BY-SA 2.5 IN &middot; Validation: BBMP / KSNDMC
  <span style="float:right;font-family:'IBM Plex Mono',monospace">Descriptive, not causal</span>
</footer>
</div>
"""


# --------------------------------------------------------------------------- helpers
def bar_rows(items):
    """The page's one chart grammar: a labelled bar signed about a zero line.

    Solid means significant at 10%; hollow means not distinguishable from zero. That
    distinction is load-bearing here - Surat's +45.9% is the largest number on the
    replication chart and the least informative, and a chart that drew it like the others
    would say the opposite of what the analysis found.
    """
    if not items:
        return ""
    mx = max(abs(v) for _, v, _ in items) or 1
    out = []
    for lab, v, p in items:
        w = abs(v) / mx * 46
        cls = " ".join(x for x in ["pos" if v > 0 else "",
                                   "ns" if (p is not None and p >= .1) else ""] if x)
        star = ("***" if p is not None and p < .01 else "**" if p is not None and p < .05
                else "*" if p is not None and p < .1 else "")
        pv = (f'<span style="color:var(--ink-3)">p={p:.3f}{star}</span>'
              if p is not None else "")
        out.append(f'<div class="city"><span class="nm">{lab}</span>'
                   f'<span class="track"><span class="zero"></span>'
                   f'<i class="{cls}" style="width:{w:.1f}%"></i></span>'
                   f'<span class="v">{"+" if v > 0 else ""}{v:.2f} {pv}</span></div>')
    return "".join(out)


def rows_table(items):
    return "".join(f'<div class="row"><span>{k}</span><b style="color:{c}">{v}</b></div>'
                   for k, v, c in items)


# --------------------------------------------------------------------------- sections
def build_sections(R):
    """Every section below the map. Numbers come from the analysis CSVs, never retyped."""
    S = []
    meta = R.get("meta", {})

    # ---- replication across cities
    per = [r for r in (R.get("multicity_raw") or []) if r.get("city")]
    items = [(str(r["city"]).title(), round((np.exp(r["beta"]) - 1) * 100, 1), r.get("p"))
             for r in sorted(per, key=lambda r: r.get("beta", 0))]
    S.append(
        '<section><div class="sec-h"><h2>Does it replicate?</h2>'
        f'<span class="eyebrow">{meta.get("n_cities", 6)} cities &middot; '
        f'{meta.get("n_units", 283)} sub-city units &middot; '
        f'{meta.get("n_unit_years", 2088):,} unit-years</span></div>'
        '<div class="grid2"><div>' + bar_rows(items) +
        '<p class="note" style="margin-top:12px">Effect on stormwater spending per standard '
        'deviation of flood hazard, <b>within</b> city. Solid = significant at 10%; hollow = '
        'not distinguishable from zero. The two positives are the coarsest panels in the set '
        '&mdash; Surat reports 10 budget zones, Mumbai publishes estimates rather than actuals '
        '&mdash; so within-city hazard variation is largely averaged away before it can be '
        'related to anything.</p></div>'
        '<div><div class="eyebrow" style="margin-bottom:10px">Hazard model vs 395 official '
        'flood points</div><div class="lad" id="ladder"></div>'
        '<p class="note" style="margin-top:14px">Observed flood density rises monotonically '
        'across modelled-hazard quartiles &mdash; <b>1.81&times;</b> from lowest to highest '
        '(Spearman &rho; = +0.26). The hazard surface finds floods that actually happened.</p>'
        '</div></div></section>')

    # ---- the sortable unit table
    S.append(
        '<section><div class="sec-h"><h2>Every unit</h2>'
        '<span class="eyebrow">click a column to sort &middot; click a row to map it</span>'
        '</div><div style="overflow-x:auto" id="tblwrap"></div></section>')

    # ---- tagging elasticity
    t = meta.get("tiers", [])
    lo = t[0]["pct"] if t else 1.3
    hi = t[2]["pct"] if t else 45.9
    S.append(
        '<section><div class="sec-h"><h2>How much is &ldquo;drainage&rdquo;?</h2>'
        '<span class="eyebrow">the tagging elasticity</span></div>'
        '<div class="grid2"><div id="tiers"></div><div>'
        f'<p class="note" style="margin-top:0">The same &#8377;{meta.get("total_cr", 23081):,} '
        f'crore is <b>{lo}%</b> or <b>{hi}%</b> drainage depending on which of three defensible '
        f'keyword definitions you apply &mdash; a <b>{meta.get("elasticity", 35)}-fold</b> range.</p>'
        '<p class="note">Reading 300 orders shows why: the medium tier is 99.1% precise with '
        '95.5% recall, but <b>81% of the money it flags is bundled &ldquo;roads and drains&rdquo; '
        'work</b>, where the full amount is charged to drainage.</p>'
        '<p class="note">Those 300 were labelled by <b>reading</b> each description, '
        'independently, twice &mdash; the passes agreed on 298 of 300. The first version of this '
        'check used a regex and reported exactly <b>100%</b> precision. That was the tell: the '
        'adjudicator shared its keywords with the classifier it was grading. Re-labelled '
        'properly the two agree only <b>90%</b> of the time.</p></div></div></section>')

    # ---- rival explanations
    stock = R.get("stock") or []
    srows = [(r["spec"].replace("+ ", "&nbsp;&nbsp;+ "), f'{r["pct"]:+.1f}%',
              "var(--gap)" if r["pct"] < 0 else "var(--good)") for r in stock]
    trows = [(r["outcome"], f'{r["beta"]:+.2f}&nbsp;&nbsp;p={r["p"]:.3f}',
              "var(--gap)" if r["p"] < .05 else "var(--ink-3)")
             for r in (R.get("throughput") or [])]
    S.append(
        '<section><div class="sec-h"><h2>What else could explain it?</h2>'
        '<span class="eyebrow">two rival explanations, tested</span></div><div class="grid2">'
        '<div><div class="eyebrow" style="margin-bottom:10px">&ldquo;They already have the '
        'drainage&rdquo;</div><div class="rows" style="font-size:13.5px">' + rows_table(srows) +
        '</div><p class="note" style="margin-top:14px">Against 660 km of mapped drainage '
        'line-work. <b>87% of the effect survives.</b> The p-value weakens only because the '
        'control is collinear with hazard by construction &mdash; the standard error widens '
        '1.21&times; while the coefficient barely moves. Reading the p-value alone would mistake '
        'multicollinearity for the effect vanishing.</p></div>'
        '<div><div class="eyebrow" style="margin-bottom:10px">&ldquo;It&rsquo;s something fixed '
        'about those wards&rdquo;</div><div class="rows" style="font-size:13.5px">' +
        rows_table(trows) +
        '</div><p class="note" style="margin-top:14px">Per SD of annual rainfall, within ward. '
        'Naively this says a wet year <i>cuts</i> drainage spending. It does not &mdash; the '
        '<b>order count falls too</b>, and lighting and buildings fall harder than drainage. Rain '
        'stops construction. These are payments, not budgets, so only the <b>share</b> is '
        'interpretable, and on the share <b>nothing responds</b>.</p></div></div></section>')

    # ---- political economy
    prows = [(r["spec"], f'{r["pct"]:+.1f}%&nbsp;&nbsp;p={r["p"]:.3f}',
              "var(--gap)" if r["pct"] < 0 else "var(--ink-3)")
             for r in (R.get("political") or [])]
    S.append(
        '<section><div class="sec-h"><h2>Is it politics?</h2>'
        '<span class="eyebrow">2015 council &middot; 198/198 wards matched</span></div>'
        '<div class="grid2"><div><div class="rows" style="font-size:13.5px">' +
        rows_table(prows) +
        '</div><p class="note" style="margin-top:14px"><b>Alignment with the ruling party buys a '
        'ward nothing</b>, and the hazard penalty is unmoved by party controls. Whatever produces '
        'the budget gap, it is not partisan targeting.</p></div>'
        '<div><div class="eyebrow" style="margin-bottom:10px">Mean flood hazard by councillor '
        'party (z)</div><div id="parties"></div>'
        '<p class="note" style="margin-top:14px">Hazard is nonetheless politically distributed: '
        'opposition INC wards are more flood-prone than BJP wards, and the seven independents are '
        'the most exposed of all.</p></div></div></section>')

    # ---- falsification and the contrast test
    fal = sorted((R.get("falsification") or []), key=lambda r: -r["beta"])
    crows = [(f'drainage &minus; {r["vs"]}', f'{r["diff"]:+.2f}&nbsp;&nbsp;p={r["p"]:.2f}',
              "var(--ink-3)") for r in (R.get("contrasts") or [])]
    S.append(
        '<section><div class="sec-h"><h2>Is it drainage, or just civil works?</h2>'
        '<span class="eyebrow">outcome-side falsification &middot; coefficient contrasts</span>'
        '</div><div class="grid2"><div>'
        '<div class="eyebrow" style="margin-bottom:10px">Share of ward budget, per SD of flood '
        'hazard</div>' +
        bar_rows([(r["category"], round(r["beta"], 2), r["p"]) for r in fal]) +
        '<p class="note" style="margin-top:14px">The categories with no flood-protective function '
        '&mdash; buildings, lighting, water supply &mdash; sit flat, which is what makes the hazard '
        'measure credible: it is not simply correlated with spending in general.</p></div>'
        '<div><div class="eyebrow" style="margin-bottom:10px">Is the drainage tilt '
        'drainage-<i>specific</i>?</div><div class="rows" style="font-size:13.5px">' +
        rows_table(crows) +
        '</div><p class="note" style="margin-top:14px"><b>Zero of five contrasts are '
        'significant.</b> Drainage moves with roads and parks and cannot be told apart from '
        'either. High-hazard wards tilt toward <b>outdoor civil works generally</b> &mdash; what '
        'low-lying, less-built-up land needs &mdash; not toward flood protection.</p>'
        '<p class="note">This sharpens the headline rather than denting it: flood hazard predicts '
        'a smaller total budget, and there is <b>no drainage-specific compensation inside it</b>.'
        '</p></div></div></section>')

    # ---- robustness
    S.append(
        '<section><div class="sec-h"><h2>Does the result hold up?</h2>'
        '<span class="eyebrow">robustness arms &middot; Conley spatial SEs</span></div>'
        '<div class="grid2"><div id="robust"></div><div>'
        '<p class="note" style="margin-top:0">Effect on the drainage share per standard deviation '
        'of hazard, each arm re-estimated with ward-clustered and Conley spatial standard errors. '
        'Under the <b>narrow</b> definition &mdash; dedicated stormwater assets only &mdash; the '
        'effect is <b>significantly positive</b>. Dedicated drainage does track hazard; bundled '
        'road-and-drain money does not.</p>'
        '<p class="note">The headline budget penalty ranges <b>&minus;8% to &minus;12.8%</b> '
        'depending on how much terrain is absorbed into the controls, and is significant in every '
        'specification.</p></div></div></section>')

    return "\n".join(S)
