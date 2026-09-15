"""Figures for the ward-level drainage-vs-hazard study."""
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors

warnings.filterwarnings("ignore")
plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 140})

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "output/figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, MUTED = "#1a1a1a", "#8a8a8a"
FLOOD = "#2166ac"      # blue  = hazard
MONEY = "#b2182b"      # red   = spending


def load():
    df = pd.read_parquet(ROOT / "data/final/bengaluru_final.parquet")
    g = gpd.read_file(ROOT / "data/raw/boundaries/bengaluru_198.geojson").to_crs(4326)
    g["ward"] = pd.to_numeric(g["WARD_NO"], errors="coerce")
    out = g.merge(df, on="ward", how="left")
    # drainage spend per resident, which F2 promises and the share alone does not show:
    # a ward can put a large SHARE of a small budget into drains and still spend little
    # per person.
    #
    # POP_TOTAL exists on BOTH the polygon file and the panel, so the merge above suffixes
    # it to POP_TOTAL_x / POP_TOTAL_y and a plain out["POP_TOTAL"] lookup returns nothing -
    # which silently produced an all-NaN per-capita panel and an empty subplot. Prefer the
    # panel's own `pop` column, which the regressions use, and fall back through the
    # suffixed names rather than assuming one of them.
    pop = None
    for c in ("pop", "POP_TOTAL", "POP_TOTAL_y", "POP_TOTAL_x"):
        if c in out.columns:
            v = pd.to_numeric(out[c], errors="coerce")
            if v.notna().any() and (v > 0).any():
                pop = v
                break
    if pop is None:
        raise KeyError("no usable population column for the per-capita panel")
    out["drain_pc"] = np.where(pop > 0, out["drain_medium"] / pop, np.nan)
    return out


