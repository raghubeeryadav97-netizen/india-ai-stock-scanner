import streamlit as st
import pandas as pd
import json
import hashlib
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
# Portable path: saves next to this script in ./artifacts/ (works on Windows + Linux)
SAVED_DATA_FILE = Path(__file__).parent / "artifacts" / "saved_ai_stock_analysis.json"

def load_saved_data():
    if SAVED_DATA_FILE.exists():
        try:
            with open(SAVED_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_data_to_file(data_dict):
    try:
        SAVED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SAVED_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Could not save: {e}")
        return False

def delete_saved_data():
    if SAVED_DATA_FILE.exists():
        try:
            SAVED_DATA_FILE.unlink()
        except Exception:
            pass

# ==================== AUTO-LOAD ====================
if "ai_data" not in st.session_state:
    saved = load_saved_data()
    if saved:
        st.session_state["ai_data"] = saved
        st.session_state["_loaded_from_file"] = True
    else:
        st.session_state["_loaded_from_file"] = False

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
        "",
        height=200,
        placeholder='{"market": {...}, "stocks": [...]}\n\nPaste full JSON from AI here'
    )

    if st.button("🚀 Load Analysis", type="primary", use_container_width=True):
        if pasted_json.strip():
            try:
                data = json.loads(pasted_json)
                st.session_state["ai_data"] = data
                st.session_state["_loaded_from_file"] = False
                save_data_to_file(data)
                st.success("✅ Loaded & saved!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Invalid JSON: {str(e)}")
        else:
            st.warning("Please paste JSON first")

    st.markdown("---")

    # Live market snapshot
    if "ai_data" in st.session_state:
        m = st.session_state["ai_data"].get("market", {})
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
                    st.metric("Regime", m["regime"][:12])
            if m.get("fii_flow"):
                st.caption(f"**FII:** {m['fii_flow']}")
            if m.get("dii_flow"):
                st.caption(f"**DII:** {m['dii_flow']}")
            if m.get("market_breadth"):
                st.caption(f"**Breadth:** {m['market_breadth']}")
            sectors = m.get("top_bullish_sectors", [])
            if sectors:
                st.markdown("**Top Bullish Sectors:**")
                for s in sectors[:5]:
                    st.markdown(f"  ✅ {s}")
            st.markdown("---")

    if st.button("🗑️ Reset / Clear Data", use_container_width=True):
        for k in ["ai_data", "_loaded_from_file"]:
            st.session_state.pop(k, None)
        delete_saved_data()
        st.rerun()


# ==================== LOAD DATA ====================
if "ai_data" in st.session_state:
    data       = st.session_state["ai_data"]
    stocks     = data.get("stocks", [])
    market     = data.get("market", {})
    strategy   = data.get("strategy", {})
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

if st.session_state.get("_loaded_from_file") and stocks:
    st.info("💾 Auto-loaded from previously saved analysis. Click **Reset** to clear.")

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
st.markdown("### 📊 Full Scanner Table")

if not df.empty:
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        search = st.text_input("🔍 Search", placeholder="Symbol / Company...")
    with f2:
        secs = ["All"] + sorted(df['sector'].unique().tolist()) if 'sector' in df.columns else ["All"]
        sel_sec = st.selectbox("Sector", secs)
    with f3:
        min_conf = st.slider("Min AI Score", 60, 99, 75)
    with f4:
        verd_filter = st.multiselect("Verdict", ["STRONG BUY", "BUY", "HOLD"], default=["STRONG BUY", "BUY"])

    fdf = df.copy()
    if search and 'symbol' in fdf.columns:
        fdf = fdf[
            fdf['symbol'].str.contains(search, case=False, na=False) |
            fdf['full_name'].str.contains(search, case=False, na=False)
        ]
    if sel_sec != "All" and 'sector' in fdf.columns:
        fdf = fdf[fdf['sector'] == sel_sec]
    if 'ai_confidence' in fdf.columns:
        fdf = fdf[fdf['ai_confidence'] >= min_conf]
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
    if 'Price ₹' in [rename_map.get(c,c) for c in disp_cols]:
        col_cfg["Price ₹"] = st.column_config.NumberColumn(format="₹%.2f")
    if 'Chg %' in [rename_map.get(c,c) for c in disp_cols]:
        col_cfg["Chg %"] = st.column_config.NumberColumn(format="%.2f%%")
    if 'AI Score' in [rename_map.get(c,c) for c in disp_cols]:
        col_cfg["AI Score"] = st.column_config.ProgressColumn(min_value=60, max_value=100, format="%d%%")
    if 'RR' in [rename_map.get(c,c) for c in disp_cols]:
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
        mime="text/csv"
    )
    st.caption(f"Showing **{len(fdf)}** of **{len(df)}** stocks · Min AI Score ≥ {min_conf}%")

else:
    st.info("Load data from sidebar to see full scanner table.")

# ==================== DISCLAIMER ====================
st.markdown("---")
st.caption(
    "⚠️ **Disclaimer:** AI-assisted educational & research tool only. Not SEBI-registered investment advice. "
    "Always do your own research and consult a SEBI-registered advisor before investing. "
    "Prices are indicative and may not be real-time."
)
