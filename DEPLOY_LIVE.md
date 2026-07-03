# India AI Stock Scanner — Live Hosting Guide

## Option 1: Instant Live URL (PC ON = Site ON)

Double-click: **`START_LIVE.bat`**

- Local: http://127.0.0.1:8501
- Public URL saved in: `live_url.txt`
- Uses Cloudflare Quick Tunnel (free, temporary URL)

> Note: URL changes every restart. Keep PC + this window running.

---

## Option 2: Permanent FREE Cloud Host (Render.com)

1. Create account: https://render.com
2. New → **Web Service** → Connect GitHub OR upload repo
3. Settings:
   - **Build Command:** `pip install -r requirements-scanner.txt`
   - **Start Command:** `streamlit run india_ai_stock_scanner_streamlit.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - **Python Version:** 3.11
4. Deploy → you get permanent URL like `https://india-ai-stock-scanner.onrender.com`

`render.yaml` already included in project folder.

---

## Option 3: Streamlit Community Cloud (Recommended for Streamlit)

1. Install Git: https://git-scm.com/download/win
2. Create GitHub repo and push this folder
3. Go to: https://share.streamlit.io
4. New app → select repo → main file: `streamlit_app.py`
5. Requirements file: `requirements-scanner.txt`
6. Deploy → permanent URL like `https://yourapp.streamlit.app`

---

## Files Added for Hosting

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Cloud entry point |
| `requirements-scanner.txt` | Minimal deps for deploy |
| `.streamlit/config.toml` | Theme + server config |
| `render.yaml` | Render auto-deploy |
| `host_live.py` | Python live host script |
| `tunnel_only.py` | Public tunnel helper |
| `START_LIVE.bat` | One-click live start |
| `.gitignore` | Safe git deploy |

---

## Troubleshooting

- Port busy: `taskkill /F /IM python.exe` then restart `START_LIVE.bat`
- No public URL: check `tunnel_err.log`
- Streamlit not opening: run `pip install -r requirements-scanner.txt`