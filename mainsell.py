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
MIN_EDGE_THRESHOLD   = 4.5         # Fix 3: raised from 0.5 — 85% WR at 4.5%+ empirically
MLB_MAX_ODDS         = 1.90        # Fix 2: cap — 0% WR above this in sample data
KELLY_FRACTIONS      = {"Safe": 0.25, "Moderate": 0.50, "Aggressive": 0.75}
MAX_KELLY_PCT        = 0.20
CB_STAKE_MULTIPLIER  = 0.50

# Fix 7: Market-type allowlist — TheOddsAPI Premium can return multiple market
# types per event. "h2h" (a.k.a. "moneyline") settles on the FINAL result
# including overtime/extra innings. "1x2" / "3way" settle on REGULATION TIME
# ONLY (draw is a distinct, separate outcome) — a bet placed on that market
# auto-loses whenever the game goes to overtime, even if your side wins outright.
# This is a distinct market, not a data error, so it must be filtered at the
# market level, not inferred from the odds shape.
ALLOWED_BASKETBALL_MARKETS = {"h2h", "moneyline"}
BLOCKED_BASKETBALL_MARKETS = {"1x2", "3way", "three_way", "regulation_time"}

# Fix 6: Heavy-Favorite Trap — applied across ALL sports, not just MLB.
# Below this decimal price, one unexpected loss can erase ~10 wins worth of edge;
# risk:reward is too skewed to survive normal variance (esp. tennis early rounds).
# Raised 1.30 -> 1.50 after slip review showed losses clustering at 1.28-1.41
# (Golden State 1.28 L, Dallas 1.34 W, NY Liberty 1.34 L, Aces 1.41 L, 1.41 L)
# — 1.30 was not conservative enough to price out that cluster.
HEAVY_FAVORITE_FLOOR = 1.50

# Fix 18: LINE-DRIFT SAFETY BUFFER. The floor above was being checked against
# whatever price the dashboard fetched — cached up to 15 min, plus however
# long between you seeing it and actually placing it on Rainbet. A price
# that legitimately cleared 1.50 at fetch time can easily drift below it by
# the time you act on it, especially in tennis where lines move fast close
# to first serve (this is exactly how a 1.07 favorite made it through: the
# dashboard's snapshot was a real >=1.50 price at the time, it just moved
# before execution). This buffer requires bets to clear meaningfully more
# than the bare minimum, so ordinary drift doesn't put you back in the
# heavy-favorite danger zone by the time you actually stake it.
LINE_DRIFT_BUFFER = 0.15
EFFECTIVE_FAVORITE_FLOOR = HEAVY_FAVORITE_FLOOR + LINE_DRIFT_BUFFER   # 1.65

# Fix 24: HEAVY-UNDERDOG CEILING. Real graded Rainbet results (59 bets,
# Jul 10 - Aug 4) split by odds bucket:
#   <2.00 odds:  64.5% win rate (n=31)
#   2.00-3.00:   71.4% win rate (n=14)
#   3.00+:       14.3% win rate (n=14)   <- cliff, not a gentle decline
# The model's EV+ on long-shot picks was NOT translating into real wins —
# consistent with a classic long-shot bias: a small absolute miscalibration
# in win probability (e.g. modeling 12% when the true rate is closer to 6%)
# still produces a "positive" EV+ on paper because the payout multiplier is
# so large, while losing in reality almost every time. This caps how big an
# underdog price the dashboard will ever recommend, mirroring the existing
# heavy-favorite floor on the other end. Adjustable in Settings — this is a
# starting point from n=14 in the losing bucket, not a precisely calibrated
# number; revisit once more graded data exists above/below this line.
MAX_UNDERDOG_ODDS = 3.00

# Bounded, logged exception to the floor above — NOT a silent bypass. A bet
# below the floor can still qualify, but only if edge is large enough that it
# would survive being wrong ~1 time in 20, AND it's capped at 1 such bet/day
# and half stake (see find_top_bets / calculate_stakes). Treat a bet that only
# qualifies through this path as suspect calibration, not free money — the
# model overestimating a short-priced favorite is the most common failure
# mode for exactly this kind of bet.
HEAVY_FAVORITE_EV_EXCEPTION_THRESHOLD = 0.05   # EV+ must exceed this to bypass floor

# Fix 26: the exception above had NO lower bound on price at all — it only
# checked EV+ > 5%, so a model claiming high EV+ on an extreme price (a 1.10x
# actually got through) could bypass the floor entirely with no limit on how
# far. A short-priced favorite is exactly where the model is most likely to
# be overconfident. The exception is meant for "clears the floor by a little
# less than usual, but with strong edge" — not "any price at all."
EXCEPTION_MIN_ODDS = 1.35
HEAVY_FAVORITE_EV_EXCEPTION_MAX_PER_DAY = 1

MIN_COMPLETE_SETS_TENNIS = 2   # below this, treat result as retirement/walkover, not a "real" outcome


# Fix 1 dead-zone constants: 65-70% AI prob band was 24pp overestimated in backtesting
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

# Fix 13: how often the app re-fetches automatically, in seconds. Matches the
# underlying @st.cache_data TTL on fetch_premium_odds (900s) — no point
# refreshing the page more often than the odds cache itself updates.
AUTO_REFRESH_INTERVAL_SEC = 900

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

# Matches a squished trailing block like: "ET1.8415W107/106", "ET1.5415FORFEIT",
# "ET1.815L2/6 6/3 3/6". Groups: timezone, odds (decimal), stake (int), outcome
# letter (W/L), score (rest of string, possibly containing spaces/slashes), OR
# a non-standard outcome word (FORFEIT, RETIRED, VOID, WALKOVER, CASHOUT).
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
    """
    Untangle one squished raw-log line into a clean record.

    Handles the "data squishing" bug where timezone, odds, stake, outcome,
    and score run together with no delimiters (e.g. 'ET1.8415W107/106'),
    AND non-standard terminal states like 'ET1.5415FORFEIT' that have no
    score at all.

    IMPORTANT — irreducible ambiguity: odds are sometimes logged without a
    trailing zero (e.g. '1.8' instead of '1.80'), which makes the odds/stake
    boundary genuinely ambiguous from the digit string alone (e.g. '1.815L'
    could be 1.81 odds + stake 5, OR 1.8 odds + stake 15). If you bet with a
    flat stake (this log is flat-15 throughout), pass `known_stake` so the
    parser can pick the split that matches your real staking plan instead of
    guessing. Without it, the parser defaults to assuming 2-decimal odds.

    Returns None if the line doesn't match the expected shape (caller should
    log/skip rather than crash the whole batch).
    """
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
        # The 2-decimal-odds split didn't match your known flat stake — try
        # shifting one digit from odds to stake (covers '1.8' logged as '1.815...').
        combo = f"{g['odds']}{g['stake']}"  # re-fuse the raw digit run, e.g. "1.815"
        digits_before_dot, digits_after_dot = combo.split(".")
        # try every odds-length split and pick the one matching known_stake
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
        "outcome":   outcome,           # "W" / "L" / "FORFEIT" / "RETIRED" / ...
        "score":     score,             # e.g. "107/106", "6/1 6/3", or None
        "low_confidence_split": low_confidence,  # True = odds/stake boundary was ambiguous
        "raw_line":  line.strip(),
    }


