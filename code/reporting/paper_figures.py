"""Draw the manuscript figures (Chinese and English labels) from the archived results.

No forecasts or tests are re-estimated: the inputs are the saved daily score means, the saved
descriptive series in ../publication_zh_20261024/plot_data, and the archived summary table
behind Table C1 (study1_metrics.csv). The decade heatmap averages the saved daily score means.
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "outputs/reproduced"
DATA = SRC / "plot_data"
CJK_FONT = SRC / "paper" / "fonts" / "NotoSerifCJKtc-Regular.otf"
OUT = ROOT / "outputs/reproduced/figures"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE, SHADE, CRISIS = "#135E79", "#B15C2E", "#8AB6C2", "#E8A87C"
CRISES = ["1987-10-19", "1998-08-17", "2001-09-17", "2008-09-15", "2011-08-08", "2015-08-24", "2020-02-24"]
ARM = {"A0": "EW", "A1": "EW+BCm", "A1d": "EW+BCd", "A2": "EW+DJC", "A3": "EW+YE", "A3f": "EW+YEf",
       "F": "EW+DJC-FIX", "C0": "MCS", "C1": "MCS+BCm", "C1d": "MCS+BCd", "C2": "MCS+DJC", "C3": "MCS+YE", "R0": "GJR"}
HEAT_ROWS = ["A2", "F", "A1d", "A1", "A3", "A3f", "C0", "C2", "C1d", "C1", "C3", "R0"]

LABELS = {
    "zh": {
        "lvl": lambda a: f"{100 * (1 - a):g}% 水準",
        "cum_y": "累積評分差（EW+DJC − EW）",
        "date": "日期",
        "crisis": "危機期間",
        "cum_panel_y": lambda a: f"累積評分差（{100 * (1 - a):g}%）",
        "excess_x": "EW 違反率 − 目標（百分點）",
        "z2_x": "EW 的 $Z_2$（負值表示低估）",
        "diff_y": "平均評分差（EW+DJC − EW）",
        "industry": "30 個產業",
        "index": "6 個國際指數",
        "viol_x": lambda t: f"違反率（%），目標 {t:g}%",
        "score_y": "平均 FZ0 評分（越低越好）",
        "band": "事先設定的容忍範圍",
        "decades": ["1975–79", "1980 年代", "1990 年代", "2000 年代", "2010 年代", "2020–26"],
        "heat_cb": "相對於 EW 的平均評分差（負值較佳）",
    },
    "en": {
        "lvl": lambda a: f"{100 * (1 - a):g}% level",
        "cum_y": "Cumulative score difference\n(EW+DJC − EW)",
        "date": "Date",
        "crisis": "Crisis periods",
        "cum_panel_y": lambda a: f"Cumulative difference ({100 * (1 - a):g}%)",
        "excess_x": "EW violation rate − target (percentage points)",
        "z2_x": "EW $Z_2$ (negative = underestimation)",
        "diff_y": "Mean score difference\n(EW+DJC − EW)",
        "industry": "30 industries",
        "index": "6 international indices",
        "viol_x": lambda t: f"Violation rate (%), target {t:g}%",
        "score_y": "Average FZ0 score (lower is better)",
        "band": "Prespecified tolerance",
        "decades": ["1975–79", "1980s", "1990s", "2000s", "2010s", "2020–26"],
        "heat_cb": "Mean score difference vs EW (negative = better)",
    },
}


def setup(lang):
    base = {"font.size": 10, "axes.unicode_minus": True, "axes.spines.top": False,
            "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.18,
            "pdf.fonttype": 42, "svg.fonttype": "none", "mathtext.fontset": "stix"}
    if lang == "zh":
        font_manager.fontManager.addfont(str(CJK_FONT))
        base["font.family"] = font_manager.FontProperties(fname=str(CJK_FONT)).get_name()
    else:
        base["font.family"] = "Times New Roman"
    plt.rcdefaults()
    plt.rcParams.update(base)


def save(fig, name):
    fig.tight_layout()
    for ext, kw in [("png", {"dpi": 300}), ("pdf", {}), ("svg", {})]:
        fig.savefig(OUT / f"{name}.{ext}", **kw)
    plt.close(fig)


def tradeoff(lang, L, metrics):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    offsets = {"EW": (5, 4), "MCS+BCd": (-8, -11), "EW+DJC": (-10, -13), "EW+YEf": (5, -11), "EW+DJC-FIX": (4, 6)}
    for ax, (fz, v, target, a) in zip(axes, [("fz975", "v975", 2.5, 0.025), ("fz99", "v99", 1.0, 0.01)]):
        ax.grid(False)
        if a == 0.025:
            ax.axvspan(2.25, 2.75, color=SHADE, alpha=0.25, lw=0, label=L["band"])
        ax.axvline(target, color="0.4", lw=0.8, ls="--")
        for _, r in metrics.iterrows():
            name = ARM[r.arm]
            color = "black" if name == "EW" else "#2b8a3e" if name == "GJR" else "#bf6c23" if name.startswith("MCS") else "#1f5f8b"
            ax.scatter(r[v], r[fz], s=46 if name in ("EW", "EW+DJC", "GJR") else 22, color=color, zorder=3)
            dx, dy = offsets.get(name, (4, 3))
            ax.annotate(name, (r[v], r[fz]), xytext=(dx, dy), textcoords="offset points", fontsize=7.5,
                        color=color, ha="right" if dx < 0 else "left")
        ew, djc = metrics[metrics.arm == "A0"].iloc[0], metrics[metrics.arm == "A2"].iloc[0]
        ax.annotate("", xy=(djc[v], djc[fz]), xytext=(ew[v], ew[fz]),
                    arrowprops=dict(arrowstyle="->", color="#1f5f8b", lw=1.1), zorder=2)
        ax.set_xlabel(L["viol_x"](target))
        ax.set_ylabel(L["score_y"])
        ax.set_title(L["lvl"](a))
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    save(fig, f"fig_tradeoff_{lang}")


def cumulative_industries(lang, L, daily):
    fig, ax = plt.subplots(figsize=(9, 3.7))
    ref = daily[(daily["set"] == "industries") & (daily.alpha == 0.025)].sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(ref.date)
    for c in CRISES:
        i = ref.index[ref.date >= c][0]
        ax.axvspan(dates[i], dates[min(i + 59, len(ref) - 1)], color=CRISIS, alpha=0.45, lw=0)
    for a, color in [(0.025, BLUE), (0.01, ORANGE)]:
        w = daily[(daily["set"] == "industries") & (daily.alpha == a)].sort_values("date")
        ax.plot(pd.to_datetime(w.date), (w.A2 - w.A0).cumsum(), label=L["lvl"](a), color=color, lw=1.3)
    ax.axhline(0, color="black", lw=0.7)
    ax.set_ylabel(L["cum_y"])
    ax.set_xlabel(L["date"])
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Patch(facecolor=CRISIS, alpha=0.45, lw=0))
    labels.append(L["crisis"])
    ax.legend(handles, labels, frameon=False, loc="lower left")
    save(fig, f"fig_cumulative_industries_{lang}")


def cumulative_yen(lang, L, yen):
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for ax, a, color in zip(axes, [0.025, 0.01], [BLUE, ORANGE]):
        w = yen[yen.alpha == a]
        dates = pd.to_datetime(w.date)
        ax.plot(dates, w.d_A2_A0.cumsum(), color=color, lw=1.2)
        ax.fill_between(dates, 0, 1, where=w.appreciation_state.astype(bool),
                        transform=ax.get_xaxis_transform(), color=SHADE, alpha=0.30, lw=0)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_ylabel(L["cum_panel_y"](a))
    axes[-1].set_xlabel(L["date"])
    save(fig, f"fig_cumulative_yen_{lang}")


def miscalibration(lang, L, series):
    fig, axes = plt.subplots(2, 2, figsize=(9, 6.4), sharey="row")
    for i, a in enumerate([0.025, 0.01]):
        s = series[series.alpha == a]
        for j, (col, scale, xlabel) in enumerate([("a0_breach_excess", 100, L["excess_x"]), ("a0_z2", 1, L["z2_x"])]):
            ax = axes[i, j]
            for cls, marker, color, label in [("industry", "o", "#1f5f8b", L["industry"]),
                                              ("index", "^", "#bf6c23", L["index"])]:
                ss = s[s["class"] == cls]
                ax.scatter(ss[col] * scale, ss.d_a2_minus_a0, marker=marker, color=color, label=label, s=27, alpha=0.85)
            ax.axhline(0, color="0.5", lw=0.8)
            ax.axvline(0, color="0.7", lw=0.8)
            ax.set_xlabel(xlabel)
            ax.set_title(L["lvl"](a))
            if j == 0:
                ax.set_ylabel(L["diff_y"])
            if i == 0 and j == 0:
                ax.legend(frameon=False, loc="lower left")
    save(fig, f"fig_miscalibration_gain_{lang}")


def decades(lang, L, daily):
    w = daily[(daily["set"] == "industries") & (daily.alpha == 0.025)].copy()
    year = pd.to_datetime(w.date).dt.year
    w["period"] = pd.cut(year, [1974, 1979, 1989, 1999, 2009, 2019, 2026], labels=L["decades"])
    tab = pd.DataFrame({ARM[k]: w.groupby("period", observed=True).apply(lambda g, k=k: (g[k] - g.A0).mean())
                        for k in HEAT_ROWS}).T
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.grid(False)
    lim = abs(tab.values).max()
    im = ax.imshow(tab.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(tab.shape[1]), tab.columns)
    ax.set_yticks(range(tab.shape[0]), tab.index)
    ax.tick_params(length=0)
    for i in range(tab.shape[0]):
        for j in range(tab.shape[1]):
            v = tab.values[i, j]
            ax.text(j, i, f"{v:.3f}".replace("-", "−"), ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > 0.6 * lim else "black")
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label(L["heat_cb"])
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, f"fig_decades_{lang}")
    return tab


def main():
    study1 = SRC / "study1"
    if not (study1 / "confirm_meta.json").exists():
        study1 = ROOT / "outputs/reference/study1"
    daily = pd.read_csv(study1 / "confirm_daily_means.csv")
    yen = pd.read_csv(SRC / "study2_summary/descriptive_daily.csv")
    # Derive the same Figure 4 coordinates from the selected result set, including
    # when the review path has no raw Study 1 files for the independent date audit.
    per_series = pd.read_csv(study1 / "confirm_series_metrics.csv")
    rows = []
    for (name, alpha), group in per_series[per_series.period == "main"].groupby(["name", "alpha"]):
        group = group.set_index("group")
        a, b = group.loc["A0"], group.loc["A2"]
        rows.append({"name": name, "alpha": alpha, "class": a["class"],
                     "a0_breach_excess": a.breach_rate-alpha, "a0_z2": a.z2,
                     "d_a2_minus_a0": b.fz_mean-a.fz_mean})
    series = pd.DataFrame(rows)
    metrics = pd.read_csv(SRC / "table_sources" / "study1_metrics.csv")
    metrics.columns = ["arm", "fz975", "v975", "z975", "fz99", "v99", "z99"]
    for lang, L in [("en", LABELS["en"])]:
        setup(lang)
        tradeoff(lang, L, metrics)
        cumulative_industries(lang, L, daily)
        cumulative_yen(lang, L, yen)
        miscalibration(lang, L, series)
        tab = decades(lang, L, daily)
    print(tab.round(4).to_string())
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
