import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="株バックテストアプリ",
    layout="wide"
)

st.markdown(
    "<h1 style='text-align: center;'>株バックテストアプリ</h1>",
    unsafe_allow_html=True
)

# 銘柄グループ
group_col1, group_col2, group_col3, group_col4 = st.columns(4)

with group_col1:
    stock_group = st.selectbox(
        "銘柄グループ",
        ["半導体", "大型株", "高配当", "優待株"]
    )


st.markdown("### 取引の前提条件")

condition_col1, condition_col2, condition_col3, condition_col4 = st.columns(4)

with condition_col1:
    leverage = st.selectbox(
        "信用倍率",
        [1.0, 1.3, 1.5, 2.0],
        index=2,
        format_func=lambda x: f"{x:.1f}倍"
    )

with condition_col2:
    maintenance_rate = st.selectbox(
        "追証発生保証金率",
        [0.25, 0.30, 0.35],
        index=1,
        format_func=lambda x: f"{x:.0%}"
    )

with condition_col3:
    forced_liquidation_rate = st.selectbox(
        "強制決済保証金率",
        [0.15, 0.20, 0.25],
        index=1,
        format_func=lambda x: f"{x:.0%}"
    )


st.markdown("### 売買戦略")

strategy_col1, strategy_col2, strategy_col3, strategy_col4 = st.columns(4)

with strategy_col1:
    short_window = st.selectbox(
        "短期移動平均",
        [5, 10, 25, 50],
        index=2,
        format_func=lambda x: f"{x}日"
    )

with strategy_col2:
    long_window = st.selectbox(
        "長期移動平均",
        [25, 50, 75, 100, 200],
        index=2,
        format_func=lambda x: f"{x}日"
    )


st.markdown("### 採用条件")

adopt_col1, adopt_col2, adopt_col3, adopt_col4 = st.columns(4)

with adopt_col1:
    min_return = st.selectbox(
        "最低リターン",
        [0, 30, 50, 100],
        index=2,
        format_func=lambda x: f"{x}%"
    )

with adopt_col2:
    max_drawdown_limit = st.selectbox(
        "最大下落率",
        [30, 40, 50, 60],
        index=2,
        format_func=lambda x: f"{x}%"
    )

with adopt_col3:
    min_trade_count = st.selectbox(
        "最低取引回数",
        [1, 3, 5, 10, 20],
        index=2,
        format_func=lambda x: f"{x}回"
    )

with adopt_col4:
    max_forced_liquidation_count = st.selectbox(
        "許容する強制決済回数",
        [0, 1, 2, 3, 5],
        index=0,
        format_func=lambda x: f"{x}回"
    )


st.divider()

action_col1, action_col2, action_col3, action_col4 = st.columns(4)

with action_col1:
    only_adopted = st.checkbox("採用候補のみ表示")

INITIAL_CASH = 1_000_000
FEE_RATE = 0.001
TAX_RATE = 0.20315

GROUPS = {
    "半導体": [
        "8035.T", "6920.T", "6146.T", "7735.T", "6723.T",
        "4063.T", "3436.T", "6963.T", "285A.T", "6526.T",
        "6525.T", "6521.T", "6227.T", "6613.T",
    ],
    "大型株": [
        "7203.T", "6758.T", "9984.T", "8306.T", "9432.T",
        "6861.T", "7974.T", "6098.T", "4519.T", "8058.T",
    ],
    "高配当": [
        "2914.T", "4502.T", "5020.T", "8053.T", "8316.T",
        "8591.T", "8766.T", "9433.T", "9434.T", "9104.T",
    ],
    "優待株": [
        "4755.T", "8267.T", "9831.T", "4661.T", "2702.T",
        "3197.T", "3387.T", "7412.T", "8591.T", "9202.T",
    ],
}
TICKER_NAMES = {
    "8035.T": "東京エレクトロン",
    "6920.T": "レーザーテック",
    "6146.T": "ディスコ",
    "7735.T": "SCREEN",
    "6723.T": "ルネサス",
    "4063.T": "信越化学",
    "3436.T": "SUMCO",
    "6963.T": "ローム",
    "285A.T": "キオクシア",
    "6526.T": "ソシオネクスト",
    "6525.T": "KOKUSAI ELECTRIC",
    "6521.T": "オキサイド",
    "6227.T": "AIメカテック",
    "6613.T": "QDレーザ",
}
TICKERS = GROUPS[stock_group]

