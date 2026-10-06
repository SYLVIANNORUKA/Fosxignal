# =============================================================================
#  SCANNER SETTINGS  —  edit these, then save the file.
#  The defaults match PA_Signals_Indicator.pine.
# =============================================================================

# Forex pairs to scan (no "=X", no slash).
PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD",
    "NZDUSD", "USDCHF", "EURJPY", "GBPJPY", "XAUUSD"
]

# Chart timeframes to scan. Allowed: "15M", "1H", "4H".
TIMEFRAMES = ["5M", "15M", "1H", "4H"]

# Which higher timeframe filters the trend for each chart timeframe.
# Allowed trend timeframes: "4H" or "1D". It must be HIGHER than the chart timeframe.
TREND_TIMEFRAME = {
    "15M": "4H",
    "1H":  "4H",
    "4H":  "1D",
}

# --- Trend filter ---
EMA_LENGTH = 50            # trend = last CLOSED higher-timeframe candle above/below this EMA

# --- Support / Resistance zones ---
SWING_LOOKBACK = 10        # bars on EACH side that a swing high/low must beat
MAX_ZONES = 3              # zones kept on each side (oldest dropped first)
ZONE_ATR_MULT = 0.5        # zone thickness = this x ATR(14)

# --- Patterns (True = on, False = off) ---
USE_ENGULFING = True
USE_PIN_BAR = True
USE_INSIDE_BAR = True
PIN_WICK_BODY_RATIO = 2.0  # pin bar: nose wick at least this many times the body
PIN_WICK_PERCENT = 60      # pin bar: nose wick at least this % of the whole candle

# --- Stop-loss / take-profit ---
SL_BUFFER_PIPS = 2.0       # stop-loss this many pips beyond the pattern's wick
RISK_REWARD = 2.0          # take-profit = risk x this (2.0 = 1:2)
COOLDOWN_BARS = 3          # minimum bars between two signals on the same chart

# --- Sending ---
# Ignore a signal if its candle closed more than this many minutes ago.
# Stops old signals being sent after a delayed or missed run.
MAX_LATE_MINUTES = 60
