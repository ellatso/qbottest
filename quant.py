import streamlit as st
st.set_page_config(page_title="QuantBot 多股交叉 + RSI + MACD + BBand 選股", layout="wide")

# Define or import model_prediction and test_y before using them
# Example placeholder definition (replace with actual logic):
import numpy as np
import pandas as pd

model_prediction = np.array([0])  # Replace with actual model prediction
test_y = pd.DataFrame({'values': [1]})  # Replace with actual test data
import streamlit as st

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import ta
from datetime import datetime

# Removed undefined variables 'left' and 'right' as they are not used elsewhere in the code.
# If needed, define 'left' and 'right' appropriately before using them.
st.title("📊 QuantBot：黃金交叉 + RSI + MACD + 布林通道 選股儀表板")
st.write("✅ 正在跑新版圖表程式")

# 股票清單載入
watchlist_df = pd.read_csv("quantbot_watchlist.csv")
all_stocks = watchlist_df['Stock'].tolist()
selected_stocks = st.multiselect("選擇股票進行分析：", all_stocks, default=all_stocks[:5])

# 選項參數
period = st.selectbox("觀察區間：", ["1mo", "3mo", "6mo"], index=1)
epsilon = st.slider("⚠️ 快要交叉的靈敏度", 0.01, 2.0, 0.2)
rsi_threshold = st.slider("RSI 下限：", 10, 50, 30)
use_macd = st.checkbox("啟用 MACD 濾選（MACD > Signal）")
use_bbands = st.checkbox("啟用布林通道濾選（收盤 < 下軌）")

results = []
crossover_log = []

for stock in selected_stocks:
    data = yf.download(stock, period=period)
    data['SMA10'] = data['Close'].rolling(10).mean()
    data['SMA50'] = data['Close'].rolling(50).mean()

    close_series = pd.Series(data['Close'].values.flatten(), index=data.index)

    data['RSI'] = ta.momentum.RSIIndicator(close=close_series, window=14).rsi()
    macd = ta.trend.MACD(close=close_series)
    data['MACD'] = macd.macd().reindex(data.index)
    data['MACD_signal'] = macd.macd_signal().reindex(data.index)
    data['MACD_diff'] = data['MACD'].subtract(data['MACD_signal'], fill_value=0)




    bb = ta.volatility.BollingerBands(close=close_series)
    data['BB_upper'] = bb.bollinger_hband().reindex(data.index)
    data['BB_middle'] = bb.bollinger_mavg().reindex(data.index)
    data['BB_lower'] = bb.bollinger_lband().reindex(data.index)

    crossover = None
    near_crossover = None
    rsi_value = data['RSI'].iloc[-1]
    macd_cross = data['MACD'].iloc[-1] > data['MACD_signal'].iloc[-1] if use_macd else True
    bband_break = data['Close'].iloc[-1] < data['BB_lower'].iloc[-1] if use_bbands else True

    for i in range(len(data) - 10, len(data) - 1):
        sma10_y, sma50_y = data['SMA10'].iloc[i], data['SMA50'].iloc[i]
        sma10_t, sma50_t = data['SMA10'].iloc[i + 1], data['SMA50'].iloc[i + 1]
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

# 顯示結果與圖表
if results:
    st.subheader("📋 篩選結果")
    result_df = pd.DataFrame(results)
    st.dataframe(result_df)

    now = datetime.now().strftime("%Y%m%d_%H%M")
    result_df.to_csv(f"quantbot_result_{now}.csv", index=False)

    if crossover_log:
        crossover_df = pd.DataFrame(crossover_log)
        crossover_df.to_csv(f"crossover_log_{now}.csv", index=False)

    st.subheader("📈 每支股票技術分析圖")
    for stock in result_df["股票"]:
        st.markdown(f"### {stock} 技術圖")

        try:
            data = yf.download(stock, period=period)
            if len(data) < 50:
                st.warning(f"📉 {stock} 資料不足（{len(data)} 筆），跳過圖表繪製")
                continue

            data['SMA10'] = data['Close'].rolling(10).mean()
            data['SMA50'] = data['Close'].rolling(50).mean()
            close_series = pd.Series(data['Close'].values.flatten(), index=data.index)

            data['RSI'] = ta.momentum.RSIIndicator(close=close_series, window=14).rsi()
            macd = ta.trend.MACD(close=close_series)
            data['MACD'] = macd.macd().reindex(data.index)
            data['MACD_signal'] = macd.macd_signal().reindex(data.index)
            data['MACD_diff'] = data['MACD'].subtract(data['MACD_signal'], fill_value=0)

            bb = ta.volatility.BollingerBands(close=close_series)
            data['BB_upper'] = bb.bollinger_hband().reindex(data.index)
            data['BB_middle'] = bb.bollinger_mavg().reindex(data.index)
            data['BB_lower'] = bb.bollinger_lband().reindex(data.index)

            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})
            ax1.plot(data['Close'], label='收盤價', color='black')
            ax1.plot(data['SMA10'], label='SMA10', linestyle='--', color='orange')
            ax1.plot(data['SMA50'], label='SMA50', linestyle='--', color='green')
            ax1.plot(data['BB_upper'], label='布林上軌', linestyle=':', color='blue')
            ax1.plot(data['BB_middle'], label='布林中軌', linestyle=':', color='gray')
            ax1.plot(data['BB_lower'], label='布林下軌', linestyle=':', color='blue')
            under_band = data['Close'] < data['BB_lower']
            ax1.plot(data.index[under_band], data['Close'][under_band], 'ro', label='跌破下軌')
            ax1.legend(loc='upper left')
            ax1.set_title(f"{stock} 價格與技術指標")

            ax2.plot(data['RSI'], label='RSI', color='purple')
            ax2.axhline(30, linestyle='--', color='gray')
            ax2.axhline(70, linestyle='--', color='gray')
            ax2.legend(loc='upper left')

            ax3.bar(data.index, data['MACD_diff'], label='MACD Histogram', color='gray')
            ax3.plot(data['MACD'], label='MACD', color='blue')
            ax3.plot(data['MACD_signal'], label='Signal', color='orange')
            ax3.legend(loc='upper left')
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()

            st.pyplot(fig)

        except Exception as e:
            st.error("❌ {stock} 繪圖失敗：")

else:
    st.info("🔍 沒有符合條件的股票")