def get_data(ticker):
    df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True)

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["MA_short"] = df["Close"].rolling(short_window).mean()
    df["MA_long"] = df["Close"].rolling(long_window).mean()

    return df.dropna()


def backtest(df):
    cash = INITIAL_CASH
    shares = 0
    buy_price = 0
    borrowed_amount = 0
    trade_count = 0

    max_value = INITIAL_CASH
    max_drawdown = 0

    margin_call_count = 0
    max_margin_call_amount = 0
    min_margin_rate = 1
    forced_liquidation_count = 0

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        today = df.iloc[i]

        price = today["Close"].item()

        prev_short = prev["MA_short"].item()
        prev_long = prev["MA_long"].item()
        today_short = today["MA_short"].item()
        today_long = today["MA_long"].item()

        if prev_short <= prev_long and today_short > today_long and shares == 0:
            buying_power = INITIAL_CASH * leverage
            shares = int(buying_power // (price * (1 + FEE_RATE)))

            cost = shares * price
            fee = cost * FEE_RATE

            borrowed_amount = max(cost - INITIAL_CASH, 0)
            cash = INITIAL_CASH - fee

            buy_price = price
            trade_count += 1

        elif prev_short >= prev_long and today_short < today_long and shares > 0:
            proceeds = shares * price
            fee = proceeds * FEE_RATE
            realized_profit = (price - buy_price) * shares

            tax = 0
            if realized_profit > 0:
                tax = realized_profit * TAX_RATE

            

            cash = proceeds - borrowed_amount - fee - tax

            shares = 0
            buy_price = 0
            borrowed_amount = 0
            trade_count += 1

        current_value = cash
        if shares > 0:
            position_value = shares * price
            

            equity = position_value - borrowed_amount
            current_value = equity

            margin_rate = equity / position_value if position_value > 0 else 1
            if margin_rate < min_margin_rate:
                min_margin_rate = margin_rate

            if margin_rate < maintenance_rate:
                required_equity = position_value * maintenance_rate
                margin_call_amount = required_equity - equity

                margin_call_count += 1

                if margin_call_amount > max_margin_call_amount:
                    max_margin_call_amount = margin_call_amount

            if margin_rate < forced_liquidation_rate:
                forced_liquidation_count += 1

                proceeds = shares * price
                fee = proceeds * FEE_RATE

                cash = proceeds - borrowed_amount - fee

                shares = 0
                buy_price = 0
                borrowed_amount = 0

        if current_value > max_value:
            max_value = current_value

        drawdown = (max_value - current_value) / max_value * 100

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    final_price = df.iloc[-1]["Close"].item()

    if shares > 0:
        borrowed_amount = buy_price * shares - INITIAL_CASH
        final_value = cash + shares * final_price - borrowed_amount
    else:
        final_value = cash

    profit = final_value - INITIAL_CASH
    return_rate = (final_value / INITIAL_CASH - 1) * 100

    return final_value, profit, return_rate,trade_count, max_drawdown,margin_call_count, max_margin_call_amount,min_margin_rate,forced_liquidation_count

def color_profit(val):
    try:
        num = float(str(val).replace("¥", "").replace(",", ""))
        if num > 0:
            return "color:red"
        elif num < 0:
            return "color:blue"
    except:
        pass
    return ""

with action_col2:
    run_backtest = st.button(
        "バックテスト実行",
        use_container_width=True
    )

if run_backtest:
    results = []

    for ticker in TICKERS:
        df = get_data(ticker)

        if df is None or df.empty:
            continue

        final_value, profit, return_rate,trade_count, max_drawdown,margin_call_count, max_margin_call_amount,min_margin_rate,forced_liquidation_count = backtest(df)

        rejection_reasons = []

        if return_rate < min_return:
            rejection_reasons.append(
                f"リターン不足（{return_rate:.2f}%）"
            )

        if max_drawdown > max_drawdown_limit:
            rejection_reasons.append(
                f"最大下落率超過（{max_drawdown:.2f}%）"
            )

        if trade_count < min_trade_count:
            rejection_reasons.append(
                f"取引回数不足（{trade_count}回）"
            )

        if forced_liquidation_count > max_forced_liquidation_count:
            rejection_reasons.append(
                f"強制決済あり（{forced_liquidation_count}回）"
            )

        if rejection_reasons:
            judge = "見送り"
            rejection_reason = "、".join(rejection_reasons)
        else:
            judge = "採用候補"
            rejection_reason = "条件達成"

        if forced_liquidation_count > 0:
            rating = "✕"
        elif margin_call_count > 0:
            rating = "△"
        else:
            rating = "◎"

        results.append({
            "評価": rating,
            "銘柄": f"{ticker} {TICKER_NAMES.get(ticker, '')}",
  
          "最終資産": round(final_value),
            "損益": round(profit),
            "リターン%": round(return_rate, 2),
            "取引回数": trade_count,
            "最大下落率%": round(max_drawdown, 2),
            "最低保証金率%": round(min_margin_rate * 100, 2),
            "判定": judge,
            "見送り理由": rejection_reason,
            "追証発生回数": margin_call_count,
            "最大追証額": round(max_margin_call_amount),
            "強制決済回数": forced_liquidation_count,

        })
    
    result_df = pd.DataFrame(results)

    if only_adopted:
        result_df = result_df[result_df["判定"] == "採用候補"]
    result_df["評価順"] = result_df["評価"].map({
        "◎": 0,
        "△": 1,
        "✕": 2
    })

    result_df = result_df.sort_values(
        ["評価順", "リターン%"],
        ascending=[True, False]
    )

    result_df = result_df.drop(columns=["評価順"])

    display_df = result_df.copy()

    adopted_count = int(
        (display_df["判定"] == "採用候補").sum()
    )

    st.write(f"採用候補数：{adopted_count}銘柄")


    # 概要に表示する項目
    overview_columns = [
        "評価",
        "銘柄",
        "最終資産",
        "損益",
        "リターン%",
        "取引回数",
        "最大下落率%",
        "判定",
        "見送り理由",
    ]

    # 信用リスクに表示する項目
    risk_columns = [
        "銘柄",
        "最低保証金率%",
        "追証発生回数",
        "最大追証額",
        "強制決済回数",
    ]

    overview_df = display_df[overview_columns].copy()
    risk_df = display_df[risk_columns].copy()


    # 概要表の表示形式
    overview_styled = (
        overview_df.style
        .map(
            color_profit,
            subset=["損益", "リターン%"]
        )
        .format({
            "最終資産": "¥{:,.0f}",
            "損益": "¥{:,.0f}",
            "リターン%": "{:.2f}",
            "最大下落率%": "{:.2f}",
        })
    )


    # 信用リスク表の表示形式
    risk_styled = (
        risk_df.style
        .format({
            "最低保証金率%": "{:.2f}",
            "最大追証額": "¥{:,.0f}",
        })
    )


    # 全項目表の表示形式
    all_styled = (
        display_df.style
        .map(
            color_profit,
            subset=["損益", "リターン%"]
        )
        .format({
            "最終資産": "¥{:,.0f}",
            "損益": "¥{:,.0f}",
            "リターン%": "{:.2f}",
            "最大下落率%": "{:.2f}",
            "最低保証金率%": "{:.2f}",
            "最大追証額": "¥{:,.0f}",
        })
    )


    overview_tab, risk_tab, all_tab = st.tabs(
        ["概要", "信用リスク", "全項目"]
    )

    with overview_tab:
        st.dataframe(
            overview_styled,
            use_container_width=True,
            hide_index=True
        )

    with risk_tab:
        st.dataframe(
            risk_styled,
            use_container_width=True,
            hide_index=True
        )

    with all_tab:
        st.dataframe(
            all_styled,
            use_container_width=True,
            hide_index=True
        )