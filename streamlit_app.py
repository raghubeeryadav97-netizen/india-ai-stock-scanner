"""Cloud deployment entry point for Streamlit Community Cloud."""
from pathlib import Path

_MAIN = Path(__file__).parent / "india_ai_stock_scanner_streamlit.py"
exec(compile(_MAIN.read_text(encoding="utf-8"), str(_MAIN), "exec"), {"__name__": "__main__", "__file__": str(_MAIN)})