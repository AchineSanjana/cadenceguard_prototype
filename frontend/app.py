"""
CadenceGuard · Pump Health Monitor
================================
Customer-facing dashboard for pump maintenance teams and field engineers.
Shows plain-English pump status, days remaining, failure type, and
recommended maintenance actions — no ML/model internals.

Run with:
    streamlit run frontend/app.py
"""

import json
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="CadenceGuard · Pump Health Monitor",
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Strip all Streamlit chrome for a full-bleed dashboard experience
st.markdown(
    """
    <style>
        #MainMenu { visibility: hidden; }
        footer    { visibility: hidden; }
        header    { visibility: hidden; }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        iframe { border: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

FRONTEND_DIR = Path(__file__).resolve().parent
CUSTOMER_HTML = FRONTEND_DIR / "customer.html"
CSS_PATH      = FRONTEND_DIR / "css"  / "customer.css"
JS_PATH       = FRONTEND_DIR / "js"   / "customer.js"
DATA_PATH     = FRONTEND_DIR / "data" / "app_data.json"


def ensure_data() -> bool:
    """Generate the data payload if it doesn't exist yet."""
    if DATA_PATH.exists():
        return True
    try:
        import sys
        sys.path.append(str(FRONTEND_DIR.parent))
        from src.export_frontend_data import export_all
        export_all()
        return DATA_PATH.exists()
    except Exception as e:
        st.error(f"Could not generate model data: {e}")
        return False


def build_html() -> str:
    """Inline CSS, JS, and data into a single self-contained HTML document."""
    html = CUSTOMER_HTML.read_text(encoding="utf-8")
    css  = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""
    js   = JS_PATH.read_text(encoding="utf-8")  if JS_PATH.exists() else ""
    data = DATA_PATH.read_text(encoding="utf-8") if DATA_PATH.exists() else "{}"

    # Inline CSS
    html = html.replace(
        '<link rel="stylesheet" href="css/customer.css" />',
        f"<style>\n{css}\n</style>"
    )
    # Inject data + app script (replace the external script tag)
    html = html.replace(
        '<script src="js/customer.js"></script>',
        f"<script>\nwindow.AQUAGUARD_DATA = {data};\n</script>\n<script>\n{js}\n</script>"
    )
    return html


if not ensure_data():
    st.warning("⚠️ No model output data found. Please run the training pipeline first.")
    st.stop()

st.components.v1.html(build_html(), height=1450, scrolling=True)
