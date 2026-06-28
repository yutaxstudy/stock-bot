import yfinance as yf
import pandas as pd

TICKER = "7203.T"
SHORT_WINDOW = 25
LONG_WINDOW = 75
INITIAL_CASH = 1_000_000


def get_data():
    df = yf.download(TICKER, period="5y", interval="1d", auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["MA_short"] = df["Close"].rolling(SHORT_WINDOW).mean()
    df["MA_long"] = df["Close"].rolling(LONG_WINDOW).mean()

    return df.dropna()


def backtest(df):
    cash = INITIAL_CASH
    shares = 0
    buy_price = 0
    trades = []

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        today = df.iloc[i]

        price = today["Close"].item()

        prev_short = prev["MA_short"].item()
        prev_long = prev["MA_long"].item()
        today_short = today["MA_short"].item()
        today_long = today["MA_long"].item()

        # 買いシグナル
        if prev_short <= prev_long and today_short > today_long and shares == 0:
            shares = int(cash // price)
            cash -= shares * price
            buy_price = price
            trades.append(["BUY", today.name.date(), price, shares, cash])

        # 売りシグナル
        elif prev_short >= prev_long and today_short < today_long and shares > 0:
            cash += shares * price
            profit = (price - buy_price) * shares
            trades.append(["SELL", today.name.date(), price, shares, cash, profit])
            shares = 0
            buy_price = 0

    final_price = df.iloc[-1]["Close"].item()
    final_value = cash + shares * final_price

    return final_value, trades


def main():
    df = get_data()
    final_value, trades = backtest(df)

    print(f"銘柄: {TICKER}")
    print(f"初期資金: {INITIAL_CASH:,.0f}円")
    print(f"最終資産: {final_value:,.0f}円")
    print(f"損益: {final_value - INITIAL_CASH:,.0f}円")
    print(f"リターン: {(final_value / INITIAL_CASH - 1) * 100:.2f}%")
    print(f"取引回数: {len(trades)}回")

    print("\n取引履歴")
    for trade in trades:
        print(trade)


if __name__ == "__main__":
    main()