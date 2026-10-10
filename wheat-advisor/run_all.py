
import json

import sim_core as sc


def main():
    results = {}

    for name, (lat, lon, province) in sc.DISTRICTS.items():
        print(f"\nProcessing {name}...")

        df = sc.load(name)
        summary = sc.district_summary(df)

        results[name] = {
            "lat": lat,
            "lon": lon,
            "province": province,
            **summary,
        }

        print(
            f"{name}: best={summary['best']}, "
            f"window={summary['window_start']} to "
            f"{summary['window_end']}"
        )

        if summary["edge_warning"]:
            print("WARNING: best date is at the search boundary.")

    output_path = sc.BASE_DIR / "results.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()
