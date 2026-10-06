# PA Signals: Beginner Setup Guide

This folder has two scripts:

| File | What it is | Use it for |
|---|---|---|
| `PA_Signals_Indicator.pine` | **Indicator**: shows signals and sends alerts, never trades | Everyday live use |
| `PA_Signals_Strategy.pine` | **Strategy**: the same logic, simulating trades at 1% risk | Backtesting in the Strategy Tester |

---

## 1. Paste the scripts into TradingView

Do this on a computer (tradingview.com in a browser, or the desktop app).

1. Log in to TradingView and open a chart (top menu: **Products → Supercharts**).
2. Click the **Pine Editor** tab at the very bottom of the screen.
3. In the Pine Editor, click the script name dropdown (top-left of the editor), then choose **Create new → Indicator**.
4. Select everything in the editor (**Ctrl + A**) and delete it.
5. Open `PA_Signals_Indicator.pine` in Notepad, select all (**Ctrl + A**), copy (**Ctrl + C**), and paste it into the Pine Editor (**Ctrl + V**).
6. Click **Save** and give it a name, for example `PA Signals`.
7. Click **Add to chart**. If you see red error text at the bottom of the editor, copy it and send it to me.

Repeat the same steps for the strategy:

- Choose **Create new → Strategy** in step 3.
- Paste `PA_Signals_Strategy.pine` in step 5.
- Save it as `PA Strategy`.

---

## 2. Add them to a chart

1. In the symbol box (top-left), type your pair, for example `EURUSD`, and pick one (OANDA or FXCM work well).
2. Set the timeframe (top bar) to **15m** or **1h**.
3. Click **Indicators** (top bar), open **My scripts** (sometimes called **Personal**), and click **PA Signals**.
4. To change settings, hover over the indicator's name at the top-left of the chart and click the **gear icon** ⚙.

**What you'll see:**

- **Green boxes** are support zones and **red boxes** are resistance zones.
- The **stepped line** is the 4H 50 EMA. It turns green in an uptrend and red in a downtrend.
- **BUY/SELL labels** show the pattern, Entry, SL, TP and risk in pips.
- On each signal, a **red line** marks the stop-loss, a **green line** the take-profit, and a **dotted grey line** the entry.
- The **table** in the top-right shows the current trend and the latest signal.

**Good to know:**

- A signal only appears **after the candle closes**. That is intentional, because it stops signals from appearing and then disappearing.
- Swing zones appear a few candles after the swing. Each swing needs 10 candles on its right side (the "Swing lookback" setting) before it counts.
- **Trend timeframe must be higher than your chart timeframe.** If it isn't, the table shows a ⚠ warning.
- Pips are worked out automatically: **0.0001** for normal forex pairs and **0.01** for JPY pairs. This works whether your data shows 4 or 5 decimals. The table shows the "Pip size" in use. On gold or indices, check it, and set "Pip size override" if needed.

---

## 3. Set up alerts on your phone

### A. Prepare your phone (one time only)

1. Install the **TradingView** app (App Store or Google Play).
2. Log in with the **same account** you use on the computer.
3. Allow notifications when the app asks. If you missed the prompt, go to your phone's **Settings → Notifications → TradingView** and turn them on.

### B. Create the alert (on the computer)

1. Open the chart with the pair and timeframe you want to watch, for example EURUSD 15m, with **PA Signals** added.
2. Click the **Alert** button (alarm-clock icon in the top bar) or press **Alt + A**.
3. Under **Condition**, choose **PA Signals**.
4. In the box below it, choose one of these:
   - **Any alert() function call** *(recommended)*. One alert covers both BUY and SELL, with neatly rounded prices and the pattern name.
   - Or **BUY signal**, then create a second alert for **SELL signal**.
5. **Trigger**: choose **Once per bar close**.
6. **Expiration**: set it as far ahead as your plan allows, or "Open-ended" if available.
7. Open the **Notifications** tab and tick **Notify in app** (this sends the phone push). Optionally tick **Send email** too.
8. Click **Create**.

Example message:

```
BUY EURUSD (15m) Pin Bar | Entry: 1.08452 | SL: 1.08311 | TP: 1.08734
```

With the BUY/SELL signal option, the timeframe shows in minutes ("15" or "60"), and the prices may show more decimal places.

**Important:**

- **Each alert watches one pair on one timeframe.** To watch EURUSD and GBPUSD, create one alert on each chart.
- An alert saves the settings the indicator had when you created it. **If you change any settings, delete the alert and create it again.**
- Free TradingView plans allow only a few active alerts. Paid plans allow more.
- To test the alert, temporarily switch to a 1-minute chart, create the alert there, and wait for a signal. Delete the test alert afterwards.

---

## 4. Read the Strategy Tester results

1. Add **PA Strategy** to a chart (Indicators → My scripts).
2. Click the **Strategy Tester** tab at the bottom of the screen.
3. If you want the chart to look cleaner, remove the indicator. Both scripts draw the same zones.

### Overview / Performance Summary — what the numbers mean

| Metric | Meaning | What to look for |
|---|---|---|
| **Net Profit** | Total profit or loss over the test | Positive. Compare it to the starting $10,000 |
| **Total Closed Trades** | How many trades happened | **At least 30–50** before you trust anything. Fewer trades means the result is mostly luck |
| **Percent Profitable** | Win rate | With 1:2 R:R you break even at about **34%**. Anything clearly above that is an edge |
| **Profit Factor** | Gross profit ÷ gross loss | Above **1.0** is profitable. Above **1.3–1.5** is decent |
| **Max Drawdown** | Biggest drop from a peak in account value | Lower is better. Ask yourself whether you could stomach this drop live |
| **Avg Trade** | Average profit per trade | Should be positive |
| **Avg # Bars in Trade** | How long trades last | Helps you plan screen time |

Other tabs:

- **List of Trades**: every trade with its entry, exit, profit and the reason it closed ("SL" or "TP"). Click a trade to jump to it on the chart.
- **Properties**: the test assumptions.

### Settings you can change (gear icon on PA Strategy → Properties tab)

- **Initial capital**: default $10,000.
- **Commission**: 0.004% per side, which is about 1 pip of spread per round trip on major pairs. Raise it for pairs with wider spreads (for example, 0.008 ≈ 2 pips).
- **Slippage**: leave it at **0**. TradingView measures slippage in "ticks", and a tick is 0.1 pip on some data feeds but a full pip on others, so it's easy to get it 10x wrong.

### The numbers next to trades on the chart are SIZE, not profit

A marker like **"TP +26315"** means "closed at take-profit, 26,315 units" (0.26 lot). It is **not** $26,315 of profit. The real profit of each trade is in the **List of Trades** tab. Each strategy BUY/SELL label also shows the risk in pips, the dollar risk and the size. With 1% risk, the dollar risk should be close to 1% of your current balance.

To hide those numbers: gear icon on PA Strategy → **Style** tab → untick **Quantity**.
- **Risk per trade**: in the **Inputs** tab. Default is 1%.

### Tips for an honest backtest

- **Test several pairs** (EURUSD, GBPUSD, USDJPY, AUDUSD) and both 15m and 1H. A strategy that only works on one pair is fragile.
- 15m charts only load a limited amount of history, so you may get few trades. 1H gives a longer test.
- Don't keep tweaking settings until the results look perfect. That's "curve fitting", and it usually fails live.
- The strategy ignores new signals while a trade is open. The indicator still shows them, so you may see a few more signals than trades.
- **Past results don't guarantee future results.** Forward-test on a **demo account** for a few weeks before risking real money.
