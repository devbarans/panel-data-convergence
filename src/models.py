"""Panel data models and diagnostic tests.

Estimated equation (Solow-type conditional convergence regression):

    growth_it = a + b1*ln_gdp0_it + b2*investment_it + b3*pop_growth_it + b4*ln_hc0_it
                + (time-invariant regressors) + period effects + mu_i + e_it

Estimators : pooled OLS, fixed effects (FE), random effects (RE)
Tests      : F (poolability), Breusch-Pagan LM, Hausman, Mundlak,
             Wooldridge (serial correlation), modified Wald (groupwise heteroskedasticity),
             Pesaran CD (cross-sectional dependence)

The main analysis uses the PWT 11.0 panel (1973-2023). The same model is estimated on
the PWT 5 panel (1960-1985) for comparison.

Outputs: outputs/tables/*.csv and outputs/results.json
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects
from scipy import stats

from paths import PROCESSED, RAW, RESULTS, TABLES

PERIOD_LENGTH = 5  # years per period

PANELS = {
    "pwt11": {
        "file": "panel_pwt11.csv",
        "time_varying": ["ln_gdp0", "investment", "pop_growth", "ln_hc0"],
        "time_invariant": ["landlocked"],
    },
    "pwt5": {
        "file": "panel_pwt5.csv",
        "time_varying": ["ln_gdp0", "investment", "pop_growth"],
        "time_invariant": ["opec", "communist"],
    },
}
MODELS = ["pooled", "fe", "re"]


def load_panel(file: str) -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / file).sort_values(["country", "period"])
    for period in sorted(df["period"].unique())[1:]:
        df[f"d{period}"] = (df["period"] == period).astype(float)
    return df.set_index(["country", "period"])


def period_dummies(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("d") and c[1:].isdigit()]


def estimate(df: pd.DataFrame, time_varying: list[str], time_invariant: list[str]) -> dict:
    dummies = period_dummies(df)
    y = df["growth"]
    x_full = sm.add_constant(df[time_varying + time_invariant + dummies])
    x_fe = df[time_varying + dummies]  # time-invariant regressors are absorbed by the country effect

    clustered = dict(cov_type="clustered", cluster_entity=True)
    return {
        "pooled": PooledOLS(y, x_full).fit(**clustered),
        "fe": PanelOLS(y, x_fe, entity_effects=True).fit(**clustered),
        "re": RandomEffects(y, x_full).fit(**clustered),
        # Conventional covariances for the Hausman test and the standard-error comparison
        "fe_conventional": PanelOLS(y, x_fe, entity_effects=True).fit(),
        "re_conventional": RandomEffects(y, x_full).fit(),
    }


# ----------------------------------------------------------------------------
# Diagnostic tests
# ----------------------------------------------------------------------------
def f_test(pooled, fe) -> dict:
    """Classical F test. H0: all country effects are equal (poolability)."""
    df_den = int(fe.df_resid)
    df_num = int(pooled.df_resid) - df_den
    f = ((pooled.resid_ss - fe.resid_ss) / df_num) / (fe.resid_ss / df_den)
    return {"statistic": float(f), "p": float(stats.f.sf(f, df_num, df_den)), "df": [df_num, df_den]}


def breusch_pagan_lm(pooled) -> dict:
    """Breusch-Pagan LM test. H0: the variance of the country effect is zero."""
    e = pooled.resids.to_frame("e")
    n = e.index.get_level_values(0).nunique()
    t = len(e) // n
    sum_sq = (e.groupby(level=0)["e"].sum() ** 2).sum()
    lm = (n * t) / (2 * (t - 1)) * (sum_sq / (e["e"] ** 2).sum() - 1) ** 2
    return {"statistic": float(lm), "p": float(stats.chi2.sf(lm, 1)), "df": 1}


def hausman(fe, re) -> dict:
    """Hausman test on the slope coefficients shared by FE and RE (period dummies excluded)."""
    common = [p for p in fe.params.index if p in re.params.index and not p.startswith("d")]
    diff = (fe.params[common] - re.params[common]).values
    v = (fe.cov.loc[common, common] - re.cov.loc[common, common]).values
    v = (v + v.T) / 2
    if np.any(np.linalg.eigvalsh(v) <= 0):
        return {"statistic": None, "p": None, "df": None, "status": "covariance_difference_not_positive_definite"}
    h = float(diff @ np.linalg.solve(v, diff))
    return {"statistic": h, "p": float(stats.chi2.sf(h, len(common))), "df": len(common)}


def mundlak(df: pd.DataFrame, time_varying: list[str], time_invariant: list[str]) -> dict:
    """Country means are added to the RE model; joint zero is tested with a clustered Wald test."""
    dummies = period_dummies(df)
    means = df[time_varying].groupby(level=0).transform("mean")
    means.columns = [f"{c}_mean" for c in time_varying]
    x = sm.add_constant(pd.concat([df[time_varying + time_invariant + dummies], means], axis=1))
    result = RandomEffects(df["growth"], x).fit(cov_type="clustered", cluster_entity=True)
    wald = result.wald_test(formula=" , ".join(f"{c} = 0" for c in means.columns))
    return {"statistic": float(wald.stat), "p": float(wald.pval), "df": len(means.columns)}


def wooldridge_serial_correlation(df: pd.DataFrame, time_varying: list[str]) -> dict:
    """Wooldridge (2002): is the coefficient of lagged first-difference residuals equal to -0.5?"""
    dummies = period_dummies(df)
    fd = df.groupby(level=0)[["growth"] + time_varying + dummies].diff().dropna()
    e = sm.OLS(fd["growth"], fd[time_varying + dummies]).fit().resid.to_frame("e")
    e["e_lag"] = e.groupby(level=0)["e"].shift(1)
    e = e.dropna()
    reg = sm.OLS(e["e"], e["e_lag"]).fit(cov_type="cluster", cov_kwds={"groups": e.index.get_level_values(0)})
    rho, se = float(reg.params["e_lag"]), float(reg.bse["e_lag"])
    t = (rho + 0.5) / se
    groups = int(e.index.get_level_values(0).nunique())
    return {"statistic": float(t ** 2), "rho": rho, "p": float(2 * stats.t.sf(abs(t), groups - 1)),
            "df": [1, groups - 1]}


def modified_wald(fe) -> dict:
    """Greene's modified Wald test. H0: the error variance is the same in every country."""
    e = fe.idiosyncratic.iloc[:, 0].rename("e")
    groups = e.groupby(level=0)
    t = int(groups.size().iloc[0])
    sigma2 = (e ** 2).mean()
    s2 = groups.apply(lambda x: (x ** 2).mean())
    v = groups.apply(lambda x: ((x ** 2 - (x ** 2).mean()) ** 2).sum() / (t * (t - 1)))
    w = float((((s2 - sigma2) ** 2) / v).sum())
    return {"statistic": w, "p": float(stats.chi2.sf(w, groups.ngroups)), "df": groups.ngroups}


