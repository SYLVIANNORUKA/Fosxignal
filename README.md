# Forex Signal Scanner → Telegram

A Python copy of the **PA Signals** TradingView indicator (`PA_Signals_Indicator.pine`). It scans forex pairs on the **5M, 15M, 1H and 4H** timeframes and sends new signals to your phone through **Telegram**, and optionally by **email** (Gmail).

> ⚠️ **Signals only.** This scanner never connects to a broker and never places a trade. You decide and place every trade yourself.

Example message:

```
🔴 SELL EURUSD (15M) – Pin Bar | Entry: 1.12234 | SL: 1.12270 | TP: 1.12162 | Risk: 3.6 pips | 4H trend: Bearish
```

---

## What's in this folder

| File | What it does |
|---|---|
| `scanner.py` | The scanner |
| `config.py` | **Your settings**: pairs, timeframes, patterns on/off, R:R and so on |
| `requirements.txt` | The Python libraries it needs |
| `.github/workflows/scanner.yml` | Runs the scanner on GitHub every 5 minutes |
| `sent_signals.json` | Record of signals already sent, so nothing is sent twice. Updated automatically |
| `PA_Signals_*.pine`, `SETUP_GUIDE.md` | The TradingView scripts and their guide |

---

## How it decides on a signal (same rules as the Pine indicator)

| Rule | Setting |
|---|---|
| Trend filter | The last **closed** 4H candle above or below the 4H 50 EMA (for 5M, 15M and 1H charts). The 4H chart uses the **daily** 50 EMA instead |
| Support/resistance | Swing highs and lows with 10 candles on each side. 3 zones are kept on each side, each 0.5 × ATR(14) thick. A zone is removed once price **closes** through it |
| Patterns | Engulfing, pin bar (wick ≥ 2× body and ≥ 60% of the candle), inside bar. Each can be switched on or off |
| BUY | Bullish pattern touches support, closes back above it, and the trend is up |
| SELL | Bearish pattern touches resistance, closes back below it, and the trend is down |
| Stop-loss | 2 pips beyond the pattern's wick |
| Take-profit | 1:2 risk:reward |
| Cooldown | At least 3 candles between signals on the same chart |
| Pip size | 0.0001, or 0.01 for JPY pairs |
| Minimum stop (`MIN_RISK_PIPS`) | Signals with a smaller stop-loss are not sent: 5M = 5 pips, 15M = 6 pips, 1H and 4H = no minimum. TradingView has no such filter, so it still shows these signals |
| No repainting | Only the most recently **closed** candle of each timeframe can give a new signal. A signal is never sent twice |

All of these can be changed in `config.py`.

### Where the price data comes from

| Timeframe | Yahoo data used |
|---|---|
| 5M | 5-minute candles, last 30 days. Yahoo only keeps about 60 days of 5-minute data, so 30 days stays safely inside the limit |
| 15M | 15-minute candles, last 60 days |
| 1H | 1-hour candles, last year |
| 4H and daily | Built from the 1-hour candles. They start at 17:00 New York time, like TradingView's forex charts |

---

## Step 1: Create your Telegram bot (about 5 minutes)

1. Install **Telegram** on your phone and sign up.
2. In Telegram, search for **@BotFather** (it has a blue tick) and open the chat.
3. Send `/newbot`. Then:
   - Give the bot a display name, for example `My FX Signals`.
   - Give it a username ending in `bot`, for example `myfx_signals_123_bot`.
4. BotFather replies with a **token** that looks like `7123456789:AAH...xyz`. This is your **TELEGRAM_TOKEN**.
   - 🔒 Treat the token like a password. Never share it or put it in a file you upload.
