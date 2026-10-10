
import pandas as pd

import sim_core as sc


def main():
    name = "Faisalabad"
    df = sc.load(name)

    base_gdd = sc.GDD_TOTAL
    base_heat = sc.HEAT_C

    rows = []

    for threshold in [33, 34, 35]:
        for gdd_total in [
            base_gdd * 0.9,
            base_gdd,
            base_gdd * 1.1,
        ]:
            sc.HEAT_C = float(threshold)
            sc.GDD_TOTAL = float(gdd_total)

            print(
                f"Testing heat threshold={threshold}, "
                f"GDD={gdd_total:.0f}"
            )

            try:
                summary = sc.district_summary(df)

                rows.append({
                    "heat_threshold_C": threshold,
                    "GDD_TOTAL": round(gdd_total),
                    "best_date": summary["best"],
                    "window_start": summary["window_start"],
                    "window_end": summary["window_end"],
                    "edge_warning": summary["edge_warning"],
                })

            except Exception as exc:
                print(f"Could not calculate this setting: {exc}")

    # Restore the defaults in this Python process.
    sc.HEAT_C = base_heat
    sc.GDD_TOTAL = base_gdd

    table = pd.DataFrame(rows)

    docs = sc.BASE_DIR / "docs"
    docs.mkdir(exist_ok=True)

    output_path = docs / "sensitivity.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Sensitivity Analysis: Faisalabad\n\n")
        f.write(
            "The table compares simulated candidate dates under "
            "different heat thresholds and GDD totals. These "
            "settings are assumptions, not measured crop parameters.\n\n"
        )

        if table.empty:
            f.write("No valid results were produced.\n")
        else:
            f.write(table.to_markdown(index=False))

    print(f"\nSaved sensitivity table to {output_path}")


if __name__ == "__main__":
    main()