def pesaran_cd(fe) -> dict:
    """Pesaran CD test on FE residuals. H0: no cross-sectional correlation."""
    e = fe.idiosyncratic.iloc[:, 0].unstack(level=1)
    n, t = e.shape
    upper = np.corrcoef(e.values)[np.triu_indices(n, k=1)]
    cd = float(np.sqrt(2 * t / (n * (n - 1))) * upper.sum())
    return {"statistic": cd, "mean_correlation": float(upper.mean()), "p": float(2 * stats.norm.sf(abs(cd)))}


# ----------------------------------------------------------------------------
# Tables and additional results
# ----------------------------------------------------------------------------
def coefficient_table(fits: dict) -> pd.DataFrame:
    rows = []
    for model in MODELS:
        r = fits[model]
        ci = r.conf_int()
        for p in r.params.index:
            if p.startswith("d") and p[1:].isdigit():
                continue
            rows.append({
                "model": model, "variable": p,
                "estimate": float(r.params[p]), "std_error": float(r.std_errors[p]),
                "t": float(r.tstats[p]), "p": float(r.pvalues[p]),
                "ci_lower": float(ci.loc[p, "lower"]), "ci_upper": float(ci.loc[p, "upper"]),
            })
    return pd.DataFrame(rows)


def fit_table(fits: dict) -> pd.DataFrame:
    rows = []
    for model in MODELS:
        r = fits[model]
        rows.append({
            "model": model, "observations": int(r.nobs), "countries": int(r.entity_info["total"]),
            "r2_within": float(r.rsquared_within),
            # The FE model has no intercept, so between and overall R2 are not reported
            "r2_between": None if model == "fe" else float(r.rsquared_between),
            "r2_overall": None if model == "fe" else float(r.rsquared_overall),
        })
    return pd.DataFrame(rows)


