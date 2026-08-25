"""
Generates the static figures saved to outputs/figures/, used by both the
notebooks (for a paper-ready proposal appendix) and as a fallback/preview
inside the Streamlit frontend.
"""

from __future__ import annotations

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config, data_loader, preprocessing

sns.set_theme(style="whitegrid")
ALERT_COLORS = {"Normal": "#2ca02c", "Watch": "#ffbf00", "Warning": "#ff7f0e", "Critical": "#d62728"}


def score_full_timeline(variant: str, pump_id: str) -> pd.DataFrame:
    """Re-score a single pump's ENTIRE timeline (not just the test split)
    with the already-trained variant model, for a nicer end-to-end trend
    chart (pre-failure through to failure)."""
    artifact = joblib.load(config.MODELS_DIR / f"{variant}_pipeline.joblib")
    scaler, autoencoder = artifact["scaler"], artifact["autoencoder"]
    feature_cols, window_size = artifact["feature_cols"], artifact["window_size"]

    df = data_loader.load_variant(variant)
    pump_df = df[df["pump_id"] == pump_id]
    X_win, X_last, meta = preprocessing.build_windows(pump_df, feature_cols, scaler, window_size)
    if len(meta) == 0:
        return pd.DataFrame()

    rul_model, classifier = artifact["rul_model"], artifact["classifier"]
    health = autoencoder.reconstruction_error(X_win)
    alert = autoencoder.alert_level(health)
    X_stage2 = np.hstack([X_last, health.reshape(-1, 1)])
    rul_pred = rul_model.predict(X_stage2)
    mode_pred = classifier.predict(X_stage2)

    meta = meta.copy()
    meta["health_score"] = health
    meta["alert_level"] = alert
    meta["RUL_days_predicted"] = rul_pred
    meta["failure_mode_predicted"] = mode_pred
    return meta


def plot_reconstruction_error_timeline(variant: str, pump_id: str, save_path):
    meta = score_full_timeline(variant, pump_id)
    if meta.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(meta["timestamp"], meta["health_score"], color="#1f4e79", linewidth=1)
    for level, color in ALERT_COLORS.items():
        mask = meta["alert_level"] == level
        ax.scatter(meta.loc[mask, "timestamp"], meta.loc[mask, "health_score"],
                   s=8, color=color, label=level, zorder=3)
    ax.set_title(f"Stage 1 - Reconstruction Error / Health Score  ({pump_id}, {config.VARIANT_LABELS[variant]})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Reconstruction error (health score)")
    ax.legend(title="Alert level", loc="upper left")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(save_path, dpi=140)
    plt.close(fig)


def plot_rul_curve(variant: str, pump_id: str, save_path):
    meta = score_full_timeline(variant, pump_id)
    if meta.empty:
        return
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(meta["timestamp"], meta["RUL_days"], label="Actual RUL (ground truth)",
             color="#333333", linewidth=1.5)
    ax.plot(meta["timestamp"], meta["RUL_days_predicted"], label="Predicted RUL",
             color="#d62728", linewidth=1.2, alpha=0.8)
    ax.set_title(f"Stage 2 - Remaining Useful Life  ({pump_id}, {config.VARIANT_LABELS[variant]})")
    ax.set_xlabel("Time")
    ax.set_ylabel("RUL (days)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(save_path, dpi=140)
    plt.close(fig)


def plot_confusion_matrix(cm, labels, variant, save_path):
    fig, ax = plt.subplots(figsize=(5, 4.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(f"Stage 3 - Failure-Mode Confusion Matrix\n({config.VARIANT_LABELS[variant]})")
    fig.tight_layout()
    fig.savefig(save_path, dpi=140)
    plt.close(fig)


def plot_variant_comparison(comparison_df, save_path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    labels = [v.replace("Variant ", "V").split(" - ")[0] for v in comparison_df["label"]]

    axes[0].bar(labels, comparison_df["rul_rmse"], color="#4c72b0")
    axes[0].set_title("RUL RMSE (days) - lower is better")

    axes[1].bar(labels, comparison_df["classification_f1_macro"], color="#55a868")
    axes[1].set_title("Failure-mode macro-F1 - higher is better")
    axes[1].set_ylim(0, 1)

    axes[2].bar(labels, comparison_df["anomaly_f1"], color="#c44e52")
    axes[2].set_title("Anomaly detection F1 - higher is better")
    axes[2].set_ylim(0, 1)

    for ax in axes:
        ax.set_xlabel("Input variant")
    fig.suptitle("Three-Variant Comparative Experiment (Section 6, Component C)")
    fig.tight_layout()
    fig.savefig(save_path, dpi=140)
    plt.close(fig)


def generate_all_figures(results: dict):
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Representative pumps: PUMP_02 (mechanical failure), PUMP_03 (chemical failure)
    for pump_id in ["PUMP_02", "PUMP_03"]:
        plot_reconstruction_error_timeline("variant3", pump_id,
                                            config.FIGURES_DIR / f"reconstruction_error_{pump_id}.png")
        plot_rul_curve("variant3", pump_id, config.FIGURES_DIR / f"rul_curve_{pump_id}.png")

    for variant in ["variant1", "variant2", "variant3"]:
        m = results["per_variant"][variant]["metrics"]["failure_mode_classification"]
        plot_confusion_matrix(np.array(m["confusion_matrix"]), m["labels"], variant,
                               config.FIGURES_DIR / f"confusion_matrix_{variant}.png")

    plot_variant_comparison(results["comparison"], config.FIGURES_DIR / "variant_comparison.png")
