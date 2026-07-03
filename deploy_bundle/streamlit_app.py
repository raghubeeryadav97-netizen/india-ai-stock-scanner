"""Cloud deployment entry point for Streamlit Community Cloud / Render."""
from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).parent / "india_ai_stock_scanner_streamlit.py"),
    run_name="__main__",
)