def country_effects(fe, df: pd.DataFrame) -> pd.DataFrame:
    effects = fe.estimated_effects.iloc[:, 0].groupby(level=0).first().rename("fixed_effect")
    means = df.groupby(level=0)[["growth", "investment", "ln_gdp0"]].mean()
    out = pd.concat([effects, means], axis=1).reset_index()
    out["fixed_effect_deviation"] = out["fixed_effect"] - out["fixed_effect"].mean()
    return out.sort_values("fixed_effect", ascending=False)


def bivariate_slopes(df: pd.DataFrame) -> dict:
    """Slope of growth on initial income: pooled, between-country and within-country."""
    g = df[["ln_gdp0", "growth"]]
    means = g.groupby(level=0).mean()
    demeaned = g - g.groupby(level=0).transform("mean")
    return {name: float(np.polyfit(v["ln_gdp0"], v["growth"], 1)[0])
            for name, v in [("pooled", g), ("between", means), ("within", demeaned)]}


def cross_section_slopes(df: pd.DataFrame) -> dict:
    """A separate cross-section for every period: slope of growth on initial income.

    A positive slope means richer countries grew faster (divergence); a negative slope
    means poorer countries caught up (unconditional convergence).
    """
    return {str(p): float(np.polyfit(g["ln_gdp0"], g["growth"], 1)[0]) for p, g in df.groupby(level=1)}


def convergence_speed(b: float) -> dict:
    """Annual convergence speed and half-life implied by the five-year growth coefficient.

    growth = 100 * (ln y_end - ln y_start) / 5, hence b = -100 * (1 - exp(-5*lambda)) / 5.
    """
    lam = -np.log(1 + b * PERIOD_LENGTH / 100) / PERIOD_LENGTH
    return {"lambda": float(lam), "half_life": float(np.log(2) / lam) if lam > 0 else None}


def panel_length_effect(df: pd.DataFrame, time_varying: list[str]) -> list[dict]:
    """How does the FE initial-income coefficient change as the same panel gets longer?

    In FE models with a lagged dependent variable the bias is of order 1/T (Nickell, 1981).
    """
    periods = sorted(df.index.get_level_values(1).unique())
    out = []
    for t in range(4, len(periods) + 1):
        sub = df[df.index.get_level_values(1).isin(periods[:t])]
        dummies = [c for c in period_dummies(sub) if sub[c].sum() > 0]
        r = PanelOLS(sub["growth"], sub[time_varying + dummies], entity_effects=True).fit(
            cov_type="clustered", cluster_entity=True)
        out.append({"T": t, "end_year": int(periods[t - 1] + PERIOD_LENGTH),
                    "estimate": float(r.params["ln_gdp0"]), "std_error": float(r.std_errors["ln_gdp0"])})
    return out


def turkey(fe, df: pd.DataFrame) -> pd.DataFrame:
    """Actual growth and FE fitted values for Turkey, period by period."""
    fitted = (fe.fitted_values.iloc[:, 0] + fe.estimated_effects.iloc[:, 0]).rename("fitted")
    t = df.loc[["TUR"]].join(fitted).reset_index()
    t["residual"] = t["growth"] - t["fitted"]
    t["period_label"] = t["period"].astype(str) + "–" + (t["period"] + PERIOD_LENGTH).astype(str).str[2:]
    t["sample_mean"] = t["period"].map(df.groupby(level=1)["growth"].mean())
    return t[["period", "period_label", "growth", "fitted", "residual", "sample_mean",
              "investment", "pop_growth", "ln_gdp0"]]


