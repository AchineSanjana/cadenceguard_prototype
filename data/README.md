# AquaGuard — Synthetic Component B → C Dataset (Phase A Rehearsal Data)

## What this is
This is **synthetic, placeholder data** — not real NWSDB readings. It's built to be
*structurally identical* to what Component B (Fusion & Feature Engineering Pipeline)
will hand off to Component C once A1/A2 sensors are deployed (Months 3–4). Both the
Component B and Component C procedure docs call for exactly this: build and unit-test
the pipeline on synthetic/benchmark data first ("Phase A — Pipeline Rehearsal"), then
swap in real data later without changing the code.

Row grain: **one row per pump per hour** (Component B resamples all four input
streams — A1, A2, weather, maintenance logs — onto a shared hourly time index).

## Files

| File | Purpose |
|---|---|
| `aquaguard_fused_dataset_full.csv` | Every engineered column, all 4 pumps. Your working dataset. |
| `variant1_mechanical_only.csv` | Component C **Variant 1** input (A1 only) — ablation baseline |
| `variant2_mechanical_water_quality.csv` | Component C **Variant 2** input (A1 + A2 raw) |
| `variant3_fully_fused.csv` | Component C **Variant 3** input (A1 + A2 + weather + Component B engineered features — **no maintenance-log-derived columns**) |
| `maintenance_logs_REFERENCE_ONLY_not_used_in_training.csv` | Synthetic NWSDB-style failure/maintenance log, kept only as context for how the failure scenarios line up. **Not fused into any of the training CSVs above** — per project decision, maintenance-log data is excluded from model input. |

> **Note on maintenance logs:** the Component B doc's own Variant 3 definition lists
> "historical maintenance logs" as part of the fully-fused input. That column
> (`days_since_last_maintenance`) has been **removed** from all four training
> datasets here per your instruction — maintenance logs are not going into the
> model. The log file is included purely as a readable reference for how each
> pump's `failure_mode_label` timeline was constructed.

The three `variantN_*.csv` files exist because §6 of the Component C doc requires
training/evaluating the *same* CNN‑LSTM architecture three times on three different
input widths, then running a paired t‑test / Wilcoxon test to prove fusion actually
helps. They're just column subsets of the full file, split by time the same way, so
results are directly comparable across variants.

## Scenario design (4 pumps, 90-day window, hourly)
- **PUMP_01** — healthy the entire window (right-censored RUL; majority "Normal" class)
- **PUMP_02** — pure **mechanical** degradation, onset day 45, failure day 70
- **PUMP_03** — pure **chemical/water-quality** degradation, onset day 30, failure day 55
- **PUMP_04** — mechanical degradation, onset day 60, failure day 85 (staggered timing)

For the chemical-failure pump, mechanical stress features are given a deliberate
**~4-day lag** after water-aggression rises — a synthetic stand-in for the
rainfall → water-quality → mechanical-stress causal chain Component B is meant to
test. Don't read anything scientific into the exact lag/shape; it exists so your
lag features and cross-correlation logic have a signal to actually find.

## Column reference

**Identifiers**
- `pump_id`, `timestamp`

**A1 — Mechanical (edge-processed, via MQTT)**
- `vibration_rms_g`, `vibration_peak_freq_hz`, `temperature_c`, `acoustic_level_db`, `current_draw_a`

**A2 — Water quality (edge-processed, via MQTT)**
- `ph`, `turbidity_ntu`, `conductivity_us_cm`, `flow_lmin`, `water_aggression_index` (A2's own edge-computed composite)

**Weather (Open-Meteo-style)**
- `rainfall_mm`, `humidity_pct`

**Component B — Stage 3 engineered features**
- `vibration_rms_roll_mean_6h`, `vibration_rms_roll_std_6h` — rolling mechanical stats
- `turbidity_roll_mean_24h`, `ph_roll_mean_24h` — rolling water-quality stats
- `rainfall_lag_24h`, `turbidity_lag_6h`, `ph_lag_6h`, `water_aggression_index_lag_24h` — lag features for the causal/correlation study
- `turbidity_baseline_expected`, `turbidity_deviation_from_baseline` — weather-conditioned baseline
- `pump_stress_index` — Component B's composite index (0.6×mechanical z-score + 0.4×WAI)

**Labels / targets** (ground truth — only available because this is synthetic;
in real deployment these come from `maintenance_logs.csv`-style records + the
Stage 1 autoencoder's own reconstruction error once trained)
- `RUL_days` — remaining useful life at that timestamp; capped/right-censored for the healthy pump
- `right_censored` — True if the pump had not failed by the end of this window
- `failure_mode_label` — `Normal` / `Mechanical` / `Chemical` (Component C Stage 3 classifier target)
- `anomaly_label` — 1 once the hidden degradation level passes a threshold (useful for sanity-checking your Stage 1 autoencoder's reconstruction-error threshold against a known answer)
- `data_split` — `train` / `val` / `test`, split **by time per pump** (first 70% / next 15% / last 15%), not randomly — matches the no-future-leakage rule in both procedure docs

## Using it for Component C
1. **Stage 1 (autoencoder)**: train only on `data_split == "train"` rows where `failure_mode_label == "Normal"`. Build sliding windows (e.g. last 24–48 hourly rows) as the LSTM input sequence — the CSV is intentionally long-format so you can window it however your model needs.
2. **Stage 2 (RUL)**: regress `RUL_days` from the health-score trajectory your autoencoder produces, or directly from features as a baseline.
3. **Stage 3 (classifier)**: `failure_mode_label` is your target; note classes are imbalanced (mostly `Normal`), same as real degradation data will be.
4. **Three-variant ablation**: train identically on `variant1`, `variant2`, `variant3`, compare RMSE/MAE (RUL) and F1 (classification), then run the paired t-test called for in §7.1.

## Regenerating / adjusting
The full generator is reproducible (`numpy` seed = 42). If you want more pumps, a
longer window, different failure timing, or minute-level instead of hourly
resolution, the generation script can be adjusted — happy to tweak parameters if
this mix of scenarios doesn't stress-test what you need.
