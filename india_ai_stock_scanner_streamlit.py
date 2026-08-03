import streamlit as st
import pandas as pd
import json
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path

PROMPT_ACCESS_HASH = hashlib.sha256("543251".encode()).hexdigest()

st.set_page_config(
    page_title="India AI Stock Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== PERSISTENT STORAGE ====================
# ONLY last USER "Load Analysis" data is kept — never old demo / git JSON.
# Layers: session → browser localStorage → memory store → disk (user-marked only)
import streamlit.components.v1 as components

_APP_DIR = Path(__file__).resolve().parent
_LS_COMPONENT_DIR = _APP_DIR / "ls_component"
_SAVE_CANDIDATES = [
    # Prefer temp/home first so git-bundled artifacts file never wins on Cloud reboot
    Path(os.environ.get("TMPDIR", os.environ.get("TMP", "/tmp"))) / "india_ai_stock_analysis_USER.json",
    Path.home() / ".india_ai_stock_scanner" / "saved_ai_stock_analysis_USER.json",
    _APP_DIR / "artifacts" / "saved_ai_stock_analysis_USER.json",
]
_BROWSER_KEY = "india_ai_scanner_user_last_v1"

try:
    _ls_component = components.declare_component("india_ai_ls", path=str(_LS_COMPONENT_DIR))
except Exception:
    _ls_component = None


@st.cache_resource
def _global_analysis_store():
    """Last USER load only. Survives browser reconnect while process is warm."""
    return {"data": None, "saved_at": None, "source": None}


def _is_valid_analysis(data):
    """Must have real stocks — empty placeholder / demo without stocks = invalid."""
    if not isinstance(data, dict):
        return False
    stocks = data.get("stocks")
    return isinstance(stocks, list) and len(stocks) > 0


def _is_user_loaded(data):
    """Only data the user explicitly loaded via Load Analysis button."""
    if not _is_valid_analysis(data):
        return False
    if data.get("_user_loaded") is True:
        return True
    # Memory store may hold user payload before marker re-check
    return False


def _strip_internal_keys(data):
    if not isinstance(data, dict):
        return data
    return {k: v for k, v in data.items() if not str(k).startswith("_")}


def _mark_user_payload(data_dict):
    payload = dict(data_dict)
    # Drop any stale internal flags from a previous paste
    for k in list(payload.keys()):
        if str(k).startswith("_"):
            payload.pop(k, None)
    payload["_user_loaded"] = True
    payload["_scanner_saved_at"] = datetime.now().isoformat(timespec="seconds")
    n = len(payload.get("stocks") or [])
    payload["_scanner_label"] = f"{n} stocks @ {payload['_scanner_saved_at']}"
    return payload


def _browser_ls(mode="get", value=None, key="ls_bridge"):
    """Read/write last user analysis in the browser (survives hard refresh)."""
    # Fire-and-forget HTML backup write (works even if declare_component is flaky)
    if mode == "set" and value:
        try:
            safe = json.dumps(value)
            components.html(
                f"""<script>
                try {{ localStorage.setItem({json.dumps(_BROWSER_KEY)}, {safe}); }} catch (e) {{}}
                </script>""",
                height=0,
                width=0,
            )
        except Exception:
            pass
    if mode == "clear":
        try:
            components.html(
                f"""<script>
                try {{ localStorage.removeItem({json.dumps(_BROWSER_KEY)}); }} catch (e) {{}}
                </script>""",
                height=0,
                width=0,
            )
        except Exception:
            pass

    if _ls_component is None:
        return {"ok": True, "mode": mode, "value": None} if mode == "get" else {"ok": True, "mode": mode}
    try:
        if mode == "set":
            return _ls_component(mode="set", value=value or "", key=key, default=None)
        if mode == "clear":
            return _ls_component(mode="clear", key=key, default=None)
        return _ls_component(mode="get", key=key, default=None)
    except Exception:
        return None


def _read_user_json_file(path: Path):
    try:
        if path.exists() and path.stat().st_size > 2:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if _is_user_loaded(data):
                return data, path.stat().st_mtime
    except Exception:
        pass
    return None, 0


def load_saved_user_data():
    """Only restore files written by Load Analysis (_user_loaded=true)."""
    best, best_mtime = None, 0
    for path in _SAVE_CANDIDATES:
        data, mtime = _read_user_json_file(path)
        if data is not None and mtime >= best_mtime:
            best, best_mtime = data, mtime
    return best


def save_user_data_to_disk(payload):
    ok = False
    last_err = None
    for path in _SAVE_CANDIDATES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            ok = True
        except Exception as e:
            last_err = e
    return ok, last_err


def delete_saved_data():
    store = _global_analysis_store()
    store["data"] = None
    store["saved_at"] = None
    store["source"] = None
    for path in _SAVE_CANDIDATES:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass
    # Clear browser copy on next run
    st.session_state["_ls_clear"] = True
    st.session_state.pop("_ls_got", None)
    st.session_state.pop("ai_data", None)


def persist_analysis(data_dict, source="user_load"):
    """Save ONLY explicit user Load Analysis — overwrites previous user load."""
    payload = _mark_user_payload(data_dict)
    st.session_state["ai_data"] = payload
    st.session_state["_loaded_from_file"] = False
    st.session_state["_data_source"] = "user_load"
    st.session_state["_data_loaded_at"] = datetime.now().strftime("%d %b %Y %I:%M %p")
    st.session_state["_ls_pending_write"] = json.dumps(payload, ensure_ascii=False)
    st.session_state.pop("_ls_clear", None)

    store = _global_analysis_store()
    store["data"] = payload
    store["saved_at"] = time.time()
    store["source"] = "user_load"

    ok, last_err = save_user_data_to_disk(payload)
    if not ok and last_err is not None:
        st.warning(f"Disk save partial fail (browser+memory still hold your load): {last_err}")
    return payload


def _apply_restored(data, source):
    st.session_state["ai_data"] = data
    st.session_state["_loaded_from_file"] = source != "user_load"
    st.session_state["_data_source"] = source
    label = data.get("_scanner_saved_at") or data.get("_scanner_label") or ""
    st.session_state["_data_loaded_at"] = label or datetime.now().strftime("%d %b %Y %I:%M %p")
    store = _global_analysis_store()
    store["data"] = data
    store["saved_at"] = store.get("saved_at") or time.time()
    store["source"] = source


def restore_analysis_into_session():
    """
    Restore LAST USER load only.
    Order: existing session (if user) → browser LS → memory → disk user file.
    Never loads old demo / git placeholder.
    """
    current = st.session_state.get("ai_data")
    if _is_user_loaded(current):
        store = _global_analysis_store()
        if store.get("data") is not current:
            store["data"] = current
            store["saved_at"] = store.get("saved_at") or time.time()
            store["source"] = "user_load"
        return

    # If session has non-user junk (old demo), drop it
    if current is not None:
        st.session_state.pop("ai_data", None)

    store = _global_analysis_store()
    if _is_user_loaded(store.get("data")):
        _apply_restored(store["data"], store.get("source") or "memory")
        return

    saved = load_saved_user_data()
    if _is_user_loaded(saved):
        _apply_restored(saved, "file")
        return

    st.session_state["_loaded_from_file"] = False


def _sync_browser_storage():
    """
    Hard-refresh safe via browser localStorage.
    Component returns None on first paint, then real value → Streamlit auto-reruns.
    """
    # Clear requested (Reset button)
    if st.session_state.get("_ls_clear"):
        result = _browser_ls(mode="clear", key="ls_clear")
        if result is not None:
            st.session_state.pop("_ls_clear", None)
        return

    # Pending write after Load Analysis — browser localStorage (hard-refresh survival)
    pending = st.session_state.get("_ls_pending_write")
    if pending:
        _browser_ls(mode="set", value=pending, key="ls_set")
        # HTML write is fire-and-forget; clear pending so we don't rewrite every run
        st.session_state.pop("_ls_pending_write", None)
        st.session_state["_ls_synced"] = True
        return

    # Already have THIS user's last load — nothing to restore
    if _is_user_loaded(st.session_state.get("ai_data")):
        return

    # Hard refresh / new session: pull last user load from THIS browser
    result = _browser_ls(mode="get", key="ls_get")
    if isinstance(result, dict) and result.get("ok") and result.get("value"):
        try:
            data = json.loads(result["value"])
            if _is_user_loaded(data):
                _apply_restored(data, "browser")
                store = _global_analysis_store()
                store["data"] = data
                store["saved_at"] = time.time()
                store["source"] = "browser"
                save_user_data_to_disk(data)
        except Exception:
            pass


# ==================== AUTO-LOAD (every rerun) ====================
restore_analysis_into_session()
_sync_browser_storage()

# ==================== MINIMAL CSS (only safe overrides) ====================
st.markdown("""
<style>
/* Progress bar for AI score */
.score-wrap { margin: 4px 0 8px 0; }
.score-bar-bg { background: #e2e8f0; border-radius: 4px; height: 6px; }
.score-bar-fill { height: 6px; border-radius: 4px; background: linear-gradient(90deg,#2563eb,#7c3aed); }

/* Verdict pill */
.pill { display:inline-block; padding:2px 10px; border-radius:9999px; font-weight:700; font-size:12px; }
.pill-sb  { background:#dcfce7; color:#14532d; }
.pill-buy { background:#dbeafe; color:#1e3a8a; }
.pill-hld { background:#fef9c3; color:#713f12; }
.pill-def { background:#f1f5f9; color:#475569; }

/* Target boxes */
.tbox-row { display:flex; gap:8px; margin:8px 0; }
.tbox { flex:1; border-radius:8px; padding:6px 10px; text-align:center; }
.tbox-entry { background:#eff6ff; border:1px solid #bfdbfe; }
.tbox-sl    { background:#fff1f2; border:1px solid #fecdd3; }
.tbox-t1    { background:#f0fdf4; border:1px solid #bbf7d0; }
.tbox-t2    { background:#faf5ff; border:1px solid #e9d5ff; }
.tbox-lbl { font-size:9px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.4px; }
.tbox-val { font-size:13px; font-weight:800; color:#0f2744; margin-top:1px; }

/* Hindi box */
.hindi-box { background:#fef3c7; border:1px solid #fde68a; border-radius:8px;
             padding:8px 12px; font-size:12px; color:#78350f; line-height:1.6; margin-top:6px; }

/* Inst view */
.inst-box { font-size:11px; color:#4338ca; margin-top:6px; line-height:1.5; }

/* Sector tag */
.sec-tag { display:inline-block; background:#eff6ff; color:#1d4ed8;
           padding:2px 8px; border-radius:5px; font-size:10px; font-weight:600; }

/* Divider line between cards */
.card-divider { border:none; border-top:1px solid #f1f5f9; margin:0; }

/* Metric cards */
.metric-box { background:white; border-radius:12px; padding:14px 18px;
              box-shadow:0 1px 6px rgba(0,0,0,0.07); text-align:center; }
.metric-box .val { font-size:28px; font-weight:800; color:#0f2744; }
.metric-box .lbl { font-size:11px; color:#94a3b8; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-top:2px; }
.metric-box .sub { font-size:10px; color:#cbd5e1; margin-top:2px; }

/* Prompt lock — discourage copy */
[data-testid="stSidebar"] .stCodeBlock pre {
  user-select: none;
  -webkit-user-select: none;
}

/* Regime banner */
.regime { background:linear-gradient(90deg,#052e16,#064e3b); border-radius:10px;
          padding:12px 20px; color:#6ee7b7; font-size:13px; margin-bottom:16px; }
.regime b { color:#d1fae5; }

/* Hero */
.hero { background:linear-gradient(135deg,#0f2744,#1a4a7a); border-radius:16px;
        padding:24px 28px; margin-bottom:20px; }
.hero h1 { color:white; font-size:28px; font-weight:800; margin:0 0 4px 0; }
.hero p  { color:#93c5fd; font-size:13px; margin:0; }
.hero-badges { margin-top:10px; }
.hbadge { display:inline-block; background:rgba(255,255,255,0.12); color:#bfdbfe;
          padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600;
          border:1px solid rgba(255,255,255,0.15); margin-right:6px; }
</style>
""", unsafe_allow_html=True)


# ==================== HELPERS ====================
def verdict_pill(v):
    v = str(v).strip().upper()
    if "STRONG" in v:
        return f'<span class="pill pill-sb">⭐ {v}</span>'
    elif v == "BUY":
        return f'<span class="pill pill-buy">✅ {v}</span>'
    elif v == "HOLD":
        return f'<span class="pill pill-hld">⏸ {v}</span>'
    else:
        return f'<span class="pill pill-def">{v}</span>'

def change_color(c):
    try:
        c = float(c)
        if c > 0:
            return f"🟢 +{c:.2f}%"
        elif c < 0:
            return f"🔴 {c:.2f}%"
        else:
            return f"⚪ {c:.2f}%"
    except:
        return ""

def ai_bar(score):
    pct = min(int(score), 100)
    return f"""<div class="score-wrap">
        <div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%"></div></div>
    </div>"""

def target_boxes(row):
    return f"""<div class="tbox-row">
      <div class="tbox tbox-entry">
        <div class="tbox-lbl">Buy Zone</div>
        <div class="tbox-val" style="font-size:11px">₹{row.get('buy_zone_low','-')}–{row.get('buy_zone_high','-')}</div>
      </div>
      <div class="tbox tbox-sl">
        <div class="tbox-lbl">Stop Loss</div>
        <div class="tbox-val">₹{row.get('stop_loss','-')}</div>
      </div>
      <div class="tbox tbox-t1">
        <div class="tbox-lbl">T1 (1M)</div>
        <div class="tbox-val">₹{row.get('target_1','-')}</div>
      </div>
      <div class="tbox tbox-t2">
        <div class="tbox-lbl">T2 (3-6M)</div>
        <div class="tbox-val">₹{row.get('target_2','-')}</div>
      </div>
    </div>"""


def get_ai_prompt_text():
    return """You are an elite Indian equity market strategist, institutional flow analyst, portfolio manager, and quantitative stock screener specializing in Indian equities.

MISSION
Analyze the CURRENT Indian stock market using the latest available verified data and identify ONLY the highest-probability bullish opportunities for swing trading and positional investing.

Your goal is to find stocks with the strongest combination of:
- Earnings Momentum
- Institutional Accumulation (especially DII)
- Relative Strength
- Sector Leadership
- Technical Trend Quality
- Growth Visibility
- Risk-Reward Potential

Use deep research before generating any output. Use available tools (web_search, browse_page) extensively to fetch latest data from NSE India, Moneycontrol, Trendlyne, and other reliable sources.

MANDATORY RESEARCH PHASE
Before selecting any stock, analyze:
Market Indices: NIFTY 50, BANK NIFTY, NIFTY FINANCIAL SERVICES, NIFTY PSU BANK, NIFTY CAPITAL GOODS, NIFTY INFRASTRUCTURE, NIFTY POWER, NIFTY PHARMA, NIFTY IT, NIFTY AUTO, NIFTY REALTY, NIFTY FMCG, NIFTY DEFENCE

Market Factors: FII Flows, DII Flows, India VIX, Market Breadth, Advance Decline Ratio, Sector Rotation, Earnings Trends, Institutional Ownership Trends

MARKET REGIME DETECTION
Determine current market regime: Bull Trend Continuation / Bullish Consolidation / Range Bound Consolidation / Mild Correction / Deep Correction
Assign confidence score (0-100).

SECTOR STRENGTH ANALYSIS
Rank all sectors based on: Relative Strength vs NIFTY, Earnings Growth, Revenue Growth, Margin Expansion, Institutional Buying, Breakout Structures, Volume Expansion, Momentum, Future Earnings Visibility

Identify TOP 5 BULLISH SECTORS. Only select stocks from these top 5 sectors.

STOCK UNIVERSE
Screen from: NIFTY 500, F&O Stocks, Large Caps, Mid Caps, High Liquidity Growth Stocks
Exclude: Illiquid stocks, Stocks below 200 DMA, Stocks with weak earnings, Stocks under institutional distribution

SCORING MODEL
Technical Score = 30% | Fundamental Score = 30% | Institutional Score = 20% | Sector Strength = 10% | Momentum = 10%

MINIMUM QUALIFICATION CRITERIA
- Revenue growth > 10%
- Positive profit growth
- Above 50 DMA and 200 DMA
- Strong relative strength
- Institutional accumulation visible
- AI Confidence >= 80
- Opportunity Score >= 80

RANKING RULES
Return: Minimum 10 stocks (Ideal: 12-20), Maximum 30 stocks
Sort by: AI Confidence → Opportunity Score → Probability of Success

TARGET GENERATION
For every stock: Current Price, Buy Zone Low/High, Stop Loss, Swing Target (1M), Positional Target (3-6M), Risk Reward Ratio
Targets based on: Support/Resistance, Trend Structure, Volatility, Historical Price Behaviour

DATA QUALITY RULES
- Use latest available verified market data only.
- DO NOT GUESS. DO NOT FABRICATE. DO NOT INVENT VALUES.
- If you cannot compile at least 10 high-quality stocks, return an error JSON.

OUTPUT FORMAT
Return ONLY valid JSON. No markdown. No explanation. No notes.

{
  "market": {
    "regime": "",
    "confidence": 0,
    "vix_level": "",
    "risk_environment": "",
    "nifty_trend": "",
    "nifty_level": 0,
    "fii_flow": "",
    "dii_flow": "",
    "market_breadth": "",
    "top_bullish_sectors": []
  },
  "strategy": {
    "name": "",
    "description": ""
  },
  "stocks": [
    {
      "rank": 1,
      "symbol": "",
      "full_name": "",
      "sector": "",
      "sector_strength": 0,
      "price": 0,
      "change_pct": 0,
      "market_cap_category": "Large Cap",
      "ai_confidence": 0,
      "opportunity_score": 0,
      "risk_reward": 0,
      "probability_success": 0,
      "verdict": "STRONG BUY",
      "buy_zone_low": 0,
      "buy_zone_high": 0,
      "stop_loss": 0,
      "target_1": 0,
      "target_2": 0,
      "strategy": "",
      "institutional_view": "",
      "reason": "",
      "hindi_reason": ""
    }
  ]
}"""


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 📈 India AI Scanner")
    st.markdown("---")
    st.markdown("### 🤖 Step 1 — Get AI Prompt")

    if not st.session_state.get("prompt_unlocked"):
        st.markdown("🔒 **Prompt locked**")
        st.caption("Sirf authorized users prompt dekh/copy kar sakte hain.")
        prompt_pwd = st.text_input("Password", type="password", key="prompt_password", placeholder="Enter password")
        if st.button("🔓 Unlock Prompt", use_container_width=True):
            entered_hash = hashlib.sha256(prompt_pwd.encode()).hexdigest()
            if entered_hash == PROMPT_ACCESS_HASH:
                st.session_state["prompt_unlocked"] = True
                st.success("✅ Unlocked!")
                st.rerun()
            else:
                st.error("❌ Galat password")
    else:
        if st.button("📋 Show AI Prompt", use_container_width=True):
            st.session_state["show_prompt"] = True
        if st.session_state.get("show_prompt"):
            st.code(get_ai_prompt_text(), language="text")
            st.info("⬆️ Copy → Paste in Claude/Grok → Get JSON → Come back here")
        if st.button("🔒 Lock Prompt", use_container_width=True):
            st.session_state["prompt_unlocked"] = False
            st.session_state.pop("show_prompt", None)
            st.rerun()

    st.markdown("---")
    st.markdown("### 📥 Step 2 — Paste JSON")
    pasted_json = st.text_area(
        "JSON payload",
        height=200,
        placeholder='{"market": {...}, "stocks": [...]}\n\nPaste full JSON from AI here',
        key="pasted_json_input",
        label_visibility="collapsed",
    )

    smart_api = st.text_input(
        "Smart Market API (trade feed)",
        value=os.environ.get("SMART_MARKET_API", "http://localhost:5001"),
        help="Load Analysis pe picks yahan push honge → Trade Desk confirm trade",
        key="smart_market_api",
    )

    if st.button("🚀 Load Analysis", type="primary", use_container_width=True, key="btn_load_analysis"):
        if pasted_json.strip():
            try:
                raw = pasted_json.strip()
                # Strip accidental markdown fences from AI output
                if raw.startswith("```"):
                    raw = raw.strip("`")
                    if raw.lower().startswith("json"):
                        raw = raw[4:].lstrip()
                data = json.loads(raw)
                if not _is_valid_analysis(data):
                    st.error("❌ JSON parsed, lekin stocks/market data nahi mila. Full AI JSON paste karo.")
                else:
                    persist_analysis(data, source="user_load")
                    # Optional Trade Desk push (local only; cloud → localhost fail OK)
                    try:
                        import urllib.request
                        url = f"{smart_api.rstrip('/')}/api/picks/import"
                        body = json.dumps({**data, "source": "streamlit_india_ai_scanner"}).encode("utf-8")
                        req = urllib.request.Request(
                            url,
                            data=body,
                            headers={"Content-Type": "application/json", "X-Picks-Source": "streamlit"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            push = json.loads(resp.read().decode("utf-8"))
                        st.success(
                            f"✅ Loaded & saved ({len(data.get('stocks', []))} stocks). "
                            f"Trade Desk: {push.get('imported')} imported."
                        )
                    except Exception:
                        st.success(
                            f"✅ Loaded & saved ({len(data.get('stocks', []))} stocks). "
                            "Yahi data hard refresh tak rahega — purana demo nahi aayega."
                        )
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Invalid JSON: {str(e)}")
        else:
            st.warning("Please paste JSON first")

    st.markdown("---")

    # Live market snapshot — only YOUR last Load Analysis
    if _is_user_loaded(st.session_state.get("ai_data")):
        m = st.session_state["ai_data"].get("market", {}) or {}
        n_stocks = len(st.session_state["ai_data"].get("stocks") or [])
        saved_at = st.session_state["ai_data"].get("_scanner_saved_at", "")
        st.success(f"💾 **Aapka last load:** {n_stocks} stocks" + (f" · {saved_at}" if saved_at else ""))
        st.caption("Hard refresh pe bhi yahi rahega. Naya JSON load karoge tab overwrite hoga.")
        if m:
            st.markdown("### 🌐 Market Snapshot")
            if m.get("nifty_level"):
                st.metric("NIFTY", f"{m['nifty_level']}")
            cols = st.columns(2)
            with cols[0]:
                if m.get("vix_level"):
                    st.metric("VIX", m["vix_level"])
            with cols[1]:
                if m.get("regime"):
                    st.metric("Regime", str(m["regime"])[:12])
            if m.get("fii_flow"):
                st.caption(f"**FII:** {m['fii_flow']}")
            if m.get("dii_flow"):
                st.caption(f"**DII:** {m['dii_flow']}")
            if m.get("market_breadth"):
                st.caption(f"**Breadth:** {m['market_breadth']}")
            sectors = m.get("top_bullish_sectors", []) or []
            if sectors:
                st.markdown("**Top Bullish Sectors:**")
                for s in sectors[:5]:
                    if isinstance(s, dict):
                        st.markdown(f"  ✅ {s.get('sector', s)}")
                    else:
                        st.markdown(f"  ✅ {s}")
            st.markdown("---")

    if st.button("🗑️ Reset / Clear Data", use_container_width=True, key="btn_reset_data"):
        for k in [
            "ai_data", "_loaded_from_file", "_data_source", "_data_loaded_at",
            "_ls_pending_write", "_ls_synced", "_ls_got",
        ]:
            st.session_state.pop(k, None)
        delete_saved_data()
        st.rerun()


# ==================== LOAD DATA ====================
# Only YOUR last Load Analysis (never old demo JSON)
if _is_user_loaded(st.session_state.get("ai_data")):
    data       = st.session_state["ai_data"]
    stocks     = data.get("stocks", []) or []
    market     = data.get("market", {}) or {}
    strategy   = data.get("strategy", {}) or {}
else:
    data, stocks, market, strategy = {}, [], {}, {}

df = pd.DataFrame(stocks) if stocks else pd.DataFrame()


# ==================== HERO ====================
ts = datetime.now().strftime("%d %b %Y  %I:%M %p")
st.markdown(f"""
<div class="hero">
  <h1>📈 India AI Stock Scanner</h1>
  <p>Institutional Intelligence • NSE / BSE • Nifty 500 Universe</p>
  <div class="hero-badges">
    <span class="hbadge">🤖 AI-Powered</span>
    <span class="hbadge">📊 Swing + Positional</span>
    <span class="hbadge">🕐 {ts}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if stocks:
    src = st.session_state.get("_data_source", "user_load")
    saved_at = data.get("_scanner_saved_at") or st.session_state.get("_data_loaded_at", "")
    st.success(
        f"✅ **Aapka last Load Analysis** — **{len(stocks)} stocks**"
        + (f" · saved `{saved_at}`" if saved_at else "")
        + f" · restore via **{src}**. "
        "Hard refresh pe bhi yahi rahega jab tak naya JSON load / Reset na karo."
    )
else:
    st.warning(
        "📭 Koi **user-loaded** analysis nahi hai. Purana demo data band hai. "
        "Sidebar se aaj ka JSON paste karke **Load Analysis** dabao."
    )

# ==================== REGIME BANNER ====================
if market:
    reg  = market.get("regime", "")
    conf = market.get("confidence", "")
    vix  = market.get("vix_level", "")
    risk = market.get("risk_environment", "")
    nt   = market.get("nifty_trend", "")
    parts = []
    if reg:  parts.append(f"🏛 Regime: <b>{reg}</b>")
    if conf: parts.append(f"🎯 Confidence: <b>{conf}%</b>")
    if vix:  parts.append(f"⚡ VIX: <b>{vix}</b>")
    if risk: parts.append(f"🛡 Risk: <b>{risk}</b>")
    if nt:   parts.append(f"📊 Nifty: <b>{nt}</b>")
    if parts:
        st.markdown(
            f'<div class="regime">&nbsp;&nbsp;{"&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)}</div>',
            unsafe_allow_html=True
        )
    if strategy.get("name"):
        st.success(f"🎯 **Strategy:** {strategy['name']} — {strategy.get('description','')}")


# ==================== METRICS ====================
if not df.empty:
    total     = len(df)
    sb        = len(df[df.get('verdict', pd.Series(dtype=str)).eq('STRONG BUY')]) if 'verdict' in df.columns else 0
    avg_conf  = round(df['ai_confidence'].mean(), 1) if 'ai_confidence' in df.columns else 0
    high_rr   = len(df[df['risk_reward'] >= 2.5]) if 'risk_reward' in df.columns else 0
    avg_rr    = round(df['risk_reward'].mean(), 1) if 'risk_reward' in df.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-box"><div class="val">{total}</div><div class="lbl">Total Picks</div><div class="sub">Nifty 500</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-box"><div class="val" style="color:#16a34a">{sb}</div><div class="lbl">Strong Buy</div><div class="sub">Highest conviction</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-box"><div class="val" style="color:#7c3aed">{avg_conf}%</div><div class="lbl">Avg AI Score</div><div class="sub">Confidence</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-box"><div class="val" style="color:#d97706">{high_rr}</div><div class="lbl">RR ≥ 2.5x</div><div class="sub">Best risk-reward</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-box"><div class="val" style="color:#0f2744">{avg_rr}x</div><div class="lbl">Avg RR</div><div class="sub">Portfolio avg</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ==================== SECTOR CHART ====================
if not df.empty and 'sector' in df.columns:
    st.markdown("### 🏭 Sector Distribution")
    scol1, scol2 = st.columns([3, 1])
    sector_counts = df['sector'].value_counts()
    with scol1:
        st.bar_chart(sector_counts, height=200)
    with scol2:
        st.markdown("**Breakdown**")
        for sec, cnt in sector_counts.items():
            pct = round(cnt / len(df) * 100)
            st.caption(f"**{sec}** — {cnt} ({pct}%)")

st.markdown("---")

# ==================== TOP PICKS CARDS ====================
st.markdown("### 🏆 Top Institutional Picks")

if not df.empty:
    top = df.head(15)
    cols = st.columns(3)

    for i, (_, row) in enumerate(top.iterrows()):
        col = cols[i % 3]
        with col:
            with st.container(border=True):
                # Row 1: Symbol + Verdict + Price
                r1a, r1b = st.columns([3, 2])
                with r1a:
                    st.markdown(f"**#{int(row.get('rank', i+1))} &nbsp; {row.get('symbol','')}**")
                    st.caption(row.get('full_name', ''))
                with r1b:
                    st.markdown(
                        verdict_pill(row.get('verdict', '')),
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**₹{row.get('price', 0)}** &nbsp; {change_color(row.get('change_pct', 0))}")

                # Sector tag
                st.markdown(
                    f'<span class="sec-tag">{row.get("sector","")}</span>'
                    f'<span style="font-size:10px;color:#94a3b8;margin-left:6px">{row.get("market_cap_category","")}</span>',
                    unsafe_allow_html=True
                )

                # AI score bar
                score = int(row.get('ai_confidence', 0))
                st.markdown(
                    f'{ai_bar(score)}',
                    unsafe_allow_html=True
                )

                # Mini stats
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("AI", f"{score}%", label_visibility="collapsed")
                mc2.metric("RR", f"{row.get('risk_reward',0)}x", label_visibility="collapsed")
                mc3.metric("Win%", f"{row.get('probability_success',0)}%", label_visibility="collapsed")
                mc4.metric("Opp", f"{row.get('opportunity_score',0)}", label_visibility="collapsed")

                st.caption(f"🤖 AI Score &nbsp;&nbsp; ⚡ Risk-Reward &nbsp;&nbsp; ✅ Win Prob &nbsp;&nbsp; 📊 Opportunity")

                # Target boxes
                st.markdown(target_boxes(row), unsafe_allow_html=True)

                # Why / Reason
                reason = str(row.get('reason', ''))
                if reason and reason != 'nan':
                    with st.expander("📝 Analysis", expanded=False):
                        st.write(reason)
                        inst = str(row.get('institutional_view', ''))
                        if inst and inst != 'nan':
                            st.markdown(f'<div class="inst-box">🏦 <b>Institutional:</b> {inst}</div>', unsafe_allow_html=True)
                        strat = str(row.get('strategy', ''))
                        if strat and strat != 'nan':
                            st.caption(f"📌 Strategy: {strat}")

                # Hindi reason
                hindi = str(row.get('hindi_reason', ''))
                if hindi and hindi != 'nan':
                    st.markdown(f'<div class="hindi-box">🇮🇳 {hindi}</div>', unsafe_allow_html=True)

else:
    st.info(
        "📭 **Koi data nahi hai abhi.**\n\n"
        "1. Sidebar mein **Copy Fresh AI Prompt** click karo\n"
        "2. Claude / Grok / ChatGPT mein paste karo\n"
        "3. JSON output copy karke **Paste JSON** box mein daalo\n"
        "4. **Load Analysis** click karo ✅"
    )

st.markdown("---")

# ==================== FULL SCANNER TABLE ====================
# Fragment: filter/slider changes only re-run this block (no full-page jump / "data gayab" feel)
@st.fragment
def render_scanner_table(source_df: pd.DataFrame):
    st.markdown("### 📊 Full Scanner Table")
    if source_df.empty:
        st.info("Load data from sidebar to see full scanner table.")
        return

    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        search = st.text_input("🔍 Search", placeholder="Symbol / Company...", key="tbl_search")
    with f2:
        secs = ["All"] + sorted(source_df['sector'].dropna().unique().tolist()) if 'sector' in source_df.columns else ["All"]
        sel_sec = st.selectbox("Sector", secs, key="tbl_sector")
    with f3:
        min_conf = st.slider("Min AI Score", 60, 99, 75, key="tbl_min_conf")
    with f4:
        verd_filter = st.multiselect(
            "Verdict",
            ["STRONG BUY", "BUY", "HOLD"],
            default=["STRONG BUY", "BUY"],
            key="tbl_verdict",
        )

    fdf = source_df.copy()
    if search and 'symbol' in fdf.columns:
        name_col = fdf['full_name'] if 'full_name' in fdf.columns else pd.Series([""] * len(fdf))
        fdf = fdf[
            fdf['symbol'].astype(str).str.contains(search, case=False, na=False) |
            name_col.astype(str).str.contains(search, case=False, na=False)
        ]
    if sel_sec != "All" and 'sector' in fdf.columns:
        fdf = fdf[fdf['sector'] == sel_sec]
    if 'ai_confidence' in fdf.columns:
        fdf = fdf[pd.to_numeric(fdf['ai_confidence'], errors='coerce').fillna(0) >= min_conf]
    if verd_filter and 'verdict' in fdf.columns:
        fdf = fdf[fdf['verdict'].isin(verd_filter)]

    disp_cols = [c for c in [
        'rank','symbol','full_name','sector','market_cap_category',
        'price','change_pct','ai_confidence','opportunity_score',
        'risk_reward','probability_success','verdict',
        'buy_zone_low','buy_zone_high','stop_loss','target_1','target_2'
    ] if c in fdf.columns]

    rename_map = {
        'rank':'#','symbol':'Symbol','full_name':'Company',
        'sector':'Sector','market_cap_category':'Cap',
        'price':'Price ₹','change_pct':'Chg %',
        'ai_confidence':'AI Score','opportunity_score':'Opp',
        'risk_reward':'RR','probability_success':'P(Win)%',
        'verdict':'Verdict',
        'buy_zone_low':'Buy↓','buy_zone_high':'Buy↑',
        'stop_loss':'SL','target_1':'T1','target_2':'T2'
    }

    col_cfg = {}
    renamed_preview = [rename_map.get(c, c) for c in disp_cols]
    if 'Price ₹' in renamed_preview:
        col_cfg["Price ₹"] = st.column_config.NumberColumn(format="₹%.2f")
    if 'Chg %' in renamed_preview:
        col_cfg["Chg %"] = st.column_config.NumberColumn(format="%.2f%%")
    if 'AI Score' in renamed_preview:
        col_cfg["AI Score"] = st.column_config.ProgressColumn(min_value=60, max_value=100, format="%d%%")
    if 'RR' in renamed_preview:
        col_cfg["RR"] = st.column_config.NumberColumn(format="%.1fx")

    st.dataframe(
        fdf[disp_cols].rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg,
        height=420
    )

    csv = fdf.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Export CSV",
        data=csv,
        file_name=f"india_ai_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="btn_export_csv",
    )
    st.caption(f"Showing **{len(fdf)}** of **{len(source_df)}** stocks · Min AI Score ≥ {min_conf}%")


render_scanner_table(df)

# ==================== DISCLAIMER ====================
st.markdown("---")
st.caption(
    "⚠️ **Disclaimer:** AI-assisted educational & research tool only. Not SEBI-registered investment advice. "
    "Always do your own research and consult a SEBI-registered advisor before investing. "
    "Prices are indicative and may not be real-time."
)
