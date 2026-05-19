import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pandas as pd
import os
from datetime import datetime

st.set_page_config(
    page_title="Gold AI Dashboard Pro",
    page_icon="🔥",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #0e1117;
}
[data-testid="stMetric"] {
    background-color: #111827;
    padding: 15px;
    border-radius: 14px;
    border: 1px solid #374151;
}
h1, h2, h3 {
    color: white;
}
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=60000, key="refresh")

st.title("🔥 Gold AI Dashboard Pro")
st.caption("Live Gold Analysis • Multi Asset Scanner • Trade Journal • Backtest")

page = st.sidebar.radio(
    "📊 Select Page",
    ["Gold Dashboard", "Multi Asset Scanner", "Trade Journal", "Backtest"]
)

st.sidebar.divider()
st.sidebar.subheader("💰 Risk Settings")

risk_reward = st.sidebar.slider("Risk Reward Ratio", 1, 5, 2)
account_balance = st.sidebar.number_input("Account Balance ($)", value=1000)
risk_percent = st.sidebar.slider("Risk %", 1, 10, 2)

st.sidebar.divider()
st.sidebar.info("Version 1.0\n\nAuto refresh: 60 seconds")

assets = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Bitcoin": "BTC-USD",
    "NASDAQ": "^IXIC",
    "S&P500": "^GSPC",
    "EUR/USD": "EURUSD=X"
}

journal_file = "trade_journal.csv"

if not os.path.exists(journal_file):
    pd.DataFrame(columns=[
        "Date", "Asset", "Signal", "Entry", "Stop Loss",
        "Take Profit", "Result", "Notes"
    ]).to_csv(journal_file, index=False)

def get_data(ticker):
    data = yf.download(ticker, period="2d", interval="5m", progress=False)

    if data.empty:
        return None

    open_price = data["Open"]
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    if hasattr(close, "columns"):
        open_price = open_price.iloc[:, 0]
        high = high.iloc[:, 0]
        low = low.iloc[:, 0]
        close = close.iloc[:, 0]

    return data, open_price, high, low, close

def analyse(close):
    ma20 = close.rolling(20).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    latest_price = close.iloc[-1]
    latest_ma20 = ma20.iloc[-1]
    latest_rsi = rsi.iloc[-1]

    if latest_price > latest_ma20 and latest_rsi < 70:
        signal = "BUY"
        strength = "STRONG"
    elif latest_price < latest_ma20 and latest_rsi > 30:
        signal = "SELL"
        strength = "STRONG"
    else:
        signal = "WAIT"
        strength = "WEAK"

    return latest_price, latest_ma20, latest_rsi, ma20, signal, strength

def calculate_trade_levels(price, signal):
    sl_distance = price * 0.003

    if signal == "BUY":
        stop_loss = price - sl_distance
        take_profit = price + (sl_distance * risk_reward)
    elif signal == "SELL":
        stop_loss = price + sl_distance
        take_profit = price - (sl_distance * risk_reward)
    else:
        stop_loss = price
        take_profit = price

    return stop_loss, take_profit, sl_distance

def draw_chart(data, open_price, high, low, close, ma20, title, entry=None, sl=None, tp=None):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data.index,
        open=open_price,
        high=high,
        low=low,
        close=close,
        name=title
    ))

    fig.add_trace(go.Scatter(
        x=data.index,
        y=ma20,
        mode="lines",
        name="MA20"
    ))

    if entry:
        fig.add_hline(y=entry, line_dash="dash", annotation_text="Entry")
    if sl:
        fig.add_hline(y=sl, line_dash="dot", annotation_text="Stop Loss")
    if tp:
        fig.add_hline(y=tp, line_dash="dot", annotation_text="Take Profit")

    fig.update_layout(title=title, template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)

if page == "Gold Dashboard":
    st.subheader("🥇 Gold Dashboard")

    result = get_data("GC=F")

    if result is None:
        st.error("No gold data.")
        st.stop()

    data, open_price, high, low, close = result
    latest_price, latest_ma20, latest_rsi, ma20, signal, strength = analyse(close)
    stop_loss, take_profit, sl_distance = calculate_trade_levels(latest_price, signal)

    risk_amount = account_balance * (risk_percent / 100)
    position_size = risk_amount / sl_distance if sl_distance != 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gold Price", "$" + str(round(latest_price, 2)))
    c2.metric("MA20", round(latest_ma20, 2))
    c3.metric("RSI", round(latest_rsi, 2))
    c4.metric("AI Signal", signal + " | " + strength)

    st.divider()

    st.subheader("🎯 Trade Execution")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Entry", round(latest_price, 2))
    e2.metric("Stop Loss", round(stop_loss, 2))
    e3.metric("Take Profit", round(take_profit, 2))
    e4.metric("Risk Reward", "1:" + str(risk_reward))

    st.divider()

    st.subheader("💰 Risk Calculator")
    r1, r2, r3 = st.columns(3)
    r1.metric("Risk Amount", "$" + str(round(risk_amount, 2)))
    r2.metric("SL Distance", round(sl_distance, 2))
    r3.metric("Position Size", round(position_size, 2))

    st.warning("⚠️ Educational/demo use only. This is not financial advice.")

    st.divider()

    draw_chart(
        data, open_price, high, low, close, ma20,
        "Gold Live Chart", latest_price, stop_loss, take_profit
    )

