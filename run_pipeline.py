#!/usr/bin/env python3
"""
Run the entire AquaGuard Component C prototype pipeline end-to-end:
loads the three input variants, trains Stage 1/2/3 models for each, evaluates
them, runs the three-variant statistical comparison, and writes everything to
outputs/ (models/, results/, figures/).

Run this once after installing requirements, before opening the notebooks or
launching the frontend - it's what actually generates the artifacts they read.

    python run_pipeline.py
"""

import warnings

from src.pipeline import run_all
from src.figures import generate_all_figures

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    results = run_all(verbose=True)
    print("\nGenerating figures...")
    generate_all_figures(results)
    print("\nDone. See outputs/models, outputs/results, outputs/figures.")
    print("Next: launch the dashboard with  streamlit run frontend/app.py")
