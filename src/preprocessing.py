"""
Preprocessing: scaling and sliding-window construction.

Component B's docs specify per-channel normalisation (so no single sensor
dominates by scale) and sliding time windows as the model's input sequence.
This module implements both in a framework-light way (StandardScaler +
NumPy windowing) so the prototype has no heavy deep-learning dependency,
while keeping the exact same shape of pipeline your real model will use.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from . import config


def fit_scaler(train_df: pd.DataFrame, feature_cols: list[str]) -> StandardScaler:
    """Fit a StandardScaler on TRAIN rows only - never on val/test - to avoid
    leaking future statistics backwards, per the docs' no-leakage rule."""
    scaler = StandardScaler()
    scaler.fit(train_df[feature_cols].values)
    return scaler


def scale(df: pd.DataFrame, feature_cols: list[str], scaler: StandardScaler) -> np.ndarray:
    return scaler.transform(df[feature_cols].values)


def build_windows(
    df: pd.DataFrame,
    feature_cols: list[str],
    scaler: StandardScaler,
    window_size: int = config.WINDOW_SIZE_HOURS,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Build sliding windows PER PUMP (never across pump boundaries) so each
    window is a contiguous run of readings from one pump. Returns:
      X_windowed  - shape (n_windows, window_size * n_features), flattened,
                    for the Stage 1 autoencoder
      X_last_step - shape (n_windows, n_features), the scaled feature vector
                    at the window's LAST timestep, for Stage 2 / Stage 3
                    (which operate on "now", conditioned by the Stage 1
                    health score computed over the trailing window)
      meta_df     - one row per window: pump_id, timestamp, and the label
                    columns that apply to the window's last timestep
    """
    X_win_list, X_last_list, meta_rows = [], [], []

    for pump_id, g in df.groupby("pump_id", sort=False):
        g = g.sort_values("timestamp").reset_index(drop=True)
        scaled = scale(g, feature_cols, scaler)
        n = len(g)
        if n < window_size:
            continue
        for end in range(window_size - 1, n):
            start = end - window_size + 1
            window = scaled[start:end + 1]  # (window_size, n_features)
            X_win_list.append(window.flatten())
            X_last_list.append(scaled[end])
            row = g.iloc[end]
            meta_rows.append({
                "pump_id": pump_id,
                "timestamp": row["timestamp"],
                "RUL_days": row.get("RUL_days", np.nan),
                "failure_mode_label": row.get("failure_mode_label", np.nan),
                "anomaly_label": row.get("anomaly_label", np.nan),
                "data_split": row.get("data_split", np.nan),
            })

    n_feat = len(feature_cols)
    X_windowed = np.array(X_win_list) if X_win_list else np.empty((0, window_size * n_feat))
    X_last_step = np.array(X_last_list) if X_last_list else np.empty((0, n_feat))
    meta_df = pd.DataFrame(meta_rows)
    return X_windowed, X_last_step, meta_df
