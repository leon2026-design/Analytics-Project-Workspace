"""Inspect JCRL route parsing against a sample of the source files."""

import re

import pandas as pd


def main():
    """Run the diagnostic only when source data is available locally."""
    test_jcrls = [
        "SADASR00032**C    0 ",
        "SADASR00032**C  334 ",
        "SWOOUS00006**C17505",
        "SWOOIR00070**C30120",
    ]

    print("JCRL Cleaning Test:")
    print("=" * 60)
    for jcrl in test_jcrls:
        cleaned = re.sub(r"\s*\d+\s*$", "", jcrl.strip()).strip()
        match = re.search(r"([A-Z]{2})(\d{5})", cleaned)
        if match:
            print(f"{jcrl:30s} -> {cleaned:20s} ({match.group(1)}, {int(match.group(2))})")
        else:
            print(f"{jcrl:30s} -> {cleaned:20s} (NO MATCH)")

    df_2024 = pd.read_csv("backend/data/24CarGrowthData(CMS5).csv", nrows=100)
    df_2025 = pd.read_csv("backend/data/CMS_2025.csv", nrows=100)
    print("\n2024 sample JCRL values:")
    print(df_2024["JCRL"].head().to_string(index=False))
    print("\n2025 sample route information:")
    print(df_2025[["NLFID", "ROUTE_TYPE", "ROUTE_NBR"]].head().to_string(index=False))


if __name__ == "__main__":
    main()
