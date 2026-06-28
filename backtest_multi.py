import yfinance as yf
import pandas as pd

TICKERS = [
    "8035.T",  # 東京エレクトロン
    "6920.T",  # レーザーテック
    "6146.T",  # ディスコ
    "7735.T",  # SCREEN
    "6723.T",  # ルネサス
    "4063.T",  # 信越化学
    "3436.T",  # SUMCO
    "6963.T",  # ローム
    "285A.T",  # キオクシア
    "6526.T",  # ソシオネクスト
    "6525.T",  # KOKUSAI ELECTRIC
    "6521.T",  # オキサイド
    "6227.T",  # AIメカテック
    "6613.T",  # QDレーザ
]

SHORT_WINDOW = 25
LONG_WINDOW = 75
INITIAL_CASH = 1_000_000

FEE_RATE = 0.001
TAX_RATE = 0.20315
MAX_DRAWDOWN_LIMIT = 30


def get_data(ticker):
    df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["MA_short"] = df["Close"].rolling(SHORT_WINDOW).mean()
    df["MA_long"] = df["Close"].rolling(LONG_WINDOW).mean()

    return df.dropna()


def backtest(df):
    cash = INITIAL_CASH
    shares = 0
    buy_price = 0
    trade_count = 0

    max_value = INITIAL_CASH
    max_drawdown = 0

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        today = df.iloc[i]

        price = today["Close"].item()

        prev_short = prev["MA_short"].item()
        prev_long = prev["MA_long"].item()
        today_short = today["MA_short"].item()
        today_long = today["MA_long"].item()

        if prev_short <= prev_long and today_short > today_long and shares == 0:
            shares = int(cash // (price * (1 + FEE_RATE)))
            cost = shares * price
            fee = cost * FEE_RATE
            cash -= cost + fee
            buy_price = price
            trade_count += 1

        elif prev_short >= prev_long and today_short < today_long and shares > 0:
            proceeds = shares * price
            fee = proceeds * FEE_RATE
            realized_profit = (price - buy_price) * shares

            tax = 0
            if realized_profit > 0:
                tax = realized_profit * TAX_RATE

            cash += proceeds - fee - tax
            shares = 0
            buy_price = 0
            trade_count += 1

        current_value = cash + shares * price

        if current_value > max_value:
            max_value = current_value

        drawdown = (max_value - current_value) / max_value * 100

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    final_price = df.iloc[-1]["Close"].item()
    final_value = cash + shares * final_price
    profit = final_value - INITIAL_CASH
    return_rate = (final_value / INITIAL_CASH - 1) * 100

    return final_value, profit, return_rate, trade_count, max_drawdown


def main():
    print("複数銘柄バックテスト")
    print("--------------------")

    results = []

    for ticker in TICKERS:
        try:
            df = get_data(ticker)
            final_value, profit, return_rate, trade_count, max_drawdown = backtest(df)

            results.append({
                "ticker": ticker,
                "final_value": final_value,
                "profit": profit,
                "return_rate": return_rate,
                "trade_count": trade_count,
                "max_drawdown": max_drawdown,
            })

            print(f"{ticker}")
            print(f"  最終資産: {final_value:,.0f}円")
            print(f"  損益: {profit:,.0f}円")
            print(f"  リターン: {return_rate:.2f}%")
            print(f"  取引回数: {trade_count}回")
            print(f"  最大下落率: {max_drawdown:.2f}%")
            
            if return_rate >= 50 and max_drawdown <= 50 and trade_count >= 5:
                print("  判定: 採用候補")
            else:
                print("  判定: 見送り")

        except Exception as e:
            print(f"{ticker}: エラー - {e}")

    result_df = pd.DataFrame(results)
    result_df.to_csv("backtest_result.csv", index=False, encoding="utf-8-sig")

    print("--------------------")
    print("結果を backtest_result.csv に保存しました。")


if __name__ == "__main__":
    main()