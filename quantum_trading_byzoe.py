import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="GSS Quantum Analytics",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CUSTOM (Tampilan Profesional GSS) ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #FFD700; text-align: center; font-weight: bold; }
    .sub-header { font-size: 1.2rem; color: #cccccc; text-align: center; margin-bottom: 2rem; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; font-size: 1.5rem; font-weight: bold; }
    .price-box { background-color: #1E1E1E; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #444; }
    .buy-signal { background-color: #004d00; color: #00ff00; border: 2px solid #00ff00; }
    .sell-signal { background-color: #4d0000; color: #ff4b4b; border: 2px solid #ff4b4b; }
    .neutral-signal { background-color: #4d4d00; color: #ffff00; border: 2px solid #ffff00; }
    .big-font { font-size: 1.8rem; font-weight: bold; }
    .small-font { font-size: 0.9rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# --- DAFTAR ASET GSS ---
# Note: Gold Pluang basisnya GC=F tapi dikonversi ke Gram & IDR
ASSETS = {
    "EMAS PLUANG (Gram)": {"ticker": "GC=F", "type": "Commodity", "is_gold": True}, 
    "PAX GOLD (PAXG)": {"ticker": "PAXG-USD", "type": "Crypto", "is_gold": False},
    "S&P 500 (SPY)": {"ticker": "SPY", "type": "ETF", "is_gold": False},
    "NVIDIA (NVDA)": {"ticker": "NVDA", "type": "Stock", "is_gold": False},
    "BITCOIN (BTC)": {"ticker": "BTC-USD", "type": "Crypto", "is_gold": False}
}

# --- FUNGSI ENGINE ---

@st.cache_data(ttl=300)
def get_exchange_rate():
    """Mengambil kurs USD ke IDR hari ini"""
    try:
        ticker = yf.Ticker("IDR=X")
        # Ambil data hari ini
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 16000.0 # Fallback jika gagal
    except:
        return 16000.0

@st.cache_data(ttl=60) # Cache pendek biar data selalu fresh
def get_market_data(ticker, period="1y"):
    """Mengambil data pasar dan menghitung indikator teknikal"""
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        
        # Handle MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or 'Close' not in df.columns:
            # Coba fallback ke 'Adj Close' jika Close kosong
            if 'Adj Close' in df.columns:
                df['Close'] = df['Adj Close']
            else:
                return None

        # --- INDIKATOR TEKNIKAL ---
        # 1. EMA (Exponential Moving Average)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        
        # 2. RSI (Relative Strength Index)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 3. MACD
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df['MACD'] = macd.iloc[:, 0]
            df['MACD_SIGNAL'] = macd.iloc[:, 2]
            
        return df

    except Exception:
        return None

def analyze_signal(df):
    """
    Analisis Sinyal Dinamis (Bukan Template).
    Teks akan berubah sesuai angka real-time.
    """
    if df is None: return 50, ["Data tidak tersedia"]

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    score = 0
    reasons = []
    
    # 1. ANALISIS TREN (EMA)
    price_now = last['Close']
    ema200 = last['EMA_200']
    
    if price_now > ema200:
        gap = ((price_now - ema200) / ema200) * 100
        score += 25
        reasons.append(f"Harga berada {gap:.1f}% DI ATAS garis tren jangka panjang (EMA 200). Pasar Bullish.")
    else:
        gap = ((ema200 - price_now) / ema200) * 100
        score -= 25
        reasons.append(f"Harga berada {gap:.1f}% DI BAWAH garis tren jangka panjang (EMA 200). Pasar Bearish.")
        
    # Golden Cross / Death Cross
    if last['EMA_50'] > last['EMA_200']:
        score += 15
        reasons.append(f"Golden Cross Terkonfirmasi (EMA 50 > EMA 200). Tren menengah kuat.")
    elif last['EMA_50'] < last['EMA_200']:
        score -= 10
        reasons.append(f"Death Cross (EMA 50 < EMA 200). Tren menengah lemah.")

    # 2. ANALISIS MOMENTUM (RSI)
    rsi = last['RSI']
    if rsi < 30:
        score += 35
        reasons.append(f"RSI Sangat Murah (Oversold) di level {rsi:.1f}. Potensi pantulan harga tinggi!")
    elif rsi > 70:
        score -= 25
        reasons.append(f"RSI Sangat Mahal (Overbought) di level {rsi:.1f}. Hati-hati koreksi.")
    elif 30 <= rsi <= 50:
        score += 10
        reasons.append(f"RSI di level {rsi:.1f} (Zona Akumulasi). Masih aman untuk masuk.")
    else: # 50-70
        score += 5
        reasons.append(f"RSI di level {rsi:.1f} (Zona Pertumbuhan). Momentum positif.")
        
    # 3. MACD Dynamic
    macd_val = last['MACD']
    macd_sig = last['MACD_SIGNAL']
    
    if macd_val > macd_sig:
        score += 20
        reasons.append(f"MACD Line ({macd_val:.2f}) di atas Signal. Momentum beli aktif.")
    else:
        score -= 20
        reasons.append(f"MACD Line ({macd_val:.2f}) di bawah Signal. Tekanan jual masih ada.")
        
    # Normalisasi Score 0-100
    final_score = max(0, min(100, 50 + score))
    return final_score, reasons

# --- UI VISUALIZATION ---

def main():
    # Header
    st.markdown("<div class='main-header'>🦅 GSS QUANTUM ANALYTICS</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Gold Standard Society - Intelligent Market Signaling</div>", unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.header("🎛️ Kontrol Panel")
    selected_asset_name = st.sidebar.selectbox("Pilih Aset:", list(ASSETS.keys()))
    asset_info = ASSETS[selected_asset_name]
    
    st.sidebar.markdown("---")
    
    # Process Data
    with st.spinner("Menghubungkan ke satelit data global..."):
        # Ambil Kurs
        usd_idr = get_exchange_rate()
        st.sidebar.metric("Kurs USD/IDR Hari Ini", f"Rp {usd_idr:,.0f}")
        
        # Ambil Data Market
        df = get_market_data(asset_info['ticker'])
    
    if df is not None:
        last_close_usd = df['Close'].iloc[-1]
        prev_close_usd = df['Close'].iloc[-2]
        change_pct = ((last_close_usd - prev_close_usd) / prev_close_usd) * 100
        
        # --- LOGIKA KONVERSI HARGA (VERSION 2.0) ---
        if asset_info['is_gold']:
            # Konversi Emas Dunia (Troy Ounce) ke Emas Pluang (Gram)
            # 1 Troy Ounce = 31.1035 Gram
            price_idr = (last_close_usd / 31.1035) * usd_idr
            price_usd_display = last_close_usd # Tetap tampilkan harga per Ounce utk referensi
            unit_label = "/ gram"
            usd_label = "/ troy oz"
        else:
            # Konversi Aset Lain (Saham/Crypto) langsung kali kurs
            price_idr = last_close_usd * usd_idr
            price_usd_display = last_close_usd
            unit_label = "/ unit"
            usd_label = "/ USD"

        # --- TAMPILAN HARGA DUAL VERSION ---
        st.markdown("### 💰 Harga Terkini (Real-Time)")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        
        with c1:
            st.markdown(f"<div class='price-box'><div class='small-font'>Harga Rupiah (Estimasi Pluang)</div><div class='big-font' style='color:#00ff00'>Rp {price_idr:,.0f}</div><div class='small-font'>{unit_label}</div></div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"<div class='price-box'><div class='small-font'>Harga Global (USD)</div><div class='big-font' style='color:#FFD700'>${price_usd_display:,.2f}</div><div class='small-font'>{usd_label}</div></div>", unsafe_allow_html=True)
            
        with c3:
            # Perubahan Harga
            color = "green" if change_pct >= 0 else "red"
            st.markdown(f"<div class='price-box'><div class='small-font'>Perubahan 24 Jam</div><div class='big-font' style='color:{color}'>{change_pct:+.2f}%</div><div class='small-font'>vs Kemarin</div></div>", unsafe_allow_html=True)

        st.markdown("---")

        # 2. ANALISIS QUANTUM SCORE
        score, reasons = analyze_signal(df)
        
        st.markdown("### 🔮 Quantum Signal Analysis")
        cols_sig1, cols_sig2 = st.columns([1, 2])
        
        with cols_sig1:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Kekuatan Sinyal"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "white"},
                    'steps': [
                        {'range': [0, 40], 'color': "#ff4b4b"},
                        {'range': [40, 60], 'color': "#ffff00"},
                        {'range': [60, 100], 'color': "#00ff00"}],
                }
            ))
            fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="#0e1117")
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with cols_sig2:
            if score >= 75:
                st.markdown(f"<div class='signal-box buy-signal'>STRONG BUY 🚀<br><span style='font-size:1rem'>Momentum Sangat Kuat</span></div>", unsafe_allow_html=True)
            elif score >= 55:
                st.markdown(f"<div class='signal-box buy-signal' style='background-color:#003300'>BUY (ACCUMULATE) 🛒<br><span style='font-size:1rem'>Mulai Cicil Masuk</span></div>", unsafe_allow_html=True)
            elif score <= 25:
                st.markdown(f"<div class='signal-box sell-signal'>STRONG SELL 🛑<br><span style='font-size:1rem'>Pasar Sedang Jatuh</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='signal-box neutral-signal'>NEUTRAL / WAIT ✋<br><span style='font-size:1rem'>Tunggu Konfirmasi</span></div>", unsafe_allow_html=True)
            
            st.write("")
            st.caption("🔍 **Alasan Logis (Berdasarkan Data Live):**")
            for reason in reasons:
                st.text(f"• {reason}")

        # 3. CHART UTAMA
        st.markdown("### 📉 Grafik Teknikal")
        fig = go.Figure()
        # Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price USD'))
        # EMAs
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1.5), name='EMA 50'))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='blue', width=2), name='EMA 200'))
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark",
                          title=f"Pergerakan Global {selected_asset_name} (Basis USD)")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("Gagal mengambil data. Silakan refresh halaman.")

if __name__ == "__main__":
    main()
