"""
Forex price-action SIGNAL scanner  -  a Python copy of PA_Signals_Indicator.pine.

It ONLY sends signals to Telegram. It never connects to a broker and never
places trades. You decide and place every trade yourself.

How to run it:
    python scanner.py              scan all pairs and send NEW signals to Telegram
    python scanner.py --test       send one test message to Telegram
    python scanner.py --backcheck  print the last 10 signals per pair and timeframe
                                   (to compare with TradingView). Sends nothing.
    python scanner.py --dry-run    scan and print what WOULD be sent. Sends nothing.

Settings are in config.py. Telegram details come from the environment variables
TELEGRAM_TOKEN and TELEGRAM_CHAT_ID (never written in the code).
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

import config

# File that remembers which signals were already sent, so none is sent twice.
SENT_FILE = Path(__file__).with_name("sent_signals.json")
KEEP_SENT_DAYS = 14

TF_MINUTES = {"15M": 15, "1H": 60, "4H": 240, "1D": 1440}
TREND_NAME = {"4H": "4H", "1D": "Daily"}

# TradingView's forex 4H and daily candles start at 17:00 New York time
# (the forex "day" starts then), so we build ours the same way.
NY = "America/New_York"
FX_DAY_START = pd.Timedelta(hours=17)


# =============================================================================
#  PAIR HELPERS
# =============================================================================
def pip_size(pair):
    """1 pip = 0.01 for JPY pairs, 0.0001 for every other pair (same as the Pine script)."""
    return 0.01 if pair.endswith("JPY") else 0.0001


def price_decimals(pair):
    """Prices are shown to a tenth of a pip: 3 decimals for JPY pairs, 5 for others."""
    return 3 if pair.endswith("JPY") else 5


# =============================================================================
#  INDICATOR MATHS  (written to match TradingView's ta.ema / ta.atr exactly)
# =============================================================================
def ema(values, length):
    """ta.ema: starts with a simple average of the first `length` values."""
    out = np.full(len(values), np.nan)
    if len(values) < length:
        return out
    alpha = 2 / (length + 1)
    out[length - 1] = values[:length].mean()
    for i in range(length, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def atr(high, low, close, length=14):
    """ta.atr: Wilder's average (RMA) of the true range."""
    tr = np.empty(len(close))
    tr[0] = high[0] - low[0]
    tr[1:] = np.maximum(high[1:] - low[1:],
                        np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    out = np.full(len(close), np.nan)
    if len(close) < length:
        return out
    out[length - 1] = tr[:length].mean()
    for i in range(length, len(close)):
        out[i] = (out[i - 1] * (length - 1) + tr[i]) / length
    return out


def is_swing_high(high, c, n):
    """ta.pivothigh: candle c's high is above the n candles on each side.
    (If an earlier candle has exactly the same high, it still counts.)"""
    return high[c] >= high[c - n:c].max() and high[c] > high[c + 1:c + n + 1].max()


def is_swing_low(low, c, n):
    """ta.pivotlow: candle c's low is below the n candles on each side."""
    return low[c] <= low[c - n:c].min() and low[c] < low[c + 1:c + n + 1].min()


# =============================================================================
#  DATA  (Yahoo Finance via yfinance)
# =============================================================================
def download(pair, interval, period):
    """Download candles, e.g. download("EURUSD", "1h", "1y"). Index = candle OPEN time in UTC."""
    df = yf.Ticker(pair + "=X").history(period=period, interval=interval, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"no {interval} data from Yahoo for {pair}")
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = df.index.tz_convert("UTC")
    # Drop odd rows Yahoo sometimes adds (e.g. a live tick stamped 10:37).
    step = 15 if interval == "15m" else 60
    df = df[df.index.minute % step == 0]
    df = df[~df.index.duplicated(keep="last")]
    # Round like a real price feed so comparisons (e.g. close >= open) match TradingView.
    return df.round(price_decimals(pair))


def to_ny(utc_times):
    """UTC times -> New York clock times (without timezone, for easy maths)."""
    return utc_times.tz_convert(NY).tz_localize(None)


def candle_start(ny_times, hours):
    """Start time (New York clock) of the 4H or daily candle each time falls in."""
    return (ny_times - FX_DAY_START).floor(f"{hours}h") + FX_DAY_START


def resample(df_1h, hours):
    """Build 4H (hours=4) or daily (hours=24) candles from 1H candles.
    Index = candle start, New York clock."""
    starts = candle_start(to_ny(df_1h.index), hours)
    return df_1h.groupby(starts).agg(Open=("Open", "first"), High=("High", "max"),
                                     Low=("Low", "min"), Close=("Close", "last"))


def add_trend(chart, htf, htf_hours):
    """Add trend_up / trend_down columns to a chart.

    Like the Pine script (request.security with [1] and lookahead_on), each chart
    candle uses the higher-timeframe candle BEFORE the one it is inside, i.e. the
    last fully CLOSED one. So the trend never changes after the fact (no repainting).
    """
    left = pd.DataFrame({"start": candle_start(pd.DatetimeIndex(chart["ny"]), htf_hours)})
    right = pd.DataFrame({"start": htf.index, "htf_close": htf["Close"].to_numpy(),
                          "htf_ema": ema(htf["Close"].to_numpy(), config.EMA_LENGTH)})
    left["start"] = left["start"].astype("datetime64[ns]")
    right["start"] = right["start"].astype("datetime64[ns]")
    # allow_exact_matches=False -> take the previous HTF candle, not the current one.
    merged = pd.merge_asof(left, right, on="start", direction="backward", allow_exact_matches=False)
    chart["trend_up"] = (merged["htf_close"] > merged["htf_ema"]).to_numpy()
    chart["trend_down"] = (merged["htf_close"] < merged["htf_ema"]).to_numpy()
    return chart


def load_charts(pair, now):
    """Return {timeframe: chart} for one pair. Each chart holds ONLY closed candles,
    with columns Open, High, Low, Close, open_utc, ny, trend_up, trend_down."""
    data_1h = download(pair, "1h", "1y")   # 1 year: plenty for the daily 50 EMA
    htf = {"4H": resample(data_1h, 4), "1D": resample(data_1h, 24)}
    charts = {}
    for tf in config.TIMEFRAMES:
        if tf == "4H":
            chart = resample(data_1h, 4)
            chart["ny"] = chart.index
            ambiguous = np.ones(len(chart), dtype=bool)   # DST change-over hour: pick summer time
            chart["open_utc"] = chart.index.tz_localize(NY, ambiguous=ambiguous,
                                                        nonexistent="shift_forward").tz_convert("UTC")
        elif tf in ("15M", "1H"):
            # Yahoo keeps only ~60 days of 15-minute data, which is plenty here.
            chart = download(pair, "15m", "60d") if tf == "15M" else data_1h.copy()
            chart["ny"] = to_ny(chart.index)
            chart["open_utc"] = chart.index
        else:
            raise ValueError(f"Unknown timeframe {tf!r} in config.TIMEFRAMES (use 15M, 1H or 4H)")
        chart = chart.reset_index(drop=True)

        # Keep CLOSED candles only - the candle still forming is ignored (no repainting).
        closed = chart["open_utc"] + pd.Timedelta(minutes=TF_MINUTES[tf]) <= now
        chart = chart[closed].reset_index(drop=True)

        trend_tf = config.TREND_TIMEFRAME[tf]
        if TF_MINUTES[trend_tf] <= TF_MINUTES[tf]:
            raise ValueError(f"Trend timeframe {trend_tf} must be higher than {tf}")
        charts[tf] = add_trend(chart, htf[trend_tf], 4 if trend_tf == "4H" else 24)
    return charts


# =============================================================================
#  SIGNAL LOGIC  (bar by bar, in the same order as the Pine script)
# =============================================================================
def pattern_names(engulf, pin, inside):
    names = [name for on, name in ((engulf, "Engulfing"), (pin, "Pin Bar"), (inside, "Inside Bar")) if on]
    return " + ".join(names)


def find_signals(chart, pair):
    """Walk through every closed candle and return all signals found, oldest first."""
    o = chart["Open"].to_numpy()
    h = chart["High"].to_numpy()
    l = chart["Low"].to_numpy()
    c = chart["Close"].to_numpy()
    trend_up = chart["trend_up"].to_numpy()
    trend_down = chart["trend_down"].to_numpy()
    a = atr(h, l, c, 14)
    n = config.SWING_LOOKBACK
    pip = pip_size(pair)
    sl_buffer = config.SL_BUFFER_PIPS * pip

    support, resistance = [], []   # zones, each stored as (bottom, top)
    last_signal_bar = None
    signals = []

    for i in range(len(c)):
        # --- 1. New S/R zone when a swing high/low is confirmed (n candles after it) ---
        if i >= 2 * n and not np.isnan(a[i - n]):
            s = i - n                                  # the swing candle
            zone_h = a[s] * config.ZONE_ATR_MULT
            if is_swing_high(h, s, n):
                resistance.append((h[s] - zone_h, h[s]))
                if len(resistance) > config.MAX_ZONES:
                    resistance.pop(0)                  # drop the oldest zone
            if is_swing_low(l, s, n):
                support.append((l[s], l[s] + zone_h))
                if len(support) > config.MAX_ZONES:
                    support.pop(0)

        if i >= 1:
            # --- 2. Candlestick patterns (i = this candle, i-1 = previous candle) ---
            body = abs(c[i] - o[i])
            rng = h[i] - l[i]
            up_wick = h[i] - max(o[i], c[i])
            dn_wick = min(o[i], c[i]) - l[i]
            prev_body = abs(c[i - 1] - o[i - 1])

            bull_engulf = (config.USE_ENGULFING and c[i] > o[i] and c[i - 1] < o[i - 1]
                           and c[i] >= o[i - 1] and o[i] <= c[i - 1] and body > prev_body)
            bear_engulf = (config.USE_ENGULFING and c[i] < o[i] and c[i - 1] > o[i - 1]
                           and c[i] <= o[i - 1] and o[i] >= c[i - 1] and body > prev_body)

            nose = rng * config.PIN_WICK_PERCENT / 100
            bull_pin = (config.USE_PIN_BAR and rng > 0 and dn_wick >= config.PIN_WICK_BODY_RATIO * body
                        and dn_wick >= nose and up_wick <= rng * 0.25)
            bear_pin = (config.USE_PIN_BAR and rng > 0 and up_wick >= config.PIN_WICK_BODY_RATIO * body
                        and up_wick >= nose and dn_wick <= rng * 0.25)

            inside = h[i] < h[i - 1] and l[i] > l[i - 1]
            bull_inside = config.USE_INSIDE_BAR and inside and c[i] > o[i]
            bear_inside = config.USE_INSIDE_BAR and inside and c[i] < o[i]

            # Pattern's extreme wick (two-candle patterns use both candles).
            bull_low = min(l[i], l[i - 1]) if (bull_engulf or bull_inside) else l[i]
            bear_high = max(h[i], h[i - 1]) if (bear_engulf or bear_inside) else h[i]

            # --- 3. Entry / SL / TP ---
            entry = c[i]
            buy_sl = bull_low - sl_buffer
            buy_tp = entry + (entry - buy_sl) * config.RISK_REWARD
            sell_sl = bear_high + sl_buffer
            sell_tp = entry - (sell_sl - entry) * config.RISK_REWARD

            # --- 4. Signal = pattern + at a zone + with the trend + cooldown passed ---
            # At support: the wick reached the zone and price closed back above its bottom.
            at_support = any(bull_low <= top and c[i] >= bottom for bottom, top in support)
            at_resistance = any(bear_high >= bottom and c[i] <= top for bottom, top in resistance)
            cooldown_ok = last_signal_bar is None or i - last_signal_bar > config.COOLDOWN_BARS

            buy = (cooldown_ok and trend_up[i] and (bull_engulf or bull_pin or bull_inside)
                   and at_support and entry > buy_sl)
            sell = (cooldown_ok and trend_down[i] and (bear_engulf or bear_pin or bear_inside)
                    and at_resistance and entry < sell_sl)

            if buy or sell:
                last_signal_bar = i
                signals.append({
                    "bar": i,
                    "open_utc": chart["open_utc"].iloc[i],
                    "direction": "BUY" if buy else "SELL",
                    "patterns": pattern_names(bull_engulf, bull_pin, bull_inside) if buy
                                else pattern_names(bear_engulf, bear_pin, bear_inside),
                    "entry": entry,
                    "sl": buy_sl if buy else sell_sl,
                    "tp": buy_tp if buy else sell_tp,
                    "risk_pips": (entry - buy_sl if buy else sell_sl - entry) / pip,
                    "trend": "Bullish" if buy else "Bearish",
                })

        # --- 5. Remove zones that price CLOSED through (broken support is no longer support) ---
        support = [z for z in support if not c[i] < z[0]]
        resistance = [z for z in resistance if not c[i] > z[1]]

    return signals


def format_message(pair, tf, sig):
    """e.g. 🔴 SELL EURUSD (1H) – Pin Bar | Entry: 1.12234 | SL: 1.12270 | TP: 1.12162 | Risk: 3.6 pips | 4H trend: Bearish"""
    d = price_decimals(pair)
    icon = "🟢" if sig["direction"] == "BUY" else "🔴"
    return (f"{icon} {sig['direction']} {pair} ({tf}) – {sig['patterns']} | "
            f"Entry: {sig['entry']:.{d}f} | SL: {sig['sl']:.{d}f} | TP: {sig['tp']:.{d}f} | "
            f"Risk: {sig['risk_pips']:.1f} pips | {TREND_NAME[config.TREND_TIMEFRAME[tf]]} trend: {sig['trend']}")


# =============================================================================
#  TELEGRAM
# =============================================================================
def telegram_settings():
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        sys.exit("ERROR: set the TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables (see README.md).")
    return token, chat_id


def send_telegram(text, token, chat_id):
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat_id, "text": text}, timeout=20)
    except requests.RequestException as e:
        # Don't print the request URL: it contains the bot token.
        raise RuntimeError(f"could not reach Telegram ({type(e).__name__})") from None
    if not r.ok:
        raise RuntimeError(f"Telegram refused the message: {r.status_code} {r.text}")


