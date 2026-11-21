"""Draw the figures used in the report and the slides.

Light theme, grayscale only. Series are told apart by line style, marker shape, hatching
and direct labels instead of colour, so every figure survives black-and-white printing.
Labels inside the figures are Turkish because the report and the slides are in Turkish.

Input : data/raw/pwt110.csv, data/processed/*.csv, outputs/tables/*.csv, outputs/results.json
Output: outputs/figures/*.png
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from paths import FIGURES, PROCESSED, RAW, RESULTS, ROOT, TABLES

RESULT = json.loads(RESULTS.read_text(encoding="utf-8"))

BLACK, DARK, MID, LIGHT = "#111111", "#444444", "#7a7a7a", "#c4c4c4"
MODEL_LABELS = {"pooled": "Havuzlanmış EKK", "fe": "Sabit Etkiler", "re": "Rassal Etkiler"}

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "font.family": "DejaVu Sans", "font.size": 14,
    "axes.titlesize": 16, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 14, "axes.edgecolor": BLACK, "axes.linewidth": 1.2,
    "xtick.color": BLACK, "ytick.color": BLACK, "xtick.labelsize": 13, "ytick.labelsize": 13,
    "text.color": BLACK, "axes.labelcolor": BLACK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e2e2e2", "grid.linewidth": 0.8,
    "legend.frameon": False, "legend.fontsize": 13,
})


def fmt(x: float, digits: int = 2) -> str:
    """Turkish decimal comma and a true minus sign."""
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


TICK_FORMAT = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "−"))


def comma_ticks(*axes, x: bool = True) -> None:
    for ax in axes:
        ax.yaxis.set_major_formatter(TICK_FORMAT)
        if x:
            ax.xaxis.set_major_formatter(TICK_FORMAT)


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("written:", (FIGURES / name).relative_to(ROOT))


def label_box(ax, x, y, text, **kw):
    ax.text(x, y, text, transform=ax.transAxes, fontsize=14, fontweight="bold",
            bbox=dict(facecolor="white", edgecolor=BLACK, boxstyle="round,pad=0.3"), **kw)


# ----------------------------------------------------------------------------
def turkey_korea() -> None:
    """Opening figure: Turkey, South Korea and Argentina from 1960 to 2023."""
    raw = pd.read_csv(RAW / "pwt110.csv")
    raw["per_capita"] = raw["rgdpna"] / raw["pop"] / 1000
    series = {
        "KOR": ("Güney Kore", dict(color=BLACK, lw=2.6, ls="-")),
        "TUR": ("Türkiye", dict(color=BLACK, lw=3.6, ls="-", marker="o", markevery=10, ms=8)),
        "ARG": ("Arjantin", dict(color=MID, lw=2.4, ls="--")),
    }
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    for code, (name, style) in series.items():
        g = raw[(raw["countrycode"] == code) & (raw["year"] >= 1960)].dropna(subset=["per_capita"])
        ax.plot(g["year"], g["per_capita"], **style)
        last = g.iloc[-1]
        ax.annotate(f"{name}  {fmt(last['per_capita'], 1)}", (last["year"], last["per_capita"]),
                    xytext=(8, 0), textcoords="offset points", va="center", fontsize=13, fontweight="bold")
    ax.set_yscale("log")
    ax.set_yticks([2, 5, 10, 20, 50])
    ax.yaxis.set_major_formatter(TICK_FORMAT)
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xlim(1960, 2036)
    ax.set_xticks(range(1960, 2030, 10))
    ax.set_ylabel("Kişi başı GSYH (bin $, 2021 fiyatları, log)")
    ax.set_title("Kişi başı gelir, 1960–2023")
    fig.tight_layout()
    save(fig, "01_turkey_korea.png")


def panel_structure(df: pd.DataFrame) -> None:
    selected = ["USA", "KOR", "CHN", "BRA", "EGY", "IND", "ITA", "MEX", "NGA", "ESP", "GRC", "POL", "ARG"]
    periods = sorted(df["period"].unique())
    x = range(len(periods))
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for code in selected:
        g = df[df["country"] == code].sort_values("period")
        ax.plot(x, g["growth"], color=LIGHT, lw=1.6, marker=".", ms=6, zorder=2)
    mean = df.groupby("period")["growth"].mean()
    ax.plot(x, mean.values, color=DARK, lw=2.6, ls="--", marker="s", ms=7, zorder=4)
    tur = df[df["country"] == "TUR"].sort_values("period")
    ax.plot(x, tur["growth"], color=BLACK, lw=3.6, marker="o", ms=9, zorder=5)
    ax.annotate("Türkiye", (len(x) - 1, tur["growth"].iloc[-1]), xytext=(10, 0), textcoords="offset points",
                va="center", fontsize=14, fontweight="bold")
    ax.annotate(f"{RESULT['pwt11']['data']['N']} ülke ortalaması", (len(x) - 1, mean.iloc[-1]), xytext=(10, -2),
                textcoords="offset points", va="center", fontsize=13, color=DARK, fontweight="bold")
    ax.axhline(0, color=BLACK, lw=1)
    ax.set_xticks(list(x), [f"{p}–{str(p + 5)[2:]}" for p in periods], rotation=0, fontsize=11.5)
    ax.set_xlim(-0.3, len(x) + 1.6)
    ax.set_ylim(-8, 13)
    ax.set_ylabel("Yıllık ortalama büyüme (%)")
    ax.set_title("Her ülke için on dönemlik bir zaman serisi")
    ax.yaxis.set_major_formatter(TICK_FORMAT)
    fig.tight_layout()
    save(fig, "02_panel_structure.png")


def pooled_vs_within(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.3))
    x, y = df["ln_gdp0"], df["growth"]
    x_dm = x - df.groupby("country")["ln_gdp0"].transform("mean")
    y_dm = y - df.groupby("country")["growth"].transform("mean")
    panels = [
        (ax[0], x, y, "o", "-", "Havuzlanmış veri", "ln(Başlangıç GSYH)", "Yıllık büyüme (%)"),
        (ax[1], x_dm, y_dm, "s", "--", "Ülke ortalamalarından sapmalar", "ln(Başlangıç GSYH) − ülke ort.",
         "Büyüme − ülke ort."),
    ]
    for a, xx, yy, marker, ls, title, xlabel, ylabel in panels:
        slope, intercept = np.polyfit(xx, yy, 1)
        a.scatter(xx, yy, s=14, color=MID, alpha=0.5, edgecolor="none", marker=marker)
        xs = np.linspace(xx.min(), xx.max(), 50)
        a.plot(xs, intercept + slope * xs, color=BLACK, lw=2.8, ls=ls)
        a.set_ylim(-16, 16)
        a.set_title(title)
        a.set_xlabel(xlabel)
        a.set_ylabel(ylabel)
        label_box(a, 0.04, 0.05, f"Eğim = {fmt(slope)}")
    comma_ticks(*ax)
    fig.tight_layout()
    save(fig, "03_pooled_vs_within.png")


def convergence() -> None:
    """Cross-section slope of every period; both data sources in one chart."""
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    for name, style, label in [
        ("pwt5", dict(color=MID, lw=2.4, ls="--", marker="^", ms=10, mfc="white", mew=2), "PWT 5 (1991), 125 ülke"),
        ("pwt11", dict(color=BLACK, lw=2.8, ls="-", marker="o", ms=9), "PWT 11.0 (2025), 129 ülke"),
    ]:
        slopes = RESULT[name]["cross_section_slopes"]
        midpoints = [int(k) + 2.5 for k in slopes]
        ax.plot(midpoints, list(slopes.values()), label=label, **style)
    ax.axhline(0, color=BLACK, lw=1.3)
    ax.text(1968, 1.0, "Zenginler daha hızlı büyüyor (ıraksama)", fontsize=12.5, color=DARK, va="center")
    ax.text(1958.5, -0.85, "Yoksullar arayı kapatıyor (yakınsama)", fontsize=12.5, color=DARK, va="center")
    ax.set_ylim(-1.2, 1.2)
    ax.set_xticks(range(1960, 2030, 10))
    ax.set_xlabel("Beş yıllık dönemin orta noktası")
    ax.set_ylabel("Büyümenin başlangıç gelirine eğimi")
    ax.set_title("Koşulsuz yakınsama: her dönem için ayrı yatay kesit regresyonu")
    ax.legend(loc="upper right")
    ax.yaxis.set_major_formatter(TICK_FORMAT)
    fig.tight_layout()
    save(fig, "04_convergence.png")


def coefficients() -> None:
    coef = pd.read_csv(TABLES / "coefficients_pwt11.csv")
    variables = [("ln_gdp0", "ln(Başlangıç GSYH)"), ("investment", "Yatırım oranı"),
                 ("pop_growth", "Nüfus artışı"), ("ln_hc0", "ln(Beşeri sermaye)")]
    models = [("pooled", "o", "white"), ("fe", "s", BLACK), ("re", "^", LIGHT)]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), gridspec_kw={"wspace": 0.22})
    for ax, (variable, title) in zip(axes, variables):
        for i, (model, marker, fill) in enumerate(models):
            r = coef[(coef["model"] == model) & (coef["variable"] == variable)].iloc[0]
            ax.errorbar(r["estimate"], 3 - i,
                        xerr=[[r["estimate"] - r["ci_lower"]], [r["ci_upper"] - r["estimate"]]],
                        fmt=marker, ms=12, color=BLACK, mfc=fill, mec=BLACK, mew=1.8, elinewidth=2.2,
                        capsize=5, label=MODEL_LABELS[model])
        ax.axvline(0, color=BLACK, lw=1.3, ls=":")
        ax.set_title(title, fontsize=14, loc="center")
        ax.set_yticks([])
        ax.set_ylim(0.4, 3.6)
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_formatter(TICK_FORMAT)
        ax.tick_params(axis="x", labelsize=12)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04), columnspacing=2.2)
    fig.suptitle("Katsayılar ve %95 güven aralıkları (ülke düzeyinde kümelenmiş standart hata)",
                 fontsize=15, fontweight="bold", x=0.04, ha="left")
    fig.subplots_adjust(left=0.03, right=0.98, top=0.82, bottom=0.2)
    save(fig, "05_coefficients.png")


def panel_length() -> None:
    t = pd.DataFrame(RESULT["pwt11"]["panel_length_effect"])
    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.errorbar(t["T"], t["estimate"], yerr=1.96 * t["std_error"], fmt="o-", color=BLACK, ms=9, lw=2.4,
                capsize=5, mfc="white", mew=2)
    for _, r in t.iterrows():
        ax.annotate(fmt(r["estimate"]), (r["T"], r["estimate"]), xytext=(12, -2), textcoords="offset points",
                    fontsize=12.5, fontweight="bold", va="center")
    ax.set_xticks(t["T"], [f"T = {a}\n1973–{str(b)[2:]}" for a, b in zip(t["T"], t["end_year"])], fontsize=11.5)
    ax.set_xlim(3.5, 10.7)
    ax.set_ylabel("FE katsayısı: ln(Başlangıç GSYH)")
    ax.set_title("Panel uzadıkça sabit etkiler katsayısı küçülüyor")
    ax.yaxis.set_major_formatter(TICK_FORMAT)
    fig.tight_layout()
    save(fig, "06_panel_length.png")


def turkey() -> None:
    t = pd.read_csv(TABLES / "turkey.csv")
    x = np.arange(len(t))
    w = 0.38
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.bar(x - w / 2, t["growth"], w, color=BLACK, edgecolor=BLACK, label="Gerçekleşen")
    ax.bar(x + w / 2, t["fitted"], w, color="white", edgecolor=BLACK, hatch="///", lw=1.4,
           label="Sabit etkiler modeli")
    ax.plot(x, t["sample_mean"], color=DARK, lw=2, ls="--", marker="D", ms=6, label="Tüm ülkelerin ortalaması")
    ax.axhline(0, color=BLACK, lw=1.1)
    for xi, g in zip(x, t["growth"]):
        ax.text(xi - w / 2, g + (0.15 if g >= 0 else -0.45), fmt(g, 1), ha="center", fontsize=11.5,
                fontweight="bold")
    ax.set_xticks(x, t["period_label"], fontsize=11.5)
    ax.set_ylabel("Yıllık ortalama büyüme (%)")
    ax.set_title("Türkiye: gerçekleşen büyüme ve model uyumu")
    ax.set_ylim(-0.8, 7)
    ax.legend(loc="upper left", ncol=3)
    ax.yaxis.set_major_formatter(TICK_FORMAT)
    fig.tight_layout()
    save(fig, "07_turkey.png")


def fixed_effect_distribution() -> None:
    e = pd.read_csv(TABLES / "country_fixed_effects.csv")
    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.hist(e["fixed_effect_deviation"], bins=20, color=LIGHT, edgecolor=BLACK, lw=1.2, hatch="//")
    ax.axvline(0, color=BLACK, lw=2.4, ls="--")
    tur = float(e.loc[e["country"] == "TUR", "fixed_effect_deviation"].iloc[0])
    ax.annotate("Türkiye", (tur, 0), xytext=(tur, ax.get_ylim()[1] * 0.75), ha="center",
                fontsize=13, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=BLACK, lw=1.6))
    ax.set_xlabel("Ülke sabit etkisinin ortalamadan farkı (yüzde puan)")
    ax.set_ylabel("Ülke sayısı")
    ax.set_title("Ülke sabit etkilerinin dağılımı")
    comma_ticks(ax)
    fig.tight_layout()
    save(fig, "08_fixed_effect_distribution.png")


def main() -> None:
    df = pd.read_csv(PROCESSED / "panel_pwt11.csv")
    turkey_korea()
    panel_structure(df)
    pooled_vs_within(df)
    convergence()
    coefficients()
    panel_length()
    turkey()
    fixed_effect_distribution()


if __name__ == "__main__":
    main()
