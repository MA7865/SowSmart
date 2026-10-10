"""
config.py - every model assumption in one place, with its source and status.

status values:
  SOURCED   : value taken directly from a source you extracted
  DERIVED   : computed from sourced numbers (derivation in notes)
  ASSUMPTION: no source found; kept configurable and covered by sensitivity runs
"""
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------- sources
SOURCES = {
    "APP1": "APP, 'Farmers advised to complete wheat sowing by Nov 20' https://www.app.com.pk/?p=1110857",
    "NEWS": "The News, 'Early wheat sowing gathers momentum' https://www.thenews.pk/print/1381951-early-wheat-sowing-gathers-momentum",
    "SIAL05": "Sial et al. 2005, Pak J Bot 37(3):575 (Tando Jam, Sindh)",
    "CHANDIO16": "Chandio et al. 2016, Sindh Univ Res J (Tando Jam, Sindh)",
    "AHMED26": "Ahmed et al. 2026, Sci Reports (Islamabad/Chakwal, DSSAT) https://pub.epsilon.slu.se/id/document/20460335",
    "REHMAN21": "Rehman et al. 2021, Plants 10(3):455 (Faisalabad) https://pmc.ncbi.nlm.nih.gov/articles/PMC7997430",
}

# Sowing windows as (start MM-DD, end MM-DD).
# Punjab: union of APP (Nov 1-20 ideal) and The News (Nov 15 - Dec 15 benchmark).
# Sindh: NO official window was found. Nov 1 - Dec 20 brackets the dates used in
# Tando Jam trials (SIAL05: 18 Nov normal / 11 Dec late; CHANDIO16: 8 Nov - 21 Dec).
WINDOWS = {
    "punjab": ("11-01", "12-15"),
    "sindh": ("11-01", "12-20"),
}
DISTRICT_PROVINCE = {
    "Multan": "punjab",
    "Hyderabad": "sindh",
    "Larkana": "sindh",
}


@dataclass
class ModelConfig:
    # --- phenology (GDD) ---
    gdd_base: float = 4.0            # SOURCED  AHMED26 Eq.1
    gdd_ceiling: float = 35.0        # SOURCED  AHMED26 (stage ceilings 31-35.4; 35 used). Cap applies to GDD ONLY
    gdd_total: float = 2200.0        # SOURCED  AHMED26 (~2200 base 4; Chakwal mean 2214, Islamabad 2252). Cultivar/site dependent -> calibrate
    anthesis_frac: float = 0.78      # DERIVED  anthesis/maturity days: REHMAN21 ~107/139, AHMED26 105/135 & 100/127 -> 0.77-0.79

    # --- stress terms ---
    heat_threshold: float = 34.0     # SOURCED range 33-35 (SIAL05, CHANDIO16 use 35; AHMED26 uses 30-35). Sensitivity: 33/34/35
    heat_from_frac: float = 0.78     # heat counted from anthesis to maturity (same derivation as anthesis_frac)
    warm_optimum_max: float = 22.0   # SOURCED  REHMAN21: timely-sown wheat needs 12-22 C. Warm exposure above 22 before anthesis is penalised
    frost_threshold: float = 0.0     # ASSUMPTION  no source gives a frost temperature
    frost_from_frac: float = 0.5     # ASSUMPTION  frost counted from ~booting onwards
    maturity_deadline: str = "05-15"  # ASSUMPTION carried over from your original model; sources say harvest Apr-May

    # --- weights (ALL ASSUMPTIONS; units: weighted stress degree-days or days) ---
    w_heat: float = 1.0
    w_warm: float = 0.1              # small: mild warmth early is common and mostly sub-lethal
    w_frost: float = 2.0             # same weight as your original model
    w_late: float = 2.0              # same as your original model (per day past deadline)

    # --- reference values used only for VALIDATION / sanity checks (not in the score) ---
    ref_delay_loss_pct_per_day: float = 1.0   # SOURCED APP1 (Punjab, after Nov 20)
    ref_yield_loss_pct_per_degC: float = 6.0  # SOURCED REHMAN21 (global, secondary citation)
    ref_late_sowing_maturity_shortening_days: tuple = (10, 12)  # SOURCED REHMAN21 Table 1 (Nov vs Dec sowing)
    ref_days_to_maturity: tuple = (120, 145)  # SOURCED SIAL05 / CHANDIO16 / REHMAN21 / AHMED26 (rough envelope)

    # --- sowing-date search ---
    step_days: int = 1
    edge_tolerance_days: int = 2     # best date within this many days of window edge => flagged
    score_tolerance: float = 0.5     # ASSUMPTION: dates scoring within this of the best form the 'acceptable range'

    # --- scenario offsets: PLACEHOLDERS, replace with NEX-GDDP-CMIP6-derived values ---
    scenario_offsets: dict = field(default_factory=lambda: {
        "baseline": (0.0, 0.0),      # (delta tmax, delta tmin) in C
        "+1.0C": (1.0, 1.0),
        "+2.0C": (2.0, 2.0),
        "+3.0C": (3.0, 3.0),
    })


def assumptions_table(cfg: ModelConfig = None):
    """Rows for your report's 'Model assumptions' table."""
    cfg = cfg or ModelConfig()
    rows = [
        ("gdd_base (C)", cfg.gdd_base, "SOURCED", "AHMED26"),
        ("gdd_ceiling (C, GDD only)", cfg.gdd_ceiling, "SOURCED", "AHMED26"),
        ("gdd_total (C-days)", cfg.gdd_total, "SOURCED", "AHMED26; calibrate per district"),
        ("anthesis_frac", cfg.anthesis_frac, "DERIVED", "REHMAN21, AHMED26 day counts"),
        ("heat_threshold (C)", cfg.heat_threshold, "SOURCED", "SIAL05, CHANDIO16, AHMED26 (range 33-35)"),
        ("warm_optimum_max (C)", cfg.warm_optimum_max, "SOURCED", "REHMAN21"),
        ("frost_threshold (C)", cfg.frost_threshold, "ASSUMPTION", "no source found"),
        ("frost_from_frac", cfg.frost_from_frac, "ASSUMPTION", ""),
        ("maturity_deadline", cfg.maturity_deadline, "ASSUMPTION", "from original model"),
        ("w_heat / w_warm / w_frost / w_late", (cfg.w_heat, cfg.w_warm, cfg.w_frost, cfg.w_late), "ASSUMPTION", "calibrate vs yield"),
        ("Punjab window", WINDOWS["punjab"], "SOURCED", "APP1, NEWS"),
        ("Sindh window", WINDOWS["sindh"], "ASSUMPTION", "bracketed by SIAL05 / CHANDIO16 trial dates; no official window found"),
    ]
    return [dict(parameter=a, value=b, status=c, source_or_note=d) for a, b, c, d in rows]


if __name__ == "__main__":
    for r in assumptions_table():
        print(r)