"""Turn the raw datasets into balanced five-year panels.

Two panels are built:

1) PWT 11.0 panel (main analysis)
   Source : Penn World Table 11.0 (October 2025), data/raw/pwt110.csv
   Span   : 1973-2023, 10 periods (1973-78, ..., 2018-23)
   Output : data/processed/panel_pwt11.csv

2) PWT 5 panel (comparison)
   Source : Penn World Table 5 (Summers and Heston), data/raw/SumHes.csv
   Span   : 1960-1985, 5 periods
   Output : data/processed/panel_pwt5.csv

Variables are defined the same way in both panels, so results from data
published in 1991 can be compared with data published in 2025.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from paths import PROCESSED, RAW, ROOT

PERIOD_LENGTH = 5

# Landlocked countries (ISO3). The indicator is time-invariant, so it is absorbed by
# the country effect under fixed effects; it is kept to contrast FE with RE.
LANDLOCKED = {
    "AFG", "AND", "ARM", "AUT", "AZE", "BDI", "BFA", "BLR", "BOL", "BTN", "BWA", "CAF",
    "CHE", "CZE", "ETH", "HUN", "KAZ", "KGZ", "LAO", "LIE", "LSO", "LUX", "MDA", "MKD",
    "MLI", "MNG", "MWI", "NER", "NPL", "PRY", "RWA", "SMR", "SRB", "SSD", "SVK", "SWZ",
    "TCD", "TJK", "TKM", "UGA", "UZB", "ZMB", "ZWE",
}


def period_values(country: pd.DataFrame, start: int) -> dict:
    """Compute the period variables for one country. `country` is indexed by year."""
    end = start + PERIOD_LENGTH
    window = country.loc[start:end - 1]  # the five years of the period; periods do not overlap
    return {
        "period": start,
        "growth": 100 * (country.loc[end, "ln_gdp"] - country.loc[start, "ln_gdp"]) / PERIOD_LENGTH,
        "ln_gdp0": country.loc[start, "ln_gdp"],
        "investment": window["investment"].mean(),
        "pop_growth": 100 * (country.loc[end, "ln_pop"] - country.loc[start, "ln_pop"]) / PERIOD_LENGTH,
    }


def build_pwt11_panel() -> pd.DataFrame:
    raw = pd.read_csv(RAW / "pwt110.csv")
    # rgdpna (national-accounts growth rates, 2021 prices) is consistent over time.
    raw["ln_gdp"] = np.log(raw["rgdpna"] / raw["pop"])
    raw["ln_pop"] = np.log(raw["pop"])
    raw["investment"] = 100 * raw["csh_i"]

    starts = list(range(1973, 2023, PERIOD_LENGTH))  # 1973, 1978, ..., 2018
    years = range(starts[0], starts[-1] + PERIOD_LENGTH + 1)
    required = ["rgdpna", "pop", "csh_i", "hc"]

    rows = []
    for code, country in raw.groupby("countrycode"):
        country = country.set_index("year")
        if not country.reindex(years)[required].notna().all().all():
            continue  # balanced panel: keep countries with complete data in every year
        for start in starts:
            row = period_values(country, start)
            row.update(
                country=code,
                country_name=country["country"].iloc[0],
                ln_hc0=np.log(country.loc[start, "hc"]),
                landlocked=int(code in LANDLOCKED),
            )
            rows.append(row)
    columns = ["country", "country_name", "period", "growth", "ln_gdp0", "investment",
               "pop_growth", "ln_hc0", "landlocked"]
    return pd.DataFrame(rows)[columns]


def build_pwt5_panel() -> pd.DataFrame:
    raw = pd.read_csv(RAW / "SumHes.csv")
    raw["ln_gdp"] = np.log(raw["gdp"])
    raw["ln_pop"] = np.log(raw["pop"])
    raw["investment"] = raw["sr"]  # PWT 5 reports the saving rate

    rows = []
    for name, country in raw.groupby("country"):
        country = country.set_index("year")
        for start in [1960, 1965, 1970, 1975, 1980]:
            row = period_values(country, start)
            row.update(
                country=name,
                opec=int(country["opec"].iloc[0] == "yes"),
                communist=int(country["com"].iloc[0] == "yes"),
            )
            rows.append(row)
    columns = ["country", "period", "growth", "ln_gdp0", "investment", "pop_growth", "opec", "communist"]
    return pd.DataFrame(rows)[columns]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, panel in [("pwt11", build_pwt11_panel()), ("pwt5", build_pwt5_panel())]:
        path = PROCESSED / f"panel_{name}.csv"
        panel.to_csv(path, index=False)
        n, t = panel["country"].nunique(), panel["period"].nunique()
        print(f"{Path(path).relative_to(ROOT)}: N={n}, T={t}, observations={len(panel)}")


if __name__ == "__main__":
    main()