def parse_raw_log_batch(lines: list[str], known_stake: float | None = None) -> pd.DataFrame:
    """Parse many raw log lines; rows that fail to parse are kept with a
    '_parse_failed' flag instead of being silently dropped, so you can see
    exactly which lines need a format tweak rather than losing data.
    Pass known_stake (e.g. 15.0 for a flat-stake bettor) to correctly resolve
    the odds/stake boundary on lines where odds lack a trailing zero."""
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
    """
    Fix 9: TheOddsAPI / Rainbet tennis feeds report names as 'Last, First'
    (e.g. 'Muchova, Karolina'); backtesting logs and most display contexts
    use 'First Last'. Converts the former to the latter. Names that don't
    match the 'Last, First' shape (no comma, or already 'First Last', or a
    multi-part name with extra commas/suffixes) are returned unchanged rather
    than mangled, since guessing wrong is worse than leaving it alone.
    """
    if not name or not isinstance(name, str):
        return name
    s = name.strip()
    if "," not in s:
        return s
    # Only handle the simple single-comma "Last, First" case; anything with
    # more than one comma (suffixes, multi-part names) is ambiguous — leave as-is.
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
    """Apply normalize_tennis_name to every 'Last, First' occurrence inside a
    larger string (e.g. a full slip line 'Muchova, Karolina vs Gauff, Coco'),
    without needing the names pre-split. Splits on ' vs ' when present."""
    if not text or not isinstance(text, str):
        return text
    if " vs " in text:
        parts = text.split(" vs ")
        return " vs ".join(normalize_tennis_name(p) for p in parts)
    return normalize_tennis_name(text)


def _normalize_player_key(match_str: str) -> str:
    """Order-independent key for 'A vs B' so 'A vs B' and 'B vs A' collide."""
    parts = [p.strip().lower() for p in _re.split(r"\s+vs\s+", str(match_str))]
    return "|".join(sorted(parts))


def dedupe_match_logs(df: pd.DataFrame, date_col: str = "date",
                       match_col: str = "match") -> pd.DataFrame:
    """
    Fix: Rain-Delay / Duplicate Logging Bug.

    When a suspended match gets re-logged under a later timestamp, the same
    fixture appears twice with different dates. This keeps only ONE row per
    fixture: the row with the LATEST date/time AND a fully-graded outcome
    (real W/L with a complete score), preferring that over an earlier
    in-progress/void/forfeit snapshot of the same match.
    """
    if df is None or df.empty:
        return df
    work = df.copy()
    work["_pkey"] = work[match_col].apply(_normalize_player_key)

    def _is_final(row) -> bool:
        outcome = str(row.get("outcome", "")).upper()
        return outcome in ("W", "L")

    work["_is_final"] = work.apply(_is_final, axis=1)
    work["_sort_dt"]  = pd.to_datetime(work.get(date_col), errors="coerce")

    # Prefer: final outcome first, then most recent date — so a later FORFEIT
    # snapshot doesn't get kept over an earlier completed result, and a final
    # result always wins over an unresolved/void duplicate either direction.
    work = work.sort_values(["_pkey", "_is_final", "_sort_dt"],
                             ascending=[True, False, False])
    deduped = work.drop_duplicates(subset="_pkey", keep="first")
    return deduped.drop(columns=["_pkey", "_is_final", "_sort_dt"]).reset_index(drop=True)


def _count_completed_sets(score: str | None) -> int:
    """Count finished sets in a tennis score string like '6/4 7/6' or '6/7 4/6'."""
    if not score:
        return 0
    sets = [s for s in str(score).split() if "/" in s]
    return len(sets)


def grade_with_sportsbook_rules(outcome: str, score: str | None,
                                 sport: str = "Tennis",
                                 grading_rule: str = "1st_set") -> dict:
    """
    Apply ACTUAL sportsbook grading rules instead of "ideal" outcomes.

    Rainbet (and similarly-ruled books) grade retirements/walkovers using a
    1st-ball or 1st-set action rule: if action started (or the 1st set
    finished) before the retirement, the bet still grades as a normal
    W/L on whoever was leading at that point — it is NOT voided.

    Args:
        outcome:      raw outcome token ("W","L","FORFEIT","RETIRED","WALKOVER","VOID")
        score:        score string, e.g. "0:0", "1:0", "6/4 3/1" (retired mid-set)
        sport:        sport label (only Tennis has set-based grading here)
        grading_rule: "1st_set" (must complete 1 full set to count) or
                      "1st_ball" (any action at all counts, even 0:0/1:0)

    Returns dict: {"graded_outcome": "W"/"L"/"VOID", "is_void": bool, "note": str}
    """
    outcome_u = (outcome or "").upper()
    sets_done = _count_completed_sets(score)

    if outcome_u in ("W", "L"):
        return {"graded_outcome": outcome_u, "is_void": False, "note": "Standard completed result."}

    if outcome_u in ("FORFEIT", "RETIRED", "WALKOVER"):
        if sport != "Tennis":
            return {"graded_outcome": "VOID", "is_void": True, "note": "Non-tennis retirement — treat as void by default."}

        if grading_rule == "1st_ball":
            # Rainbet-style: any action counted as a result, even 0:0/1:0 pre-match retirements.
            return {"graded_outcome": "W", "is_void": False,
                    "note": "1st-ball rule: book graded this as a live result despite early retirement; "
                            "do not void in backtest — it cost/won real money."}

        # "1st_set" rule: needs >=1 completed set to be a graded result, not a void.
        if sets_done >= 1:
            return {"graded_outcome": "W", "is_void": False,
                    "note": f"{sets_done} set(s) completed before retirement — books grade this live, not void."}
        return {"graded_outcome": "VOID", "is_void": True,
                "note": "No completed set before retirement — true void under 1st-set rule."}

    return {"graded_outcome": "VOID", "is_void": True, "note": f"Unrecognized outcome token: {outcome!r}"}


def apply_sportsbook_grading(df: pd.DataFrame, outcome_col: str = "outcome",
                              score_col: str = "score", sport_col: str = "sport",
                              grading_rule: str = "1st_set") -> pd.DataFrame:
    """Vectorized application of grade_with_sportsbook_rules across a trade log,
    so backtests reflect what Rainbet actually paid/took, not the 'ideal' result."""
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

