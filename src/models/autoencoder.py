"""
Stage 1 - Anomaly Detection.

Component C's target architecture is a CNN-LSTM autoencoder trained only on
healthy pump data, using reconstruction error as a rising "health score".

This prototype implements the exact same IDEA with a lightweight stand-in
(a bottlenecked MLP autoencoder over flattened sliding windows) so it trains
in seconds on a laptop with no GPU / deep-learning framework required. The
class is written so swapping in a real CNN-LSTM later only means replacing
the internals of `AnomalyAutoencoder` - everything upstream (windowing) and
downstream (RUL, classification, alert levels) stays the same.
"""

from __future__ import annotations

import numpy as np
from sklearn.neural_network import MLPRegressor

from .. import config


class AnomalyAutoencoder:
    def __init__(self, input_dim: int, random_state: int = config.RANDOM_STATE):
        bottleneck = max(4, input_dim // 8)
        hidden = max(bottleneck * 2, 8)
        self.model = MLPRegressor(
            hidden_layer_sizes=(hidden, bottleneck, hidden),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            max_iter=300,
            early_stopping=True,
            n_iter_no_change=10,
            random_state=random_state,
        )
        self._train_errors: np.ndarray | None = None
        self.thresholds_: dict[str, float] = {}

    def fit(self, X_healthy: np.ndarray) -> "AnomalyAutoencoder":
        """Train on HEALTHY windows only - the whole point of an autoencoder
        anomaly detector is that it never sees failure examples."""
        self.model.fit(X_healthy, X_healthy)
        self._train_errors = self.reconstruction_error(X_healthy)
        self._fit_thresholds()
        return self

    def reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        recon = self.model.predict(X)
        return np.mean((X - recon) ** 2, axis=1)

    def _fit_thresholds(self):
        for level, pct in zip(config.ALERT_LEVELS, config.ALERT_THRESHOLD_PERCENTILES):
            self.thresholds_[level] = float(np.percentile(self._train_errors, pct))

    def alert_level(self, errors: np.ndarray) -> np.ndarray:
        """Map reconstruction error -> Normal/Watch/Warning/Critical, using
        thresholds calibrated on the healthy training distribution (mirrors
        Component D's four-level escalation)."""
        levels = np.array(config.ALERT_LEVELS)
        bounds = np.array([self.thresholds_[l] for l in config.ALERT_LEVELS])
        idx = np.searchsorted(bounds, errors, side="right") - 1
        idx = np.clip(idx, 0, len(levels) - 1)
        return levels[idx]