elif page == "Multi Asset Scanner":
    st.subheader("🌍 Multi Asset Scanner")

    scanner_results = []
    chart_cache = {}

    for asset_name, ticker in assets.items():
        result = get_data(ticker)

        if result is not None:
            data, open_price, high, low, close = result
            latest_price, latest_ma20, latest_rsi, ma20, signal, strength = analyse(close)

            scanner_results.append({
                "Asset": asset_name,
                "Price": round(latest_price, 2),
                "MA20": round(latest_ma20, 2),
                "RSI": round(latest_rsi, 2),
                "Signal": signal,
                "Strength": strength
            })

            chart_cache[asset_name] = {
                "data": data,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "ma20": ma20
            }

    scanner_df = pd.DataFrame(scanner_results)
    st.dataframe(scanner_df, use_container_width=True)

    if not scanner_df.empty:
        st.divider()
        buy_assets = scanner_df[scanner_df["Signal"] == "BUY"]
        sell_assets = scanner_df[scanner_df["Signal"] == "SELL"]
        wait_assets = scanner_df[scanner_df["Signal"] == "WAIT"]

        a, b, c = st.columns(3)
        a.metric("BUY Signals", len(buy_assets))
        b.metric("SELL Signals", len(sell_assets))
        c.metric("WAIT Signals", len(wait_assets))

    st.divider()

    if len(chart_cache) > 0:
        selected_asset = st.selectbox("Select Asset Chart", list(chart_cache.keys()))
        selected = chart_cache[selected_asset]

        draw_chart(
            selected["data"], selected["open"], selected["high"],
            selected["low"], selected["close"], selected["ma20"],
            selected_asset + " Live Chart"
        )

elif page == "Trade Journal":
    st.subheader("📒 Trade Journal")

    with st.form("trade_form"):
        asset = st.selectbox("Asset", list(assets.keys()))
        signal = st.selectbox("Signal", ["BUY", "SELL", "WAIT"])
        entry = st.number_input("Entry")
        stop_loss = st.number_input("Stop Loss")
        take_profit = st.number_input("Take Profit")
        result = st.selectbox("Result", ["PENDING", "WIN", "LOSS"])
        notes = st.text_area("Notes")
        submit = st.form_submit_button("💾 Save Trade")

    if submit:
        journal = pd.read_csv(journal_file)

        new_trade = pd.DataFrame([{
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Asset": asset,
            "Signal": signal,
            "Entry": entry,
            "Stop Loss": stop_loss,
            "Take Profit": take_profit,
            "Result": result,
            "Notes": notes
        }])

        journal = pd.concat([journal, new_trade], ignore_index=True)
        journal.to_csv(journal_file, index=False)
        st.success("Trade saved successfully!")

    journal = pd.read_csv(journal_file)

    st.divider()
    st.subheader("📊 Journal Analytics")

    total_trades = len(journal)
    wins = len(journal[journal["Result"] == "WIN"])
    losses = len(journal[journal["Result"] == "LOSS"])
    pending = len(journal[journal["Result"] == "PENDING"])

    closed_trades = wins + losses
    win_rate = round((wins / closed_trades) * 100, 2) if closed_trades > 0 else 0

    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Total Trades", total_trades)
    a2.metric("Wins", wins)
    a3.metric("Losses", losses)
    a4.metric("Pending", pending)
    a5.metric("Win Rate", str(win_rate) + "%")

    if total_trades > 0:
        result_counts = journal["Result"].value_counts()

        pie_fig = go.Figure(
            data=[go.Pie(labels=result_counts.index, values=result_counts.values, hole=0.4)]
        )

        pie_fig.update_layout(template="plotly_dark", height=400, title="Trade Result Distribution")
        st.plotly_chart(pie_fig, use_container_width=True)

    st.divider()
    st.subheader("📋 Journal Records")
    st.dataframe(journal, use_container_width=True)

    csv = journal.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download Journal CSV",
        data=csv,
        file_name="trade_journal.csv",
        mime="text/csv"
    )

elif page == "Backtest":
    st.subheader("📈 Gold Strategy Backtest")

    result = get_data("GC=F")

    if result is None:
        st.error("No backtest data.")
        st.stop()

    data, open_price, high, low, close = result
    ma20 = close.rolling(20).mean()

    balance = account_balance
    wins = 0
    losses = 0
    equity_curve = []
    trade_log = []

    for i in range(20, len(close) - 1):
        current_price = close.iloc[i]
        current_ma20 = ma20.iloc[i]
        next_price = close.iloc[i + 1]

        bt_signal = "WAIT"

        if current_price > current_ma20:
            bt_signal = "BUY"
        elif current_price < current_ma20:
            bt_signal = "SELL"

        if bt_signal != "WAIT":
            risk_amount_bt = balance * (risk_percent / 100)

            if bt_signal == "BUY" and next_price > current_price:
                balance += risk_amount_bt * risk_reward
                wins += 1
                bt_result = "WIN"
            elif bt_signal == "SELL" and next_price < current_price:
                balance += risk_amount_bt * risk_reward
                wins += 1
                bt_result = "WIN"
            else:
                balance -= risk_amount_bt
                losses += 1
                bt_result = "LOSS"

            trade_log.append({
                "Date": str(data.index[i]),
                "Signal": bt_signal,
                "Result": bt_result,
                "Balance": round(balance, 2)
            })

        equity_curve.append(balance)

    total = wins + losses
    win_rate = round((wins / total) * 100, 2) if total > 0 else 0

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Final Balance", "$" + str(round(balance, 2)))
    b2.metric("Wins", wins)
    b3.metric("Losses", losses)
    b4.metric("Win Rate", str(win_rate) + "%")

    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(y=equity_curve, mode="lines", name="Balance"))
    equity_fig.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(equity_fig, use_container_width=True)

    trade_df = pd.DataFrame(trade_log)
    st.dataframe(trade_df, use_container_width=True)

st.divider()
st.caption("© 2026 Gold AI Dashboard Pro • Educational Use Only • Not Financial Advice")