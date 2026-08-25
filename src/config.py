"""
Central configuration for the AquaGuard Component C prototype.
Keeping paths and column groupings in one place so notebooks, src/, and the
frontend all agree on the same schema.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all resolved relative to the project root, so this works the same
# whether you run it from a notebook, a script, or the Streamlit app)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = OUTPUTS_DIR / "models"
RESULTS_DIR = OUTPUTS_DIR / "results"
FIGURES_DIR = OUTPUTS_DIR / "figures"

for d in (MODELS_DIR, RESULTS_DIR, FIGURES_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATA_FILES = {
    "variant1": DATA_DIR / "variant1_mechanical_only.csv",
    "variant2": DATA_DIR / "variant2_mechanical_water_quality.csv",
    "variant3": DATA_DIR / "variant3_fully_fused.csv",
    "full": DATA_DIR / "aquaguard_fused_dataset_full.csv",
}

# ---------------------------------------------------------------------------
# Column groupings (mirrors the AquaGuard Component B / Component C docs)
# ---------------------------------------------------------------------------
ID_COLS = ["pump_id", "timestamp"]
LABEL_COLS = ["RUL_days", "right_censored", "failure_mode_label", "anomaly_label", "data_split"]

FEATURE_COLS = {
    "variant1": [
        "vibration_rms_g", "vibration_peak_freq_hz", "temperature_c",
        "acoustic_level_db", "current_draw_a",
        "vibration_rms_roll_mean_6h", "vibration_rms_roll_std_6h",
    ],
    "variant2": [
        "vibration_rms_g", "vibration_peak_freq_hz", "temperature_c",
        "acoustic_level_db", "current_draw_a",
        "vibration_rms_roll_mean_6h", "vibration_rms_roll_std_6h",
        "ph", "turbidity_ntu", "conductivity_us_cm", "flow_lmin", "water_aggression_index",
    ],
    "variant3": [
        "vibration_rms_g", "vibration_peak_freq_hz", "temperature_c",
        "acoustic_level_db", "current_draw_a",
        "vibration_rms_roll_mean_6h", "vibration_rms_roll_std_6h",
        "ph", "turbidity_ntu", "conductivity_us_cm", "flow_lmin", "water_aggression_index",
        "rainfall_mm", "humidity_pct",
        "turbidity_roll_mean_24h", "ph_roll_mean_24h",
        "rainfall_lag_24h", "turbidity_lag_6h", "ph_lag_6h", "water_aggression_index_lag_24h",
        "turbidity_baseline_expected", "turbidity_deviation_from_baseline",
        "pump_stress_index",
    ],
}

VARIANT_LABELS = {
    "variant1": "Variant 1 - Mechanical Only (A1)",
    "variant2": "Variant 2 - Mechanical + Water Quality (A1 + A2)",
    "variant3": "Variant 3 - Fully Fused (A1 + A2 + Weather + Component B features)",
}

FAILURE_MODE_CLASSES = ["Normal", "Mechanical", "Chemical"]

# Sliding window length (hours) used to build sequences for the Stage 1
# autoencoder - matches Component C's "last 30-60 minutes" idea, scaled to our
# hourly-resampled data (Component B resamples everything to an hourly index).
WINDOW_SIZE_HOURS = 24

# Alert-level thresholds applied to the Stage 1 reconstruction-error score,
# expressed as percentiles of the *healthy training* reconstruction error
# distribution - mirrors Component D's four-level escalation (Normal / Watch /
# Warning / Critical) described in the Component B TAF.
ALERT_LEVELS = ["Normal", "Watch", "Warning", "Critical"]
ALERT_THRESHOLD_PERCENTILES = [0, 90, 97, 99.5]  # lower bound of each level

RANDOM_STATE = 42
