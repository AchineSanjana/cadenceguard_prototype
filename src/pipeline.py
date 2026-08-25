"""
End-to-end pipeline: load -> preprocess -> Stage 1 (anomaly) -> Stage 2 (RUL)
-> Stage 3 (failure-mode classification) -> evaluate -> save artifacts.

This is the single source of truth used by the notebooks, `run_pipeline.py`,
and the Streamlit frontend, so all three always show the same numbers.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from . import config, data_loader, preprocessing, evaluate
from .models.autoencoder import AnomalyAutoencoder
from .models.rul_estimator import RULEstimator
from .models.classifier import FailureModeClassifier


def run_variant(variant: str, verbose: bool = True) -> dict:
    """Run the full three-stage pipeline for one input variant
    ('variant1' | 'variant2' | 'variant3') and save all artifacts."""
    if verbose:
        print(f"\n{'=' * 70}\n Running pipeline for {config.VARIANT_LABELS[variant]}\n{'=' * 70}")

    df = data_loader.load_variant(variant)
    splits = data_loader.split_by_time(df)
    feature_cols = config.FEATURE_COLS[variant]

    scaler = preprocessing.fit_scaler(splits["train"], feature_cols)

    windows = {}
    for split_name, split_df in splits.items():
        X_win, X_last, meta = preprocessing.build_windows(split_df, feature_cols, scaler)
        windows[split_name] = {"X_win": X_win, "X_last": X_last, "meta": meta}
        if verbose:
            print(f"  {split_name}: {len(split_df)} rows -> {X_win.shape[0]} windows")

    # ---------------- Stage 1: Anomaly Detection (autoencoder) ----------------
    train_meta = windows["train"]["meta"]
    healthy_mask = (train_meta["failure_mode_label"] == "Normal").values
    autoencoder = AnomalyAutoencoder(input_dim=windows["train"]["X_win"].shape[1])
    autoencoder.fit(windows["train"]["X_win"][healthy_mask])

    health_scores = {}
    alert_levels = {}
    for split_name in ["train", "val", "test"]:
        health_scores[split_name] = autoencoder.reconstruction_error(windows[split_name]["X_win"])
        alert_levels[split_name] = autoencoder.alert_level(health_scores[split_name])

    anomaly_pred_test = (alert_levels["test"] != "Normal").astype(int)
    anomaly_true_test = windows["test"]["meta"]["anomaly_label"].fillna(0).astype(int).values
    anomaly_metrics = evaluate.anomaly_detection_metrics(anomaly_true_test, anomaly_pred_test)

    # ---------------- Stage 2: RUL Estimation ----------------
    def rul_feature_matrix(split_name):
        return np.hstack([windows[split_name]["X_last"], health_scores[split_name].reshape(-1, 1)])

    X_rul_train = rul_feature_matrix("train")
    y_rul_train = windows["train"]["meta"]["RUL_days"].values
    rul_model = RULEstimator().fit(X_rul_train, y_rul_train)

    X_rul_test = rul_feature_matrix("test")
    y_rul_test = windows["test"]["meta"]["RUL_days"].values
    y_rul_pred_test = rul_model.predict(X_rul_test)
    rul_metrics = evaluate.rul_metrics(y_rul_test, y_rul_pred_test)

    # ---------------- Stage 3: Failure-Mode Classification ----------------
    X_clf_train = X_rul_train  # same shared representation, per Component C's design intent
    y_clf_train = windows["train"]["meta"]["failure_mode_label"].values
    classifier = FailureModeClassifier().fit(X_clf_train, y_clf_train)

    X_clf_test = X_rul_test
    y_clf_test = windows["test"]["meta"]["failure_mode_label"].values
    y_clf_pred_test = classifier.predict(X_clf_test)
    y_clf_proba_test = classifier.predict_proba(X_clf_test)
    clf_metrics = evaluate.classification_metrics(y_clf_test, y_clf_pred_test, config.FAILURE_MODE_CLASSES)

    # ---------------- Assemble test-set predictions table (for the frontend) ----------------
    proba_df = pd.DataFrame(y_clf_proba_test, columns=[f"proba_{c}" for c in classifier.classes_])
    test_predictions = windows["test"]["meta"].copy().reset_index(drop=True)
    test_predictions["health_score"] = health_scores["test"]
    test_predictions["alert_level"] = alert_levels["test"]
    test_predictions["RUL_days_predicted"] = y_rul_pred_test
    test_predictions["failure_mode_predicted"] = y_clf_pred_test
    test_predictions = pd.concat([test_predictions, proba_df], axis=1)
    test_predictions["abs_rul_error"] = np.abs(
        test_predictions["RUL_days"] - test_predictions["RUL_days_predicted"]
    )
    test_predictions["variant"] = variant

    # ---------------- Save artifacts ----------------
    joblib.dump(
        {
            "scaler": scaler,
            "autoencoder": autoencoder,
            "rul_model": rul_model,
            "classifier": classifier,
            "feature_cols": feature_cols,
            "window_size": config.WINDOW_SIZE_HOURS,
        },
        config.MODELS_DIR / f"{variant}_pipeline.joblib",
    )

    test_predictions.to_csv(config.RESULTS_DIR / f"{variant}_test_predictions.csv", index=False)

    metrics_out = {
        "variant": variant,
        "label": config.VARIANT_LABELS[variant],
        "n_features": len(feature_cols),
        "feature_cols": feature_cols,
        "n_train_windows": int(windows["train"]["X_win"].shape[0]),
        "n_val_windows": int(windows["val"]["X_win"].shape[0]),
        "n_test_windows": int(windows["test"]["X_win"].shape[0]),
        "anomaly_detection": anomaly_metrics,
        "rul_estimation": rul_metrics,
        "failure_mode_classification": clf_metrics,
        "alert_level_distribution_test": pd.Series(alert_levels["test"]).value_counts().to_dict(),
    }
    with open(config.RESULTS_DIR / f"{variant}_metrics.json", "w") as f:
        json.dump(metrics_out, f, indent=2, default=str)

    if verbose:
        print(f"  Stage 1 (anomaly)  -> precision={anomaly_metrics['precision']:.3f}, "
              f"recall={anomaly_metrics['recall']:.3f}, f1={anomaly_metrics['f1']:.3f}")
        print(f"  Stage 2 (RUL)      -> RMSE={rul_metrics['rmse']:.2f} days, MAE={rul_metrics['mae']:.2f} days")
        print(f"  Stage 3 (classify) -> accuracy={clf_metrics['accuracy']:.3f}, "
              f"macro-F1={clf_metrics['f1_macro']:.3f}")

    return {"metrics": metrics_out, "test_predictions": test_predictions}


def run_all(verbose: bool = True) -> dict:
    """Run all three variants and produce the cross-variant comparison +
    paired significance tests required by Section 7.1 of the Component C doc."""
    results = {}
    for variant in ["variant1", "variant2", "variant3"]:
        results[variant] = run_variant(variant, verbose=verbose)

    # ---------------- Cross-variant comparison table ----------------
    comparison_rows = []
    for variant, res in results.items():
        m = res["metrics"]
        comparison_rows.append({
            "variant": variant,
            "label": m["label"],
            "n_features": m["n_features"],
            "rul_rmse": m["rul_estimation"]["rmse"],
            "rul_mae": m["rul_estimation"]["mae"],
            "classification_accuracy": m["failure_mode_classification"]["accuracy"],
            "classification_f1_macro": m["failure_mode_classification"]["f1_macro"],
            "anomaly_precision": m["anomaly_detection"]["precision"],
            "anomaly_recall": m["anomaly_detection"]["recall"],
            "anomaly_f1": m["anomaly_detection"]["f1"],
        })
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.to_csv(config.RESULTS_DIR / "variant_comparison.csv", index=False)

    # ---------------- Paired significance test: Variant 3 vs Variant 1 ----------------
    # Align on (pump_id, timestamp) so we're comparing the SAME test instants
    # across variants, per the doc's "same test folds for each variant" rule.
    v1 = results["variant1"]["test_predictions"][["pump_id", "timestamp", "abs_rul_error"]]
    v3 = results["variant3"]["test_predictions"][["pump_id", "timestamp", "abs_rul_error"]]
    merged = v1.merge(v3, on=["pump_id", "timestamp"], suffixes=("_v1", "_v3"))
    significance = evaluate.paired_significance_test(
        merged["abs_rul_error_v1"].values, merged["abs_rul_error_v3"].values
    )
    significance["n_paired_samples"] = int(len(merged))
    significance["mean_abs_rul_error_variant1"] = float(merged["abs_rul_error_v1"].mean())
    significance["mean_abs_rul_error_variant3"] = float(merged["abs_rul_error_v3"].mean())

    with open(config.RESULTS_DIR / "significance_tests.json", "w") as f:
        json.dump(significance, f, indent=2, default=str)

    if verbose:
        print(f"\n{'=' * 70}\n Cross-variant comparison\n{'=' * 70}")
        print(comparison_df.to_string(index=False))
        print(f"\nPaired t-test (Variant 1 vs Variant 3 RUL abs. error): "
              f"p={significance['paired_t_test']['p_value']:.4f}, "
              f"significant={significance['significant_at_0.05']}")

    return {"per_variant": results, "comparison": comparison_df, "significance": significance}
