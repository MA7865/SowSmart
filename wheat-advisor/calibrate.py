
from pathlib import Path

import numpy as np
import pandas as pd

import sim_core as sc


TOTALS_TO_TEST = [1800, 2000, 2200, 2400, 2600]
YEARS_TO_TEST = range(2005, 2021)


def main():
    rows = []

    for total in TOTALS_TO_TEST:
        sc.GDD_TOTAL = float(total)
        print(f"\nGDD_TOTAL = {total}")

        for name in sc.DISTRICTS:
            df = sc.load(name)
            maturity_dates = []

            for year in YEARS_TO_TEST:
                result = sc.simulate(
                    df,
                    pd.Timestamp(f"{year}-{sc.STD_SOW}")
                )

                if result is not None:
                    maturity_dates.append(result["maturity"])

            if not maturity_dates:
                print(f"  {name}: no valid maturity dates")
                continue

            # Average day-of-year for an approximate seasonal
            # comparison. This is not independent validation.
            mean_doy = np.mean([
                d.dayofyear for d in maturity_dates
            ])

            approximate_date = (
                pd.Timestamp("2001-01-01")
                + pd.Timedelta(days=float(mean_doy) - 1)
            )

            print(
                f"  {name}: approximately "
                f"{approximate_date.strftime('%b %d')} "
                f"({len(maturity_dates)} seasons)"
            )

            rows.append({
                "GDD_TOTAL": total,
                "district": name,
                "approx_maturity": approximate_date.strftime("%b %d"),
                "seasons_available": len(maturity_dates),
            })

    table = pd.DataFrame(rows)
    docs = sc.BASE_DIR / "docs"
    docs.mkdir(exist_ok=True)

    output = docs / "calibration_table.md"
    with open(output, "w", encoding="utf-8") as f:
        f.write("# GDD Calibration Comparison\n\n")
        f.write(
            "These are simulated maturity dates under alternative "
            "GDD assumptions. Compare them with the cited official "
            "agronomic reference; this is tuning, not independent "
            "validation.\n\n"
        )
        f.write(table.to_markdown(index=False))

    print(f"\nSaved calibration table to {output}")


if __name__ == "__main__":
    main()