def fig1_maps(gdf):
    """The money figure: hazard vs drainage spending, side by side."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    for ax, col, cmap, title, unit in [
        (axes[0], "flood_hazard", "Blues",
         "Flood hazard", "share of ward below 5 m\nabove nearest drainage"),
        (axes[1], "sh_drainage", "Reds",
         "Drainage spending", "% of ward works budget\nFY2013–2022"),
    ]:
        v = gdf[col]
        gdf.plot(column=col, cmap=cmap, ax=ax, edgecolor="white", linewidth=.25,
                 vmin=np.nanpercentile(v, 2), vmax=np.nanpercentile(v, 98))
        ax.set_title(title, fontweight="bold", loc="left", pad=8)
        ax.set_axis_off()
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(
            np.nanpercentile(v, 2), np.nanpercentile(v, 98)))
        cb = fig.colorbar(sm, ax=ax, fraction=.035, pad=.02)
        cb.ax.tick_params(labelsize=7, length=0)
        cb.outline.set_visible(False)
        cb.set_label(unit, size=7, color=MUTED)
    fig.suptitle("Bengaluru: where the water goes, and where the money goes",
                 x=.02, ha="left", fontsize=13, fontweight="bold")
    fig.text(.02, .01, "198 BBMP wards. Hazard from Copernicus DEM 30 m (HAND). "
             "Spending from 82,443 ward-tagged BBMP work orders.",
             size=7, color=MUTED)
    fig.tight_layout(rect=[0, .03, 1, .94])
    fig.savefig(FIG / "F1_hazard_vs_spending_maps.png", bbox_inches="tight")
    plt.close(fig)


def fig2_scatter(gdf):
    """Hazard vs drainage spending, as a SHARE and PER CAPITA.

    Both panels are needed and they say different things. The share asks whether a ward
    prioritises drainage within its own budget; per capita asks whether a resident of that
    ward actually gets drainage money. A ward can score well on the first and badly on the
    second, which is precisely the gap this study documents - so showing only the share
    would flatter the result the paper is arguing against.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.9))
    panels = [
        ("sh_drainage", "Drainage spending  (% of ward works budget)",
         "Share: does the ward prioritise drainage?", False),
        ("drain_pc", "Drainage spending per resident  (Rs, FY2013-2022)",
         "Per capita: does a resident get the money?", True),
    ]
    for ax, (col, ylab, title, logy) in zip(axes, panels):
        d = gdf.dropna(subset=["flood_hazard", col])
        d = d[d[col] > 0] if logy else d
        if d.empty:
            continue
        ax.scatter(d.flood_hazard, d[col], s=26, c=MONEY, alpha=.55,
                   edgecolor="white", linewidth=.5)
        yv = np.log10(d[col]) if logy else d[col]
        b, a = np.polyfit(d.flood_hazard, yv, 1)
        xs = np.linspace(d.flood_hazard.min(), d.flood_hazard.max(), 50)
        ax.plot(xs, 10 ** (a + b * xs) if logy else a + b * xs, color=INK, lw=1.4)
        r = d.flood_hazard.corr(yv)
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel("Flood hazard  (share of ward below 5 m above nearest drainage)",
                      size=9)
        ax.set_ylabel(ylab, size=9)
        ax.set_title(title, fontweight="bold", loc="left", size=10)
        ax.text(.97, .05, f"r = {r:+.2f}", transform=ax.transAxes, ha="right",
                va="bottom", size=8, color=MUTED)
        for _, row in d.nlargest(3, "flood_hazard").iterrows():
            ax.annotate(str(row.blr_ward_name)[:18], (row.flood_hazard, row[col]),
                        fontsize=7, color=MUTED, xytext=(4, 4),
                        textcoords="offset points")
    fig.suptitle("Drainage spending barely tracks flood hazard, on either measure",
                 fontweight="bold", x=.02, ha="left", size=11.5)
    fig.tight_layout(rect=[0, 0, 1, .94])
    fig.savefig(FIG / "F2_scatter.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def fig3_gap(gdf):
    d = gdf.dropna(subset=["flood_hazard", "sh_drainage"]).copy()
    b, a = np.polyfit(d.flood_hazard, d.sh_drainage, 1)
    d["resid"] = d.sh_drainage - (a + b * d.flood_hazard)
    hi = d[d.flood_hazard > d.flood_hazard.quantile(.7)]
    worst = hi.nsmallest(12, "resid").iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.barh(range(len(worst)), worst.resid, color=FLOOD, alpha=.85, height=.68)
    ax.set_yticks(range(len(worst)))
    ax.set_yticklabels([str(x)[:24] for x in worst.blr_ward_name], fontsize=8)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlabel("Drainage spending, percentage points below what its hazard predicts")
    ax.set_title("The alignment gap: high-hazard wards getting the least drainage money",
                 fontweight="bold", loc="left")
    ax.text(.98, .03, "wards in the top 30% of flood hazard",
            transform=ax.transAxes, ha="right", size=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIG / "F3_alignment_gap.png", bbox_inches="tight")
    plt.close(fig)


def fig4_falsification():
    f = pd.read_csv(ROOT / "output/tables/falsification_outcome_side.csv")
    f = f.sort_values("beta")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    cols = [MONEY if c == "drainage" else MUTED for c in f.category]
    ax.errorbar(f.beta, range(len(f)), xerr=1.96 * f.se, fmt="o", ms=6,
                color=INK, ecolor=MUTED, elinewidth=1.2, capsize=3, zorder=3)
    for i, (_, r) in enumerate(f.iterrows()):
        ax.plot(r.beta, i, "o", ms=7, color=cols[i], zorder=4)
    ax.axvline(0, color=INK, lw=.8, ls="--")
    ax.set_yticks(range(len(f)))
    ax.set_yticklabels(f.category, fontsize=9)
    ax.set_xlabel("Effect of 1 SD more flood hazard on spending share (pp, 95% CI)")
    ax.set_title("Falsification: only roads respond to flood hazard - not drainage",
                 fontweight="bold", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "F4_falsification.png", bbox_inches="tight")
    plt.close(fig)


def fig5_tagging():
    wo = pd.read_parquet(ROOT / "data/interim/bbmp_workorders.parquet")
    w = wo[(wo.ward.between(1, 198)) & (wo.fy.between(2013, 2022))]
    tot = w.amount.sum()
    vals = [(t, w.loc[w[f"is_{t}"], "amount"].sum() / tot * 100)
            for t in ["narrow", "medium", "broad"]]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.bar([v[0] for v in vals], [v[1] for v in vals],
           color=[FLOOD, MONEY, "#d6a0a8"], width=.6)
    for i, (t, v) in enumerate(vals):
        ax.text(i, v + 1, f"{v:.1f}%\n₹{w.loc[w[f'is_{t}'],'amount'].sum()/1e7:,.0f} Cr",
                ha="center", size=8)
    ax.set_ylabel("Share of ward works spending classified as drainage (%)")
    ax.set_title("The tagging elasticity: the same data, three defensible definitions",
                 fontweight="bold", loc="left")
    ax.text(.98, .9, "a 29× difference in the measured\n'drainage share' of the budget",
            transform=ax.transAxes, ha="right", size=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIG / "F5_tagging_elasticity.png", bbox_inches="tight")
    plt.close(fig)


def fig6_scale():
    h = pd.read_parquet(ROOT / "data/interim/ward_hazard.parquet")
    t = pd.read_parquet(ROOT / "data/interim/ward_terrain.parquet")
    b = h[h.city == "bengaluru_198"].merge(t[t.city == "bengaluru_198"],
                                           on=["city", "unit_id"])
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    for ax, col, lab, col_c in [
            (axes[0], "hot_days_35c", "CCKP heat index (0.25° grid)", FLOOD),
            (axes[1], "hand_lt5m_share", "Terrain hazard, HAND (30 m)", MONEY)]:
        v = b[col].dropna()
        ax.hist(v, bins=30, color=col_c, alpha=.85)
        ax.set_title(lab, fontweight="bold", loc="left", fontsize=10)
        ax.set_ylabel("wards")
        ax.text(.97, .92, f"{v.round(4).nunique()} distinct values\nCV {v.std()/abs(v.mean())*100:.1f}%",
                transform=ax.transAxes, ha="right", va="top", size=8, color=MUTED)
    fig.suptitle("Why a 0.25° climate grid cannot answer a ward-level question",
                 x=.02, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, .92])
    fig.savefig(FIG / "F6_scale_problem.png", bbox_inches="tight")
    plt.close(fig)


