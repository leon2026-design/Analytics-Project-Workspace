"""Test if NLFID and cleaned JCRL can match on route info."""

import pandas as pd
import re


def main():
    """Compare parsed route fields with a sample of the source files."""
    df_2024 = pd.read_csv("backend/data/24CarGrowthData(CMS5).csv", nrows=1000)
    df_2025 = pd.read_csv("backend/data/CMS_2025.csv", nrows=1000)

    df_2024["jcrl_clean"] = df_2024["JCRL"].apply(
        lambda value: re.sub(r"\s*\d+\s*$", "", str(value).strip()).strip()
    )
    df_2024["route_24"] = df_2024["jcrl_clean"].apply(
        lambda value: re.search(r"([A-Z]{2})(\d{5})", value)
    )
    df_2024["rtype_24"] = df_2024["route_24"].apply(
        lambda match: match.group(1) if match else None
    )
    df_2024["rnbr_24"] = df_2024["route_24"].apply(
        lambda match: int(match.group(2)) if match else None
    )

    df_2025["route_25"] = df_2025["NLFID"].apply(
        lambda value: re.search(r"([A-Z]{2})(\d{5})", str(value))
    )
    df_2025["rtype_25"] = df_2025["route_25"].apply(
        lambda match: match.group(1) if match else None
    )
    df_2025["rnbr_25"] = df_2025["route_25"].apply(
        lambda match: int(match.group(2)) if match else None
    )

    print("2024 Route extraction (first 10):")
    print(df_2024[["jcrl_clean", "rtype_24", "rnbr_24"]].head(10).to_string(index=False))
    print("\n2025 Route extraction (first 10):")
    print(
        df_2025[["NLFID", "ROUTE_TYPE", "ROUTE_NBR", "rtype_25", "rnbr_25"]]
        .head(10)
        .to_string(index=False)
    )

    route_type_rate = (df_2025["rtype_25"] == df_2025["ROUTE_TYPE"]).mean() * 100
    route_number_rate = (df_2025["rnbr_25"] == df_2025["ROUTE_NBR"]).mean() * 100
    print(f"\nNLFID route type match rate: {route_type_rate:.1f}%")
    print(f"NLFID route number match rate: {route_number_rate:.1f}%")

    routes_24 = set(zip(df_2024["rtype_24"].dropna(), df_2024["rnbr_24"].dropna()))
    routes_25 = set(zip(df_2025["ROUTE_TYPE"].dropna(), df_2025["ROUTE_NBR"].dropna()))
    common = routes_24.intersection(routes_25)
    print(f"\nCommon routes: {len(common)} of {len(routes_24)} (2024) and {len(routes_25)} (2025)")


if __name__ == "__main__":
    main()
