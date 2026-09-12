# CV lines and the spoken version

*(plan items 6.5 and 6.6)*

---

## CV — two lines, quantified

> **Ward-level climate finance study, India** — Built an end-to-end open-source pipeline
> testing whether Indian municipal capital spending reaches the neighbourhoods most exposed
> to flooding. Assembled 82,443 ward-tagged BBMP work orders (₹37,539 Cr, FY2011–2026) and
> sub-city spending panels for Chennai, Pune, Ahmedabad and Surat; derived 30 m
> terrain-based flood hazard (HAND, Copernicus DEM) for 1,946 sub-city units across 17
> cities and validated it against 395 official BBMP/KSNDMC flood locations.

> **Finding:** flood-prone wards receive **8–13% smaller capital budgets** (p < 0.01) while
> allocating a *higher* share of what they get to drainage — the misallocation sits in the
> budget, not the drainage line, and survives party fixed effects. Replicated with the same
> sign in four cities.

### Shorter variant (one line, if space is tight)

> Built an open-source pipeline joining 82,443 municipal work orders to satellite-derived
> flood hazard across 17 Indian cities; found flood-prone wards receive 8–13% smaller
> capital budgets (p < 0.01), replicated in four cities.

---

## The 90-second spoken version

**The hook (10s)**
> Every Indian city is told to spend on climate resilience. Nobody has checked whether the
> money actually reaches the neighbourhoods that flood. I checked, for Bengaluru.

**The method (25s)**
> BBMP publishes every work order it pays — ward-tagged, dated, with a description. I pulled
> 82,000 of them, about ₹37,000 crore over thirteen years, and classified which were
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
> Same negative sign in Chennai, Pune and Ahmedabad. The whole thing runs on free data, and
> the code is public.

---

## Questions you will get, and the honest answers

**"Is this causal?"**
> No, and I don't claim it is. Terrain hazard is fixed — there's no counterfactual Bengaluru
> with flatter ground. It's descriptive with a decomposition. The causal version would need a
> budget-rule discontinuity, and I haven't found one.

**"How sensitive is it to how you define drainage?"**
> Very, and that's a finding in itself. The same budget is 1.3% or 46% drainage depending on
> the keyword tier — a 29-fold range. I hand-adjudicated 300 orders: the broad tier has 98%
> recall but 80% of what it catches is bundled "roads and drains" work. Under the strict
> definition — dedicated stormwater assets only — the effect on drainage share is actually
> significantly *positive*.

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

**"Could you do this for another country?"**
> The hazard half runs anywhere on earth for free. The spending half is the constraint. I
> swept 1,099 datasets across 76 Indian municipal organisations — only six cities publish
> sub-city capital spending at all. South Africa's National Treasury publishes it for 257
> municipalities pre-coded by function, which is where I'd go next.
