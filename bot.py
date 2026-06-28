import yfinance as yf
import pandas as pd
from datetime import datetime
from pathlib import Path

TICKERS = [
    "7203.T",  # トヨタ
    "9432.T",  # NTT
    "9984.T",  # ソフトバンクG
    "6857.T",  # アドバンテスト
]

SHORT_WINDOW = 5
LONG_WINDOW = 25

LOG_FILE = Path("trade_log.csv")


def get_price_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True)

    if df.empty:
        raise ValueError("株価データを取得できませんでした。")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["MA_short"] = df["Close"].rolling(SHORT_WINDOW).mean()
    df["MA_long"] = df["Close"].rolling(LONG_WINDOW).mean()

    return df.dropna()


def judge_signal(df):
    prev = df.iloc[-2]
    latest = df.iloc[-1]

    prev_short = prev["MA_short"].item()
    prev_long = prev["MA_long"].item()
    latest_short = latest["MA_short"].item()
    latest_long = latest["MA_long"].item()
    latest_close = latest["Close"].item()

    if prev_short <= prev_long and latest_short > latest_long:
        signal = "BUY"
    elif prev_short >= prev_long and latest_short < latest_long:
        signal = "SELL"
    else:
        signal = "HOLD"

    return signal, latest_close


def save_logs(rows):
    df = pd.DataFrame(rows)

    if LOG_FILE.exists():
        df.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")


def main():
    rows = []

    for ticker in TICKERS:
        try:
            df = get_price_data(ticker)
            signal, price = judge_signal(df)

            print(f"{ticker}: {price:.2f} / {signal}")

            rows.append({
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ticker": ticker,
                "signal": signal,
                "price": price,
            })

        except Exception as e:
            print(f"{ticker}: エラー - {e}")

    if rows:
        save_logs(rows)


if __name__ == "__main__":
    main()