# Fix 19: RAINBET PRICING HAIRCUT. The API polls major books (FanDuel,
# DraftKings, BetMGM, etc.) — Rainbet has never once appeared in the polled
# book list across every debug dump seen so far. The dashboard was showing
# best-of-market across those OTHER books, but you can only actually bet on
# Rainbet, which prices consistently worse. Real side-by-side examples:
#   Tabilo/Shelton:    dash 3.95 -> Rainbet 3.45  (12.7% worse)
#   Jodar/Musetti:     dash 1.54 -> Rainbet 1.51  ( 1.9% worse)
#   Portland Fire:     dash 3.75 -> Rainbet 3.60  ( 4.0% worse)
#   Washington Mystics:dash 2.40 -> Rainbet 2.26  ( 5.8% worse)
# All four moved the SAME direction (Rainbet always shorter) including two
# bets checked in the same batch/session — ruling out simple time-drift as
# the sole explanation. This is a rough correction from only 4 samples, not
# a precise calibration — it should be refined as more real examples come
# in. It leans slightly conservative (above the ~6% sample average) since
# the cost of under-correcting (false-positive edge that isn't really there
# on Rainbet) is worse than over-correcting (skipping a few real edges).
RAINBET_PRICING_HAIRCUT = 0.08

def apply_rainbet_haircut(decimal_odds: float) -> float:
    """Shaves the 'profit portion' of a decimal price proportionally, which
    mirrors how bookmaker margin actually works (unlike a flat subtraction,
    this can never push odds below 1.0 even on very short favorites)."""
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
    }
    sport_label = {
        "basketball_nba":  "NBA",
        "basketball_wnba": "WNBA",
        "baseball_mlb":    "MLB",
        "tennis":          "Tennis",
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
                # Fix 9: API returns tennis names as "Last, First" — normalize
                # to "First Last" so Match strings line up with backtesting logs.
                # IMPORTANT: keep home_raw/away_raw for matching against
                # outcome.name below, since the API's outcomes[].name field
                # still comes back as "Last, First" — matching against the
                # normalized name here silently zeroed out every tennis odds
                # lookup (best_h/best_a stayed 0.0, so every event got dropped
                # by the best_h<=1 filter and the tab showed "no matches").
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
                    # Explicit reject, not just "not h2h" — this is a regulation-time-only
                    # market that would auto-lose on any game that goes to overtime.
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

            # Fix 19: haircut the validated best-of-market price down toward a
            # realistic Rainbet-equivalent BEFORE it flows into EV/floor/stake
            # calculations, so those numbers reflect what you can actually get,
            # not a price from a book you can't bet on. Sanity check above runs
            # on the raw price first, since the haircut shouldn't mask genuinely
            # corrupted odds data.
            best_h = apply_rainbet_haircut(best_h)
            best_a = apply_rainbet_haircut(best_a)

            # event_id is the stable identity from the API — fall back to a
            # name-based key only if the API omits it, so dedupe/velocity
            # tracking doesn't silently break on a missing field.
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

    # Fix 4: sport-specific boosts — MLB halved to stop flat boost overvaluing dogs
    home_boost = {"NBA": 0.060, "MLB": 0.035, "Tennis": 0.055}.get(sport, 0.060)

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

        # Fix 17: injury/risk penalty now reads the side-specific risk fields
        # set by apply_injury_flags (_home_injury_risk / _away_injury_risk),
        # falling back to the old flat "Risk Meter" if those aren't present
        # (e.g. rows that never went through apply_injury_flags). The penalty
        # is applied to the FLAGGED side's own probability, not always home —
        # and >=90 (solo-sport flag) hits harder than >=65 (team-sport flag),
        # reflecting that one hurt tennis player usually decides the match
        # while one hurt bench player is diluted across a roster.
        #
        # Fix 22: the >=90 multiplier was 3.0x, which at the default 5%
        # injury_penalty_pct means a SINGLE ESPN RSS headline that fuzzy-
        # matches a player's last name could swing model_h by 15 points on
        # a coarse keyword-substring match (apply_injury_flags' own docstring
        # admits this "can false-flag on an unrelated headline sharing a
        # word"). Tennis is exactly where the losing streak concentrated
        # right after this went live. Reduced to 1.5x, AND hard-capped at 8
        # points absolute regardless of what injury_penalty_pct is set to —
        # so even if someone raises the base penalty later via Settings, one
        # noisy headline can no longer single-handedly flip a close match's
        # recommended side.
        _MAX_INJURY_SWING = 0.08   # hard ceiling, independent of injury_pen setting
        def _risk_penalty(risk: int) -> float:
            if risk >= 90: pct = injury_pen * 1.5
            elif risk >= 65: pct = injury_pen
            elif risk >= 35: pct = injury_pen * 0.5
            else: return 0.0
            return min(pct, _MAX_INJURY_SWING)

        if "_home_injury_risk" in row.index or "_away_injury_risk" in row.index:
            home_risk = int(row.get("_home_injury_risk", 30) or 30)
            away_risk = int(row.get("_away_injury_risk", 30) or 30)
            model_h -= _risk_penalty(home_risk)     # home team's own player flagged -> hurts home
            model_h += _risk_penalty(away_risk)     # away team's player flagged -> helps home relatively
        else:
            risk = int(row.get("Risk Meter", 30))
            if risk >= 65:   model_h -= injury_pen
            elif risk >= 35: model_h -= injury_pen * 0.5

        # Confidence blend
        model_h = fair_h + (model_h - fair_h) * confidence
        model_h = max(0.02, min(0.98, model_h))

        # Fix 1: dead-zone calibration discount — 65-70% band overestimates by 24pp in sample
        if _DZ_LO <= model_h < _DZ_HI:
            model_h *= _DZ_DISCOUNT

        # Fix 5: MLB cliff-edge SP/bullpen penalty — danger zone where SP quality dominates
        if sport == "MLB" and 1.85 <= h_odds <= 2.10:
            model_h -= 0.04

        model_h = max(0.02, min(0.98, model_h))
        model_a = 1.0 - model_h   # binary market (no draw) — away is the complement

        # Fix 10: BOTH-SIDES EVALUATION. The model previously only ever priced
        # the home side (model_h vs h_odds), but downstream code (heavy-favorite
        # floor check, and the "BET ON: X" display) assumed whichever side was
        # CHEAPER was the recommended bet. Those two things silently disagreed
        # whenever the away team was the favorite: the floor filter tested the
        # away price, while EV+/Edge%/Stake were computed for the home side —
        # and if away "won" the display pick, the numbers shown next to it
        # weren't actually its numbers at all. Evaluate both sides for real and
        # pick whichever has the genuinely better edge; every downstream
        # consumer (floor filter, stake sizing, UI) now reads *_bet_side_*
        # fields instead of re-deriving a side from a raw odds comparison.
        ev_h   = model_h * (h_odds - 1) - (1.0 - model_h)
        ev_a   = model_a * (a_odds - 1) - (1.0 - model_a)
        edge_h = (model_h - imp_h) * 100
        edge_a = (model_a - imp_a) * 100

        home_t = row.get("Home Team", "")
        away_t = row.get("Away Team", "")

        if ev_h >= ev_a:
            bet_side, bet_prob, bet_price_v, bet_ev, bet_edge, bet_team = \
                "Home", model_h, h_odds, ev_h, edge_h, home_t
        else:
            bet_side, bet_prob, bet_price_v, bet_ev, bet_edge, bet_team = \
                "Away", model_a, a_odds, ev_a, edge_a, away_t

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
    """
    Fix 8: max_stake_cap is the hard dollar ceiling from bankroll_settings.json
    ("Max Stake (C$)"). Previously this setting was saved/displayed but never
    actually applied here — only the Kelly *percentage* was capped (5%), so on
    a large bankroll the dollar stake could still exceed what the user
    configured as their max. Now the dollar figure itself is clamped, after
    all other sizing (Kelly fraction, covariance shield, floor-exception
    halving) is applied. Pass None to skip the cap (falls back to pct-only
    behavior for backward compatibility).
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    # Fix 10 follow-through: stake sizing must be based on the side actually
    # being bet (df["Bet Odds"], set in calculate_real_ev), not always the
    # home price — otherwise Kelly sizing silently uses the wrong team's odds
    # whenever away was the recommended side.
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

            # Fix 2 follow-through: a bet that only qualified via the heavy-favorite
            # floor exception rides at half stake, same rule as the Underdog tab.
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
    """
    Quantifies why straight (single-game) Kelly bets beat the same legs combined
    into a parlay/combo bet — the leak flagged in the Rainbet slips.

    Args:
        legs: list of {"prob": true_win_probability (0-1), "odds": decimal_odds} per leg.
        bankroll, risk_level: same semantics as calculate_stakes.

    Returns a dict comparing: total stake risked, expected profit, and variance
    for (a) staking each leg straight with fractional Kelly vs (b) combining all
    legs into one parlay at the product odds/probability.
    """
    frac = KELLY_FRACTIONS.get(risk_level, 0.5)

    # --- Straight bets: independent fractional-Kelly stake per leg ---
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
        var   = (stake ** 2) * p * (1 - p) * (b + 1) ** 2  # win/loss payoff variance
        straight_stake_total += stake
        straight_ev_total    += ev
        straight_var_total   += var  # independent legs → variances add

    # --- Parlay: all legs must hit; odds multiply, probability multiplies ---
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
        sport_key = "basketball_nba" if sport == "NBA" else "baseball_mlb"
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
    """
    Fix 27: find_top_bets' filtering stages (time window, floor, ceiling,
    edge threshold) only ever printed their reasoning to server-side logs via
    print([DEBUG] ...) — logs a Streamlit Cloud user generally can't see from
    the app itself. That meant "why is Top Bets empty right now" was
    genuinely unanswerable from the UI alone; you had to take it on faith
    that the filtering was working correctly rather than being able to check.

    Read-only mirror of find_top_bets' filter stages, for display purposes
    only — does not affect what actually gets recommended. Returns a stage-
    by-stage count so a genuinely empty result (e.g. no game currently prices
    between the floor and ceiling with enough edge) is visibly distinguishable
    from a bug that's silently zeroing everything out.
    """
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
    """
    Fix 2 applied here: MLB rows with Home Odds > MLB_MAX_ODDS are excluded before ranking.
    """
    SPORT_CAPS = {"MLB": 2, "NBA": per_sport_cap, "Tennis": per_sport_cap}
    now_est    = datetime.now(_TZ_EASTERN)
    cutoff_est = now_est + timedelta(hours=hours)

    def _in_window(iso: str) -> bool:
        try:
            naive_utc = datetime.strptime(str(iso).replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            dt_est = _TZ_UTC.localize(naive_utc).astimezone(_TZ_EASTERN)
            return now_est <= dt_est <= cutoff_est
        except Exception:
            return False

    capped = []
    for df in dfs:
        if df is None or df.empty: continue

        if "_start_iso" in df.columns:
            df = df[df["_start_iso"].apply(_in_window)].copy()
        if df.empty: continue

        # Fix 2: MLB odds cap — exclude heavy dogs (0% WR above 1.90 in sample)
        # Fix 10: check the side actually being bet, not always Home Odds.
        sport_name = df["_sport"].iloc[0] if "_sport" in df.columns else "?"
        if sport_name == "MLB":
            price_col = "Bet Odds" if "Bet Odds" in df.columns else ("Home Odds" if "Home Odds" in df.columns else "P1 Odds")
            df = df[pd.to_numeric(df[price_col], errors="coerce").fillna(99) <= MLB_MAX_ODDS].copy()
        if df.empty: continue

        # Fix 6: Heavy-Favorite Trap — exclude prices below HEAVY_FAVORITE_FLOOR for
        # ALL sports (not just MLB).
        # Fix 10: this now floors the price of the side actually being bet
        # (df["Bet Odds"], from calculate_real_ev) — NOT min(home,away). The old
        # version tested whichever side happened to be cheaper, which frequently
        # wasn't the side the model's EV+/Edge% were even computed for (e.g. an
        # away favorite at 1.35 would kill the whole game even when the model's
        # real recommendation was a home underdog at 3.20 with genuine edge).
        # At 1.09–1.25 on the side you're ACTUALLY staking, you risk far more
        # than you can win; one unexpected upset erases ~10 winning bets' worth
        # of edge — but that only applies to the price you're really betting.
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

        # Fix 24: hard ceiling on underdog price — real graded results show a
        # cliff at 3.00+ (14.3% win rate vs 64-71% below it), not a gentle
        # decline, so this excludes those picks entirely rather than just
        # de-weighting them. Read from model_settings.json each call (not
        # threaded through the function signature) so the Settings panel's
        # slider takes effect immediately without touching every call site.
        max_dog_odds = float(load_model_config().get("max_underdog_odds", MAX_UNDERDOG_ODDS))
        over_ceiling_count = int((bet_price > max_dog_odds).sum())
        if over_ceiling_count:
            print(f"[DEBUG] {sport_name}: {over_ceiling_count} bet(s) excluded — "
                  f"odds above underdog ceiling ({max_dog_odds:.2f}x)")
        above_floor = above_floor[bet_price.loc[above_floor.index] <= max_dog_odds].copy()

        # Fix 16: exception admission is now tracked persistently across app
        # checks (see apply_floor_exception), not recalculated blind each call.
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
    """
    Fix 10: previously picked whichever of home/away had the higher price and
    filtered on df["EV+"] > 0 — but EV+ was computed for the home side only,
    so a game could get flagged as an "underdog play" on the away team's price
    while the EV+/edge shown was actually the home side's math. Now uses
    df["Bet Odds"]/df["Bet Team"] directly (set in calculate_real_ev), so the
    underdog price and the EV+ number are guaranteed to be about the same side.
    """
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

def execute_paper_trade(*dfs) -> tuple[bool, str]:
    top3 = find_top_bets(*dfs, n=3)
    if not top3:
        return False, "No qualifying bets found (EV+ > threshold + Edge ≥ 4.5% required)."
    trades = load_paper_trades()
    logged = []
    for best in top3:
        # Fix 10 follow-through: log the side actually being bet, not always home.
        bet_odds_v = best.get("Bet Odds")
        if bet_odds_v not in (None, ""):
            logged_odds = bet_odds_v
        else:
            h_col = "Home Odds" if pd.notna(best.get("Home Odds")) else "P1 Odds"
            logged_odds = best.get(h_col, 0) or 0
        trades.append({
            "id":           f"{best.get('Match','?')}_{datetime.now().strftime('%H%M%S')}",
            "timestamp":    datetime.now().isoformat(),
            "match":        best.get("Match", "Unknown"),
            # Fix 25: the log previously stored the Match string ("A vs B") but
            # never which side was actually recommended, so the Grade Picks
            # panel could only show the matchup, not the pick — no way to know
            # which team to check the result for without opening the debug log.
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
        logged.append(f"{best.get('Bet Team','?')} — {best.get('Match','?')} (EV+ {float(best.get('EV+',0)):+.4f})")
    save_paper_trades(trades)
    return True, f"✅ Logged {len(logged)} trade(s): " + " | ".join(logged)

def grade_trade_manually(trade_id: str, result: str) -> bool:
    """
    Fix 21: REAL OUTCOME GRADING. settle_pending_trades() previously "graded"
    every pending pick with a random.random() coin-flip weighted by the
    model's OWN predicted probability — meaning the "Recommendation Log" was
    never actually measuring whether picks won or lost, it was just measuring
    whether Python's RNG agreed with the model about itself. That number was
    guaranteed to drift toward the model's self-assessment no matter how bad
    the model actually was, and could never surface a real problem.

    This replaces it: result is entered by hand from the actual Rainbet slip
    (WIN / LOSS / PUSH / VOID), keyed by the trade's stable id. Only trades
    matching trade_id are touched. Returns True if a matching PENDING (or
    already-graded, re-gradable) row was found and updated.
    """
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
    """Win rate broken out by sport, strategy, or any other logged column —
    lets you see e.g. 'Tennis underdog picks are the leak' instead of one
    blended number that hides which bet type is actually losing."""
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
    """
    Fix 16: the "1 exception per day" cap was being recalculated from
    scratch on every single find_top_bets() call, with no memory of which
    bet (if any) had already used that slot. Combined with the sticky bet
    ledger, that meant a DIFFERENT below-floor bet could win the "exception"
    on a later refresh and get added ALONGSIDE the earlier one instead of
    replacing it — so the daily cap of 1 could silently become 3 or 4 over
    the course of a day of checks. This now persists which event(s) have
    actually used the slot, per sport, per calendar day, to a small file —
    so re-checking the app never grants a second exception, and an
    already-admitted exception keeps being recognized (not re-evaluated
    against the cap) as long as it's the SAME event.
    """
    if below_floor is None or below_floor.empty:
        return None
    ev_below = pd.to_numeric(below_floor.get("EV+"), errors="coerce")
    price_col = "Bet Odds" if "Bet Odds" in below_floor.columns else (
        "Home Odds" if "Home Odds" in below_floor.columns else "P1 Odds")
    price_below = pd.to_numeric(below_floor.get(price_col), errors="coerce")
    # Fix 26: hard absolute floor on the exception path itself — EV+ alone is
    # no longer sufficient to bypass the floor at any price.
    candidates = below_floor[(ev_below > HEAVY_FAVORITE_EV_EXCEPTION_THRESHOLD) &
                              (price_below >= EXCEPTION_MIN_ODDS)].copy()
    if candidates.empty:
        return None
    candidates = candidates.sort_values("EV+", ascending=False)

    log = load_exception_log()
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Keep only today's entries so the file doesn't grow forever
    log = {today_str: log.get(today_str, {})}
    used_today = set(log[today_str].get(sport_name, []))

    admitted = []
    for _, row in candidates.iterrows():
        eid = row.get("_event_id") or row.get("Match", "")
        if not eid:
            continue
        if eid in used_today:
            admitted.append(row)   # already-used exception -- keep recognizing it, not a new grant
            continue
        if len(used_today) < HEAVY_FAVORITE_EV_EXCEPTION_MAX_PER_DAY:
            admitted.append(row)
            used_today.add(eid)
        # else: today's cap for this sport is spent -- do not admit a new one

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
    """
    Fix 14: without this, the Top Bets list is recomputed from nothing on
    every single refresh cycle — a bet that qualified a moment ago can vanish
    on the very next refresh just because its edge dipped a fraction of a
    percent, even though nothing meaningful actually changed. That "appears
    then disappears" flicker is exactly what was reported.

    This makes qualification STICKY: once a bet clears the bar, it stays
    visible — with its EV/Edge/Stake numbers refreshed each cycle if the game
    is still live in the odds feed — until either (a) its start time passes,
    or (b) the event vanishes from the API entirely (postponed/pulled). It is
    NOT re-judged from zero on every refresh.
    """
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

    # Expire: game already started, OR the event no longer appears anywhere
    # in the latest full fetch at all (postponed/pulled from the board).
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


def bet_timing_status(start_iso: str) -> tuple[str, str]:
    """
    Heuristic only — there's no real closing-line-value feed available here,
    so this is a rough "how much time do you have" indicator, not a
    scientifically-derived optimal-entry signal:
      - very early: line has more room to move, could firm up or drift
      - a few hours out: usually the most stable window to act
      - <30 min: closing fast, line may be thin/moving quickly
    """
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
    """Returns the lowercase text of headlines that matched RISK_KEYWORDS."""
    return {h.lower() for h in headlines if detect_injury_alert(h)}


def apply_injury_flags(df: pd.DataFrame, flagged_headlines: set, sport: str = "") -> pd.DataFrame:
    """
    Fix 15/17: Risk Meter was previously a hardcoded constant (30) for every
    single game, so the injury-penalty logic could never fire regardless of
    when you checked. Wired to the same RSS headlines already pulled for the
    Live Hub's news panel. Two follow-on problems fixed here:

    (a) SPORT-AWARE MAGNITUDE: a flat penalty treated a hurt tennis player
        the same as a hurt bench player on a 12-man roster. In a 1-on-1
        sport, the flagged player basically IS the match; in a team sport,
        one player is diluted across a full roster. Tennis now gets a much
        larger probability adjustment than team sports do.

    (b) SIDE-AWARE DIRECTION: previously ANY flag (home or away) reduced the
        HOME team's win probability, even when it was the AWAY team's player
        who was actually hurt — backwards half the time. Home and away are
        now tracked and penalized separately, in the correct direction.

    IMPORTANT caveat either way: this is a coarse heuristic, not a real
    injury-report API. It flags a team if the last significant word of its
    name (mascot, or a player's last name for tennis) appears in a headline
    that also matched RISK_KEYWORDS. ESPN's RSS feed is sparse, can lag real
    news by hours, and this substring match can both miss real news and
    occasionally false-flag on an unrelated headline sharing a word.
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    is_solo_sport = (sport == "Tennis")
    flagged_risk_level = 95 if is_solo_sport else 70   # solo sport: near match-deciding; team sport: diluted

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
    # Keep "Risk Meter" for display/back-compat, showing the worse of the two
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
                    # Fix 10: read the side the model actually priced, rather than
                    # re-guessing "whichever is cheaper" — those disagreed whenever
                    # the away team was the favorite but home had the real edge.
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
    # Fix 13: auto-refresh the app on a timer so data updates on its own —
    # no more relying on manually clicking Force Refresh. Prefers the
    # streamlit-autorefresh component (smooth, doesn't reset scroll position
    # or collapse expanders); falls back to a plain HTML meta-refresh if that
    # package isn't installed, which works but causes a full page reload.
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=AUTO_REFRESH_INTERVAL_SEC * 1000, key="auto_refresh_ticker")
    except ImportError:
        st.markdown(
            f"<meta http-equiv='refresh' content='{AUTO_REFRESH_INTERVAL_SEC}'>",
            unsafe_allow_html=True)
        st.caption(
            "ℹ️ Auto-refresh is using a basic page reload. For smoother "
            "refreshing that doesn't reset your scroll position, run: "
            "`pip install streamlit-autorefresh`")

    defaults = {
        "last_paper_trade": datetime.now() - timedelta(seconds=PAPER_TRADE_INTERVAL),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    model_cfg    = load_model_config()
    bankroll_cfg = load_bankroll_config()

    # ── Settings (in-page, sidebar removed) ─────────────────────────────────
    # Fix 23: this expander previously loaded model_cfg/bankroll_cfg from disk
    # but never displayed or let you edit either — model_settings.json was
    # completely invisible from the UI, and the bankroll input's default was
    # hardcoded to 1500.0 instead of reading bankroll_cfg["starting_bankroll"],
    # so load_bankroll_config()'s return value was fetched and silently
    # discarded. Given Streamlit Cloud wipes these JSON files on every
    # redeploy (ephemeral filesystem), there was previously NO way to notice
    # if either config had silently reverted to generic defaults. Both are
    # now visible and editable here, with the CURRENT live values shown
    # explicitly so a redeploy-triggered reset is obvious instead of silent.
    with st.expander("⚙️ Settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            # Fix 26: no artificial minimum — a real bankroll can be well under 100.
            bankroll   = st.number_input("Bankroll (C$)", min_value=1.0,
                                          value=float(bankroll_cfg.get("starting_bankroll", 1500.0)), step=1.0)
            risk_level = st.radio("Kelly Risk Level", ["Safe","Moderate","Aggressive"],
                                   index=["Safe","Moderate","Aggressive"].index(
                                       bankroll_cfg.get("kelly_fraction", "Moderate")))
        with c2:
            st.markdown(f"**All sports:** {'✅ Premium Odds API' if ODDS_API_KEY else '❌ ODDS_API_KEY missing'}")
            st.caption("NBA · MLB · Tennis ATP · Tennis WTA — all via The Odds API Premium")
        with c3:
            rainbet_multiplier = st.number_input(
                "Current Rainbet Multiplier (X)", min_value=1.01, max_value=50.0, value=1.90, step=0.05,
                help="Enter the live decimal odds from Rainbet.")
            st.caption("If Rainbet shows 1.85 on a game, enter 1.85 here.")
        st.caption(
            "📊 **Model calibration (static constants — not affected by JSON reset)**\n"
            f"Edge threshold: {MIN_EDGE_THRESHOLD}% | MLB cap: {MLB_MAX_ODDS}x | "
            f"Heavy-favorite floor: {HEAVY_FAVORITE_FLOOR}x, effective {EFFECTIVE_FAVORITE_FLOOR}x with drift buffer\n"
            "Dead-zone discount: 65–70% band → ×0.88\n"
            "Boosts: NBA 6% | MLB 3.5% | Tennis 5.5%"
        )

        st.divider()
        st.markdown("**🤖 Live model_settings.json values** — *this is the file that resets to generic "
                     "defaults on every redeploy; check this after any redeploy to confirm it wasn't silently wiped.*")
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            model_confidence = st.slider("Model Confidence", 0.5, 2.0,
                                          float(model_cfg.get("model_confidence", 1.0)), 0.05,
                                          help="1.0 = neutral. >1 amplifies the home-boost signal.")
        with mcol2:
            injury_penalty_pct = st.slider("Injury Penalty %", 1.0, 20.0,
                                            float(model_cfg.get("injury_penalty_pct", 5.0)), 0.5,
                                            help="Base probability reduction for a flagged team/player. "
                                                 "Tennis solo-sport flags apply up to 1.5x this, hard-capped at 8pts.")
        with mcol3:
            edge_threshold_pct = st.slider("Edge Threshold %", 1.0, 10.0,
                                            float(model_cfg.get("edge_threshold_pct", MIN_EDGE_THRESHOLD)), 0.5,
                                            help="Minimum edge vs. bookmaker to flag a qualifying bet.")
        with mcol4:
            max_underdog_odds = st.slider("Max Underdog Odds (ceiling)", 1.50, 10.0,
                                           float(model_cfg.get("max_underdog_odds", MAX_UNDERDOG_ODDS)), 0.10,
                                           help="Fix 24: real graded results show win rate falls off a cliff "
                                                "above 3.00x (14.3% vs 64-71% below it) — bets priced above this "
                                                "are excluded entirely, not just de-weighted.")
        save_col1, save_col2 = st.columns(2)
        if save_col1.button("💾 Save model_settings.json", width="stretch"):
            save_model_config({
                "model_confidence": model_confidence,
                "edge_threshold_pct": edge_threshold_pct,
                "injury_penalty_pct": injury_penalty_pct,
                "max_underdog_odds": max_underdog_odds,
                "form_factor": model_cfg.get("form_factor", 0.5),
                "odds_weight": model_cfg.get("odds_weight", 0.5),
            })
            # Without this, the already-cached odds data (computed with the OLD
            # model_cfg) would keep being shown until the next 15-min auto-refresh
            # cycle — the save would silently have no visible effect for up to
            # 15 minutes, which looks exactly like "the setting didn't work."
            st.cache_data.clear()
            for key in ["data_nba","data_mlb","data_tennis","data_wnba","data_fetched_at"]:
                st.session_state.pop(key, None)
            st.success("✅ Saved and recomputing now. Note: this file resets to defaults on "
                       "the NEXT redeploy — re-check after pushing any code change.")
            st.rerun()
        if save_col2.button("💾 Save bankroll_settings.json", width="stretch"):
            save_bankroll_config({
                "starting_bankroll": bankroll,
                "min_stake": bankroll_cfg.get("min_stake", 10.0),
                "max_stake": bankroll_cfg.get("max_stake", 500.0),
                "max_drawdown_pct": bankroll_cfg.get("max_drawdown_pct", 25.0),
                "kelly_fraction": risk_level,
            })
            st.cache_data.clear()
            for key in ["data_nba","data_mlb","data_tennis","data_wnba","data_fetched_at"]:
                st.session_state.pop(key, None)
            st.success("✅ Saved and recomputing now. Same redeploy-reset caveat applies.")
            st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    col_t, col_l = st.columns([4,1])
    with col_t:
        st.markdown("<h1 style='margin:0'>📈 Sports EV+ Dashboard</h1>", unsafe_allow_html=True)
        st.caption("NBA/WNBA · MLB · Tennis")
    with col_l:
        if st.button("🔄 Force Refresh Data", width="stretch"):
            # Wipes the @st.cache_data-backed fetch_premium_odds cache so a
            # stuck/stale response can never survive a click — clearing only
            # session_state (as before) left the underlying cache intact.
            st.cache_data.clear()
            for key in ["data_nba","data_mlb","data_tennis","data_wnba","data_fetched_at"]:
                st.session_state.pop(key, None)
            st.rerun()

    _key_status_banner()

    # ── Data fetch ────────────────────────────────────────────────────────────
    # Fix 13 follow-through: previously gated on calendar day, so once fetched
    # it wouldn't refresh again until midnight regardless of how stale the
    # 15-min-cached odds got. Now gated on elapsed time, matching the
    # auto-refresh ticker above, so it genuinely stays current all day without
    # needing a manual click.
    last_fetch_at = st.session_state.get("data_fetched_at")
    seconds_since_fetch = (datetime.now() - last_fetch_at).total_seconds() if last_fetch_at else None
    needs_fetch = last_fetch_at is None or seconds_since_fetch >= AUTO_REFRESH_INTERVAL_SEC

    if needs_fetch:
        prog = st.progress(0, text="📡 Connecting to Odds API…")
        try:
            max_stake_cap = bankroll_cfg.get("max_stake")

            # Fix 15: pull injury/news headlines ONCE per fetch cycle here (not
            # per-tab) so the same signal both flags risk for the model AND
            # feeds the Live Hub's news panel below — one fetch, two uses.
            nba_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/nba/news"])
            mlb_hl    = fetch_rss_headlines(["https://www.espn.com/espn/rss/mlb/news"])
            tennis_hl = fetch_rss_headlines(["https://www.espn.com/espn/rss/tennis/news"])
            all_hl    = nba_hl + mlb_hl + tennis_hl
            flagged_hl = flagged_injury_headlines(all_hl)
            st.session_state["_nba_hl"], st.session_state["_mlb_hl"], st.session_state["_tennis_hl"] = nba_hl, mlb_hl, tennis_hl

            prog.progress(15, text="🏀 Fetching NBA…")
            df_nba_raw = apply_injury_flags(fetch_premium_odds("basketball_nba"), flagged_hl, sport="NBA")
            st.session_state["data_nba"] = calculate_stakes(
                calculate_real_ev(df_nba_raw, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(30, text="🏀 Fetching WNBA (NBA off-season fill)…")
            df_wnba_raw = apply_injury_flags(fetch_premium_odds("basketball_wnba"), flagged_hl, sport="NBA")
            # Merge WNBA into NBA tab if NBA is empty (off-season)
            if df_nba_raw.empty and not df_wnba_raw.empty:
                st.session_state["data_nba"] = calculate_stakes(
                    calculate_real_ev(df_wnba_raw, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)
            elif not df_wnba_raw.empty:
                combined_bball = pd.concat([df_nba_raw, df_wnba_raw], ignore_index=True)
                st.session_state["data_nba"] = calculate_stakes(
                    calculate_real_ev(combined_bball, model_cfg, "NBA"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(55, text="⚾ Fetching MLB…")
            df_mlb_raw = apply_injury_flags(fetch_premium_odds("baseball_mlb"), flagged_hl, sport="MLB")
            st.session_state["data_mlb"] = calculate_stakes(
                calculate_real_ev(df_mlb_raw, model_cfg, "MLB"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            prog.progress(75, text="🎾 Fetching Tennis…")
            df_tennis_raw = apply_injury_flags(fetch_premium_odds("tennis"), flagged_hl, sport="Tennis")
            if not df_tennis_raw.empty:
                dedupe_cols = ["_event_id"] if "_event_id" in df_tennis_raw.columns and df_tennis_raw["_event_id"].astype(bool).any() else ["Match","_date"]
                df_tennis_raw = df_tennis_raw.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)
            st.session_state["data_tennis"] = calculate_stakes(
                calculate_real_ev(df_tennis_raw, model_cfg, "Tennis"), bankroll, risk_level, max_stake_cap=max_stake_cap)

            st.session_state["data_fetched_at"] = datetime.now()
            prog.progress(100, text="✅ Done!"); prog.empty()
        except Exception as e:
            prog.empty(); st.error(f"❌ Data fetch error: {e}")

    # Fix 13: always show how old the current numbers are, so staleness is
    # visible at a glance instead of a silent guess.
    fresh_ts = st.session_state.get("data_fetched_at")
    if fresh_ts:
        age_min = int((datetime.now() - fresh_ts).total_seconds() / 60)
        st.caption(f"🕐 Data last refreshed {age_min} min ago (auto-refreshes every {AUTO_REFRESH_INTERVAL_SEC // 60} min) · Model: V5")

    df_nba    = _filter_past_games(st.session_state.get("data_nba",    pd.DataFrame()))
    df_mlb    = _filter_past_games(st.session_state.get("data_mlb",    pd.DataFrame()))
    df_tennis = _filter_past_games(st.session_state.get("data_tennis", pd.DataFrame()))

    # ── Debug panel ───────────────────────────────────────────────────────────
    bypass_filters = st.checkbox(
        "🔧 Show all games (bypass implied-sum filter)",
        value=st.session_state.get("debug_bypass_filters", False),
        key="debug_bypass_filters",
    )
    if bypass_filters:
        for _sk in ["data_nba","data_mlb","data_tennis","data_fetched_at"]:
            st.session_state.pop(_sk, None)
        fetch_premium_odds.clear()

    with st.expander("🔍 Pipeline counts", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("NBA rows",    len(df_nba))
        c2.metric("MLB rows",    len(df_mlb))
        c3.metric("Tennis rows", len(df_tennis))

        # Fix 27: shows WHY the Top Bets list is empty (or isn't) instead of
        # requiring you to trust it — walks the same filter stages find_top_bets
        # uses (24h window → floor → ceiling → edge threshold) and reports the
        # count remaining after each one, plus the closest miss if nothing
        # qualifies, so a real "no games meet the bar right now" is visibly
        # different from a bug silently zeroing everything out.
        st.markdown("**Why Top Bets shows what it shows (next 24h):**")
        for label, df_s in [("NBA", df_nba), ("MLB", df_mlb), ("Tennis", df_tennis)]:
            sport_key = "MLB" if label == "MLB" else ("Tennis" if label == "Tennis" else "NBA")
            funnel = diagnose_qualification_funnel(df_s, sport_key, hours=24)
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            fc1.metric(f"{label}: in window", funnel["in_24h_window"])
            fc2.metric("MLB cap", funnel["after_mlb_cap"])
            fc3.metric("Above floor", funnel["above_floor"])
            fc4.metric("Below ceiling", funnel["below_ceiling"])
            fc5.metric("Qualifying", funnel["meets_edge_threshold"])
            if funnel["meets_edge_threshold"] == 0 and funnel["closest_miss"]:
                cm = funnel["closest_miss"]
                st.caption(f"Closest miss: {cm['match']} — edge {cm['edge_pct']:+.2f}% "
                           f"(needs ≥{cm['needed_edge_pct']}%), EV+ {cm['ev_plus']}")

        st.divider()
        for label, df_s in [("NBA", df_nba), ("MLB", df_mlb), ("Tennis", df_tennis)]:
            if df_s is not None and not df_s.empty and "EV+" in df_s.columns:
                cols_to_show = [c for c in ["Match","Home Odds","Away Odds","EV+","Edge %"] if c in df_s.columns]
                st.markdown(f"**{label} — sample EV+ values:**")
                st.dataframe(df_s[cols_to_show].head(3), hide_index=True, width="stretch")
        for label, sk in [("NBA","basketball_nba"),("MLB","baseball_mlb"),("Tennis","tennis")]:
            raw = st.session_state.get(f"debug_raw_event_{sk}")
            if raw:
                st.markdown(f"**{label} — first raw event:**")
                st.json(raw)

    # Auto paper trade
    if not df_nba.empty or not df_mlb.empty or not df_tennis.empty:
        if (datetime.now() - st.session_state.last_paper_trade).total_seconds() >= PAPER_TRADE_INTERVAL:
            _ok, _msg = execute_paper_trade(df_nba, df_mlb, df_tennis)
            # Fix 21: no auto-settle anymore. Picks stay PENDING until you
            # grade them by hand from the actual Rainbet result — see the
            # "Grade Picks" panel in the Recommendation Log below.
            st.session_state.last_paper_trade = datetime.now()

    # ── TABS ──────────────────────────────────────────────────────────────────
    tabs = st.tabs(["🏆 Live Hub","🏀 NBA","⚾ MLB","🎾 Tennis"])

    # ── TAB 0: Live Hub ───────────────────────────────────────────────────────
    with tabs[0]:
        # Fix 11: banner and list share one source of truth (still true here).
        # Fix 14: that source is now the STICKY LEDGER, not a raw live recompute
        # — a bet that qualified a cycle ago stays listed (numbers refreshed)
        # until it starts or vanishes from the feed, instead of flickering
        # in/out because its edge moved a fraction of a percent between runs.
        all_known_keys = set()
        for _df in [df_nba, df_mlb, df_tennis]:
            if _df is not None and not _df.empty:
                for _, _r in _df.iterrows():
                    _k = _r.get("_event_id") or _r.get("Match", "")
                    if _k: all_known_keys.add(_k)

        qualifying_now = find_top_bets(df_nba, df_mlb, df_tennis, n=50, per_sport_cap=50, hours=24)
        ledger = update_bet_ledger(qualifying_now, all_known_keys)
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
        c1, c2, c3 = st.columns(3)
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

        st.divider()
        st.subheader("📰 Injury & News Alerts")
        # Fix 15: reuse the SAME headline fetch already done this cycle for the
        # Risk Meter flagging above, instead of a second redundant RSS call.
        nba_hl    = st.session_state.get("_nba_hl", [])
        mlb_hl    = st.session_state.get("_mlb_hl", [])
        tennis_hl = st.session_state.get("_tennis_hl", [])
        all_hl    = nba_hl + mlb_hl + tennis_hl
        alerts    = [h for h in all_hl if detect_injury_alert(h)]
        st.caption("These headlines also feed the model's Risk Meter — a heuristic keyword match, not a real injury-report feed.")
        for a in alerts[:6]: st.warning(f"⚠️ {a}")
        for h in [h for h in nba_hl    if not detect_injury_alert(h)][:3]: st.markdown(f"🏀 {h}")
        for h in [h for h in mlb_hl    if not detect_injury_alert(h)][:3]: st.markdown(f"⚾ {h}")
        if not alerts: st.success("✅ No injury alerts detected.")

        st.divider()
        with st.expander("✅ Grade Picks — enter real Rainbet results", expanded=True):
            st.caption(
                "Fix 21: picks no longer auto-settle on a random-number coin-flip. "
                "Pick the match, enter what actually happened on Rainbet, and it's "
                "saved permanently to the graded record below.")
            pending = [t for t in load_paper_trades() if t.get("status") == "PENDING"]
            if pending:
                pending_sorted = sorted(pending, key=lambda t: t.get("timestamp",""), reverse=True)
                def _pick_label(t: dict) -> str:
                    bet_team = t.get("bet_team", "")
                    # Fix 25: rows logged before this fix have no bet_team saved —
                    # fall back to just the matchup rather than showing a blank pick.
                    pick = f"✅ {bet_team}" if bet_team else "⚠️ pick not recorded (pre-fix)"
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

        st.divider()
        with st.expander("📋 Recommendation Log (background auto-logged picks)", expanded=False):
            st.caption(
                "This is a passive record of what the app recommended in the background "
                "roughly every 20 minutes — not a record of what you actually bet on "
                "Rainbet. Grade real results in the panel above; this table just shows "
                "everything logged, including still-pending picks. Note: this file resets "
                "whenever the app container redeploys or restarts, so it won't show picks "
                "from before the last restart.")
            trades = load_paper_trades()
            if trades:
                try:
                    tdf = pd.DataFrame(trades)
                    col_order = ["timestamp","match","sport","odds","ev_plus","stake",
                                 "edge_pct","strategy","result","status"]
                    tdf = tdf[[c for c in col_order if c in tdf.columns]]
                    tdf = tdf.rename(columns={
                        "timestamp":"Time","match":"Match","sport":"Sport","odds":"Odds",
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

    st.divider()
    st.markdown(
        "<p style='text-align:center;font-size:12px;color:#555;'>"
        "📈 Sports EV+ Dashboard v2 &nbsp;|&nbsp; NBA · MLB · Tennis"
        " &nbsp;|&nbsp; Data: The Odds API &nbsp;|&nbsp; All amounts in CAD"
        "</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
