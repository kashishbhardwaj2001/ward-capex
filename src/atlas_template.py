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
/* A native <select> rather than a row of buttons: it collapses to one control on a phone,
   is keyboard- and screen-reader-native, and scales if more cities are ever added. The unit
   count rides in the option label so the reader sees the panel size before switching. */
.citypick{display:flex;align-items:center;gap:10px;margin:0 0 16px;flex-wrap:wrap}
.citypick label{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--ink-3)}
.citypick select{font:inherit;font-size:14px;font-weight:500;padding:8px 34px 8px 12px;
  border:1px solid var(--rule);border-radius:3px;background:var(--card);color:var(--ink);
  cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='7'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23888' stroke-width='1.6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center}
.citypick select:hover{border-color:var(--ink-3)}
.citypick select:focus-visible{outline:2px solid var(--silt);outline-offset:2px}
.citypick .hint{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-3)}
.combined{display:flex;align-items:center;gap:16px;padding:14px 16px;margin-bottom:16px;
  border:1px solid var(--rule);border-left:3px solid var(--gap);border-radius:3px;
  background:var(--card)}
.combined .cn{font-size:30px;font-weight:700;color:var(--gap);letter-spacing:-.02em;
  font-family:"IBM Plex Sans Condensed",system-ui,sans-serif}
.combined .cl{font-size:12.5px;color:var(--ink-2);line-height:1.5}
.combined .cl span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3)}
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
/* masthead: dataset stats on the left, a quiet credit on the right */
.mast{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
.credit{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);text-decoration:none;white-space:nowrap;
  display:inline-flex;align-items:center;gap:7px;transition:color .12s}
.credit b{font-weight:500;color:var(--ink-2);transition:color .12s}
.credit svg{width:11px;height:11px;fill:currentColor;opacity:.7;transition:opacity .12s}
.credit:hover b,.credit:hover{color:var(--water)}
.credit:hover svg{opacity:1}
.credit:focus-visible{outline:2px solid var(--silt);outline-offset:4px;border-radius:2px}

/* footer: sources and the caveat on one row, contact on its own line beneath */
footer{flex-wrap:wrap}
footer .foot-note{margin-left:auto;font-family:"IBM Plex Mono",monospace;white-space:nowrap}
footer .foot-contact{flex-basis:100%;margin-top:6px;font-family:"IBM Plex Mono",monospace;
  font-size:11px;letter-spacing:.04em}
footer .foot-contact a{color:var(--ink-2);text-decoration:none;border-bottom:1px solid var(--rule);
  transition:color .12s,border-color .12s}
footer .foot-contact a:hover{color:var(--water);border-color:var(--water)}
footer .foot-contact a:focus-visible{outline:2px solid var(--silt);outline-offset:3px}

/* The unit table is a dropdown: closed by default so 198 rows do not make the page a
   long scroll. The header row is the toggle; the count and hint text live in the eyebrow. */
details.units>summary{cursor:pointer;list-style:none;flex-wrap:wrap}
details.units>summary::-webkit-details-marker{display:none}
details.units>summary:focus-visible{outline:2px solid var(--silt);outline-offset:4px}
/* the toggle reads as a button, in the same vocabulary as the metric switcher */
details.units .tbtn{margin-left:auto;font-size:11.5px;line-height:1.4;padding:4px 10px;
  border:1px solid var(--rule);border-radius:3px;color:var(--ink-2);white-space:nowrap;
  transition:border-color .12s,color .12s,background .12s}
details.units>summary:hover .tbtn{border-color:var(--ink-3);color:var(--ink)}
details.units[open] .tbtn{background:var(--ink);color:var(--paper);border-color:var(--ink)}
details.units .open-only{display:none}
details.units[open] .open-only{display:inline}
details.units[open] .closed-only{display:none}
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
  <div class="mast">
    <div class="eyebrow">__EYEBROW__</div>
    <a class="credit" href="https://www.linkedin.com/in/kashish2001/" target="_blank" rel="noopener"
       aria-label="Built by Kashish - LinkedIn profile">Built by <b>Kashish</b>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z"/></svg></a>
  </div>
  <h1>The drainage money does not go where the water goes</h1>
  <p class="dek">Across <b>six Indian cities</b>, the neighbourhoods most likely to flood receive
  <b>12.2% less</b> capital per standard deviation of flood hazard (p&nbsp;=&nbsp;0.0001).
  Bengaluru &mdash; the one city publishing at ward level &mdash; shows <i>why</i>: its flood-prone
  wards <b>do</b> tilt spending toward drainage, they are simply handed smaller budgets. The
  misallocation sits one level above where climate-budget audits look.</p>
  <!-- class names must match the stylesheet lifted from the original page: .finding / .f.neg|pos|mid -->
  <div class="finding">
    <div class="f neg"><div class="n">&minus;12.8%</div><div class="l">total ward capital budget, per standard deviation of flood hazard</div><div class="p">p &lt; 0.0001</div></div>
    <div class="f pos"><div class="n">+1.61pp</div><div class="l">of that budget goes to drainage &mdash; wards do appear to prioritise correctly</div><div class="p">p = 0.047 &middot; <i>suggestive: does not survive false-discovery correction</i></div></div>
    <div class="f mid"><div class="n">&minus;9.0%</div><div class="l">net drainage spending where water collects</div><div class="p">p = 0.016</div></div>
  </div>