# =============================================================================
#  SENT-SIGNAL RECORD
# =============================================================================
def load_sent():
    try:
        return json.loads(SENT_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sent(sent):
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=KEEP_SENT_DAYS)
    sent = {k: v for k, v in sent.items() if pd.Timestamp(v) >= cutoff}   # forget old entries
    SENT_FILE.write_text(json.dumps(sent, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# =============================================================================
#  MODES
# =============================================================================
def scan(dry_run):
    token, chat_id = (None, None) if dry_run else telegram_settings()
    now = pd.Timestamp.now(tz="UTC")
    sent = load_sent()
    failed = 0
    found = 0

    for pair in config.PAIRS:
        try:
            charts = load_charts(pair, now)
        except Exception as e:
            print(f"[{pair}] skipped - {e}")
            failed += 1
            continue

        for tf, chart in charts.items():
            signals = find_signals(chart, pair)
            # Only a signal on the most recently CLOSED candle is new.
            if not signals or signals[-1]["bar"] != len(chart) - 1:
                continue
            sig = signals[-1]
            closed_at = sig["open_utc"] + pd.Timedelta(minutes=TF_MINUTES[tf])
            if now - closed_at > pd.Timedelta(minutes=config.MAX_LATE_MINUTES):
                print(f"[{pair} {tf}] signal on candle closed at {closed_at:%Y-%m-%d %H:%M} UTC is too old - not sent")
                continue
            key = f"{pair}|{tf}|{sig['open_utc']:%Y-%m-%d %H:%M}|{sig['direction']}"
            if key in sent:
                continue   # already sent on an earlier run

            message = format_message(pair, tf, sig)
            found += 1
            if dry_run:
                print("[dry run] " + message)
                continue
            send_telegram(message, token, chat_id)
            print("Sent: " + message)
            sent[key] = now.isoformat()
            save_sent(sent)   # save straight away so a later crash can't cause a repeat

    print(f"Done. {found} new signal(s). {failed} pair(s) failed.")
    if failed == len(config.PAIRS):
        sys.exit("ERROR: every pair failed to download.")


def backcheck():
    now = pd.Timestamp.now(tz="UTC")
    print("Last 10 signals per pair and timeframe. Times are candle OPEN times in UTC.")
    print("Tip: set TradingView's chart timezone to UTC to compare.\n")
    for pair in config.PAIRS:
        try:
            charts = load_charts(pair, now)
        except Exception as e:
            print(f"[{pair}] skipped - {e}\n")
            continue
        for tf, chart in charts.items():
            signals = find_signals(chart, pair)[-10:]
            print(f"=== {pair} {tf}  ({len(signals)} shown) ===")
            for sig in signals:
                print(f"  {sig['open_utc']:%Y-%m-%d %H:%M}  " + format_message(pair, tf, sig))
            print()


def main():
    parser = argparse.ArgumentParser(description="Forex price-action signal scanner (signals only, never trades).")
    parser.add_argument("--test", action="store_true", help="send one test message to Telegram")
    parser.add_argument("--backcheck", action="store_true", help="print the last 10 signals per pair/timeframe")
    parser.add_argument("--dry-run", action="store_true", help="scan and print, but send nothing")
    args = parser.parse_args()

    # Windows terminals may not show emojis by default.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.test:
        token, chat_id = telegram_settings()
        send_telegram("✅ Test from your forex signal scanner. Telegram is set up correctly!", token, chat_id)
        print("Test message sent.")
    elif args.backcheck:
        backcheck()
    else:
        scan(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
