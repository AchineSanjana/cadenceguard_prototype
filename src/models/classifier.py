"""
Stage 3 - Failure-Mode Classification.

Component C's target design shares an encoder between RUL and classification.
For this lightweight prototype the two stages are trained separately (simpler
to reason about and debug for a proposal demo) but consume the SAME feature
representation (raw engineered features + Stage 1 reconstruction error), so
conceptually they are "two heads reading the same signal" as the real design
intends. Swap in a shared-encoder neural net later without touching anything
upstream.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .. import config


class FailureModeClassifier:
    def __init__(self, random_state: int = config.RANDOM_STATE):
        # Note: class_weight="balanced" was tried but over-corrects here - with
        # Mechanical being both a minority class AND the class most easily
        # confused with Normal, aggressive reweighting pushed recall on it
        # down sharply. Plain (unweighted) trees performed better on every
        # variant, so that's what's used; revisit if you add more pumps/data.
        self.model = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=1,
            random_state=random_state,
            n_jobs=-1,
        )
        self.classes_ = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "FailureModeClassifier":
        self.model.fit(X, y)
        self.classes_ = self.model.classes_
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)