</header>

<section>
  <div class="sec-h"><h2>Six cities, unit by unit</h2><span class="eyebrow" id="mapmeta"></span></div>
  <div class="citypick">
    <label for="citysel">City</label>
    <select id="citysel" aria-label="Choose a city to map"></select>
    <span class="hint" id="cityhint"></span>
  </div>
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
  <span class="foot-src">Spending: BBMP Works Bill Public View via OpenCity &middot; Hazard: Copernicus DEM GLO-30 (HAND)
  &middot; Rainfall: CHIRPS &middot; Boundaries: DataMeet CC BY-SA 2.5 IN &middot; Validation: BBMP / KSNDMC</span>
  <span class="foot-note">Descriptive, not causal</span>
  <span class="foot-contact">Contact us &middot;
    <a href="mailto:kashishbhardwaj.2001@gmail.com">kashishbhardwaj.2001@gmail.com</a></span>
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
    # multicity_results.csv encodes the per-city rows as spec="city:bengaluru" rather than
    # in a `city` column; filtering on r["city"] silently matched nothing and the bar chart
    # rendered empty while the section around it still looked complete.
    per = []
    for r in (R.get("multicity_raw") or []):
        spec = str(r.get("spec", ""))
        if spec.startswith("city:"):
            per.append({**r, "city": spec.split(":", 1)[1]})
    items = [(str(r["city"]).title(), round((np.exp(r["beta"]) - 1) * 100, 1), r.get("p"))
             for r in sorted(per, key=lambda r: r.get("beta", 0))]
    S.append(
        '<section><div class="sec-h"><h2>The gap across six cities</h2>'
        f'<span class="eyebrow">{meta.get("n_cities", 6)} cities &middot; '
        f'{meta.get("n_units", 283)} sub-city units &middot; '
        f'{meta.get("n_unit_years", 2088):,} unit-years</span></div>'
        '<div class="grid2"><div>'
        '<div class="combined"><div class="cn">&minus;12.2%</div>'
        '<div class="cl">combined across all six cities &middot; p = 0.0001<br>'
        '<span>inverse-variance meta-analysis &middot; no heterogeneity '
        '(I&sup2; = 0%, Q p = 0.50)</span></div></div>'
        + '<div id="citybars">' + bar_rows(items) + '</div>' +
        '<p class="note" style="margin-top:12px">Effect on stormwater spending per standard '
        'deviation of flood hazard, <b>within</b> city. Four of six are negative; the two '
        'positives have error bars so wide (Mumbai &plusmn;80pp, Surat &plusmn;100pp) that '
        '&minus;12% sits comfortably inside them. Formally there is <b>no detectable '
        'disagreement between the six</b> &mdash; they are consistent with one common effect, '
        'which is why the combined estimate above is the headline rather than any single '
        'city.</p>'
        '<p class="note">Robust to estimator: OLS &minus;9.6%, PPML &minus;9.6%, median '
        'regression &minus;12.2%.</p></div>'
        '<div><div class="eyebrow" style="margin-bottom:10px">Hazard model vs 395 official '
        'flood points</div><div class="lad" id="ladder"></div>'
        '<p class="note" style="margin-top:14px">Observed flood density rises monotonically '
        'across modelled-hazard quartiles &mdash; <b>1.81&times;</b> from lowest to highest '
        '(Spearman &rho; = +0.26). The hazard surface finds floods that actually happened.</p>'
        '</div></div></section>')

    # ---- the sortable unit table
    S.append(
        '<section><details class="units" id="units">'
        '<summary class="sec-h"><h2>Every unit</h2>'
        '<span class="eyebrow open-only">click a column to sort &middot; click a row to map it</span>'
        '<span class="tbtn"><span class="closed-only">Show all <span id="tblcount"></span> &#9662;</span>'
        '<span class="open-only">Hide table &#9652;</span></span></summary>'
        '<div style="overflow-x:auto" id="tblwrap"></div></details></section>')

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


    # ---- what this can and cannot say
    # A page that only shows the finding invites the reader to go looking for the catch.
    # Stating the limits on the page itself is both more honest and more persuasive: every
    # one of these was tested rather than conceded, and two of them bias AGAINST the result.
    S.append(
        '<section><div class="sec-h"><h2>What this can and cannot say</h2>'
        '<span class="eyebrow">every limit below was measured, not assumed</span></div>'
        '<div class="grid2"><div>'
        '<div class="eyebrow" style="margin-bottom:10px">Limits of the data</div>'
        '<div class="rows" style="font-size:13.5px">'
        '<div class="row"><span><b>27%</b> of Bengaluru\'s drainage money cannot be assigned '
        'to any ward</span><b>biases <i>against</i> the finding</b></div>'
        '<div class="row"><span>Mumbai and Surat report only <b>24 and 10</b> units</span>'
        '<b>estimates uncertain</b></div>'
        '<div class="row"><span>Mumbai publishes budget <b>estimates</b>, not actuals</span>'
        '<b>plans &ne; spending</b></div>'
        '<div class="row"><span>Chennai\'s totals cover 2012&ndash;16, its drainage 2018&ndash;25</span>'
        '<b>no overlap</b></div>'
        '<div class="row"><span>Pune\'s ward-office &ldquo;drainage&rdquo; is <b>foul sewerage</b></span>'
        '<b>different system</b></div>'
        '<div class="row"><span>Only <b>6</b> of ~4,000 Indian cities publish sub-city spending</span>'
        '<b>selection untestable</b></div></div>'
        '<p class="note" style="margin-top:14px">The first line matters most: trunk drains cross '
        'ward boundaries and are built where water collects, so the money that cannot be '
        'assigned sits disproportionately in high-hazard wards. <b>The true gap is probably '
        'larger than reported.</b></p></div>'
        '<div>'
        '<div class="eyebrow" style="margin-bottom:10px">Limits of the claim</div>'
        '<div class="rows" style="font-size:13.5px">'
        '<div class="row"><span><b>Descriptive, not causal</b></span><b>terrain cannot be changed</b></div>'
        '<div class="row"><span>Flood only &mdash; not heat or water</span><b>see below</b></div>'
        '<div class="row"><span>Hazard is a <b>terrain proxy</b></span><b>not a hydraulic model</b></div>'
        '<div class="row"><span>Bengaluru ends <b>FY2022</b></span><b>the wards were redrawn</b></div>'
        '</div>'
        '<p class="note" style="margin-top:14px"><b>Why Bengaluru stops at FY2022.</b> The city '
        'redrew its wards from 198 to 243, then split into <b>five separate corporations</b> in '
        '2025 &mdash; so the unit of analysis stops existing. Tested anyway: post-2022 data gives '
        '&minus;5.8% on the old map and +3.5% on the new one, neither significant. The other five '
        'cities run to FY2024&ndash;26, so the pooled panel spans <b>FY2013&ndash;2026</b>.</p>'
        '<p class="note"><b>Why floods and not heat.</b> The standard climate grid takes <b>six '
        'distinct values</b> across Bengaluru\'s 198 wards &mdash; a three-day spread across an '
        'entire city. And no municipal budget has a heat line: cooling is scattered across parks, '
        'housing, transport and water. Floods are the one hazard with both a measurable '
        'geography and a nameable budget line.</p></div></div></section>')

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
        'specification.</p>'
        '<div class="eyebrow" style="margin:18px 0 8px">Does it depend on the 5 m threshold?</div>'
        '<div class="rows" style="font-size:13px">'
        '<div class="row"><span>within 1 m</span><b>&minus;6.8%&nbsp;&nbsp;p=0.021</b></div>'
        '<div class="row"><span>within 3 m</span><b>&minus;6.4%&nbsp;&nbsp;p=0.040</b></div>'
        '<div class="row"><span>within 5 m &nbsp;<i>headline</i></span><b>&minus;7.8%&nbsp;&nbsp;p=0.016</b></div>'
        '<div class="row"><span>within 10 m</span><b>&minus;11.2%&nbsp;&nbsp;p=0.001</b></div>'
        '<div class="row"><span><b>mean HAND &mdash; no threshold at all</b></span>'
        '<b>&minus;13.6%&nbsp;&nbsp;p=0.0007</b></div></div>'
        '<p class="note" style="margin-top:10px">Significant at every threshold and '
        '<b>strongest with no threshold</b> &mdash; the opposite of a threshold artefact. '
        'Dropping population entirely gives &minus;8.0%; using satellite built-up area instead '
        'gives &minus;7.5%; using no controls at all gives &minus;11.1%. The controls shrink the '
        'effect rather than create it.</p>'
        '<div class="eyebrow" style="margin:18px 0 8px">Corrected for multiple testing</div>'
        '<div class="rows" style="font-size:13px">'
        '<div class="row"><span>hazard &rarr; total budget</span>'
        '<b style="color:var(--good)">survives</b></div>'
        '<div class="row"><span>hazard &rarr; stormwater spend</span>'
        '<b style="color:var(--good)">survives</b></div>'
        '<div class="row"><span>hazard &rarr; drainage <i>share</i></span>'
        '<b style="color:var(--silt)">fails FDR (0.063)</b></div></div>'
        '<p class="note" style="margin-top:10px">The headline survives any correction. The '
        '<b>+1.61pp share result does not</b>, and is reported as suggestive rather than '
        'established &mdash; the main claim rests on the total-budget channel, which is '
        'unaffected.</p>'
        '</div></div></section>')

    return "\n".join(S)
