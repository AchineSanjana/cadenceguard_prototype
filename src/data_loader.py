"""
Data loading utilities.

These functions are the prototype's stand-in for "Component B's handoff" -
in the real system Component C would query InfluxDB for the fused feature
set; here it reads the CSV files that were generated to look exactly like
that handoff (see /data/README inherited from the dataset generation step).
"""

from __future__ import annotations

import pandas as pd

from . import config


def load_variant(variant: str) -> pd.DataFrame:
    """Load one of 'variant1', 'variant2', 'variant3', or 'full'."""
    if variant not in config.DATA_FILES:
        raise ValueError(f"Unknown variant '{variant}'. Choose from {list(config.DATA_FILES)}.")
    df = pd.read_csv(config.DATA_FILES[variant], parse_dates=["timestamp"])
    return df.sort_values(["pump_id", "timestamp"]).reset_index(drop=True)


def split_by_time(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split using the pre-computed `data_split` column (train/val/test),
    which was built per-pump, time-ordered - never randomly - matching the
    no-future-leakage rule from the Component B/C procedure docs."""
    return {split: df[df["data_split"] == split].reset_index(drop=True)
            for split in ["train", "val", "test"]}


def list_pumps(df: pd.DataFrame) -> list[str]:
    return sorted(df["pump_id"].unique().tolist())
