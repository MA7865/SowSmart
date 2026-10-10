import pandas as pd
import sim_core as sc
import pandas as pd

districts = [
    "Faisalabad", "Multan", "Bahawalpur", "Rahim Yar Khan",
    "Sargodha", "Sahiwal", "Larkana", "Hyderabad"
]

for district in districts:
    print(f"\n{'='*50}\n{district}")

    try:
        data = sc.load(district)
        data = data.sort_index()

        print("Rows:", len(data))
        print("Date range:", data.index.min(), "to", data.index.max())
        print("Duplicate dates:", data.index.duplicated().sum())

        expected = pd.date_range(
            data.index.min(), data.index.max(), freq="D"
        )
        missing_dates = expected.difference(data.index)
        print("Missing dates:", len(missing_dates))

        print("Missing values per column:")
        print(data.isna().sum().to_dict())

        print("Temperature min/max:")
        print(data[[
            "temperature_2m_min", "temperature_2m_max"
        ]].min().to_dict())
        print(data[[
            "temperature_2m_min", "temperature_2m_max"
        ]].max().to_dict())

        print("Negative precipitation days:",
              (data["precipitation_sum"] < 0).sum())

        print("Min temperature > max temperature:",
              (data["temperature_2m_min"] >
               data["temperature_2m_max"]).sum())

    except Exception as e:
        print("ERROR:", repr(e))