5. Find your new bot in Telegram (search its username), open it, and press **Start**. Then send it any message, like `hi`.
6. Get your **chat ID**:
   - In a web browser, open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`, replacing `<YOUR_TOKEN>` with your token.
   - Look for `"chat":{"id":123456789`. That number is your **TELEGRAM_CHAT_ID**.
   - If the page shows `"result":[]`, send the bot another message and refresh.

---

## Step 2: Run it on your own computer (optional, good for testing)

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).
   - On Windows, tick **"Add Python to PATH"** during installation.
2. Open a terminal in this folder.
   - On Windows: open the folder in File Explorer, click the address bar, type `powershell` and press Enter.
3. Install the libraries:

   ```
   pip install -r requirements.txt
   ```

4. Set your Telegram details for this terminal window. You'll need to do this again each time you open a new window.

   **Windows (PowerShell):**

   ```powershell
   $env:TELEGRAM_TOKEN = "7123456789:AAH...xyz"
   $env:TELEGRAM_CHAT_ID = "123456789"
   ```

   **Mac / Linux:**

   ```bash
   export TELEGRAM_TOKEN="7123456789:AAH...xyz"
   export TELEGRAM_CHAT_ID="123456789"
   ```

   Optional, for email alerts (see [Email alerts](#optional-email-alerts-gmail) below):

   ```powershell
   $env:EMAIL_ADDRESS = "you@gmail.com"
   $env:EMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"
   $env:EMAIL_TO = "you@gmail.com"
   ```

   On Mac / Linux, use `export EMAIL_ADDRESS="you@gmail.com"` and so on.

5. Try it:

   | Command | What it does |
   |---|---|
   | `python scanner.py --test` | Sends one test message to Telegram, and a test email if email is set up. Check your phone and inbox |
   | `python scanner.py --dry-run` | Scans and prints what it would send, without sending |
   | `python scanner.py --backcheck` | Prints the last 10 signals per pair and timeframe (no Telegram needed) |
   | `python scanner.py` | The real scan: sends new signals to Telegram |

---

## Step 3: Run it automatically on GitHub (free, every 5 minutes)

GitHub can run the scanner for you in the cloud, so your computer doesn't need to stay on.

1. Create a free account at [github.com](https://github.com).
2. Click **+** (top-right) → **New repository**.
   - Give it a name, for example `fx-signals`.
   - Choose **Public**. Public repositories get unlimited free GitHub Actions minutes. A private repository would run out of its free 2,000 minutes a month in about a week, because the scanner runs about 7,500 times a month.
   - Your token stays secret either way, because it is stored as a secret in the next step and never in the files.
   - Click **Create repository**.
3. Upload the files:
   - Click **uploading an existing file**.
   - Drag in **everything in this folder, including the `.github` folder**.
   - Windows hides folders that start with a dot. If `.github` doesn't appear, in File Explorer click **View → Show → Hidden items**.
   - Click **Commit changes**.
   - Check that `.github/workflows/scanner.yml` appears in the repository. If it doesn't, click **Add file → Create new file**, type `.github/workflows/scanner.yml` as the name, paste in the file's contents and commit.
4. Add your Telegram details as **secrets**:
   - Go to the repository's **Settings → Secrets and variables → Actions → New repository secret**.
   - Add a secret with Name `TELEGRAM_TOKEN` and your token as the Secret.
   - Add a second secret with Name `TELEGRAM_CHAT_ID` and your chat ID as the Secret.
5. Allow the workflow to save its record of sent signals:
   - Go to **Settings → Actions → General → Workflow permissions**.
   - Choose **Read and write permissions** and click **Save**.
6. Test it:
   - Open the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
   - Click **Forex signal scanner** → **Run workflow** → **Run workflow**.
   - After about a minute, click the run to see its log. "Done. 0 new signal(s)" is normal: most candles have no signal.

From then on it runs **every 5 minutes, Sunday to Friday**, 1 minute after each 5-minute candle closes (:01, :06, :11 … UTC). Every run checks all four timeframes, and 15M, 1H and 4H candles always close on one of these 5-minute marks.

**Two runs never overlap.** The workflow has a *concurrency group*: if a run is still going when the next one is due, the new run waits until the first has finished. Each run also loads the very latest `sent_signals.json` when it starts, so a run that had to wait still knows what was just sent.

**Good to know:**

- ⚠️ **GitHub's timing isn't exact.** Scheduled runs often start a few minutes late, and some are skipped when GitHub is busy. Each run only looks at the **most recently closed** candle. So if a run is late by more than 5 minutes, a **5M** signal from the candle before is never sent. 15M, 1H and 4H signals are rarely affected, because the next run usually happens before their next candle closes. If you rely on 5M signals, run the scanner on your own computer as well (Step 2), for example every 5 minutes with Windows Task Scheduler. Your computer and GitHub each keep their own `sent_signals.json` and don't share it. So when both catch the same signal, it arrives twice: once from each.
- Signals whose candle closed more than 60 minutes ago are not sent (`MAX_LATE_MINUTES` in `config.py`).
- GitHub pauses scheduled workflows in a repository that has had **no activity for 60 days**. If your messages stop, open the Actions tab and re-enable the workflow.
- When a signal is sent, the bot commits an updated `sent_signals.json` to your repository. Those commits are expected.
- To change settings, edit `config.py` on GitHub (click the file, then the ✏️ pencil icon), then **Commit changes**.
- To stop the scanner: **Actions → Forex signal scanner → ⋯ → Disable workflow**.

---

## Optional: Email alerts (Gmail)

Each signal can also arrive as an email, with the signal as the subject line:

```
Subject: 🔴 SELL EURUSD (1H) – Pin Bar
```

The email body lists the entry, SL, TP, risk and trend on separate lines. Telegram keeps working as before. **Email is optional:** if the three email secrets aren't set, the scanner skips email and sends Telegram only.

### A. Create a Gmail App Password (about 5 minutes)

An App Password is a special 16-letter password that only lets the scanner send email. Your real Gmail password is never used, and you can delete the App Password at any time.

1. **Turn on 2-Step Verification** (Google requires it before you can create App Passwords):
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security).
   - Under **How you sign in to Google**, click **2-Step Verification** and follow the steps. Skip this if it's already on.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and sign in again if asked.
3. Under **App name**, type `Forex scanner` and click **Create**.
4. Google shows a 16-letter password, like `abcd efgh ijkl mnop`. **Copy it now**, because Google only shows it once.
   - Spaces don't matter; the scanner removes them.
   - 🔒 Treat it like a password. Never put it in a file you upload.

If the App Passwords page says the setting isn't available, 2-Step Verification is not on yet (step 1). On a work or school account, your administrator may have blocked App Passwords. Use a personal Gmail account instead.

### B. Add the three email secrets on GitHub

Go to your repository's **Settings → Secrets and variables → Actions → New repository secret**, and add each of these:

| Name | Secret (what to paste) |
|---|---|
| `EMAIL_ADDRESS` | The Gmail address you created the App Password for, e.g. `you@gmail.com` |
| `EMAIL_APP_PASSWORD` | The 16-letter App Password from step A |
| `EMAIL_TO` | Where to send the alerts. Usually the same address. For several addresses, separate them with commas: `you@gmail.com,friend@example.com` |

The names must be typed **exactly** as shown, in capitals. The workflow already passes these secrets to the scanner, so no other change is needed. From the next run, each signal is also emailed.

### C. Test it

- **On GitHub:** go to **Actions → Forex signal scanner → Run workflow**. Open the run and click **Scan and send signals**. The log should show `Email alerts: on`. If it shows `off`, one of the three secrets is missing or misspelled. An email only arrives when there is a new signal.
- **On your computer:** set the three `EMAIL_...` variables (Step 2, point 4) and run `python scanner.py --test`. A test email should arrive within a minute. Check your **Spam** folder the first time, and mark it **Not spam**.

To turn email off again, delete the `EMAIL_APP_PASSWORD` secret on GitHub. You can also revoke the App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## Step 4: Compare with TradingView (`--backcheck`)

```
python scanner.py --backcheck
```

This prints the last 10 signals for every pair and timeframe, with the **candle open time in UTC**. To compare:

1. In TradingView, set the chart timezone to **UTC**: click the clock at the bottom-right of the chart, then choose **UTC**.
2. Open the same pair and timeframe, with **PA Signals** using the same settings as `config.py`.
   - For the 4H chart, set the indicator's **Trend timeframe** to **1D**.
3. Find each printed time on the chart and check the label is there.
   - Lines marked **[NOT SENT: stop below MIN_RISK_PIPS]** do appear on TradingView. The scanner just doesn't send them to Telegram.

**Small differences are normal, because the price data differs:**

- The scanner uses **Yahoo Finance** data. TradingView uses your chosen broker's feed, such as OANDA or FX. Candle highs and lows can differ by a fraction of a pip, which can create or remove a borderline signal.
- Your history starts at a different point, so an early swing zone or a cooldown can differ.
- In the rare case where two swing candles have exactly the same high or low, the scanner and TradingView may pick a different one.

Most signals should match. Many mismatches on one pair usually means the settings differ.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ERROR: set the TELEGRAM_TOKEN ...` | The environment variables or GitHub secrets are missing or misspelled |
| `Telegram refused the message: 401` | The token is wrong |
| `Telegram refused the message: 400 chat not found` | The chat ID is wrong, or you haven't pressed **Start** in your bot's chat |
| `Email alerts: off` in the log | One of `EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`, `EMAIL_TO` is missing or misspelled |
| `WARNING: email not sent (SMTPAuthenticationError ...)` | Wrong App Password, or `EMAIL_ADDRESS` isn't the account that created it. Create a new App Password and update the secret. Your normal Gmail password won't work here |
| Test email never arrives | Check the Spam folder and mark it **Not spam** |
| `[EURUSD] skipped - no data` | Yahoo had a temporary problem. The next run usually works |
| No messages for a long time | Usually normal, because signals need several conditions to line up. Check the Actions tab for red ❌ runs |
| Workflow fails at "Save sent-signal record" | Do Step 3, point 5 (Read and write permissions) |
