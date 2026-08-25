"""
Stage 2 - Remaining Useful Life (RUL) Estimation.

Component C's target design tracks the Stage 1 health-score trajectory
against a (water-quality-conditioned) failure threshold. The prototype keeps
that same input contract - engineered features PLUS the Stage 1 reconstruction
error - and regresses directly against the synthetic ground-truth RUL_days
label, using a Random Forest as a simple, dependency-light baseline regressor
that is easy to swap for a trajectory-based model later.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from .. import config


class RULEstimator:
    def __init__(self, random_state: int = config.RANDOM_STATE):
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            random_state=random_state,
            n_jobs=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RULEstimator":
        self.model.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.clip(self.model.predict(X), 0, None)
