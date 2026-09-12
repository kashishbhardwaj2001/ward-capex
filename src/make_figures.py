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
    return g.merge(df, on="ward", how="left")


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
    d = gdf.dropna(subset=["flood_hazard", "sh_drainage"])
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(d.flood_hazard, d.sh_drainage, s=26, c=MONEY, alpha=.55,
               edgecolor="white", linewidth=.5)
    b, a = np.polyfit(d.flood_hazard, d.sh_drainage, 1)
    xs = np.linspace(d.flood_hazard.min(), d.flood_hazard.max(), 50)
    ax.plot(xs, a + b * xs, color=INK, lw=1.4)
    r = d.flood_hazard.corr(d.sh_drainage)
    ax.set_xlabel("Flood hazard  (share of ward below 5 m above nearest drainage)")
    ax.set_ylabel("Drainage spending  (% of ward works budget)")
    ax.set_title("Drainage spending barely tracks flood hazard",
                 fontweight="bold", loc="left")
    ax.text(.97, .05, f"r = {r:+.2f}\nno significant relationship\n(p = 0.24, ward-year panel)",
            transform=ax.transAxes, ha="right", va="bottom", size=8, color=MUTED)
    for _, row in d.nlargest(3, "flood_hazard").iterrows():
        ax.annotate(str(row.blr_ward_name)[:18], (row.flood_hazard, row.sh_drainage),
                    fontsize=7, color=MUTED, xytext=(4, 4), textcoords="offset points")
    fig.tight_layout()
    fig.savefig(FIG / "F2_scatter.png", bbox_inches="tight")
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
    ax.set_title("Falsification: only roads respond to flood hazard — not drainage",
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


if __name__ == "__main__":
    gdf = load()
    fig1_maps(gdf); print("  F1 hazard vs spending maps")
    fig2_scatter(gdf); print("  F2 scatter")
    fig3_gap(gdf); print("  F3 alignment gap")
    fig4_falsification(); print("  F4 falsification")
    fig5_tagging(); print("  F5 tagging elasticity")
    fig6_scale(); print("  F6 scale problem")
    print(f"\n  -> {FIG}")
