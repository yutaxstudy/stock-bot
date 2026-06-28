import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="株バックテストアプリ",
    layout="wide"
)

if "result_period_label" not in st.session_state:
    st.session_state["result_period_label"] = None
    
if "result_df" not in st.session_state:
    st.session_state["result_df"] = None

if "trade_histories_by_ticker" not in st.session_state:
    st.session_state["trade_histories_by_ticker"] = {}

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

with condition_col4:
    backtest_period = st.selectbox(
        "バックテスト期間",
        [
            "直近1年",
            "直近3年",
            "直近5年",
            "直近10年",
            "上場来すべて",
            "期間を指定",
        ],
        index=2
    )

custom_start_date = date(2019, 1, 1)
custom_end_date = date.today()

if backtest_period == "期間を指定":
    period_col1, period_col2, period_col3, period_col4 = st.columns(4)

    with period_col1:
        custom_start_date = st.date_input(
            "開始日",
            value=date(2019, 1, 1)
        )

    with period_col2:
        custom_end_date = st.date_input(
            "終了日",
            value=date.today(),
            min_value=custom_start_date
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
    download_options = {
        "interval": "1d",
        "auto_adjust": True,
        "progress": False,
    }

    today = pd.Timestamp.today().normalize()

    if backtest_period == "直近1年":
        start_date = today - pd.DateOffset(years=1)
        download_options["start"] = start_date.strftime("%Y-%m-%d")

    elif backtest_period == "直近3年":
        start_date = today - pd.DateOffset(years=3)
        download_options["start"] = start_date.strftime("%Y-%m-%d")

    elif backtest_period == "直近5年":
        start_date = today - pd.DateOffset(years=5)
        download_options["start"] = start_date.strftime("%Y-%m-%d")

    elif backtest_period == "直近10年":
        start_date = today - pd.DateOffset(years=10)
        download_options["start"] = start_date.strftime("%Y-%m-%d")

    elif backtest_period == "上場来すべて":
        download_options["period"] = "max"

    elif backtest_period == "期間を指定":
        download_options["start"] = custom_start_date.isoformat()

        # 終了日を含めるため、yfinanceには翌日を渡す
        inclusive_end_date = custom_end_date + timedelta(days=1)
        download_options["end"] = inclusive_end_date.isoformat()

    df = yf.download(
        ticker,
        **download_options
    )

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
    trade_history = []
    buy_date = None
    buy_fee = 0

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
            available_cash = cash
            buying_power = available_cash * leverage
            shares = int(
                buying_power // (price * (1 + FEE_RATE))
            )

            cost = shares * price
            fee = cost * FEE_RATE
            total_purchase = cost + fee

            borrowed_amount = max(
                total_purchase - available_cash,
                0
            )
            cash = (
                available_cash
                + borrowed_amount
                - total_purchase
            )

            buy_price = price
            buy_date = df.index[i]
            buy_fee = fee
            trade_count += 1

        elif prev_short >= prev_long and today_short < today_long and shares > 0:
            proceeds = shares * price
            fee = proceeds * FEE_RATE
            realized_profit = (price - buy_price) * shares

            taxable_profit = realized_profit - buy_fee - fee
            tax = max(taxable_profit, 0) * TAX_RATE

            cash = (
                cash
                + proceeds
                - borrowed_amount
                - fee
                - tax
            )

            trade_history.append({
                "買付日": buy_date.strftime("%Y-%m-%d") if buy_date is not None else "",
                "買付価格": round(buy_price, 2),
                "売却日": df.index[i].strftime("%Y-%m-%d"),
                "売却価格": round(price, 2),
                "決済理由": "通常売却",
                "株数": shares,
                "売買差益": round(realized_profit),
                "買付手数料": round(buy_fee),
                "売却手数料": round(fee),
                "税金": round(tax),
                "実現損益": round(realized_profit - buy_fee - fee - tax),
})

            shares = 0
            buy_price = 0
            buy_date = None
            buy_fee = 0
            borrowed_amount = 0
            trade_count += 1

        current_value = cash
        if shares > 0:
            position_value = shares * price
            

            equity = cash + position_value - borrowed_amount
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

                cash = (
                    cash
                    + proceeds
                    - borrowed_amount
                    - fee
                )

                forced_realized_profit = (price - buy_price) * shares

                trade_history.append({
                    "買付日": buy_date.strftime("%Y-%m-%d") if buy_date is not None else "",
                    "買付価格": round(buy_price, 2),
                    "売却日": df.index[i].strftime("%Y-%m-%d"),
                    "売却価格": round(price, 2),
                    "決済理由": "強制決済",
                    "株数": shares,
                    "売買差益": round(forced_realized_profit),
                    "買付手数料": round(buy_fee),
                    "売却手数料": round(fee),
                    "税金": 0,
                    "実現損益": round(forced_realized_profit - buy_fee - fee),
                })

                shares = 0
                buy_price = 0
                buy_date = None
                buy_fee = 0
                borrowed_amount = 0
                trade_count += 1


        if current_value > max_value:
            max_value = current_value

        drawdown = (max_value - current_value) / max_value * 100

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    final_price = df.iloc[-1]["Close"].item()

    if shares > 0:
        unrealized_profit = (final_price - buy_price) * shares

        trade_history.append({
            "買付日": buy_date.strftime("%Y-%m-%d") if buy_date is not None else "",
            "買付価格": round(buy_price, 2),
            "売却日": df.index[-1].strftime("%Y-%m-%d"),
            "売却価格": round(final_price, 2),
            "決済理由": "期末保有中",
            "株数": shares,
            "売買差益": round(unrealized_profit),
            "買付手数料": round(buy_fee),
            "売却手数料": 0,
            "税金": 0,
            "実現損益": None,
        })

    if shares > 0:
        final_value = cash + shares * final_price - borrowed_amount
    else:
        final_value = cash

    profit = final_value - INITIAL_CASH
    return_rate = (final_value / INITIAL_CASH - 1) * 100

    return final_value, profit, return_rate,trade_count, max_drawdown,margin_call_count, max_margin_call_amount,min_margin_rate,forced_liquidation_count, trade_history

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
    trade_histories_by_ticker = {}

    for ticker in TICKERS:
        df = get_data(ticker)

        if df is None or df.empty:
            continue

        final_value, profit, return_rate,trade_count, max_drawdown,margin_call_count, max_margin_call_amount,min_margin_rate,forced_liquidation_count, trade_history = backtest(df)
        trade_histories_by_ticker[ticker] = trade_history
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

    st.session_state["result_df"] = result_df.copy()
    st.session_state["trade_histories_by_ticker"] = trade_histories_by_ticker.copy()
    if backtest_period == "期間を指定":
        st.session_state["result_period_label"] = (
        f"{custom_start_date.strftime('%Y-%m-%d')}"
        f" ～ "
        f"{custom_end_date.strftime('%Y-%m-%d')}"
     )
    else:
        st.session_state["result_period_label"] = backtest_period


if st.session_state["result_df"] is not None:
    result_df = st.session_state["result_df"].copy()
    trade_histories_by_ticker = st.session_state["trade_histories_by_ticker"]

    display_df = result_df.copy()

    adopted_count = int(
        (display_df["判定"] == "採用候補").sum()
    )

    if st.session_state["result_period_label"] is not None:
        st.caption(
            f"バックテスト期間："
            f"{st.session_state['result_period_label']}"
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


    overview_tab, risk_tab, history_tab, all_tab = st.tabs(
        ["概要", "信用リスク", "売買履歴", "全項目"]
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
    with history_tab:
        history_tickers = list(trade_histories_by_ticker.keys())

        if history_tickers:
            selected_ticker = st.selectbox(
                "売買履歴を確認する銘柄",
                history_tickers,
                format_func=lambda ticker: (
                    f"{ticker} {TICKER_NAMES.get(ticker, '')}"
                ),
                key="trade_history_ticker"
            )

            selected_history = trade_histories_by_ticker.get(
                selected_ticker,
                []
            )

            if selected_history:
                history_df = pd.DataFrame(selected_history)

                closed_df = history_df[
                    history_df["決済理由"] != "期末保有中"
                ].copy()

                open_df = history_df[
                    history_df["決済理由"] == "期末保有中"
                ].copy()


                # 決済済みの取引
                if not closed_df.empty:
                    st.markdown("#### 決済済み取引")

                    closed_df = closed_df[
                        [
                            "買付日",
                            "買付価格",
                            "売却日",
                            "売却価格",
                            "決済理由",
                            "株数",
                            "買付手数料",
                            "売却手数料",
                            "税金",
                            "実現損益",
                        ]
                    ]

                    closed_styled = (
                        closed_df.style
                        .format({
                            "買付価格": "¥{:,.2f}",
                            "売却価格": "¥{:,.2f}",
                            "株数": "{:,.0f}",
                            "買付手数料": "¥{:,.0f}",
                            "売却手数料": "¥{:,.0f}",
                            "税金": "¥{:,.0f}",
                            "実現損益": "¥{:,.0f}",
                        })
                    )

                    st.dataframe(
                        closed_styled,
                        use_container_width=True,
                        hide_index=True
                    )


                # 期末時点で保有中の建玉
                if not open_df.empty:
                    st.markdown("#### 期末保有中")

                    open_df = open_df.rename(columns={
                        "売却日": "期末日",
                        "売却価格": "期末価格",
                        "売買差益": "含み損益",
                    })

                    open_df = open_df[
                        [
                            "買付日",
                            "買付価格",
                            "期末日",
                            "期末価格",
                            "決済理由",
                            "株数",
                            "買付手数料",
                            "含み損益",
                        ]
                    ]

                    open_styled = (
                        open_df.style
                        .format({
                            "買付価格": "¥{:,.2f}",
                            "期末価格": "¥{:,.2f}",
                            "株数": "{:,.0f}",
                            "買付手数料": "¥{:,.0f}",
                            "含み損益": "¥{:,.0f}",
                        })
                    )

                    st.dataframe(
                        open_styled,
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("この銘柄には売買履歴がありません。")
        else:
            st.info("表示できる売買履歴がありません。")

    with all_tab:
        st.dataframe(
            all_styled,
            use_container_width=True,
            hide_index=True
        )