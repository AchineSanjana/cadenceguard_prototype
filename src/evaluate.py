"""
Evaluation helpers - metrics matching the "Evaluation Metrics Summary" tables
in the Component C procedure doc: RMSE/MAE for RUL, Accuracy/F1/Confusion
Matrix for failure-mode classification, Precision/Recall for anomaly
detection, plus the paired significance test used in the three-variant
ablation (Section 7.1).
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
    precision_score,
    recall_score,
)


def rul_metrics(y_true, y_pred) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return {"rmse": rmse, "mae": mae}


def classification_metrics(y_true, y_pred, labels) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    f1_macro = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    report = classification_report(y_true, y_pred, labels=labels, zero_division=0, output_dict=True)
    return {"accuracy": acc, "f1_macro": f1_macro, "confusion_matrix": cm,
            "labels": labels, "report": report}


def anomaly_detection_metrics(y_true_binary, y_pred_binary) -> dict:
    precision = float(precision_score(y_true_binary, y_pred_binary, zero_division=0))
    recall = float(recall_score(y_true_binary, y_pred_binary, zero_division=0))
    f1 = float(f1_score(y_true_binary, y_pred_binary, zero_division=0))
    return {"precision": precision, "recall": recall, "f1": f1}


def paired_significance_test(errors_a, errors_b) -> dict:
    """Section 7.1: paired t-test (or Wilcoxon if not normally distributed)
    comparing per-sample error metrics across two variants on the SAME
    test rows. Returns both tests; caller picks whichever is appropriate."""
    errors_a = np.asarray(errors_a)
    errors_b = np.asarray(errors_b)
    n = min(len(errors_a), len(errors_b))
    errors_a, errors_b = errors_a[:n], errors_b[:n]

    t_stat, t_p = stats.ttest_rel(errors_a, errors_b)
    try:
        w_stat, w_p = stats.wilcoxon(errors_a, errors_b)
    except ValueError:
        w_stat, w_p = float("nan"), float("nan")

    return {
        "paired_t_test": {"statistic": float(t_stat), "p_value": float(t_p)},
        "wilcoxon_signed_rank": {"statistic": float(w_stat), "p_value": float(w_p)},
        "significant_at_0.05": bool(t_p < 0.05),
    }