def fig7_budget_channel():
    """The headline: hazard cuts the budget, not the drainage priority."""
    import statsmodels.formula.api as smf
    d = pd.read_parquet(ROOT / "data/final/bengaluru_budget_panel.parquet")
    CTRL = "log_area + log_pop + z_log_density + z_dist_centre_km"
    steps = [("Total ward\nbudget", f"log_total ~ z_hazard + {CTRL} + C(fy)", True),
             ("Stormwater\nspend", f"log_storm ~ z_hazard + {CTRL} + C(fy)", True),
             ("Stormwater,\nbudget controlled",
              f"log_storm ~ z_hazard + log_total + {CTRL} + C(fy)", True)]
    labs, bs, los, his = [], [], [], []
    for lab, f, _ in steps:
        r = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["unit"]})
        b, se = r.params["z_hazard"], r.bse["z_hazard"]
        labs.append(lab)
        bs.append((np.exp(b) - 1) * 100)
        los.append((np.exp(b - 1.96 * se) - 1) * 100)
        his.append((np.exp(b + 1.96 * se) - 1) * 100)

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    y = np.arange(len(labs))
    cols = [MONEY, "#c76b78", MUTED]
    for i in range(len(labs)):
        ax.plot([los[i], his[i]], [y[i], y[i]], color=MUTED, lw=2, zorder=2)
        ax.plot(bs[i], y[i], "o", ms=11, color=cols[i], zorder=3)
        ax.annotate(f"{bs[i]:+.1f}%", (bs[i], y[i]), xytext=(0, 13),
                    textcoords="offset points", ha="center", fontsize=9,
                    fontweight="bold")
    ax.axvline(0, color=INK, lw=.9, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labs, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Change per 1 SD more flood hazard (%, 95% CI)")
    ax.set_title("Flood-prone wards get smaller budgets - not lower drainage priority",
                 fontweight="bold", loc="left", pad=16)
    ax.set_ylim(len(labs) - 0.4, -0.75)
    fig.text(.99, .01, "Bengaluru, 198 wards, FY2013–2022 · ward-clustered SE, year FE",
             ha="right", size=7.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIG / "F7_budget_channel.png", bbox_inches="tight")
    plt.close(fig)


def fig8_validation():
    """Stop-or-go: modelled hazard vs 395 official BBMP/KSNDMC flood points."""
    w = pd.read_csv(ROOT / "output/tables/hazard_validation.csv")
    w["q"] = pd.qcut(w.hand_lt5m_share, 4, labels=["Q1\nlowest", "Q2", "Q3", "Q4\nhighest"])
    g = w.groupby("q", observed=True).agg(d=("pts_per_km2", "mean"),
                                          n=("n_flood_pts", "sum"))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2),
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    a1.bar(range(len(g)), g.d, color=[ "#c9d7e8", "#91b2d6", "#5a8ac0", FLOOD], width=.68)
    for i, (d, n) in enumerate(zip(g.d, g.n)):
        a1.text(i, d + .03, f"{d:.2f}\n({int(n)} pts)", ha="center", size=8)
    a1.set_xticks(range(len(g)))
    a1.set_xticklabels(g.index, fontsize=8)
    a1.set_ylabel("observed flood points per km²")
    a1.set_title("Modelled hazard quartile", fontweight="bold", loc="left", fontsize=10)
    a1.set_ylim(0, g.d.max() * 1.32)

    a2.scatter(w.hand_lt5m_share, w.pts_per_km2, s=24, c=FLOOD, alpha=.55,
               edgecolor="white", linewidth=.4)
    b, aa = np.polyfit(w.hand_lt5m_share, w.pts_per_km2, 1)
    xs = np.linspace(w.hand_lt5m_share.min(), w.hand_lt5m_share.max(), 40)
    a2.plot(xs, aa + b * xs, color=INK, lw=1.3)
    rs = w.hand_lt5m_share.corr(w.pts_per_km2, method="spearman")
    a2.set_xlabel("modelled flood hazard (HAND < 5 m share)")
    a2.set_ylabel("observed flood points per km²")
    a2.set_title(f"Spearman ρ = {rs:+.2f}", fontweight="bold", loc="left", fontsize=10)
    fig.suptitle("The hazard model finds Bengaluru's real flood spots",
                 x=.02, ha="left", fontweight="bold", fontsize=12.5)
    fig.text(.02, .005, "395 official flood-vulnerable, flood-prone and low-lying "
             "locations compiled by BBMP with KSNDMC, across 148 wards.",
             size=7.5, color=MUTED)
    fig.tight_layout(rect=[0, .04, 1, .93])
    fig.savefig(FIG / "F8_hazard_validation.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    gdf = load()
    fig1_maps(gdf); print("  F1 hazard vs spending maps")
    fig2_scatter(gdf); print("  F2 scatter")
    fig3_gap(gdf); print("  F3 alignment gap")
    fig4_falsification(); print("  F4 falsification")
    fig5_tagging(); print("  F5 tagging elasticity")
    fig6_scale(); print("  F6 scale problem")
    fig7_budget_channel(); print("  F7 budget channel")
    fig8_validation(); print("  F8 hazard validation")
    print(f"\n  -> {FIG}")