def analyse(name: str) -> tuple[dict, dict, pd.DataFrame]:
    spec = PANELS[name]
    tv, ti = spec["time_varying"], spec["time_invariant"]
    df = load_panel(spec["file"])
    fits = estimate(df, tv, ti)

    tests = {
        "f_poolability": f_test(fits["pooled"], fits["fe"]),
        "breusch_pagan_lm": breusch_pagan_lm(fits["pooled"]),
        "hausman": hausman(fits["fe_conventional"], fits["re_conventional"]),
        "mundlak": mundlak(df, tv, ti),
        "wooldridge": wooldridge_serial_correlation(df, tv),
        "modified_wald": modified_wald(fits["fe"]),
        "pesaran_cd": pesaran_cd(fits["fe"]),
    }
    coefficients = coefficient_table(fits)
    fit = fit_table(fits)
    coefficients.to_csv(TABLES / f"coefficients_{name}.csv", index=False)
    fit.to_csv(TABLES / f"model_fit_{name}.csv", index=False)
    df[tv + ti + ["growth"]].describe().T.to_csv(TABLES / f"descriptives_{name}.csv")

    summary = {
        "data": {"N": int(df.index.get_level_values(0).nunique()),
                 "T": int(df.index.get_level_values(1).nunique()), "observations": int(len(df))},
        "coefficients": coefficients.to_dict(orient="records"),
        "fit": fit.astype(object).where(fit.notna(), None).to_dict(orient="records"),
        "tests": tests,
        "re_theta": float(fits["re"].theta.iloc[0, 0]),
        "country_effect_variance_share": float(fits["re"].variance_decomposition["Percent due to Effects"]),
        "bivariate_slopes": bivariate_slopes(df),
        "cross_section_slopes": cross_section_slopes(df),
        "convergence_speed": {m: convergence_speed(float(fits[m].params["ln_gdp0"])) for m in MODELS},
        "period_mean_growth": {str(k): float(v) for k, v in df.groupby(level=1)["growth"].mean().items()},
        "descriptives": {c: {"mean": float(df[c].mean()), "std": float(df[c].std()),
                             "min": float(df[c].min()), "max": float(df[c].max())}
                         for c in ["growth"] + tv},
        "standard_error_comparison": {
            v: {"conventional": float(fits["fe_conventional"].std_errors[v]),
                "clustered": float(fits["fe"].std_errors[v])}
            for v in tv},
    }
    return summary, fits, df


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    results = {}

    pwt11, fits, df = analyse("pwt11")
    effects = country_effects(fits["fe"], df)
    effects.to_csv(TABLES / "country_fixed_effects.csv", index=False)
    tur = turkey(fits["fe"], df)
    tur.to_csv(TABLES / "turkey.csv", index=False)
    pwt11["panel_length_effect"] = panel_length_effect(df, PANELS["pwt11"]["time_varying"])
    pwt11["country_effect_std"] = float(effects["fixed_effect"].std())
    pwt11["turkey"] = {
        "periods": tur.to_dict(orient="records"),
        "mean_growth": float(tur["growth"].mean()),
        "sample_mean_growth": float(df["growth"].mean()),
        "fixed_effect_rank": int((effects["country"] == "TUR").values.argmax() + 1),
    }
    # For the opening slide: GDP per capita of Turkey and South Korea (thousand $, 2021 prices)
    raw = pd.read_csv(RAW / "pwt110.csv")
    raw = raw[raw["countrycode"].isin(["TUR", "KOR"]) & raw["year"].isin([1973, 2023])]
    pwt11["intro"] = {f"{r.countrycode}_{r.year}": float(r.rgdpna / r.pop / 1000) for r in raw.itertuples()}
    results["pwt11"] = pwt11
    results["pwt5"], _, _ = analyse("pwt5")

    RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    pd.set_option("display.width", 160)
    for name in ["pwt11", "pwt5"]:
        print(f"\n##### {name} #####")
        coef = pd.DataFrame(results[name]["coefficients"])
        print(coef[["model", "variable", "estimate", "std_error", "p"]].round(4).to_string(index=False))
        print(pd.DataFrame(results[name]["fit"]).round(3).to_string(index=False))
        for test, values in results[name]["tests"].items():
            print(test, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in values.items()})
        print("slopes", {k: round(v, 3) for k, v in results[name]["bivariate_slopes"].items()})
    print("\nPanel length effect:", [(r["T"], r["end_year"], round(r["estimate"], 2))
                                     for r in pwt11["panel_length_effect"]])
    print(tur.round(2).to_string(index=False))
    print("Turkey fixed-effect rank:", pwt11["turkey"]["fixed_effect_rank"], "/", pwt11["data"]["N"])


if __name__ == "__main__":
    main()
