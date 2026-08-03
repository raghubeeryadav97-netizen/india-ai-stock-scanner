"""Cloud deployment entry point for Streamlit Community Cloud."""
import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).parent / "india_ai_stock_scanner_streamlit.py"),
    run_name="__main__",
)