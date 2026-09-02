import ssl, os, time, random, json, socket, urllib3, feedparser, sqlite3
import requests
import pandas as pd
import streamlit as st
import pytz
from datetime import datetime, timedelta
from pathlib import Path

_TZ_UTC     = pytz.utc
_TZ_EASTERN = pytz.timezone("US/Eastern")

# ── SSL / proxy bypasses ─────────────────────────────────────────────────────
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["CURL_CA_BUNDLE"]     = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET] or res
socket.getaddrinfo = _ipv4_only

# =============================================================================
# API KEYS
# =============================================================================
ODDS_API_KEY  = "toa_live_qz8p0rcs"
ODDS_API_BASE = "https://api.theoddsapi.com"
# =============================================================================

st.set_page_config(
    page_title="Sports EV+ Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.stApp { background-color: #0e1117 !important; }
.main .block-container { background-color: #0e1117 !important; padding-top: 1rem !important; }
[data-testid="stSidebar"] { background-color: #0a0e27 !important; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: #e2e8f0 !important; }
.stMarkdown p  { color: #e2e8f0 !important; }
.stMarkdown h1 { color: #f1f5f9 !important; font-weight: 700 !important; }
.stMarkdown h2 { color: #f1f5f9 !important; font-weight: 700 !important; }
.stMarkdown h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
.stMarkdown li { color: #e2e8f0 !important; }
.stTextInput  > label { color: #94a3b8 !important; }
.stSelectbox  > label { color: #94a3b8 !important; }
.stSlider     > label { color: #94a3b8 !important; }
.stNumberInput> label { color: #94a3b8 !important; }
.stRadio      > label { color: #94a3b8 !important; }
.stCheckbox   > label { color: #94a3b8 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #e2e8f0 !important; }
h1, h2, h3 { color: #f1f5f9 !important; }
.stCaption p  { color: #64748b !important; font-size: 12px !important; }
.stButton > button {
    color: #f1f5f9 !important; background: #1e293b !important;
    border: 1px solid #334155 !important; border-radius: 6px !important; font-weight: 600 !important;
}
.stButton > button:hover { background: #334155 !important; border-color: #00D9FF !important; color: #00D9FF !important; }
[data-testid="stMetricLabel"]  { color: #94a3b8 !important; font-size: 12px !important; }
[data-testid="stMetricValue"]  { color: #00D9FF !important; font-size: 28px !important; }
[data-testid="stMetricDelta"]  { color: #22c55e !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px; }
.stTabs [role="tab"] {
    color: #64748b !important; font-weight: 600 !important; font-size: 13px !important;
    background: transparent !important; border-radius: 6px 6px 0 0 !important; padding: 8px 16px !important;
}
.stTabs [role="tab"]:hover { color: #e2e8f0 !important; background: #1e293b !important; }
.stTabs [role="tab"][aria-selected="true"] {
    color: #00D9FF !important; background: #0f172a !important; border-bottom: 3px solid #00D9FF !important;
}
[data-testid="stDataFrame"] > div { background: #1e293b !important; border-radius: 8px !important; border: 1px solid #334155 !important; }
.dvn-scroller { background: #1e293b !important; }
[data-testid="stAlert"] { border-radius: 8px !important; }
[data-testid="stProgressBar"] > div > div { background-color: #00D9FF !important; }
[data-testid="stProgressBar"] { background: #1e293b !important; }
.stSelectbox [data-baseweb="select"] > div { background-color: #1e293b !important; border-color: #334155 !important; color: #e2e8f0 !important; }
.stNumberInput input, .stTextInput input { background-color: #1e293b !important; color: #e2e8f0 !important; border-color: #334155 !important; }
hr { border-color: #1e293b !important; }
.metric-box {
    background: linear-gradient(135deg, #1a1f3a 0%, #0f172a 100%);
    border: 2px solid #00D9FF; border-radius: 10px; padding: 20px; margin: 10px 0;
}
.metric-title { font-size: 11px; color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-size: 26px; color: #00D9FF !important; font-weight: bold; margin-top: 6px; }
.pred-card   { background:#111827; border:1px solid #1e3a5f; border-radius:10px; padding:14px 18px; margin-bottom:10px; }
.pred-match  { font-size:14px; font-weight:700; color:#f1f5f9 !important; margin-bottom:6px; }
.event-card  { background:#111827; border:1px solid #1e293b; border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.event-date  { font-size:11px; color:#00D9FF !important; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
.event-match { font-size:15px; font-weight:700; color:#f1f5f9 !important; }
.key-warning { background:#2d1a0a; border:1px solid #f59e0b; border-radius:8px; padding:14px 18px; margin-bottom:16px; }
.key-warning * { color: #fbbf24 !important; }
.ev-green  { color:#22c55e !important; font-weight:700; }
.ev-red    { color:#ef4444 !important; font-weight:700; }
.ev-yellow { color:#f59e0b !important; font-weight:700; }
.badge-live { background:#0e2a1a; border:1px solid #22c55e; color:#22c55e !important; font-size:11px; font-weight:700; padding:2px 10px; border-radius:20px; }
.badge-warn { background:#1a1a0a; border:1px solid #f59e0b; color:#f59e0b !important; font-size:11px; font-weight:700; padding:2px 10px; border-radius:20px; }
body { overscroll-behavior-y: none !important; overflow-x: hidden !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; } header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTS
# =============================================================================
PAPER_TRADE_INTERVAL = 1200
MIN_EV_THRESHOLD     = 0.01
MIN_EDGE_THRESHOLD   = 1.5         # Eased from 2.0 after a real MLB game (Cubs/Reds) showed genuine
                                    # +3.9% EV underdog edge getting rejected at 2.0% — see chat history.
MLB_MAX_ODDS         = 2.75        # Raised to match the new underdog ceiling below, so MLB isn't
                                    # capped tighter than other sports for no reason.
KELLY_FRACTIONS      = {"Safe": 0.25, "Moderate": 0.50, "Aggressive": 0.75}
MAX_KELLY_PCT        = 0.20
CB_STAKE_MULTIPLIER  = 0.50

ALLOWED_BASKETBALL_MARKETS = {"h2h", "moneyline"}
BLOCKED_BASKETBALL_MARKETS = {"1x2", "3way", "three_way", "regulation_time"}

HEAVY_FAVORITE_FLOOR = 1.30        # Loosened from 1.50 to let more (heavier) favorites qualify.

LINE_DRIFT_BUFFER = 0.10           # Shrunk from 0.15 alongside the floor loosening above.
EFFECTIVE_FAVORITE_FLOOR = HEAVY_FAVORITE_FLOOR + LINE_DRIFT_BUFFER   # 1.40

MAX_UNDERDOG_ODDS = 2.75           # Raised from 1.85 — that ceiling was rejecting moderate
                                    # underdogs with genuine positive EV (e.g. a 2.51x underdog
                                    # with +3.9% EV that the favorite side didn't have). Stays well
                                    # below the old 3.00x zone that had a documented 14.3% win rate
                                    # in historical grading, so the real long-shot risk is still capped.

HEAVY_FAVORITE_EV_EXCEPTION_THRESHOLD = 0.05   # EV+ must exceed this to bypass floor

EXCEPTION_MIN_ODDS = 1.35
HEAVY_FAVORITE_EV_EXCEPTION_MAX_PER_DAY = 1

MIN_COMPLETE_SETS_TENNIS = 2   # below this, treat result as retirement/walkover, not a "real" outcome


_DZ_LO       = 0.65
_DZ_HI       = 0.70
_DZ_DISCOUNT = 0.88   # shrinks 0.68 → 0.599 effective probability

RISK_KEYWORDS = {
    "injury","injured","out","rest","resting","doubtful","questionable",
    "ruled out","sidelined","withdraw","withdrawn","illness","pain",
    "knee","ankle","hamstring","wrist","shoulder","back","gtd",
    "game time decision","day-to-day","scratch",
}

PAPER_TRADES_CSV = Path("paper_trades.csv")
BANKROLL_CONFIG  = Path("bankroll_settings.json")
MODEL_CONFIG     = Path("model_settings.json")
BET_LEDGER_PATH  = Path("qualified_bets_ledger.json")
FLOOR_EXCEPTION_LOG_PATH = Path("floor_exception_log.json")

AUTO_REFRESH_INTERVAL_SEC = 900

# Simple 4-digit PIN gate for the Settings panel only — not real security
# (it's a plain string check, visible to anyone reading this file), just a
# casual barrier so Settings isn't editable by anyone who opens the app.
SETTINGS_PIN = "3578"   # change this to whatever 4-digit code you want

_AS_NBA    = "https://v1.basketball.api-sports.io"
_AS_TENNIS = "https://v1.tennis.api-sports.io"
_AS_MLB    = "https://v1.baseball.api-sports.io"

# =============================================================================
# SQLITE — Line Movement Velocity
# =============================================================================
def init_market_db():
    conn = sqlite3.connect("market_history.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS odds_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, match_key TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, home_odds REAL, away_odds REAL)''')
    conn.commit(); conn.close()

def log_and_get_velocity(match_name: str, home_odds: float, away_odds: float) -> str:
    try:
        init_market_db()
        conn = sqlite3.connect("market_history.db")
        cur  = conn.cursor()
        cur.execute("INSERT INTO odds_history (match_key, home_odds, away_odds) VALUES (?,?,?)",
                    (match_name, home_odds, away_odds))
        conn.commit()
        cur.execute("SELECT home_odds FROM odds_history WHERE match_key=? AND timestamp>=datetime('now','-2 hours') ORDER BY timestamp ASC LIMIT 1",
                    (match_name,))
        row = cur.fetchone(); conn.close()
        if row and row[0]:
            shift = row[0] - home_odds
            if shift > 0.05:  return "🔥 Steaming"
            if shift < -0.05: return "❄️ Fading"
        return "平 Stable"
    except Exception:
        return "平 Stable"

# =============================================================================
# DATA HYGIENE — RAW LOG PARSING, DEDUPLICATION, SPORTSBOOK GRADING RULES
# =============================================================================
import re as _re

_RAW_LOG_RE = _re.compile(
    r"""^(?P<entity>.+?)\s*·\s*(?P<match>.+?)\s+
        (?P<date>\d{4}-\d{2}-\d{2})\s+
        (?P<time>\d{1,2}:\d{2}\s*[AP]M)\s*
        (?P<tz>[A-Z]{2,4})
        (?P<odds>\d+\.\d{2})
        (?P<stake>\d+?)
        (?:(?P<special>FORFEIT|RETIRED|WALKOVER|VOID|CASHOUT)
           |(?P<outcome>[WL])(?P<score>[\d/:\s]+))
        \s*$""",
    _re.VERBOSE,
)

def parse_raw_log_line(line: str, known_stake: float | None = None) -> dict | None:
    if not line or not line.strip():
        return None
    m = _RAW_LOG_RE.match(line.strip())
    if not m:
        return None
    g = m.groupdict()

    if g["special"]:
        outcome = g["special"]
        score   = None
    else:
        outcome = g["outcome"]
        score   = g["score"].strip() if g["score"] else None

    try:
        odds = float(g["odds"])
    except (TypeError, ValueError):
        odds = None
    try:
        stake = float(g["stake"])
    except (TypeError, ValueError):
        stake = None

    low_confidence = False
    if known_stake is not None and stake is not None and stake != known_stake:
        combo = f"{g['odds']}{g['stake']}"
        digits_before_dot, digits_after_dot = combo.split(".")
        found = False
        for cut in range(1, len(digits_after_dot)):
            cand_odds_str  = f"{digits_before_dot}.{digits_after_dot[:cut]}"
            cand_stake_str = digits_after_dot[cut:]
            if cand_stake_str and float(cand_stake_str) == known_stake:
                odds, stake = float(cand_odds_str), float(cand_stake_str)
                found = True
                break
        if not found:
            low_confidence = True

    return {
        "entity":    g["entity"].strip(),
        "match":     g["match"].strip(),
        "date":      g["date"],
        "time":      g["time"].replace(" ", "") ,
        "tz":        g["tz"],
        "odds":      odds,
        "stake":     stake,
        "outcome":   outcome,
        "score":     score,
        "low_confidence_split": low_confidence,
        "raw_line":  line.strip(),
    }


def parse_raw_log_batch(lines: list[str], known_stake: float | None = None) -> pd.DataFrame:
    records = []
    for ln in lines:
        rec = parse_raw_log_line(ln, known_stake=known_stake)
        if rec is None:
            records.append({"raw_line": ln, "_parse_failed": True})
        else:
            rec["_parse_failed"] = False
            records.append(rec)
    return pd.DataFrame(records)


_TENNIS_LAST_FIRST_RE = _re.compile(r"^\s*(?P<last>[^,]+?)\s*,\s*(?P<first>[^,]+?)\s*$")

def normalize_tennis_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return name
    s = name.strip()
    if "," not in s:
        return s
    if s.count(",") != 1:
        return s
    m = _TENNIS_LAST_FIRST_RE.match(s)
    if not m:
        return s
    last, first = m.group("last").strip(), m.group("first").strip()
    if not last or not first:
        return s
    return f"{first} {last}"


def normalize_tennis_names_in_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    if " vs " in text:
        parts = text.split(" vs ")
        return " vs ".join(normalize_tennis_name(p) for p in parts)
    return normalize_tennis_name(text)


def _normalize_player_key(match_str: str) -> str:
    parts = [p.strip().lower() for p in _re.split(r"\s+vs\s+", str(match_str))]
    return "|".join(sorted(parts))


def dedupe_match_logs(df: pd.DataFrame, date_col: str = "date",
                       match_col: str = "match") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    work = df.copy()
    work["_pkey"] = work[match_col].apply(_normalize_player_key)

    def _is_final(row) -> bool:
        outcome = str(row.get("outcome", "")).upper()
        return outcome in ("W", "L")

    work["_is_final"] = work.apply(_is_final, axis=1)
    work["_sort_dt"]  = pd.to_datetime(work.get(date_col), errors="coerce")

    work = work.sort_values(["_pkey", "_is_final", "_sort_dt"],
                             ascending=[True, False, False])
    deduped = work.drop_duplicates(subset="_pkey", keep="first")
    return deduped.drop(columns=["_pkey", "_is_final", "_sort_dt"]).reset_index(drop=True)


def _count_completed_sets(score: str | None) -> int:
    if not score:
        return 0
    sets = [s for s in str(score).split() if "/" in s]
    return len(sets)


def grade_with_sportsbook_rules(outcome: str, score: str | None,
                                 sport: str = "Tennis",
                                 grading_rule: str = "1st_set") -> dict:
    outcome_u = (outcome or "").upper()
    sets_done = _count_completed_sets(score)

    if outcome_u in ("W", "L"):
        return {"graded_outcome": outcome_u, "is_void": False, "note": "Standard completed result."}

    if outcome_u in ("FORFEIT", "RETIRED", "WALKOVER"):
        if sport != "Tennis":
            return {"graded_outcome": "VOID", "is_void": True, "note": "Non-tennis retirement — treat as void by default."}

        if grading_rule == "1st_ball":
            return {"graded_outcome": "W", "is_void": False,
                    "note": "1st-ball rule: book graded this as a live result despite early retirement; "
                            "do not void in backtest — it cost/won real money."}

        if sets_done >= 1:
            return {"graded_outcome": "W", "is_void": False,
                    "note": f"{sets_done} set(s) completed before retirement — books grade this live, not void."}
        return {"graded_outcome": "VOID", "is_void": True,
                "note": "No completed set before retirement — true void under 1st-set rule."}

    return {"graded_outcome": "VOID", "is_void": True, "note": f"Unrecognized outcome token: {outcome!r}"}


def apply_sportsbook_grading(df: pd.DataFrame, outcome_col: str = "outcome",
                              score_col: str = "score", sport_col: str = "sport",
                              grading_rule: str = "1st_set") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    graded, voided, notes = [], [], []
    for _, row in out.iterrows():
        sport = row.get(sport_col, "Tennis") if sport_col in out.columns else "Tennis"
        g = grade_with_sportsbook_rules(row.get(outcome_col), row.get(score_col), sport, grading_rule)
        graded.append(g["graded_outcome"]); voided.append(g["is_void"]); notes.append(g["note"])
    out["graded_outcome"] = graded
    out["is_void"]        = voided
    out["grading_note"]   = notes
    return out



# =============================================================================
# NETWORK
# =============================================================================
def _session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.verify    = False
    return s

def american_to_decimal(american: float) -> float:
    if american > 0: return american / 100 + 1
    return 100 / abs(american) + 1

RAINBET_PRICING_HAIRCUT = 0.08

def apply_rainbet_haircut(decimal_odds: float) -> float:
    if decimal_odds is None or decimal_odds <= 1.0:
        return decimal_odds
    profit = decimal_odds - 1.0
    return 1.0 + profit * (1.0 - RAINBET_PRICING_HAIRCUT)

# =============================================================================
# PREMIUM ODDS API
# =============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_premium_odds(sport_key: str) -> pd.DataFrame:
    if not ODDS_API_KEY:
        st.error("❌ ODDS_API_KEY not set.")
        return pd.DataFrame()

    _sport_map = {
        "basketball_nba":  "basketball_nba",
        "basketball_wnba": "basketball_wnba",
        "baseball_mlb":    "baseball_mlb",
        "tennis":          "tennis",
        "icehockey_nhl":       "icehockey_nhl",
        "americanfootball_nfl":  "americanfootball_nfl",
        "americanfootball_ncaaf": "americanfootball_ncaaf",
    }
    sport_label = {
        "basketball_nba":  "NBA",
        "basketball_wnba": "WNBA",
        "baseball_mlb":    "MLB",
        "tennis":          "Tennis",
        "icehockey_nhl":       "NHL",
        "americanfootball_nfl":  "NFL",
        "americanfootball_ncaaf": "NCAAF",
    }.get(sport_key, sport_key.upper())

    api_sport = _sport_map.get(sport_key, sport_key)
    try:
        resp = _session().get(
            f"{ODDS_API_BASE}/odds/",
            headers={"x-api-key": ODDS_API_KEY},
            params={"sport_key": api_sport, "markets": "h2h"},
            verify=False, timeout=15,
        )
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

    if resp.status_code != 200:
        st.error(f"❌ Status: {resp.status_code} | Error: {resp.text[:300]}")
        return pd.DataFrame()

    import json as _json
    payload = resp.json()
    events  = payload.get("data") or []
    print(f"[DEBUG] Got {len(events)} events for {sport_key}")

    if not events:
        return pd.DataFrame()

    print(f"[DEBUG] first event:\n" + _json.dumps(events[0], indent=2, default=str))

    bypass_filters = st.session_state.get("debug_bypass_filters", False)
    rows = []; skipped_imp = 0; skipped_bk = 0

    for ev in events:
        try:
            event_id = ev.get("event_id", "")
            home_raw  = ev.get("home_team", "")
            away_raw  = ev.get("away_team", "")
            if sport_label == "Tennis":
                home = normalize_tennis_name(home_raw)
                away = normalize_tennis_name(away_raw)
            else:
                home, away = home_raw, away_raw
            start = ev.get("start_time", "")
            try:
                naive_utc = datetime.strptime(start.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                dt_est    = _TZ_UTC.localize(naive_utc).astimezone(_TZ_EASTERN)
                time_str  = dt_est.strftime("%I:%M %p ET")
                ev_date   = dt_est.strftime("%Y-%m-%d")
            except Exception:
                time_str = "TBD"; ev_date = ""

            best_h = best_a = 0.0; book_count = 0; latest_update = ""
            blocked_market_hit = False
            for bk in (ev.get("books") or []):
                mkt = (bk.get("market") or "").strip().lower()
                if mkt in BLOCKED_BASKETBALL_MARKETS:
                    blocked_market_hit = True
                    continue
                if mkt not in ALLOWED_BASKETBALL_MARKETS and mkt != "h2h":
                    continue
                if bk.get("market") != "h2h": continue
                upd = bk.get("updated_at", "")
                if upd and upd > latest_update:
                    latest_update = upd
                for outcome in (bk.get("outcomes") or []):
                    price = american_to_decimal(float(outcome.get("price", 0)))
                    name  = outcome.get("name", "")
                    if name == home_raw and price > best_h: best_h = price
                    elif name == away_raw and price > best_a: best_a = price
                book_count += 1

            if book_count == 0: skipped_bk += 1
            if blocked_market_hit and book_count == 0:
                print(f"[DEBUG] {home} vs {away}: only 1x2/regulation-time market offered — skipped (would auto-lose on OT)")

            if not bypass_filters:
                if best_h <= 1 or best_a <= 1:
                    skipped_imp += 1; continue
                imp_sum = (1 / best_h) + (1 / best_a)
                if not (0.90 <= imp_sum <= 1.25):
                    skipped_imp += 1; continue

            best_h = apply_rainbet_haircut(best_h)
            best_a = apply_rainbet_haircut(best_a)

            velocity_key = event_id or f"{home} vs {away}"

            rows.append({
                "_event_id":    event_id,
                "Match":        f"{home} vs {away}",
                "Home Team":    home,
                "Away Team":    away,
                "Home Odds":    round(best_h, 3) if best_h else 0.0,
                "Away Odds":    round(best_a, 3) if best_a else 0.0,
                "Books":        book_count,
                "Time/Score":   time_str,
                "Status":       "Scheduled",
                "Risk Meter":   30,
                "_sport":       sport_label,
                "_date":        ev_date,
                "_start_iso":   start,
                "_updated_at":  latest_update,
                "Line Velocity": log_and_get_velocity(velocity_key, best_h, best_a),
            })
        except Exception as _exc:
            print(f"[DEBUG] parse error: {_exc} — {ev}"); continue

    print(f"[DEBUG] After filter: {len(rows)} rows (skipped {skipped_imp} bad-sum, {skipped_bk} no-books)")
    if not rows:
        return pd.DataFrame()

    df_out = pd.DataFrame(rows).sort_values("_date").reset_index(drop=True)
    st.session_state[f"debug_raw_event_{sport_key}"] = events[0]
    return df_out

# =============================================================================
# EV+ MODEL — calibrated
# =============================================================================
def calculate_real_ev(df: pd.DataFrame, model_cfg: dict, sport: str = "NBA") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()

    confidence = float(model_cfg.get("model_confidence", 1.0))
    injury_pen = float(model_cfg.get("injury_penalty_pct", 5.0)) / 100

    home_boost = {"NBA": 0.060, "MLB": 0.035, "Tennis": 0.055,
                  "NHL": 0.045, "NFL": 0.050, "NCAAF": 0.055}.get(sport, 0.060)

    h_col = "Home Odds" if "Home Odds" in df.columns else "P1 Odds"
    a_col = "Away Odds" if "Away Odds" in df.columns else "P2 Odds"
    ai_probs, edges, evs, raws, rainbets = [], [], [], [], []
    bet_sides, bet_teams, bet_odds_list = [], [], []

    for _, row in df.iterrows():
        h_odds = pd.to_numeric(row.get(h_col), errors="coerce")
        a_odds = pd.to_numeric(row.get(a_col), errors="coerce")

        if pd.isna(h_odds) or pd.isna(a_odds) or h_odds <= 1.01 or a_odds <= 1.01:
            ai_probs.append(None); edges.append(None)
            evs.append(None);      raws.append(None); rainbets.append(None)
            bet_sides.append(None); bet_teams.append(None); bet_odds_list.append(None)
            continue

        imp_h   = 1.0 / h_odds
        imp_a   = 1.0 / a_odds
        overrnd = imp_h + imp_a
        fair_h  = imp_h / overrnd

        model_h = fair_h + home_boost

        _MAX_INJURY_SWING = 0.08
        def _risk_penalty(risk: int) -> float:
            if risk >= 90: pct = injury_pen * 1.5
            elif risk >= 65: pct = injury_pen
            elif risk >= 35: pct = injury_pen * 0.5
            else: return 0.0
            return min(pct, _MAX_INJURY_SWING)

        if "_home_injury_risk" in row.index or "_away_injury_risk" in row.index:
            home_risk = int(row.get("_home_injury_risk", 30) or 30)
            away_risk = int(row.get("_away_injury_risk", 30) or 30)
            model_h -= _risk_penalty(home_risk)
            model_h += _risk_penalty(away_risk)
        else:
            risk = int(row.get("Risk Meter", 30))
            if risk >= 65:   model_h -= injury_pen
            elif risk >= 35: model_h -= injury_pen * 0.5

        model_h = fair_h + (model_h - fair_h) * confidence
        model_h = max(0.02, min(0.98, model_h))

        if _DZ_LO <= model_h < _DZ_HI:
            model_h *= _DZ_DISCOUNT

        if sport == "MLB" and 1.85 <= h_odds <= 2.10:
            model_h -= 0.04

        model_h = max(0.02, min(0.98, model_h))
        model_a = 1.0 - model_h

        ev_h   = model_h * (h_odds - 1) - (1.0 - model_h)
        ev_a   = model_a * (a_odds - 1) - (1.0 - model_a)
        edge_h = (model_h - imp_h) * 100
        edge_a = (model_a - imp_a) * 100

        home_t = row.get("Home Team", "")
        away_t = row.get("Away Team", "")

        # Favorite-lean: identify which side is the market favorite (lower
        # decimal odds) and require the underdog side to beat it by a real
        # margin, not just edge it out narrowly on paper. This discounts the
        # underdog's EV+ before comparing, so a close call goes to the
        # favorite instead of whichever side happens to have a slightly
        # inflated model probability. The underdog can still win the
        # comparison if its edge is genuinely large — this isn't a hard ban,
        # just a thumb on the scale toward favorites.
        UNDERDOG_EV_DISCOUNT = 0.0    # Balanced — no favorite lean. Whichever side (favorite or
                                       # underdog) has the higher raw EV+ gets bet, full stop. Prior
                                       # favorite-lean logic is still here (dog_ev_discounted below)
                                       # in case you want to reintroduce a lean later, but at 0.0 it's
                                       # a no-op: dog_ev_discounted == dog_ev exactly.

        if h_odds <= a_odds:
            fav_ev, fav_side  = ev_h, "Home"
            dog_ev, dog_side  = ev_a, "Away"
        else:
            fav_ev, fav_side  = ev_a, "Away"
            dog_ev, dog_side  = ev_h, "Home"

        dog_ev_discounted = dog_ev * (1.0 - UNDERDOG_EV_DISCOUNT) if dog_ev > 0 else dog_ev

        if fav_ev >= dog_ev_discounted:
            bet_side = fav_side
        else:
            bet_side = dog_side

        if bet_side == "Home":
            bet_prob, bet_price_v, bet_ev, bet_edge, bet_team = model_h, h_odds, ev_h, edge_h, home_t
        else:
            bet_prob, bet_price_v, bet_ev, bet_edge, bet_team = model_a, a_odds, ev_a, edge_a, away_t

        ai_probs.append(round(bet_prob * 100, 1))
        edges.append(round(bet_edge, 2))
        evs.append(round(bet_ev, 4))
        raws.append(bet_prob)
        rainbets.append(bet_price_v)
        bet_sides.append(bet_side)
        bet_teams.append(bet_team)
        bet_odds_list.append(bet_price_v)

    df["AI Prob %"]    = ai_probs
    df["Edge %"]       = edges
    df["EV+"]          = evs
    df["_ai_prob_raw"] = raws
    df["Rainbet Odds"] = rainbets
    df["_bet_side"]    = bet_sides
    df["Bet Team"]     = bet_teams
    df["Bet Odds"]     = bet_odds_list
    return df

# =============================================================================
# KELLY STAKES — Covariance Shield
# =============================================================================
def calculate_stakes(df: pd.DataFrame, bankroll: float, risk_level: str,
                      max_stake_cap: float | None = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    price_col = "Bet Odds" if "Bet Odds" in df.columns else ("Home Odds" if "Home Odds" in df.columns else "P1 Odds")

    ev_vals = pd.to_numeric(df.get("EV+"), errors="coerce").fillna(0)
    active_simultaneous_trades = max(1, int((ev_vals > MIN_EV_THRESHOLD).sum()))

    stakes = []
    for _, row in df.iterrows():
        h_odds = pd.to_numeric(row.get(price_col), errors="coerce")
        raw    = row.get("_ai_prob_raw")
        if pd.isna(h_odds) or raw is None:
            stakes.append(None); continue
        prob = float(raw)
        b    = h_odds - 1.0
        edge = prob * b - (1.0 - prob)
        if edge <= 0:
            stakes.append(0.0)
        else:
            frac             = KELLY_FRACTIONS.get(risk_level, 0.5)
            raw_kelly        = edge / b
            fractional_kelly = raw_kelly * frac
            if active_simultaneous_trades > 1:
                fractional_kelly /= (active_simultaneous_trades ** 0.5)
            final_pct   = min(fractional_kelly, 0.05)
            final_stake = final_pct * bankroll * CB_STAKE_MULTIPLIER

            if bool(row.get("_floor_exception", False)):
                final_stake *= 0.5

            final_stake = max(final_stake, 0.0)
            if max_stake_cap is not None and max_stake_cap > 0:
                final_stake = min(final_stake, max_stake_cap)

            stakes.append(round(final_stake, 2))

    df["Stake (C$)"]           = stakes
    df["_simultaneous_trades"] = active_simultaneous_trades
    return df


def compare_straight_vs_parlay(legs: list[dict], bankroll: float, risk_level: str = "Moderate") -> dict:
    frac = KELLY_FRACTIONS.get(risk_level, 0.5)

    straight_stake_total = 0.0
    straight_ev_total     = 0.0
    straight_var_total    = 0.0
    for leg in legs:
        p, o = leg["prob"], leg["odds"]
        b = o - 1.0
        edge = p * b - (1 - p)
        if edge <= 0:
            continue
        kelly_pct = min((edge / b) * frac, 0.05)
        stake = kelly_pct * bankroll
        ev    = stake * edge
        var   = (stake ** 2) * p * (1 - p) * (b + 1) ** 2
        straight_stake_total += stake
        straight_ev_total    += ev
        straight_var_total   += var

    parlay_prob = 1.0
    parlay_odds = 1.0
    for leg in legs:
        parlay_prob *= leg["prob"]
        parlay_odds *= leg["odds"]
    b_p = parlay_odds - 1.0
    parlay_edge = parlay_prob * b_p - (1 - parlay_prob)
    if parlay_edge > 0 and b_p > 0:
        parlay_kelly_pct = min((parlay_edge / b_p) * frac, 0.05)
        parlay_stake     = parlay_kelly_pct * bankroll
    else:
        parlay_stake = 0.0
    parlay_ev  = parlay_stake * parlay_edge
    parlay_var = (parlay_stake ** 2) * parlay_prob * (1 - parlay_prob) * (b_p + 1) ** 2

    return {
        "straight": {"total_stake": round(straight_stake_total, 2),
                     "expected_profit": round(straight_ev_total, 2),
                     "variance": round(straight_var_total, 2),
                     "std_dev": round(straight_var_total ** 0.5, 2)},
        "parlay":   {"total_stake": round(parlay_stake, 2),
                     "expected_profit": round(parlay_ev, 2),
                     "implied_prob": round(parlay_prob * 100, 3),
                     "variance": round(parlay_var, 2),
                     "std_dev": round(parlay_var ** 0.5, 2)},
        "verdict": ("Straight bets win" if straight_ev_total >= parlay_ev
                    else "Parlay technically higher EV but check variance"),
        "why": ("Each leg has independent edge captured at fair stake size; "
                "a parlay multiplies probabilities (shrinking win-rate toward zero) "
                "while concentrating the entire stake on a single all-or-nothing event, "
                "so one bad leg erases the EV+ of every other leg combined."),
    }

# =============================================================================
# ADVANCE PREDICTIONS
# =============================================================================
def build_advance_predictions(days_ahead: int, sport: str,
                               model_cfg: dict, bankroll: float,
                               risk_level: str, max_stake_cap: float | None = None) -> pd.DataFrame:
    today   = datetime.now().date()
    cutoff  = today + timedelta(days=days_ahead)

    if sport == "Tennis":
        combined = fetch_premium_odds("tennis")
        if combined.empty: return pd.DataFrame()
        combined = combined[combined["_date"].between(str(today), str(cutoff))].reset_index(drop=True)
        combined["_fetch_date"] = combined["_date"]
    else:
        sport_key_map = {
            "NBA": "basketball_nba", "MLB": "baseball_mlb",
            "NHL": "icehockey_nhl", "NFL": "americanfootball_nfl",
            "NCAAF": "americanfootball_ncaaf",
        }
        sport_key = sport_key_map.get(sport, "basketball_nba")
        combined  = fetch_premium_odds(sport_key)
        if combined.empty: return pd.DataFrame()
        combined = combined[combined["_date"].between(str(today), str(cutoff))].reset_index(drop=True)
        if combined.empty: return pd.DataFrame()
        combined["_fetch_date"] = combined["_date"]

    combined = calculate_real_ev(combined, model_cfg, sport)
    combined = calculate_stakes(combined, bankroll, risk_level, max_stake_cap=max_stake_cap)
    return combined

# =============================================================================
# BET FINDERS
# =============================================================================
def diagnose_qualification_funnel(df: pd.DataFrame, sport_name: str, hours: int = 24) -> dict:
    stages = {"total": 0, "in_24h_window": 0, "after_mlb_cap": 0, "above_floor": 0,
              "below_ceiling": 0, "meets_edge_threshold": 0, "closest_miss": None}
    if df is None or df.empty:
        return stages
    stages["total"] = len(df)

    now_est    = datetime.now(_TZ_EASTERN)
    cutoff_est = now_est + timedelta(hours=hours)
    def _in_window(iso: str) -> bool:
        try:
            naive_utc = datetime.strptime(str(iso).replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            dt_est = _TZ_UTC.localize(naive_utc).astimezone(_TZ_EASTERN)
            return now_est <= dt_est <= cutoff_est
        except Exception:
            return False

    work = df.copy()
    if "_start_iso" in work.columns:
        work = work[work["_start_iso"].apply(_in_window)]
    stages["in_24h_window"] = len(work)
    if work.empty: return stages

    if sport_name == "MLB":
        price_col = "Bet Odds" if "Bet Odds" in work.columns else ("Home Odds" if "Home Odds" in work.columns else "P1 Odds")
        work = work[pd.to_numeric(work[price_col], errors="coerce").fillna(99) <= MLB_MAX_ODDS]
    stages["after_mlb_cap"] = len(work)
    if work.empty: return stages

    bet_price = pd.to_numeric(work.get("Bet Odds"), errors="coerce").fillna(0) if "Bet Odds" in work.columns else pd.Series(dtype=float)
    work = work[bet_price >= EFFECTIVE_FAVORITE_FLOOR]
    stages["above_floor"] = len(work)
    if work.empty: return stages

    max_dog_odds = float(load_model_config().get("max_underdog_odds", MAX_UNDERDOG_ODDS))
    bet_price2 = pd.to_numeric(work.get("Bet Odds"), errors="coerce").fillna(0)
    work = work[bet_price2 <= max_dog_odds]
    stages["below_ceiling"] = len(work)
    if work.empty: return stages

    ev   = pd.to_numeric(work.get("EV+"), errors="coerce")
    edge = pd.to_numeric(work.get("Edge %"), errors="coerce")
    qual = work[(ev > MIN_EV_THRESHOLD) & (edge >= MIN_EDGE_THRESHOLD)]
    stages["meets_edge_threshold"] = len(qual)

    if qual.empty and not work.empty and not edge.dropna().empty:
        best_idx = edge.idxmax()
        stages["closest_miss"] = {
            "match": work.loc[best_idx].get("Match", "?"),
            "edge_pct": round(float(edge.loc[best_idx]), 2),
            "ev_plus": round(float(ev.loc[best_idx]), 4) if pd.notna(ev.loc[best_idx]) else None,
            "needed_edge_pct": MIN_EDGE_THRESHOLD,
        }
    return stages


def find_best_bet(*dfs) -> pd.Series | None:
    frames = [df for df in dfs if df is not None and not df.empty]
    if not frames: return None
    all_df = pd.concat(frames, ignore_index=True).dropna(subset=["EV+","Edge %"])
    qual   = all_df[(all_df["EV+"] > MIN_EV_THRESHOLD) & (all_df["Edge %"] >= MIN_EDGE_THRESHOLD)]
    if qual.empty: return None
    return all_df.loc[qual["EV+"].idxmax()]


def find_top_bets(*dfs, n: int = 8, per_sport_cap: int = 3, hours: int = 48) -> list:
    SPORT_CAPS = {"MLB": 2, "NBA": per_sport_cap, "Tennis": per_sport_cap}
    # NFL and NCAAF games are scheduled much further in advance than daily
    # sports (NBA/MLB/Tennis/NHL) — a single global lookahead window means
    # football games sitting 3-10 days out never even get considered, since
    # they're always outside a 24-48h cutoff. These two sports get a wider
    # window so games actually become visible as they approach, instead of
    # requiring the person to be checking at exactly the right moment.
    SPORT_WINDOW_HOURS_OVERRIDE = {"NFL": 168, "NCAAF": 168}   # 7 days
    now_est    = datetime.now(_TZ_EASTERN)

    def _in_window(iso: str, window_hours: float) -> bool:
        try:
            naive_utc = datetime.strptime(str(iso).replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            dt_est = _TZ_UTC.localize(naive_utc).astimezone(_TZ_EASTERN)
            cutoff_est = now_est + timedelta(hours=window_hours)
            return now_est <= dt_est <= cutoff_est
        except Exception:
            return False

    capped = []
    for df in dfs:
        if df is None or df.empty: continue

        sport_name_early = df["_sport"].iloc[0] if "_sport" in df.columns else "?"
        window_hours = SPORT_WINDOW_HOURS_OVERRIDE.get(sport_name_early, hours)

        if "_start_iso" in df.columns:
            df = df[df["_start_iso"].apply(lambda iso: _in_window(iso, window_hours))].copy()
        if df.empty: continue

        sport_name = df["_sport"].iloc[0] if "_sport" in df.columns else "?"
        if sport_name == "MLB":
            price_col = "Bet Odds" if "Bet Odds" in df.columns else ("Home Odds" if "Home Odds" in df.columns else "P1 Odds")
            df = df[pd.to_numeric(df[price_col], errors="coerce").fillna(99) <= MLB_MAX_ODDS].copy()
        if df.empty: continue

        if "Bet Odds" in df.columns:
            bet_price = pd.to_numeric(df["Bet Odds"], errors="coerce").fillna(0)
        else:
            h_col2 = "Home Odds" if "Home Odds" in df.columns else "P1 Odds"
            a_col2 = "Away Odds" if "Away Odds" in df.columns else "P2 Odds"
            bet_price = pd.concat([
                pd.to_numeric(df[h_col2], errors="coerce"),
                pd.to_numeric(df[a_col2], errors="coerce"),
            ], axis=1).min(axis=1).fillna(0)

        above_floor = df[bet_price >= EFFECTIVE_FAVORITE_FLOOR].copy()

        max_dog_odds = float(load_model_config().get("max_underdog_odds", MAX_UNDERDOG_ODDS))
        over_ceiling_count = int((bet_price > max_dog_odds).sum())
        if over_ceiling_count:
            print(f"[DEBUG] {sport_name}: {over_ceiling_count} bet(s) excluded — "
                  f"odds above underdog ceiling ({max_dog_odds:.2f}x)")
        above_floor = above_floor[bet_price.loc[above_floor.index] <= max_dog_odds].copy()

        below_floor = df[bet_price < EFFECTIVE_FAVORITE_FLOOR].copy()
        exception_pool = apply_floor_exception(below_floor, sport_name)
        if exception_pool is not None and not exception_pool.empty:
            exception_pool = exception_pool.copy()
            exception_pool["_floor_exception"] = True
            print(f"[DEBUG] {sport_name}: {len(exception_pool)} below-floor exception bet(s) "
                  f"admitted (EV+ > {HEAVY_FAVORITE_EV_EXCEPTION_THRESHOLD:.2%}) — verify calibration before trusting these.")
            above_floor["_floor_exception"] = False
            df = pd.concat([above_floor, exception_pool], ignore_index=True)
        else:
            df = above_floor
        if df.empty: continue

        ev   = pd.to_numeric(df["EV+"],    errors="coerce")
        edge = pd.to_numeric(df["Edge %"], errors="coerce")
        qual = df[(ev > MIN_EV_THRESHOLD) & (edge >= MIN_EDGE_THRESHOLD)]

        cap = SPORT_CAPS.get(sport_name, per_sport_cap)
        print(f"[DEBUG] {sport_name}: {len(df)} in window, {len(qual)} qualifying (cap={cap})")
        if qual.empty: continue
        capped.append(qual.sort_values("Edge %", ascending=False).head(cap))

    if not capped:
        print("[DEBUG find_top_bets] 0 qualifying bets")
        return []

    combined = pd.concat(capped, ignore_index=True)
    final    = combined.sort_values("Edge %", ascending=False)
    print(f"[DEBUG find_top_bets] returning top {min(n, len(final))} of {len(final)}")
    return [final.iloc[i] for i in range(min(n, len(final)))]


def find_underdog_bets(*dfs, min_odds: float = 2.5, max_picks: int = 2) -> list:
    frames = [df for df in dfs if df is not None and not df.empty]
    if not frames: return []
    all_df = pd.concat(frames, ignore_index=True).dropna(subset=["EV+","Edge %"])
    if "Bet Odds" in all_df.columns:
        best_odds = pd.to_numeric(all_df["Bet Odds"], errors="coerce").fillna(0)
    else:
        h_col  = "Home Odds" if "Home Odds" in all_df.columns else "P1 Odds"
        a_col  = "Away Odds" if "Away Odds" in all_df.columns else "P2 Odds"
        home_odds = pd.to_numeric(all_df.get(h_col, pd.Series(dtype=float)), errors="coerce").fillna(0)
        away_odds = pd.to_numeric(all_df.get(a_col, pd.Series(dtype=float)), errors="coerce").fillna(0)
        best_odds = away_odds.where(away_odds >= home_odds, home_odds)
    mask = (best_odds >= min_odds) & (all_df["EV+"] > 0)
    dogs = all_df[mask].copy()
    if dogs.empty: return []
    dogs["_dog_odds"] = best_odds[mask].values
    dogs = dogs.sort_values("_dog_odds", ascending=False)
    return [dogs.iloc[i] for i in range(min(max_picks, len(dogs)))]

# =============================================================================
# PAPER TRADING
# =============================================================================
def load_paper_trades() -> list:
    if not PAPER_TRADES_CSV.exists(): return []
    try:
        df = pd.read_csv(PAPER_TRADES_CSV)
        for col in ["odds","ev_plus","stake","ai_prob","edge_pct","rainbet_mult"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        for col in ["timestamp","match","sport","strategy","status","result"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
        return df.to_dict("records")
    except Exception:
        return []

def save_paper_trades(trades: list) -> None:
    try:
        pd.DataFrame(trades).to_csv(PAPER_TRADES_CSV, index=False)
    except Exception as e:
        print(f"[save_paper_trades] ERROR: {e}")

def dedupe_pending_trades() -> int:
    """
    One-time cleanup for duplicate PENDING rows that were logged before the
    dedup check existed in execute_paper_trade. Keeps the EARLIEST PENDING
    row per (match, bet_team) pair and drops the rest; SETTLED/VOID rows are
    left untouched since those are real graded history, not accidental repeats.
    Returns the number of rows removed.
    """
    trades = load_paper_trades()
    if not trades:
        return 0
    pending = [t for t in trades if t.get("status") == "PENDING"]
    other   = [t for t in trades if t.get("status") != "PENDING"]
    if not pending:
        return 0

    pending_sorted = sorted(pending, key=lambda t: t.get("timestamp", ""))
    seen = set()
    kept = []
    for t in pending_sorted:
        key = (str(t.get("match", "")), str(t.get("bet_team", "")))
        if key in seen:
            continue
        seen.add(key)
        kept.append(t)

    removed = len(pending) - len(kept)
    if removed > 0:
        save_paper_trades(other + kept)
    return removed

def execute_paper_trade(*dfs) -> tuple[bool, str]:
    top3 = find_top_bets(*dfs, n=3)
    if not top3:
        return False, "No qualifying bets found (EV+ > threshold + Edge ≥ 4.5% required)."
    trades = load_paper_trades()

    # Dedup: without this, the same still-qualifying match gets appended again
    # every time execute_paper_trade runs (every app rerun) for as long as it
    # stays in the qualifying window — one real game could log dozens of
    # near-identical PENDING rows. Skip logging a match that already has a
    # PENDING entry; it'll naturally drop out once it starts or gets graded.
    already_pending_matches = {
        str(t.get("match", "")) for t in trades if t.get("status") == "PENDING"
    }

    logged = []
    for best in top3:
        match_name = best.get("Match", "Unknown")
        if match_name in already_pending_matches:
            continue
        bet_odds_v = best.get("Bet Odds")
        if bet_odds_v not in (None, ""):
            logged_odds = bet_odds_v
        else:
            h_col = "Home Odds" if pd.notna(best.get("Home Odds")) else "P1 Odds"
            logged_odds = best.get(h_col, 0) or 0
        trades.append({
            "id":           f"{match_name}_{datetime.now().strftime('%H%M%S')}",
            "timestamp":    datetime.now().isoformat(),
            "match":        match_name,
            "bet_team":     best.get("Bet Team", "") or "",
            "sport":        best.get("_sport", ""),
            "odds":         logged_odds,
            "ev_plus":      best.get("EV+", 0),
            "stake":        best.get("Stake (C$)", 0),
            "ai_prob":      best.get("_ai_prob_raw", 0.5),
            "edge_pct":     best.get("Edge %", 0),
            "rainbet_mult": best.get("Rainbet Odds", logged_odds),
            "strategy":     "High EV" if (best.get("EV+", 0) or 0) > 0.05 else "Value",
            "status":       "PENDING",
            "result":       "",
        })
        already_pending_matches.add(match_name)
        logged.append(f"{best.get('Bet Team','?')} — {match_name} (EV+ {float(best.get('EV+',0)):+.4f})")
    if not logged:
        return False, "No new trades logged — all qualifying matches already have a pending entry."
    save_paper_trades(trades)
    return True, f"✅ Logged {len(logged)} trade(s): " + " | ".join(logged)

def grade_trade_manually(trade_id: str, result: str) -> bool:
    result = (result or "").upper().strip()
    if result not in ("WIN", "LOSS", "PUSH", "VOID"):
        return False
    trades = load_paper_trades()
    found = False
    for t in trades:
        if str(t.get("id", "")) == str(trade_id):
            t["result"] = result
            t["status"] = "SETTLED" if result in ("WIN", "LOSS") else "VOID"
            t["graded_at"] = datetime.now().isoformat()
            t["graded_manually"] = True
            found = True
            break
    if found:
        save_paper_trades(trades)
    return found

def calculate_success_rate() -> dict:
    trades = load_paper_trades(); total = wins = 0
    for t in trades:
        r = str(t.get("result", "")).upper()
        if r in ("WIN","LOSS"):
            total += 1
            if r == "WIN": wins += 1
    return {"total": total, "wins": wins, "losses": total - wins,
            "success_rate": round(wins / total * 100, 1) if total else 0.0}

def calculate_success_rate_by_group(group_col: str) -> pd.DataFrame:
    trades = load_paper_trades()
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    if group_col not in df.columns or "result" not in df.columns:
        return pd.DataFrame()
    graded = df[df["result"].astype(str).str.upper().isin(["WIN", "LOSS"])].copy()
    if graded.empty:
        return pd.DataFrame()
    graded["_is_win"] = graded["result"].str.upper().eq("WIN")
    out = graded.groupby(group_col).agg(
        Bets=("_is_win", "count"),
        Wins=("_is_win", "sum"),
    )
    out["Win Rate %"] = (out["Wins"] / out["Bets"] * 100).round(1)
    return out.reset_index().sort_values("Bets", ascending=False)

# =============================================================================
# HEAVY-FAVORITE FLOOR EXCEPTION — persistent daily cap
# =============================================================================
def load_exception_log() -> dict:
    if FLOOR_EXCEPTION_LOG_PATH.exists():
        try: return json.loads(FLOOR_EXCEPTION_LOG_PATH.read_text())
        except Exception: pass
    return {}

def save_exception_log(log: dict) -> None:
    try:
        FLOOR_EXCEPTION_LOG_PATH.write_text(json.dumps(log, indent=2))
    except Exception as e:
        print(f"[save_exception_log] ERROR: {e}")

def apply_floor_exception(below_floor: pd.DataFrame, sport_name: str) -> pd.DataFrame | None:
    if below_floor is None or below_floor.empty:
        return None
    ev_below = pd.to_numeric(below_floor.get("EV+"), errors="coerce")
    price_col = "Bet Odds" if "Bet Odds" in below_floor.columns else (
        "Home Odds" if "Home Odds" in below_floor.columns else "P1 Odds")
    price_below = pd.to_numeric(below_floor.get(price_col), errors="coerce")
    candidates = below_floor[(ev_below > HEAVY_FAVORITE_EV_EXCEPTION_THRESHOLD) &
                              (price_below >= EXCEPTION_MIN_ODDS)].copy()
    if candidates.empty:
        return None
    candidates = candidates.sort_values("EV+", ascending=False)

    log = load_exception_log()
    today_str = datetime.now().strftime("%Y-%m-%d")
    log = {today_str: log.get(today_str, {})}
    used_today = set(log[today_str].get(sport_name, []))

    admitted = []
    for _, row in candidates.iterrows():
        eid = row.get("_event_id") or row.get("Match", "")
        if not eid:
            continue
        if eid in used_today:
            admitted.append(row)
            continue
        if len(used_today) < HEAVY_FAVORITE_EV_EXCEPTION_MAX_PER_DAY:
            admitted.append(row)
            used_today.add(eid)

    log[today_str][sport_name] = sorted(used_today)
    save_exception_log(log)

    if not admitted:
        return None
    return pd.DataFrame(admitted)


def load_bet_ledger() -> dict:
    if BET_LEDGER_PATH.exists():
        try: return json.loads(BET_LEDGER_PATH.read_text())
        except Exception: pass
    return {}

def save_bet_ledger(ledger: dict) -> None:
    try:
        BET_LEDGER_PATH.write_text(json.dumps(ledger, indent=2, default=str))
    except Exception as e:
        print(f"[save_bet_ledger] ERROR: {e}")

def update_bet_ledger(qualifying_bets: list, all_known_keys: set) -> dict:
    ledger = load_bet_ledger()
    now_iso = datetime.now().isoformat()

    for bet in qualifying_bets:
        key = bet.get("_event_id") or bet.get("Match", "")
        if not key:
            continue
        ledger[key] = {
            "match":        bet.get("Match", ""),
            "sport":        bet.get("_sport", ""),
            "bet_team":     bet.get("Bet Team", ""),
            "bet_odds":     bet.get("Bet Odds"),
            "ev":           bet.get("EV+"),
            "edge":         bet.get("Edge %"),
            "stake":        bet.get("Stake (C$)"),
            "start_iso":    bet.get("_start_iso", ""),
            "date":         bet.get("_date", ""),
            "time_str":     bet.get("Time/Score", ""),
            "first_seen":   ledger.get(key, {}).get("first_seen", now_iso),
            "last_updated": now_iso,
        }

    now_utc = _TZ_UTC.localize(datetime.utcnow())
    for key in list(ledger.keys()):
        entry = ledger[key]
        start_iso = entry.get("start_iso", "")
        started = False
        try:
            naive = datetime.strptime(str(start_iso).replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            started = _TZ_UTC.localize(naive) <= now_utc
        except Exception:
            pass
        vanished = key not in all_known_keys
        if started or vanished:
            ledger.pop(key, None)

    save_bet_ledger(ledger)
    return ledger


def filter_ledger_to_good_window(ledger: dict) -> dict:
    """
    Restricts the ledger to bets currently in the "Good window" timing band
    (see bet_timing_status: 0.5-6 hours out — close enough that the odds
    snapshot is unlikely to have drifted, far enough that the line has
    settled). A bet that's too early is simply not shown yet; it appears
    once it enters the good window, and disappears again once it starts or
    drifts past it. This is a display filter only — it doesn't affect what's
    stored in the ledger or what execute_paper_trade logs, only what the
    Live Hub surfaces as "ready to act on."

    IMPORTANT: "Good window" describes odds freshness / timing stability —
    it is NOT a win-probability signal and never guarantees a bet will hit.
    """
    good = {}
    for key, entry in ledger.items():
        label, _ = bet_timing_status(entry.get("start_iso", ""))
        if label == "✅ Good window":
            good[key] = entry
    return good


def bet_timing_status(start_iso: str) -> tuple[str, str]:
    try:
        naive = datetime.strptime(str(start_iso).replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        start_dt = _TZ_UTC.localize(naive)
    except Exception:
        return ("Time unknown", "#64748b")
    now_utc = _TZ_UTC.localize(datetime.utcnow())
    hours_out = (start_dt - now_utc).total_seconds() / 3600
    if hours_out < 0:
        return ("Started", "#64748b")
    if hours_out <= 0.5:
        return ("⚠️ Starting soon", "#ef4444")
    if hours_out <= 6:
        return ("✅ Good window", "#22c55e")
    if hours_out <= 18:
        return ("🕒 Early — line may move", "#f59e0b")
    return ("🕒 Very early — line may move a lot", "#f59e0b")

# =============================================================================
# NEWS / INJURY SIGNAL — best-effort only, not a real injury feed
# =============================================================================
def flagged_injury_headlines(headlines: list) -> set:
    return {h.lower() for h in headlines if detect_injury_alert(h)}


def apply_injury_flags(df: pd.DataFrame, flagged_headlines: set, sport: str = "") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    is_solo_sport = (sport == "Tennis")
    flagged_risk_level = 95 if is_solo_sport else 70

    if not flagged_headlines:
        df["_home_injury_risk"] = 30
        df["_away_injury_risk"] = 30
        return df

    combined_text = " ".join(flagged_headlines)

    def _team_flagged(team: str) -> bool:
        if not team:
            return False
        token = str(team).strip().split()[-1].lower()
        return len(token) > 3 and token in combined_text

    home_risk, away_risk = [], []
    for _, row in df.iterrows():
        home_risk.append(flagged_risk_level if _team_flagged(row.get("Home Team", "")) else 30)
        away_risk.append(flagged_risk_level if _team_flagged(row.get("Away Team", "")) else 30)
    df["_home_injury_risk"] = home_risk
    df["_away_injury_risk"] = away_risk
    df["Risk Meter"] = [max(h, a) for h, a in zip(home_risk, away_risk)]
    return df

# =============================================================================
# BACKTEST
# =============================================================================
def run_backtest(days: int = 30) -> dict:
    trades  = load_paper_trades()
    settled = [t for t in trades if t.get("status") == "SETTLED"]
    if not settled: return {"error": "No settled trades yet."}
    try:
        cutoff  = datetime.now() - timedelta(days=days)
        settled = [t for t in settled if datetime.fromisoformat(str(t["timestamp"])) >= cutoff]
    except Exception: pass
    if not settled: return {"error": f"No settled trades in the last {days} days."}
    total  = len(settled)
    wins   = sum(1 for t in settled if str(t.get("result","")).upper() == "WIN")
    staked = sum(float(t.get("stake", 0)) for t in settled)
    evs    = sum(float(t.get("ev_plus", 0)) for t in settled)
    win_s  = [float(t.get("stake",0)) for t in settled if str(t.get("result","")).upper()=="WIN"]
    los_s  = [float(t.get("stake",0)) for t in settled if str(t.get("result","")).upper()=="LOSS"]
    avg_w  = round(sum(win_s)/len(win_s), 2) if win_s else 0.0
    avg_l  = round(sum(los_s)/len(los_s), 2) if los_s else 0.0
    return {
        "total_trades": total, "wins": wins, "losses": total - wins,
        "win_rate":     round(wins / total * 100, 2),
        "roi":          round(evs / staked * 100, 2) if staked else 0.0,
        "avg_win": avg_w, "avg_loss": avg_l,
        "profit_factor": round(avg_w / avg_l, 2) if avg_l else 0.0,
        "total_stake":   round(staked, 2),
        "total_ev":      round(evs, 4),
    }

# =============================================================================
# CONFIG HELPERS
# =============================================================================
def load_bankroll_config() -> dict:
    if BANKROLL_CONFIG.exists():
        try: return json.loads(BANKROLL_CONFIG.read_text())
        except Exception: pass
    return {"starting_bankroll": 1500.0, "min_stake": 10.0,
            "max_stake": 500.0, "max_drawdown_pct": 25.0, "kelly_fraction": "Moderate"}

def save_bankroll_config(cfg: dict): BANKROLL_CONFIG.write_text(json.dumps(cfg, indent=2))

def load_model_config() -> dict:
    if MODEL_CONFIG.exists():
        try: return json.loads(MODEL_CONFIG.read_text())
        except Exception: pass
    return {"model_confidence": 1.0, "edge_threshold_pct": 4.5,
            "injury_penalty_pct": 5.0, "form_factor": 0.5, "odds_weight": 0.5,
            "max_underdog_odds": MAX_UNDERDOG_ODDS}

def save_model_config(cfg: dict): MODEL_CONFIG.write_text(json.dumps(cfg, indent=2))

# =============================================================================
# RSS
# =============================================================================
def fetch_rss_headlines(urls: list) -> list:
    out = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            out.extend(e.title for e in feed.entries[:8])
        except Exception: continue
    return out[:15]

def detect_injury_alert(headline: str) -> bool:
    return any(kw in (headline or "").lower() for kw in RISK_KEYWORDS)

# =============================================================================
# DISPLAY HELPERS
# =============================================================================
def _ev_color(v) -> str:
    try:
        v = float(v)
    except Exception:
        return ""
    if v > 0.05: return "ev-green"
    if v > 0:    return "ev-yellow"
    return "ev-red"

def _fmt_cell(col: str, val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return '<span style="color:#475569;">—</span>'
    cl = col.lower()
    if "velocity" in cl:
        s = str(val)
        if "🔥" in s or "steaming" in s.lower(): return f'<span style="color:#ef4444;font-weight:700;">{s}</span>'
        if "❄️" in s or "fading" in s.lower():   return f'<span style="color:#60a5fa;font-weight:600;">{s}</span>'
        return f'<span style="color:#94a3b8;">{s}</span>'
    try:
        v = float(val)
        if "ev+" in cl or cl == "ev":
            colour = "#22c55e" if v > 0.05 else "#f59e0b" if v > 0 else "#ef4444"
            return f'<span style="color:{colour};font-weight:700;">{v:+.4f}</span>'
        if "edge" in cl:
            colour = "#22c55e" if v >= 4.5 else "#f59e0b" if v > 0 else "#ef4444"
            return f'<span style="color:{colour};">{v:+.2f}%</span>'
        if "odds" in cl:  return f'<span style="color:#00D9FF;font-weight:600;">{v:.2f}</span>'
        if "stake" in cl: return f'<span style="color:#a78bfa;font-weight:600;">C${v:.2f}</span>'
        if "prob" in cl:  return f'{v:.1f}%'
        if "books" in cl: return f'<span style="color:#64748b;">{int(v)}</span>'
        return f'{v:.3f}'
    except (TypeError, ValueError):
        s = str(val)
        if col in ("Match","match"):    return f'<span style="color:#f1f5f9;font-weight:700;">{s}</span>'
        if col in ("_date","Date"):     return f'<span style="color:#00D9FF;font-size:12px;">{s}</span>'
        if col in ("Status","status"):
            colour = "#22c55e" if "live" in s.lower() else "#94a3b8"
            return f'<span style="color:{colour};font-size:12px;">{s}</span>'
        return f'<span style="color:#e2e8f0;">{s}</span>'

def _render_df(df: pd.DataFrame, cols: list):
    available = [c for c in cols if c in df.columns]
    if not available:
        st.warning("No displayable columns found."); return
    sub = df[available].copy()
    HEADER_COLOUR = "#94a3b8"; HEADER_BG = "#0f172a"
    ROW_BG = "#1e293b"; ROW_ALT_BG = "#162032"; BORDER = "#2d3748"
    display_names = {
        "_date": "Date", "AI Prob %": "AI Prob", "Stake (C$)": "Stake",
        "Time/Score": "Time / Score", "Home Odds": "Home @", "Away Odds": "Away @",
        "P1 Odds": "P1 @", "P2 Odds": "P2 @", "Line Velocity": "Line Move",
    }
    headers = "".join(
        f'<th style="padding:10px 14px;text-align:left;color:{HEADER_COLOUR};font-size:11px;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:0.5px;'
        f'border-bottom:2px solid {BORDER};white-space:nowrap;">{display_names.get(c,c)}</th>'
        for c in available
    )
    rows_html = ""
    for i, (_, row) in enumerate(sub.iterrows()):
        bg    = ROW_BG if i % 2 == 0 else ROW_ALT_BG
        cells = "".join(
            f'<td style="padding:9px 14px;border-bottom:1px solid {BORDER};white-space:nowrap;">'
            f'{_fmt_cell(c, row.get(c))}</td>' for c in available
        )
        rows_html += f'<tr style="background:{bg};">{cells}</tr>'
    st.markdown(
        f'<div style="overflow-x:auto;border-radius:8px;border:1px solid {BORDER};margin-bottom:12px;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:sans-serif;">'
        f'<thead><tr style="background:{HEADER_BG};">{headers}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True)

def _render_schedule(events: list, sport_filter: str = "All"):
    if not events:
        st.info("No upcoming events found."); return
    df = pd.DataFrame(events)
    if sport_filter != "All":
        df = df[df["Sport"].str.contains(sport_filter, case=False, na=False)]
    if df.empty:
        st.info(f"No upcoming {sport_filter} events found."); return
    for date, group in df.groupby("Date"):
        try:   day_label = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d")
        except Exception: day_label = date
        st.markdown(f"### 📅 {day_label}")
        for _, row in group.iterrows():
            st.markdown(
                f"<div class='event-card'>"
                f"<div class='event-date'>{row.get('Sport','')} &nbsp;·&nbsp; {row.get('Time','TBD')}</div>"
                f"<div class='event-match'>{row.get('Match','')}</div></div>",
                unsafe_allow_html=True)

def _render_prediction_table(df: pd.DataFrame, sport: str):
    if df is None or df.empty:
        st.info(f"No {sport} predictions available."); return
    h_col = "Home Odds" if "Home Odds" in df.columns else "P1 Odds"
    a_col = "Away Odds" if "Away Odds" in df.columns else "P2 Odds"
    df_work = df.copy()
    df_work["_ev_sort"]  = pd.to_numeric(df_work.get("EV+"), errors="coerce").fillna(-99)
    df_work["_date_key"] = df_work.get("_date", df_work.get("_fetch_date","")).fillna("").astype(str)
    df_work = df_work.sort_values(["_date_key","_ev_sort"], ascending=[True, False])
    for date_key, group in df_work.groupby("_date_key", sort=False):
        try:   day_label = datetime.strptime(date_key, "%Y-%m-%d").strftime("%A, %B %d")
        except Exception: day_label = date_key or "TBD"
        st.markdown(
            f"<div style='margin:18px 0 8px;padding:6px 14px;background:#0f172a;"
            f"border-left:3px solid #00D9FF;border-radius:0 6px 6px 0;'>"
            f"<span style='font-size:13px;font-weight:700;color:#00D9FF;text-transform:uppercase;"
            f"letter-spacing:1px;'>📅 {day_label} &nbsp;·&nbsp; {len(group)} game{'s' if len(group)!=1 else ''}</span></div>",
            unsafe_allow_html=True)
        for _, row in group.iterrows():
            ev = row.get("EV+"); edge = row.get("Edge %"); stake = row.get("Stake (C$)")
            h_odds = row.get(h_col); a_odds = row.get(a_col)
            has_odds = pd.notna(h_odds) and pd.notna(a_odds)
            ev_cls   = _ev_color(ev) if has_odds else "ev-yellow"
            odds_str = (f"Odds: <b>{h_odds:.2f}</b> / <b>{a_odds:.2f}</b>" if has_odds
                        else "⏳ Odds not yet available")
            ev_str   = (f"EV+ <span class='{ev_cls}'>{ev:+.4f}</span> &nbsp;|&nbsp; Edge {edge:+.2f}%"
                        if has_odds and ev is not None else "<span class='ev-yellow'>EV pending odds</span>")
            stake_str = (f"&nbsp;|&nbsp; Stake: <b>C${stake:.2f}</b>"
                         if has_odds and stake and stake > 0 else "")
            pitcher_str = ""
            if sport == "MLB":
                ph = row.get("Home Pitcher","TBD"); pa = row.get("Away Pitcher","TBD")
                pitcher_str = f"<div style='font-size:11px;color:#94a3b8;margin-top:4px;'>SP: {ph} vs {pa}</div>"
            tour_str = ""
            if sport == "Tennis":
                tour_str = f"<div style='font-size:11px;color:#94a3b8;'>{row.get('Tournament','')} — {row.get('Category','')}</div>"
            bet_tag = ""
            if has_odds:
                h_f = float(h_odds); a_f = float(a_odds)
                imp_sum = (1/h_f + 1/a_f) if h_f > 1 and a_f > 1 else 0
                if imp_sum < 0.95 or imp_sum > 1.25:
                    odds_str  = f"⚠️ Bad line ({h_f:.2f}/{a_f:.2f})"
                    ev_str    = "<span class='ev-red'>Corrupted odds — do not bet</span>"
                    stake_str = ""
                else:
                    home_t = row.get("Home Team", row.get("Match","? vs ?").split(" vs ")[0].strip())
                    away_t = row.get("Away Team", row.get("Match","? vs ?").split(" vs ")[-1].strip())
                    rec_team = row.get("Bet Team") or (home_t if h_f <= a_f else away_t)
                    rec_odds = row.get("Bet Odds")
                    rec_odds = float(rec_odds) if rec_odds not in (None, "") else (h_f if h_f <= a_f else a_f)
                    bet_tag  = (f"<span style='color:#00D9FF;font-weight:700;'>✅ BET ON: {rec_team} @ {rec_odds:.2f}x</span>"
                                if ev is not None and float(ev) > MIN_EV_THRESHOLD
                                else "<span style='color:#64748b;'>⛔ No edge — skip</span>")
                    odds_str = f"{bet_tag} &nbsp;|&nbsp; Lines: <b>{h_f:.2f}</b> / <b>{a_f:.2f}</b>"
            st.markdown(
                f"<div class='pred-card'>"
                f"<div class='pred-match'>{row.get('Match','')} "
                f"<span style='font-size:11px;color:#64748b;font-weight:400;margin-left:8px;'>"
                f"{row.get('Time/Score', row.get('Time','TBD'))}</span></div>"
                f"{tour_str}{pitcher_str}"
                f"<div style='font-size:13px;margin-top:6px;'>{odds_str}</div>"
                f"<div style='font-size:13px;margin-top:4px;'>{ev_str}{stake_str}</div></div>",
                unsafe_allow_html=True)

# =============================================================================
# KEY STATUS BANNER
# =============================================================================
def _key_status_banner():
    if not ODDS_API_KEY:
        st.error("❌ ODDS_API_KEY not set — add it to the top of main.py"); return
    try:
        resp = _session().get(f"{ODDS_API_BASE}/me/", headers={"x-api-key": ODDS_API_KEY},
                              verify=False, timeout=8)
        if resp.status_code == 200:
            info      = resp.json()
            remaining = info.get("requests_remaining", "?")
            used      = info.get("requests_used", "?")
            st.success(f"✅ TheOddsAPI connected — {used} used | {remaining} remaining")
        elif resp.status_code == 401:
            st.error("❌ Odds API key invalid or expired")
        else:
            st.error(f"❌ Odds API HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        st.error(f"❌ Odds API connection error: {e}")

# =============================================================================
# PAST GAME FILTER
# =============================================================================
def _filter_past_games(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "_start_iso" not in df.columns: return df
    now_utc = _TZ_UTC.localize(datetime.utcnow())
    def _is_future(iso: str) -> bool:
        try:
            naive = datetime.strptime(str(iso).replace("Z",""), "%Y-%m-%dT%H:%M:%S")
            return _TZ_UTC.localize(naive) >= now_utc
        except Exception:
            return True
    return df[df["_start_iso"].apply(_is_future)].reset_index(drop=True)

# =============================================================================
# SCHEDULE HELPERS
# =============================================================================
def _fetch_schedule_nba(days: int = 7) -> list:
    df = fetch_premium_odds("basketball_nba")
    if df.empty: return []
    seen = set(); events = []
    for _, row in df.iterrows():
        key = row.get("_event_id") or f"{row.get('Home Team','')}{row.get('Away Team','')}{row.get('_date','')}"
        if key not in seen:
            seen.add(key)
            events.append({"Date": row.get("_date",""), "Time": row.get("Time/Score","TBD"),
                           "Match": row.get("Match",""), "Sport": "🏀 NBA"})
    return events

def _fetch_schedule_mlb(days: int = 7) -> list:
    df = fetch_premium_odds("baseball_mlb")
    if df.empty: return []
    seen = set(); events = []
    for _, row in df.iterrows():
        key = row.get("_event_id") or f"{row.get('Home Team','')}{row.get('Away Team','')}{row.get('_date','')}"
        if key not in seen:
            seen.add(key)
            events.append({"Date": row.get("_date",""), "Time": row.get("Time/Score","TBD"),
                           "Match": row.get("Match",""), "Sport": "⚾ MLB"})
    return events

def _fetch_schedule_tennis(days: int = 7) -> list:
    seen = set(); events = []
    df = fetch_premium_odds("tennis")
    if df.empty: return []
    for _, row in df.iterrows():
        key = row.get("_event_id") or f"{row.get('Match','')}{row.get('_date','')}"
        if key not in seen:
            seen.add(key)
            events.append({"Date": row.get("_date",""), "Time": row.get("Time/Score","TBD"),
                           "Match": row.get("Match",""), "Sport": "🎾 Tennis"})
    return events

# =============================================================================
# MAIN
# =============================================================================
def main():
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=AUTO_REFRESH_INTERVAL_SEC * 1000, key="auto_refresh_ticker")
    except ImportError:
        st.markdown(
            f"<meta http-equiv='refresh' content='{AUTO_REFRESH_INTERVAL_SEC}'>",
            unsafe_allow_html=True)

    defaults = {
        "last_paper_trade": datetime.now() - timedelta(seconds=PAPER_TRADE_INTERVAL),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    model_cfg    = load_model_config()
    bankroll_cfg = load_bankroll_config()

    # Always defined regardless of whether Settings is locked/unlocked — the
    # data-fetch block below needs these no matter what. When Settings is
    # locked, these just use the saved config values; unlocking lets you
    # change them via the widgets below (which then get used for this run).
    bankroll   = float(bankroll_cfg.get("starting_bankroll", 1500.0))
    risk_level = bankroll_cfg.get("kelly_fraction", "Moderate")

    with st.expander("⚙️ Settings", expanded=False):
        if not st.session_state.get("settings_unlocked", False):
            pin_entry = st.text_input("Enter 4-digit code", type="password", max_chars=4, key="settings_pin_entry")
            if st.button("Unlock", key="settings_unlock_btn"):
                if pin_entry == SETTINGS_PIN:
                    st.session_state["settings_unlocked"] = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect code.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                bankroll   = st.number_input("Bankroll (C$)", min_value=1.0,
                                              value=bankroll, step=1.0)
            with c2:
                risk_level = st.radio("Kelly Risk Level", ["Safe","Moderate","Aggressive"],
                                       index=["Safe","Moderate","Aggressive"].index(risk_level))

            # These stay fixed at their defaults unless changed here — the model/edge
            # tuning controls were removed since they're not needed day to day.
            model_confidence    = model_cfg.get("model_confidence", 1.0)
            injury_penalty_pct  = model_cfg.get("injury_penalty_pct", 5.0)
            edge_threshold_pct  = model_cfg.get("edge_threshold_pct", MIN_EDGE_THRESHOLD)
            max_underdog_odds   = model_cfg.get("max_underdog_odds", MAX_UNDERDOG_ODDS)

            if st.button("💾 Save", width="stretch"):
                save_bankroll_config({
                    "starting_bankroll": bankroll,
                    "min_stake": bankroll_cfg.get("min_stake", 10.0),
                    "max_stake": bankroll_cfg.get("max_stake", 500.0),
                    "max_drawdown_pct": bankroll_cfg.get("max_drawdown_pct", 25.0),
                    "kelly_fraction": risk_level,
                })
                st.cache_data.clear()
                for key in ["data_nba","data_mlb","data_tennis","data_wnba","data_nhl","data_nfl","data_ncaaf","data_fetched_at"]:
                    st.session_state.pop(key, None)
                st.success("✅ Saved.")
                st.rerun()

            if st.button("🔒 Lock Settings", key="settings_lock_btn"):
                st.session_state["settings_unlocked"] = False
                st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    col_t, col_l = st.columns([4,1])
    with col_t:
        st.markdown("<h1 style='margin:0'>📈 Sports EV+ Dashboard</h1>", unsafe_allow_html=True)
        st.caption("NBA/WNBA · MLB · Tennis · NHL · NFL · NCAAF")
    with col_l:
        if st.button("🔄 Force Refresh Data", width="stretch"):
            st.cache_data.clear()
            for key in ["data_nba","data_mlb","data_tennis","data_wnba","data_nhl","data_nfl","data_ncaaf","data_fetched_at"]:
                st.session_state.pop(key, None)
            st.rerun()

    _key_status_banner()

    # ── Data fetch ────────────────────────────────────────────────────────────
    last_fetch_at = st.session_state.get("data_fetched_at")
    seconds_since_fetch = (datetime.now() - last_fetch_at).total_seconds() if last_fetch_at else None
    needs_fetch = last_fetch_at is None or seconds_since_fetch >= AUTO_REFRESH_INTERVAL_SEC

    if needs_fetch:
        prog = st.progress(0, text="📡 Connecting to Odds API…")
        try:
            max_stake_cap = bankroll_cfg.get("max_stake")

            nba_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/nba/news"])
            mlb_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/mlb/news"])
            tennis_hl = fetch_rss_headlines(["https://www.espn.com/espn/rss/tennis/news"])
            nhl_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/nhl/news"])
            nfl_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/nfl/news"])
            ncaaf_hl  = fetch_rss_headlines(["https://www.espn.com/espn/rss/ncf/news"])
            all_hl    = nba_hl + mlb_hl + tennis_hl + nhl_hl + nfl_hl + ncaaf_hl
            flagged_hl = flagged_injury_headlines(all_hl)
            st.session_state["_nba_hl"], st.session_state["_mlb_hl"], st.session_state["_tennis_hl"] = nba_hl, mlb_hl, tennis_hl
            st.session_state["_nhl_hl"], st.session_state["_nfl_hl"], st.session_state["_ncaaf_hl"] = nhl_hl, nfl_hl, ncaaf_hl

            prog.progress(10, text="🏀 Fetching NBA…")
            df_nba_raw = apply_injury_flags(fetch_premium_odds("basketball_nba"), flagged_hl, sport="NBA")
            st.session_state["data_nba"] = calculate_stakes(
                calculate_real_ev(df_nba_raw, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(20, text="🏀 Fetching WNBA (NBA off-season fill)…")
            df_wnba_raw = apply_injury_flags(fetch_premium_odds("basketball_wnba"), flagged_hl, sport="NBA")
            if df_nba_raw.empty and not df_wnba_raw.empty:
                st.session_state["data_nba"] = calculate_stakes(
                    calculate_real_ev(df_wnba_raw, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)
            elif not df_wnba_raw.empty:
                combined_bball = pd.concat([df_nba_raw, df_wnba_raw], ignore_index=True)
                st.session_state["data_nba"] = calculate_stakes(
                    calculate_real_ev(combined_bball, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(35, text="⚾ Fetching MLB…")
            df_mlb_raw = apply_injury_flags(fetch_premium_odds("baseball_mlb"), flagged_hl, sport="MLB")
            st.session_state["data_mlb"] = calculate_stakes(
                calculate_real_ev(df_mlb_raw, model_cfg, "MLB"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(50, text="🎾 Fetching Tennis…")
            df_tennis_raw = apply_injury_flags(fetch_premium_odds("tennis"), flagged_hl, sport="Tennis")
            if not df_tennis_raw.empty:
                dedupe_cols = ["_event_id"] if "_event_id" in df_tennis_raw.columns and df_tennis_raw["_event_id"].astype(bool).any() else ["Match","_date"]
                df_tennis_raw = df_tennis_raw.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)
            st.session_state["data_tennis"] = calculate_stakes(
                calculate_real_ev(df_tennis_raw, model_cfg, "Tennis"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(65, text="🏒 Fetching NHL…")
            df_nhl_raw = apply_injury_flags(fetch_premium_odds("icehockey_nhl"), flagged_hl, sport="NHL")
            st.session_state["data_nhl"] = calculate_stakes(
                calculate_real_ev(df_nhl_raw, model_cfg, "NHL"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(80, text="🏈 Fetching NFL…")
            df_nfl_raw = apply_injury_flags(fetch_premium_odds("americanfootball_nfl"), flagged_hl, sport="NFL")
            st.session_state["data_nfl"] = calculate_stakes(
                calculate_real_ev(df_nfl_raw, model_cfg, "NFL"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(90, text="🏈 Fetching NCAAF…")
            df_ncaaf_raw = apply_injury_flags(fetch_premium_odds("americanfootball_ncaaf"), flagged_hl, sport="NCAAF")
            st.session_state["data_ncaaf"] = calculate_stakes(
                calculate_real_ev(df_ncaaf_raw, model_cfg, "NCAAF"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            st.session_state["data_fetched_at"] = datetime.now()
            prog.progress(100, text="✅ Done!"); prog.empty()
        except Exception as e:
            prog.empty(); st.error(f"❌ Data fetch error: {e}")

    fresh_ts = st.session_state.get("data_fetched_at")
    if fresh_ts:
        age_min = int((datetime.now() - fresh_ts).total_seconds() / 60)
        st.caption(f"🕐 Data last refreshed {age_min} min ago (auto-refreshes every {AUTO_REFRESH_INTERVAL_SEC // 60} min) · Model: V5")

    df_nba    = _filter_past_games(st.session_state.get("data_nba",    pd.DataFrame()))
    df_mlb    = _filter_past_games(st.session_state.get("data_mlb",    pd.DataFrame()))
    df_tennis = _filter_past_games(st.session_state.get("data_tennis", pd.DataFrame()))
    df_nhl    = _filter_past_games(st.session_state.get("data_nhl",    pd.DataFrame()))
    df_nfl    = _filter_past_games(st.session_state.get("data_nfl",    pd.DataFrame()))
    df_ncaaf  = _filter_past_games(st.session_state.get("data_ncaaf",  pd.DataFrame()))

    # Auto paper trade
    if not df_nba.empty or not df_mlb.empty or not df_tennis.empty or not df_nhl.empty or not df_nfl.empty or not df_ncaaf.empty:
        if (datetime.now() - st.session_state.last_paper_trade).total_seconds() >= PAPER_TRADE_INTERVAL:
            _ok, _msg = execute_paper_trade(df_nba, df_mlb, df_tennis, df_nhl, df_nfl, df_ncaaf)
            st.session_state.last_paper_trade = datetime.now()

    # Auto-dedupe: run once per app session (not every rerun) to clean up any
    # duplicate PENDING rows left over from before execute_paper_trade had its
    # own dedup check, or from any other source of repeats. Cheap no-op once
    # the log is already clean.
    if not st.session_state.get("_auto_deduped_this_session", False):
        dedupe_pending_trades()
        st.session_state["_auto_deduped_this_session"] = True

    # ── TABS ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["🏆 Live Hub","🏀 NBA","⚾ MLB","🎾 Tennis","🏒 NHL","🏈 NFL","🏈 NCAAF","📊 Tracking"])

    # ── TAB 0: Live Hub ───────────────────────────────────────────────────────
    with tabs[0]:
        all_known_keys = set()
        for _df in [df_nba, df_mlb, df_tennis, df_nhl, df_nfl, df_ncaaf]:
            if _df is not None and not _df.empty:
                for _, _r in _df.iterrows():
                    _k = _r.get("_event_id") or _r.get("Match", "")
                    if _k: all_known_keys.add(_k)

        qualifying_now = find_top_bets(df_nba, df_mlb, df_tennis, df_nhl, df_nfl, df_ncaaf, n=50, per_sport_cap=50, hours=24)
        ledger = update_bet_ledger(qualifying_now, all_known_keys)
        # Show all currently-qualifying bets regardless of timing state (early,
        # good window, or starting soon) — update_bet_ledger already handles
        # auto-removal once a bet no longer qualifies at all (game started, or
        # it vanished from the odds feed entirely). Each entry's timing label
        # (bet_timing_status) is still shown per-row so you can see at a
        # glance which ones are in a stable "Good window" right now.
        ledger_entries = sorted(ledger.values(), key=lambda e: (e.get("edge") or 0), reverse=True)
        total_simultaneous = len(ledger_entries)

        if total_simultaneous > 1:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1a1f3a,#0f172a);border:2px solid #f59e0b;"
                f"border-radius:10px;padding:16px 20px;margin-bottom:16px;'>"
                f"<div style='font-size:11px;color:#f59e0b;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:6px;'>"
                f"🛡️ CAPITAL PROTECTION SHIELD ACTIVE</div>"
                f"<div style='font-size:20px;font-weight:700;color:#fbbf24;'>{total_simultaneous} Simultaneous Qualifying Bets (next 24h)</div>"
                f"<div style='font-size:13px;color:#e2e8f0;margin-top:8px;'>"
                f"Stakes auto-scaled by <b>÷√{total_simultaneous}</b> = <b>{1/(total_simultaneous**0.5):.3f}x</b> · 5% max per trade.</div>"
                f"</div>", unsafe_allow_html=True)

        top8 = ledger_entries[:4]

        st.markdown("<div class='metric-box'><div class='metric-title'>🏆 Top 4 Bets — Next 24 Hours</div>",
                    unsafe_allow_html=True)
        st.caption("⚠️ Odds shown were live at last refresh, not necessarily right now — always confirm the price on Rainbet matches before staking, especially on short favorites.")
        if top8:
            for i, entry in enumerate(top8):
                bet_team = entry.get("bet_team") or "?"
                bet_odds = float(entry.get("bet_odds") or 0)
                stake    = float(entry.get("stake") or 0)
                ev       = float(entry.get("ev") or 0)
                edge     = float(entry.get("edge") or 0)
                rank_color = "#00D9FF" if i == 0 else "#e2e8f0"
                timing_label, timing_color = bet_timing_status(entry.get("start_iso", ""))
                st.markdown(
                    f"<div style='background:#111827;border:1px solid #1e3a5f;border-radius:10px;"
                    f"padding:12px 18px;margin-bottom:8px;display:flex;justify-content:space-between;"
                    f"align-items:center;flex-wrap:wrap;gap:8px;'>"
                    f"<div><span style='font-size:11px;color:#64748b;font-weight:700;'>"
                    f"#{i+1} &nbsp;·&nbsp; {entry.get('sport','')} &nbsp;·&nbsp; {entry.get('date','')} {entry.get('time_str','')}"
                    f"&nbsp;·&nbsp; <span style='color:{timing_color};'>{timing_label}</span></span><br>"
                    f"<span style='font-size:16px;font-weight:800;color:{rank_color};'>✅ {bet_team}</span>"
                    f"<span style='font-size:13px;color:#94a3b8;'> &nbsp;·&nbsp; {entry.get('match','')}</span></div>"
                    f"<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
                    f"<span style='text-align:center;'><div style='font-size:10px;color:#64748b;text-transform:uppercase;'>Odds</div>"
                    f"<div style='font-size:15px;font-weight:700;color:#00D9FF;'>{bet_odds:.2f}x</div></span>"
                    f"<span style='text-align:center;'><div style='font-size:10px;color:#64748b;text-transform:uppercase;'>Edge</div>"
                    f"<div style='font-size:15px;font-weight:700;color:#22c55e;'>{edge:+.2f}%</div></span>"
                    f"<span style='text-align:center;'><div style='font-size:10px;color:#64748b;text-transform:uppercase;'>EV+</div>"
                    f"<div style='font-size:15px;font-weight:700;color:#22c55e;'>{ev:+.4f}</div></span>"
                    f"<span style='text-align:center;'><div style='font-size:10px;color:#64748b;text-transform:uppercase;'>Stake</div>"
                    f"<div style='font-size:15px;font-weight:700;color:#a78bfa;'>C${stake:.2f}</div></span>"
                    f"</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:16px;color:#94a3b8;padding:12px 0;'>No qualifying bets in the next 24 hours.</div>",
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.subheader("🏀 NBA Upcoming")
            if not df_nba.empty:
                _render_df(df_nba, ["Match","_date","Time/Score","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No NBA games found. Press 🔄 Refresh.")
        with c2:
            st.subheader("⚾ MLB Upcoming")
            if not df_mlb.empty:
                _render_df(df_mlb, ["Match","_date","Time/Score","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No MLB games found. Press 🔄 Refresh.")
        with c3:
            st.subheader("🎾 Tennis Today")
            if not df_tennis.empty:
                _render_df(df_tennis, ["Match","Time/Score","_date","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No tennis matches today.")
        with c4:
            st.subheader("🏒 NHL Upcoming")
            if not df_nhl.empty:
                _render_df(df_nhl, ["Match","_date","Time/Score","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No NHL games found. Press 🔄 Refresh.")
        with c5:
            st.subheader("🏈 NFL Upcoming")
            if not df_nfl.empty:
                _render_df(df_nfl, ["Match","_date","Time/Score","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No NFL games found. Press 🔄 Refresh.")
        with c6:
            st.subheader("🏈 NCAAF Upcoming")
            if not df_ncaaf.empty:
                _render_df(df_ncaaf, ["Match","_date","Time/Score","Home Odds","Away Odds","EV+","Stake (C$)","Line Velocity"])
            else:
                st.info("No NCAAF games found. Press 🔄 Refresh.")

        st.divider()
        st.subheader("📰 Injury & News Alerts")
        nba_hl    = st.session_state.get("_nba_hl", [])
        mlb_hl    = st.session_state.get("_mlb_hl", [])
        tennis_hl = st.session_state.get("_tennis_hl", [])
        nhl_hl    = st.session_state.get("_nhl_hl", [])
        nfl_hl    = st.session_state.get("_nfl_hl", [])
        ncaaf_hl  = st.session_state.get("_ncaaf_hl", [])
        all_hl    = nba_hl + mlb_hl + tennis_hl + nhl_hl + nfl_hl + ncaaf_hl
        alerts    = [h for h in all_hl if detect_injury_alert(h)]
        st.caption("These headlines also feed the model's Risk Meter — a heuristic keyword match, not a real injury-report feed.")
        for a in alerts[:6]: st.warning(f"⚠️ {a}")
        for h in [h for h in nba_hl    if not detect_injury_alert(h)][:3]: st.markdown(f"🏀 {h}")
        for h in [h for h in mlb_hl    if not detect_injury_alert(h)][:3]: st.markdown(f"⚾ {h}")
        if not alerts: st.success("✅ No injury alerts detected.")

    # ── TAB 1: NBA ────────────────────────────────────────────────────────────
    with tabs[1]:
        st.header("🏀 NBA — Upcoming Games")
        if not df_nba.empty:
            _render_df(df_nba, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                 "AI Prob %","Edge %","EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2,c3,c4 = st.columns(4)
            ev_v = pd.to_numeric(df_nba.get("EV+"), errors="coerce").dropna()
            c1.metric("Games",           len(df_nba))
            c2.metric("Avg EV+",         f"{ev_v.mean():.4f}" if not ev_v.empty else "—")
            c3.metric("Qualifying Bets", int((ev_v > MIN_EV_THRESHOLD).sum()))
            stk = pd.to_numeric(df_nba.get("Stake (C$)"), errors="coerce").fillna(0)
            c4.metric("Total Stake C$",  f"{stk.sum():,.2f}")
            if "_simultaneous_trades" in df_nba.columns:
                st.caption(f"🛡️ Covariance Shield: {df_nba['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.info("🏀 No upcoming NBA games found. Try Refresh.")

    # ── TAB 2: MLB ────────────────────────────────────────────────────────────
    with tabs[2]:
        st.header("⚾ MLB — Upcoming Games")
        st.caption(f"⚠️ MLB odds capped at {MLB_MAX_ODDS}x — heavy underdogs excluded (0% WR in backtesting above this line).")
        if not df_mlb.empty:
            _render_df(df_mlb, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                 "AI Prob %","Edge %","EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2,c3,c4 = st.columns(4)
            ev_v = pd.to_numeric(df_mlb.get("EV+"), errors="coerce").dropna()
            c1.metric("Games",           len(df_mlb))
            c2.metric("Avg EV+",         f"{ev_v.mean():.4f}" if not ev_v.empty else "—")
            c3.metric("Qualifying Bets", int((ev_v > MIN_EV_THRESHOLD).sum()))
            stk = pd.to_numeric(df_mlb.get("Stake (C$)"), errors="coerce").fillna(0)
            c4.metric("Total Stake C$",  f"{stk.sum():,.2f}")
            if "_simultaneous_trades" in df_mlb.columns:
                st.caption(f"🛡️ Covariance Shield: {df_mlb['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.info("⚾ No upcoming MLB games found. Press Refresh.")

    # ── TAB 3: Tennis ─────────────────────────────────────────────────────────
    with tabs[3]:
        st.header("🎾 Tennis — Today's Matches")
        if not df_tennis.empty:
            _render_df(df_tennis, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                    "EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2 = st.columns(2)
            c1.metric("Matches Today",   len(df_tennis))
            c2.metric("Qualifying Bets", int((pd.to_numeric(df_tennis.get("EV+"), errors="coerce") > MIN_EV_THRESHOLD).sum()))
            if "_simultaneous_trades" in df_tennis.columns:
                st.caption(f"🛡️ Covariance Shield: {df_tennis['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.error("🎾 No tennis matches returned. Key may not support tennis on this plan.")

    # ── TAB 4: NHL ────────────────────────────────────────────────────────────
    with tabs[4]:
        st.header("🏒 NHL — Upcoming Games")
        if not df_nhl.empty:
            _render_df(df_nhl, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                 "AI Prob %","Edge %","EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2,c3,c4 = st.columns(4)
            ev_v = pd.to_numeric(df_nhl.get("EV+"), errors="coerce").dropna()
            c1.metric("Games",           len(df_nhl))
            c2.metric("Avg EV+",         f"{ev_v.mean():.4f}" if not ev_v.empty else "—")
            c3.metric("Qualifying Bets", int((ev_v > MIN_EV_THRESHOLD).sum()))
            stk = pd.to_numeric(df_nhl.get("Stake (C$)"), errors="coerce").fillna(0)
            c4.metric("Total Stake C$",  f"{stk.sum():,.2f}")
            if "_simultaneous_trades" in df_nhl.columns:
                st.caption(f"🛡️ Covariance Shield: {df_nhl['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.info("🏒 No upcoming NHL games found. Try Refresh.")

    # ── TAB 5: NFL ────────────────────────────────────────────────────────────
    with tabs[5]:
        st.header("🏈 NFL — Upcoming Games")
        if not df_nfl.empty:
            _render_df(df_nfl, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                 "AI Prob %","Edge %","EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2,c3,c4 = st.columns(4)
            ev_v = pd.to_numeric(df_nfl.get("EV+"), errors="coerce").dropna()
            c1.metric("Games",           len(df_nfl))
            c2.metric("Avg EV+",         f"{ev_v.mean():.4f}" if not ev_v.empty else "—")
            c3.metric("Qualifying Bets", int((ev_v > MIN_EV_THRESHOLD).sum()))
            stk = pd.to_numeric(df_nfl.get("Stake (C$)"), errors="coerce").fillna(0)
            c4.metric("Total Stake C$",  f"{stk.sum():,.2f}")
            if "_simultaneous_trades" in df_nfl.columns:
                st.caption(f"🛡️ Covariance Shield: {df_nfl['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.info("🏈 No upcoming NFL games found. Try Refresh.")

    # ── TAB 6: NCAAF ──────────────────────────────────────────────────────────
    with tabs[6]:
        st.header("🏈 NCAAF — Upcoming Games")
        if not df_ncaaf.empty:
            _render_df(df_ncaaf, ["Match","Time/Score","_date","Home Odds","Away Odds",
                                   "AI Prob %","Edge %","EV+","Stake (C$)","Books","Line Velocity"])
            c1,c2,c3,c4 = st.columns(4)
            ev_v = pd.to_numeric(df_ncaaf.get("EV+"), errors="coerce").dropna()
            c1.metric("Games",           len(df_ncaaf))
            c2.metric("Avg EV+",         f"{ev_v.mean():.4f}" if not ev_v.empty else "—")
            c3.metric("Qualifying Bets", int((ev_v > MIN_EV_THRESHOLD).sum()))
            stk = pd.to_numeric(df_ncaaf.get("Stake (C$)"), errors="coerce").fillna(0)
            c4.metric("Total Stake C$",  f"{stk.sum():,.2f}")
            if "_simultaneous_trades" in df_ncaaf.columns:
                st.caption(f"🛡️ Covariance Shield: {df_ncaaf['_simultaneous_trades'].iloc[0]} simultaneous trades — stakes auto-scaled")
        else:
            st.info("🏈 No upcoming NCAAF games found. Try Refresh.")

    # ── TAB 7: Tracking ───────────────────────────────────────────────────────
    with tabs[7]:
        st.header("📊 Tracking")
        st.caption("Every bet the app has logged, plus manual grading and a backtest summary from graded results.")

        if not st.session_state.get("tracking_unlocked", False):
            pin_entry_tr = st.text_input("Enter 4-digit code", type="password", max_chars=4, key="tracking_pin_entry")
            if st.button("Unlock", key="tracking_unlock_btn"):
                if pin_entry_tr == SETTINGS_PIN:
                    st.session_state["tracking_unlocked"] = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect code.")
        else:
            with st.expander("✅ Grade Picks — enter real Rainbet results", expanded=True):
                st.caption(
                    "Picks don't auto-settle. Pick the match, enter what actually "
                    "happened on Rainbet, and it's saved permanently below.")
                pending = [t for t in load_paper_trades() if t.get("status") == "PENDING"]
                if pending:
                    pending_sorted = sorted(pending, key=lambda t: t.get("timestamp",""), reverse=True)
                    def _pick_label(t: dict) -> str:
                        bet_team = t.get("bet_team", "")
                        pick = f"✅ {bet_team}" if bet_team else "⚠️ pick not recorded"
                        return (f"{pick} — {t.get('match','?')} — {t.get('sport','')} "
                                f"@ {float(t.get('odds',0) or 0):.2f}x ({str(t.get('timestamp',''))[:16]})")
                    labels = [_pick_label(t) for t in pending_sorted]
                    sel_idx = st.selectbox("Pending pick", range(len(labels)),
                                            format_func=lambda i: labels[i], key="grade_pick_select")
                    sel_trade = pending_sorted[sel_idx]
                    gcol1, gcol2, gcol3, gcol4 = st.columns(4)
                    if gcol1.button("✅ WIN", key="grade_win", width="stretch"):
                        grade_trade_manually(sel_trade.get("id"), "WIN"); st.rerun()
                    if gcol2.button("❌ LOSS", key="grade_loss", width="stretch"):
                        grade_trade_manually(sel_trade.get("id"), "LOSS"); st.rerun()
                    if gcol3.button("➖ PUSH", key="grade_push", width="stretch"):
                        grade_trade_manually(sel_trade.get("id"), "PUSH"); st.rerun()
                    if gcol4.button("🚫 VOID", key="grade_void", width="stretch"):
                        grade_trade_manually(sel_trade.get("id"), "VOID"); st.rerun()
                else:
                    st.info("No pending picks waiting to be graded.")

            with st.expander("📊 Real Win Rate (manually graded only)", expanded=True):
                stats = calculate_success_rate()
                if stats["total"] > 0:
                    s1, s2, s3, s4 = st.columns(4)
                    s1.metric("Graded Bets", stats["total"])
                    s2.metric("Wins", stats["wins"])
                    s3.metric("Losses", stats["losses"])
                    s4.metric("Win Rate", f"{stats['success_rate']:.1f}%")
                    st.caption("Broken out by sport — helps confirm which market is actually the leak:")
                    by_sport = calculate_success_rate_by_group("sport")
                    if not by_sport.empty:
                        st.dataframe(by_sport, hide_index=True, width="stretch")
                else:
                    st.info("No graded picks yet. Grade some above to start building a real track record.")

            with st.expander("📈 Backtest Summary (settled trades)", expanded=True):
                st.caption("Computed from picks graded WIN/LOSS above — not a simulation, just your real logged results.")
                days_back = st.slider("Look back (days)", 1, 90, 30, key="backtest_days")
                bt = run_backtest(days=days_back)
                if "error" in bt:
                    st.info(bt["error"])
                else:
                    b1, b2, b3, b4 = st.columns(4)
                    b1.metric("Settled Trades", bt["total_trades"])
                    b2.metric("Win Rate",       f"{bt['win_rate']:.1f}%")
                    b3.metric("ROI (on stake)", f"{bt['roi']:+.2f}%")
                    b4.metric("Profit Factor",  f"{bt['profit_factor']:.2f}")
                    b5, b6, b7 = st.columns(3)
                    b5.metric("Avg Win (C$)",   f"{bt['avg_win']:.2f}")
                    b6.metric("Avg Loss (C$)",  f"{bt['avg_loss']:.2f}")
                    b7.metric("Total Stake (C$)", f"{bt['total_stake']:,.2f}")

            with st.expander("📋 All Logged Bets", expanded=True):
                st.caption(
                    "Every bet the app has recommended and logged in the background — "
                    "not necessarily what you actually placed on Rainbet. Grade real "
                    "results above. This resets if the app container restarts.")
                if st.button("🧹 Remove duplicate pending picks", key="dedupe_trades_btn"):
                    removed = dedupe_pending_trades()
                    if removed > 0:
                        st.success(f"✅ Removed {removed} duplicate pending row(s).")
                        st.rerun()
                    else:
                        st.info("No duplicates found.")
                trades = load_paper_trades()
                if trades:
                    try:
                        tdf = pd.DataFrame(trades)
                        col_order = ["timestamp","match","bet_team","sport","odds","ev_plus","stake",
                                     "edge_pct","strategy","result","status"]
                        tdf = tdf[[c for c in col_order if c in tdf.columns]]
                        tdf = tdf.rename(columns={
                            "timestamp":"Time","match":"Match","bet_team":"Pick","sport":"Sport","odds":"Odds",
                            "ev_plus":"EV+","stake":"Stake (C$)","edge_pct":"Edge %",
                            "strategy":"Strategy","result":"Result","status":"Status"})
                        for col in ["Odds","EV+","Stake (C$)","Edge %"]:
                            if col in tdf.columns:
                                tdf[col] = pd.to_numeric(tdf[col], errors="coerce")
                        tdf = tdf.sort_values("Time", ascending=False) if "Time" in tdf.columns else tdf
                        st.dataframe(tdf, hide_index=True, width="stretch",
                            column_config={
                                "EV+":        st.column_config.NumberColumn("EV+",        format="%.4f"),
                                "Stake (C$)": st.column_config.NumberColumn("Stake (C$)", format="%.2f"),
                                "Odds":       st.column_config.NumberColumn("Odds",       format="%.2f"),
                                "Edge %":     st.column_config.NumberColumn("Edge %",     format="%.2f"),
                            })
                        st.caption(f"{len(trades)} logged picks total")
                    except Exception as e:
                        st.error(f"❌ Log table failed to render: {e}")
                        st.caption("Falling back to plain table view:")
                        st.table(pd.DataFrame(trades))
                else:
                    st.info("No picks logged yet since the last restart.")
            if st.button("🔒 Lock Tracking", key="tracking_lock_btn"):
                st.session_state["tracking_unlocked"] = False
                st.rerun()

    st.divider()


if __name__ == "__main__":
    main()
