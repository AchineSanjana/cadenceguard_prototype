# AquaGuard — Component C Prototype

**ML Anomaly Detection, Remaining Useful Life (RUL) Estimation & Failure-Mode
Classification Engine — working prototype for the project proposal.**

This is a runnable, VS-Code-ready prototype of Component C, built on synthetic
data shaped exactly like the fused feature set Component B will hand off once
real NWSDB sensors are deployed. It exists to *show the shape of the pipeline* —
how the data is handled, and what the model outputs — using a simplified,
dependency-light implementation of the three-stage architecture described in
the Component C technical procedure document. Swap in a real CNN-LSTM later
without changing anything upstream or downstream.

## What's in here

```
aquaguard-componentC-prototype/
├── data/                    Synthetic fused datasets (see data/README.md)
├── notebooks/                5 notebooks walking through the whole pipeline
├── src/                      Reusable pipeline code (data, models, training, eval)
├── frontend/                 Streamlit dashboard (stands in for Component D)
├── outputs/                  Trained models, metrics, figures (pre-generated)
├── run_pipeline.py           One command: trains everything, saves all artifacts
├── requirements.txt
└── .vscode/                  Ready-to-use VS Code settings + run configs
```

## Quick start (VS Code)

1. **Open this folder in VS Code** (`File > Open Folder…`).
2. **Create a virtual environment** (VS Code will usually offer to do this
   automatically when it detects `requirements.txt` — accept it, or do it
   manually in the integrated terminal):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Select the interpreter**: `Ctrl/Cmd+Shift+P` → *Python: Select Interpreter*
   → choose `.venv`.
4. **(Optional) Re-run training** — the repo ships with pre-trained models and
   results already in `outputs/`, so this isn't required, but if you want to
   regenerate everything from scratch:
   ```bash
   python run_pipeline.py
   ```
   Or use the included VS Code run config: *Run and Debug → "Run full
   pipeline (train all 3 variants)"*.
5. **Open the notebooks** in `notebooks/` — they run top-to-bottom with no
   external setup beyond step 2, and already contain executed output so you
   can read them without re-running anything.
6. **Launch the dashboard**:
   ```bash
   streamlit run frontend/app.py
   ```
   Or use the VS Code run config: *Run and Debug → "Launch dashboard
   (Streamlit)"*. It opens in your browser at `http://localhost:8501`.

## Notebooks

| Notebook | What it covers |
|---|---|
| `01_data_exploration.ipynb` | The fused dataset, per-pump scenarios, the rainfall→water-quality→mechanical-stress causal chain |
| `02_stage1_anomaly_detection.ipynb` | Sliding-window autoencoder trained on healthy data only, reconstruction error → alert level |
| `03_stage2_rul_estimation.ipynb` | Regressing Remaining Useful Life from engineered features + Stage 1's health score |
| `04_stage3_failure_mode_classification.ipynb` | Classifying Mechanical vs. Chemical vs. Normal degradation |
| `05_three_variant_comparison.ipynb` | The Section 6 ablation experiment (mechanical-only vs. +water-quality vs. fully fused) with paired significance testing |

## The three-stage model (`src/models/`)

Component C's target design is a CNN-LSTM autoencoder (Stage 1) feeding a
shared-encoder RUL regressor (Stage 2) and failure-mode classifier (Stage 3).
This prototype keeps that exact **contract** — sliding-window input, health
score as a shared feature, same representation feeding Stages 2 and 3 — but
implements each stage with a lightweight scikit-learn model so it trains in
seconds with no GPU or deep-learning framework:

- **Stage 1** (`autoencoder.py`) — bottlenecked MLP autoencoder over flattened
  24-hour windows, trained only on healthy data. Reconstruction error → health
  score → four-level alert (Normal / Watch / Warning / Critical).
- **Stage 2** (`rul_estimator.py`) — Random Forest regressor on engineered
  features + Stage 1's health score → predicted RUL in days.
- **Stage 3** (`classifier.py`) — Random Forest classifier on the same
  representation → Mechanical / Chemical / Normal, with class probabilities.

Swapping any of these for a real CNN-LSTM / PyTorch or TensorFlow model later
means editing only that one file — `src/preprocessing.py` (windowing),
`src/pipeline.py` (orchestration), and the frontend all stay the same.

## The dashboard (`frontend/app.py`)

A Streamlit app standing in for Component D, scoped to what Component C
itself produces:

- **Overview** — pipeline diagram, dataset summary
- **Data Explorer** — raw/engineered signals per pump, interactive
- **Stage 1 tab** — health-score trend, current alert level
- **Stage 2 tab** — predicted vs. actual RUL curve, current RUL estimate
- **Stage 3 tab** — predicted failure mode, confusion matrix
- **Variant Comparison tab** — the three-variant ablation results + paired
  significance test, side by side

If `outputs/` is ever missing or deleted, the dashboard detects that and
offers a one-click "Run training pipeline now" button — no need to touch the
terminal.

## Data

See [`data/README.md`](data/README.md) for the full column-by-column schema.
Short version: synthetic, hourly, 4 pumps, 90 days, one healthy pump and three
run-to-failure scenarios (two mechanical, one chemical), split by time
(train/val/test) per pump — never randomly, to avoid future leakage, matching
both the Component B and Component C procedure docs.

## Notes for the proposal

- Every design choice here traces back to a specific line in the Component B
  or Component C technical procedure documents — see the comments at the top
  of each `src/` file for the mapping.
- The lightweight models are a deliberate simplification for a foundational
  prototype, not a claim about final model architecture — the real system
  will use the CNN-LSTM autoencoder / shared-encoder design described in the
  procedure documents once real NWSDB sensor data is available.
- Metrics in `outputs/results/*.json` and shown in the dashboard are computed
  on synthetic data and exist to prove the *pipeline* works end-to-end, not to
  claim real-world model performance.
