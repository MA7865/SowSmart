
import pandas as pd

import sim_core as sc


def main():
    rows = []

    for name in sc.DISTRICTS:
        print(f"Extracting yearly features: {name}")
        df = sc.load(name)

        for sow_year in range(
            sc.FIRST_SOW_YEAR,
            sc.LAST_SOW_YEAR + 1
        ):
            result = sc.simulate(
                df,
                pd.Timestamp(f"{sow_year}-{sc.STD_SOW}")
            )

            if result is None:
                continue

            harvest_year = sow_year + 1

            autumn = df.loc[
                f"{sow_year}-10-01":
                f"{sow_year}-12-31"
            ]

            spring = df.loc[
                f"{harvest_year}-03-01":
                f"{harvest_year}-04-30"
            ]

            if autumn.empty or spring.empty:
                continue

            autumn_tmean = (
                autumn["temperature_2m_max"]
                + autumn["temperature_2m_min"]
            ) / 2.0

            rows.append({
                "district": name,
                "season": harvest_year,
                "heat_days_std": result["heat"],
                "frost_days_std": result["frost"],
                "stress_std": result["stress"],
                "oct_dec_tmean": round(
                    float(autumn_tmean.mean()), 2
                ),
                "mar_apr_tmax_mean": round(
                    float(spring["temperature_2m_max"].mean()),
                    2,
                ),
                "mar_apr_rain": round(
                    float(spring["precipitation_sum"].sum()),
                    1,
                ),
            })

    output_dir = sc.BASE_DIR / "data"
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / "yearly_features.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False)

    print(f"\nSaved {len(rows)} rows to {output_path}")
    print("Expected maximum: 200 rows (8 districts x 25 seasons).")


if __name__ == "__main__":
    main()
