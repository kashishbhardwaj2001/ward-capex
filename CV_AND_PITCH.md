# CV lines and the spoken version

*(plan items 6.5 and 6.6)*

---

## CV — two lines, quantified

> **Ward-level climate finance study, India** — Built an end-to-end open-source pipeline
> testing whether Indian municipal capital spending reaches the neighbourhoods most exposed
> to flooding. Assembled 82,219 ward-tagged BBMP work orders (₹37,488 Cr, FY2011–2026) plus
> sub-city spending panels for Mumbai, Chennai, Ahmedabad, Pune and Surat; derived 30 m
> terrain-based flood hazard (HAND, Copernicus DEM) for 2,157 sub-city units across 22
> cities and validated it against 395 official BBMP/KSNDMC flood locations.

> **Finding (Bengaluru, 198 wards, FY2013–22):** flood-prone wards receive **8–13% smaller capital budgets** (p < 0.01) while
> allocating a *higher* share of what they get to drainage — the misallocation sits in the
> budget envelope, not the drainage line. Survives party fixed effects, an existing-stock
> control and a ward fixed-effects arm on time-varying rainfall; same sign in four of six
> cities.

### Shorter variant (one line, if space is tight)

> Built an open-source pipeline joining 82,219 municipal work orders to satellite-derived
> flood hazard across 22 Indian cities; found flood-prone wards receive 8–13% smaller capital
> budgets (p < 0.01); extended to six cities, though only Bengaluru's disclosure is fine-grained enough to test it.

---

## The 90-second spoken version

**The hook (10s)**
> Every Indian city is told to spend on climate resilience. Nobody has checked whether the
> money actually reaches the neighbourhoods that flood. I checked, for Bengaluru.

**The method (25s)**
> BBMP publishes every work order it pays — ward-tagged, dated, with a description. I pulled
> 82,000 of them, about ₹37,500 crore over thirteen years, and classified which were
> drainage. Then I built a flood-hazard surface from free 30-metre satellite elevation —
> essentially, how low each ward sits relative to the drains it feeds into — and validated it
> against BBMP's own list of 395 flood-prone locations. The top hazard quartile has 1.8 times
> the observed flood density of the bottom.

**The twist (25s)**
> The first answer looked like flood-prone wards spend *less* on drainage. But decomposing it,
> that's not a drainage decision at all. Those wards allocate a *higher* share of their budget
> to drainage — the engineers are prioritising correctly. They're just working from budgets
> that are 8 to 13 percent smaller. The misallocation is one level above where anyone looks.

**Why it matters (20s)**
> That's a problem for climate budget tagging. An audit of the drainage line in Bengaluru
> would conclude everything is fine. The gap only shows up in the denominator. And it isn't
> politics — alignment with the ruling party buys a ward nothing, and the effect survives
> party fixed effects.

**The close (10s)**
> Same negative sign in Chennai, Pune and Ahmedabad. Two cities don't replicate — Mumbai and
> Surat — and both report at a unit too coarse to resolve the question, so I report them
> rather than drop them. The whole thing runs on free data, and the code is public.

---

## Questions you will get, and the honest answers

**"Is this causal?"**
> No, and I don't claim it is. Terrain hazard is fixed — there's no counterfactual Bengaluru
> with flatter ground. It's descriptive with a decomposition. The causal version would need a
> budget-rule discontinuity, and I haven't found one.

**"How sensitive is it to how you define drainage?"**
> Very, and that's a finding in itself. The same budget is 1.3% or 46% drainage depending on
> the keyword tier — a 35-fold range. I validated it on 300 orders labelled by reading each
> description independently, twice, with arbitration — two passes agreed on 298 of 300. The
> medium tier is 99% precise with 96% recall, but **81% of the money it catches is bundled
> "roads and drains" work**. Under the strict definition — dedicated stormwater assets only —
> the effect on drainage share is significantly *positive*.
>
> Worth saying how I got there: my first validation used a regex to adjudicate the sample,
> and it reported exactly 100% precision. That was the tell — the adjudicator shared
> keywords with the classifier it was grading, so the classifier was marking its own
> homework. Re-labelled properly, the two agree only 90% of the time, and the regex failed
> in one direction: Indian work orders name the street a drain sits on, so anything keying
> on "road" mistakes location for scope.

**"Why should I trust a terrain proxy for flood risk?"**
> I shouldn't ask you to on faith, which is why I validated it. Spearman 0.26 against 395
> official flood points, with a clean monotonic gradient across quartiles. It's moderate, not
> strong — HAND measures topographic susceptibility, not drainage capacity or blockage. Good
> enough to rank wards; not a hydraulic model.

**"What's the biggest weakness?"**
> Attribution. BBMP's own data can't assign 27% of drainage spending to any ward — the highest
> of any category — because trunk drains span wards by construction. Those are built where
> water collects, so the missing money is concentrated in exactly the high-hazard wards. That
> biases me toward finding nothing, which makes the budget result more striking but the
> drainage null less conclusive.

**"Maybe those wards already have the drainage they need?"**
> That's the best objection, and I built a test for it. I pulled 660 km of mapped drainage
> line-work from OpenStreetMap and controlled for existing stock per ward. 87% of the effect
> survives. The p-value weakens from 0.016 to 0.085, but that's multicollinearity — the
> control correlates with hazard by construction, so the standard error widens 1.2× while the
> coefficient barely moves. And the test is biased in that objection's favour, because OSM
> mapping tracks affluence, so it overstates the stock in exactly the rich central wards the
> objection needs. Where it does earn credit: the penalty is twice as large in wards with
> little existing drainage. Stock absorbs part of the gap; it doesn't close it.

**"Isn't this just some fixed characteristic of those wards?"**
> That's the limit of a cross-section, and I couldn't answer it until I had a hazard measure
> that moves. CHIRPS daily rainfall does — 4.9 extreme-rain days per ward in 2016, 17.4 in
> 2022 — so I can put in a ward fixed effect and ask whether a ward that has an unusually wet
> year reallocates. It doesn't.
>
> That specification also caught me out, which I'd rather say than hide. Naively it shows a
> wet year *cutting* drainage spend, significant at 0.001 — a dramatic result. It's fake. The
> number of work orders falls too, and street lighting and buildings fall harder than
> drainage. Rain stops construction. These are payments, not budgets, so only the share is
> interpretable, and on the share nothing responds.

**"Is the falsification test clean?"**
> Cleaner than it first looked, and it cost me a rewrite. My original design was hazard-side —
> drainage responds to flood, parks to heat. It failed, and for a while I thought the finding
> had failed. The test had: the World Bank's heat layer takes six distinct values across 198
> wards because the grid is 25 km. It's a spatial dummy, not climate. I rebuilt it outcome-side
> and added a formal contrast test, and the honest answer is that the drainage tilt isn't
> drainage-specific — it's indistinguishable from roads and parks. High-hazard wards favour
> outdoor civil works generally. That actually strengthens the headline: there's no
> drainage-specific compensation inside the smaller budget.

**"Could you do this for another country?"**
> The hazard half runs anywhere on earth for free. The spending half is the constraint. I
> swept 1,099 datasets across 76 Indian municipal organisations — only six cities publish
> sub-city capital spending at all. South Africa's National Treasury publishes it for 257
> municipalities pre-coded by function, which is where I'd go next.
