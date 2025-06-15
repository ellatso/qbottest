import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import ta
from datetime import datetime

st.write("✅ 正在跑新版圖表程式")  # ← 加這行

st.set_page_config(page_title="QuantBot 多股交叉 + RSI + MACD + BBand 選股", layout="wide")
st.title("📊 QuantBot：黃金交叉 + RSI + MACD + 布林通道 選股儀表板")

# 股票清單載入
watchlist_df = pd.read_csv("quantbot_watchlist.csv")
all_stocks = watchlist_df['Stock'].tolist()
selected_stocks = st.multiselect("選擇股票進行分析：", all_stocks, default=all_stocks[:5])

# 設定參數
period = st.selectbox("觀察區間：", ["1mo", "3mo", "6mo"], index=1)
epsilon = st.slider("⚠️ 快要交叉的靈敏度（差距容忍）", 0.01, 2.0, 0.2)
rsi_threshold = st.slider("RSI 下限：", 10, 50, 30)
use_macd = st.checkbox("啟用 MACD 濾選（MACD > Signal）")
use_bbands = st.checkbox("啟用布林通道濾選（收盤 < 下軌）")

results = []
crossover_log = []

for stock in selected_stocks:
    data = yf.download(stock, period=period)
    data['SMA10'] = data['Close'].rolling(10).mean()
    data['SMA50'] = data['Close'].rolling(50).mean()
    data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()

    macd = ta.trend.MACD(data['Close'])
    data['MACD'] = macd.macd()
    data['MACD_signal'] = macd.macd_signal()

    bb = ta.volatility.BollingerBands(data['Close'])
    data['BB_upper'] = bb.bollinger_hband()
    data['BB_middle'] = bb.bollinger_mavg()
    data['BB_lower'] = bb.bollinger_lband()

    crossover = None
    near_crossover = None
    rsi_value = data['RSI'].iloc[-1]
    macd_cross = data['MACD'].iloc[-1] > data['MACD_signal'].iloc[-1] if use_macd else True
    bband_break = data['Close'].iloc[-1] < data['BB_lower'].iloc[-1] if use_bbands else True

    for i in range(len(data) - 10, len(data) - 1):
        sma10_y, sma50_y = data['SMA10'].iloc[i], data['SMA50'].iloc[i]
        sma10_t, sma50_t = data['SMA10'].iloc[i+1], data['SMA50'].iloc[i+1]
        if pd.notna(sma10_y) and pd.notna(sma50_y) and pd.notna(sma10_t) and pd.notna(sma50_t):
            if sma10_y < sma50_y and sma10_t > sma50_t:
                crossover = data.index[i + 1].date()
                crossover_log.append({
                    "股票": stock,
                    "類型": "黃金交叉",
                    "日期": crossover,
                    "RSI": round(rsi_value, 2),
                    "MACD": round(data['MACD'].iloc[i + 1], 3),
                    "MACD_signal": round(data['MACD_signal'].iloc[i + 1], 3)
                })
                break
            elif sma10_y < sma50_y and abs(sma10_t - sma50_t) < epsilon:
                near_crossover = data.index[i + 1].date()
                crossover_log.append({
                    "股票": stock,
                    "類型": "快要交叉",
                    "日期": near_crossover,
                    "RSI": round(rsi_value, 2),
                    "MACD": round(data['MACD'].iloc[i + 1], 3),
                    "MACD_signal": round(data['MACD_signal'].iloc[i + 1], 3)
                })

    if (crossover or near_crossover or rsi_value < rsi_threshold) and macd_cross and bband_break:
        results.append({
            "股票": stock,
            "交叉時間": crossover,
            "接近交叉": near_crossover,
            "RSI": round(rsi_value, 2),
            "MACD > Signal": macd_cross,
            "收盤 < 下軌": bband_break
        })

# 顯示結果表格
if results:
    st.subheader("📋 篩選結果")
    result_df = pd.DataFrame(results)
    st.dataframe(result_df)

    now = datetime.now().strftime("%Y%m%d_%H%M")
    result_df.to_csv(f"quantbot_result_{now}.csv", index=False)

    if crossover_log:
        crossover_df = pd.DataFrame(crossover_log)
        crossover_df.to_csv(f"crossover_log_{now}.csv", index=False)

    # 畫圖區
    st.subheader("📈 每支股票技術分析圖（SMA + RSI + MACD + 布林通道）")
    for stock in result_df["股票"]:
        st.markdown(f"### {stock} 技術圖")
        data = yf.download(stock, period=period)
        data['SMA10'] = data['Close'].rolling(10).mean()
        data['SMA50'] = data['Close'].rolling(50).mean()
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        data['MACD_diff'] = data['MACD'] - data['MACD_signal']
        bb = ta.volatility.BollingerBands(data['Close'])
        data['BB_upper'] = bb.bollinger_hband()
        data['BB_middle'] = bb.bollinger_mavg()
        data['BB_lower'] = bb.bollinger_lband()

        crossover_date, near_crossover_date = None, None
        for i in range(len(data) - 10, len(data) - 1):
            sma10_y, sma50_y = data['SMA10'].iloc[i], data['SMA50'].iloc[i]
            sma10_t, sma50_t = data['SMA10'].iloc[i + 1], data['SMA50'].iloc[i + 1]
            if pd.notna(sma10_y) and pd.notna(sma50_y) and pd.notna(sma10_t) and pd.notna(sma50_t):
                if sma10_y < sma50_y and sma10_t > sma50_t:
                    crossover_date = data.index[i + 1]
                    break
                elif sma10_y < sma50_y and abs(sma10_t - sma50_t) < epsilon:
                    near_crossover_date = data.index[i + 1]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})
        ax1.plot(data['Close'], label='收盤價', color='black')
        ax1.plot(data['SMA10'], label='SMA10', linestyle='--', color='orange')
        ax1.plot(data['SMA50'], label='SMA50', linestyle='--', color='green')
        ax1.plot(data['BB_upper'], label='布林上軌', linestyle=':', color='blue')
        ax1.plot(data['BB_middle'], label='布林中軌', linestyle=':', color='gray')
        ax1.plot(data['BB_lower'], label='布林下軌', linestyle=':', color='blue')
        under_band = data['Close'] < data['BB_lower']
        ax1.plot(data.index[under_band], data['Close'][under_band], 'ro', label='跌破下軌')
        if crossover_date:
            ax1.axvline(x=crossover_date, color='red', linestyle='-', label='黃金交叉')
        elif near_crossover_date:
            ax1.axvline(x=near_crossover_date, color='gray', linestyle='--', label='快要交叉')
        ax1.legend(loc='upper left')
        ax1.set_title(f"{stock} 價格與技術指標")

        ax2.plot(data['RSI'], label='RSI', color='purple')
        ax2.axhline(30, linestyle='--', color='gray')
        ax2.axhline(70, linestyle='--', color='gray')
        ax2.set_ylabel("RSI")
        ax2.legend(loc='upper left')

        ax3.bar(data.index, data['MACD_diff'], label='MACD Histogram', color='gray')
        ax3.plot(data['MACD'], label='MACD', color='blue')
        ax3.plot(data['MACD_signal'], label='Signal', color='orange')
        ax3.set_ylabel("MACD")
        ax3.legend(loc='upper left')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        st.pyplot(fig)

else:
    st.info("🔍 沒有符合條件的股票")
