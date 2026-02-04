import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="GSS Quantum Analytics v9 - Confidence Level",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CUSTOM (Tampilan Profesional GSS) ---
st.markdown("""
<style>
    .main-header { 
        font-size: 2.5rem; 
        color: #FFD700; 
        text-align: center; 
        font-weight: bold; 
        margin-bottom: 0.5rem;
    }
    .sub-header { 
        font-size: 1.2rem; 
        color: #cccccc; 
        text-align: center; 
        margin-bottom: 2rem; 
    }
    .signal-box { 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center; 
        font-size: 1.5rem; 
        font-weight: bold; 
        margin-bottom: 1rem;
    }
    .confidence-box { 
        padding: 10px; 
        border-radius: 8px; 
        text-align: center; 
        font-size: 1.2rem; 
        font-weight: bold; 
        margin-top: 0.5rem;
    }
    .price-box { 
        background-color: #1E1E1E; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        border: 1px solid #444; 
    }
    .buy-signal { 
        background-color: #004d00; 
        color: #00ff00; 
        border: 2px solid #00ff00; 
    }
    .sell-signal { 
        background-color: #4d0000; 
        color: #ff4b4b; 
        border: 2px solid #ff4b4b; 
    }
    .neutral-signal { 
        background-color: #4d4d00; 
        color: #ffff00; 
        border: 2px solid #ffff00; 
    }
    .confidence-high { 
        background-color: #003300; 
        color: #00ff00; 
        border: 1px solid #00aa00; 
    }
    .confidence-medium { 
        background-color: #4d4d00; 
        color: #ffff00; 
        border: 1px solid #aaaa00; 
    }
    .confidence-low { 
        background-color: #4d4d00; 
        color: #ff8c00; 
        border: 1px solid #ff8c00; 
    }
    .risk-high { 
        background-color: #4d0000; 
        color: #ff4b4b; 
    }
    .risk-medium { 
        background-color: #4d4d00; 
        color: #ffff00; 
    }
    .risk-low { 
        background-color: #004d00; 
        color: #00ff00; 
    }
    .big-font { 
        font-size: 1.8rem; 
        font-weight: bold; 
    }
    .medium-font { 
        font-size: 1.2rem; 
    }
    .small-font { 
        font-size: 0.9rem; 
        color: #888; 
    }
    .info-card { 
        background-color: #2d2d2d; 
        padding: 10px; 
        border-radius: 8px; 
        margin: 5px 0; 
        border-left: 3px solid #FFD700;
    }
    /* Gaya untuk alasan sinyal */
    .signal-reason {
        margin-bottom: 0.2em;
        line-height: 1.4;
    }
    .hl-overbought { background-color: rgba(255, 75, 75, 0.2); padding: 2px 4px; border-radius: 3px; }
    .hl-oversold { background-color: rgba(0, 255, 0, 0.2); padding: 2px 4px; border-radius: 3px; }
    .hl-strong-trend { background-color: rgba(255, 215, 0, 0.2); padding: 2px 4px; border-radius: 3px; }
    .hl-volatility-info { background-color: rgba(135, 206, 250, 0.2); padding: 2px 4px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# --- DAFTAR ASET GSS ---
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
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 16000.0
    except:
        return 16000.0

@st.cache_data(ttl=60)
def get_market_data(ticker, period="1y"):
    """Mengambil data pasar dan menghitung indikator teknikal"""
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or 'Close' not in df.columns:
            if 'Adj Close' in df.columns:
                df['Close'] = df['Adj Close']
            else:
                return None

        # --- INDIKATOR TEKNIKAL (di basis USD) ---
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)

        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        if macd is not None:
            df['MACD'] = macd.iloc[:, 0]
            df['MACD_SIGNAL'] = macd.iloc[:, 2]

        # --- INOVASI SEBELUMNYA: Indikator Baru ---
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            df['BB_UPPER'] = bb.iloc[:, 0]
            df['BB_MIDDLE'] = bb.iloc[:, 1]
            df['BB_LOWER'] = bb.iloc[:, 2]

        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx is not None:
            df['ADX'] = adx['ADX_14']

        df['VOLATILITY_30D'] = df['Close'].rolling(window=30).std()

        # --- INOVASI: Average True Range (ATR) ---
        atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        if atr is not None:
            df['ATR'] = atr
        else:
            df['True_Range'] = df['High'] - df['Low']
            df['True_Range'] = df['True_Range'].combine(df['High'] - df['Close'].shift(), lambda x, y: max(x, abs(y)), fill_value=0)
            df['True_Range'] = df['True_Range'].combine(df['Close'].shift() - df['Low'], lambda x, y: max(x, abs(y)), fill_value=0)
            df['ATR'] = df['True_Range'].rolling(window=14).mean()

        return df

    except Exception as e:
        st.error(f"Error saat mengambil data: {e}")
        return None

def convert_price_to_idr(price_usd, is_gold, usd_idr_rate):
    """Fungsi utilitas untuk konversi harga USD ke IDR."""
    if is_gold:
        # 1 Troy Ounce = 31.1035 Gram
        return (price_usd / 31.1035) * usd_idr_rate
    else:
        return price_usd * usd_idr_rate

def analyze_signal(df, asset_is_gold, usd_idr_rate):
    """Analisis Sinyal Dinamis dengan integrasi nilai IDR dan Confidence Level."""
    if df is None: return 50, ["Data tidak tersedia"], 0.0, 0.0, 0

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    reasons = []
    confidence_points = 0 # Tambahkan variabel untuk menghitung kepercayaan

    volatility = last['VOLATILITY_30D'] if pd.notna(last['VOLATILITY_30D']) else 0.0
    adx_value = last['ADX'] if pd.notna(last['ADX']) else 0.0
    atr_value = last['ATR'] if pd.notna(last['ATR']) else 0.0

    # Konversi harga dan indikator ke IDR untuk digunakan dalam logika dan alasan
    price_now_idr = convert_price_to_idr(last['Close'], asset_is_gold, usd_idr_rate)
    ema200_idr = convert_price_to_idr(last['EMA_200'], asset_is_gold, usd_idr_rate)
    bb_upper_idr = convert_price_to_idr(last['BB_UPPER'], asset_is_gold, usd_idr_rate) if pd.notna(last['BB_UPPER']) else 0
    bb_lower_idr = convert_price_to_idr(last['BB_LOWER'], asset_is_gold, usd_idr_rate) if pd.notna(last['BB_LOWER']) else 0
    atr_value_idr = convert_price_to_idr(atr_value, asset_is_gold, usd_idr_rate)
    volatility_idr = convert_price_to_idr(volatility, asset_is_gold, usd_idr_rate)

    # 1. ANALISIS TREN (EMA)
    price_now = last['Close']
    ema200 = last['EMA_200']

    if pd.isna(ema200):
        reasons.append("Data EMA 200 belum cukup.")
    else:
        if price_now > ema200:
            gap = ((price_now - ema200) / ema200) * 100
            score += 25
            reasons.append(f"Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}) berada {gap:.1f}% DI ATAS garis tren jangka panjang (EMA 200: ${ema200:.2f} / Rp {ema200_idr:,.0f}). Pasar Bullish.")
            if last['EMA_50'] > ema200: # Konfirmasi tren menengah
                confidence_points += 1
                reasons.append("  -> EMA 50 > EMA 200, konfirmasi tren menengah naik.")
        else:
            gap = ((ema200 - price_now) / ema200) * 100
            score -= 25
            reasons.append(f"Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}) berada {gap:.1f}% DI BAWAH garis tren jangka panjang (EMA 200: ${ema200:.2f} / Rp {ema200_idr:,.0f}). Pasar Bearish.")
            if last['EMA_50'] < ema200: # Konfirmasi tren menengah
                confidence_points += 1
                reasons.append("  -> EMA 50 < EMA 200, konfirmasi tren menengah turun.")

    # Golden Cross / Death Cross (telah dihitung dalam EMA)
    if pd.notna(last['EMA_50']) and pd.notna(last['EMA_200']):
        if last['EMA_50'] > last['EMA_200']:
            score += 15
        elif last['EMA_50'] < last['EMA_200']:
            score -= 10

    # 2. ANALISIS MOMENTUM (RSI)
    rsi = last['RSI']
    if pd.isna(rsi):
        reasons.append("Data RSI tidak tersedia.")
    else:
        if rsi < 30:
            score += 35
            reasons.append(f"RSI Sangat Murah (Oversold) di level {rsi:.1f}. Potensi pantulan harga tinggi! Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")
            confidence_points += 1 # Oversold adalah sinyal kuat
        elif rsi > 70:
            score -= 25
            reasons.append(f"RSI Sangat Mahal (Overbought) di level {rsi:.1f}. Hati-hati koreksi. Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")
            confidence_points += 1 # Overbought adalah sinyal kuat
        elif 30 <= rsi <= 50:
            score += 10
            reasons.append(f"RSI di level {rsi:.1f} (Zona Akumulasi). Masih aman untuk masuk. Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")
        else: # 50-70
            score += 5
            reasons.append(f"RSI di level {rsi:.1f} (Zona Pertumbuhan). Momentum positif. Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")

    # 3. MACD Dynamic
    macd_val = last['MACD']
    macd_sig = last['MACD_SIGNAL']
    if pd.isna(macd_val) or pd.isna(macd_sig):
         reasons.append("Data MACD tidak tersedia.")
    else:
        if macd_val > macd_sig:
            score += 20
            reasons.append(f"MACD Line ({macd_val:.2f}) di atas Signal ({macd_sig:.2f}). Momentum beli aktif. Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")
            confidence_points += 1 # MACD crossover adalah sinyal kuat
        else:
            score -= 20
            reasons.append(f"MACD Line ({macd_val:.2f}) di bawah Signal ({macd_sig:.2f}). Tekanan jual masih ada. Harga (${price_now:.2f} / Rp {price_now_idr:,.0f}).")
            confidence_points += 1 # MACD crossover adalah sinyal kuat

    # --- INOVASI SEBELUMNYA: Logika dari Indikator Baru ---
    # 4. Bollinger Bands
    if pd.notna(last['BB_UPPER']) and pd.notna(last['BB_LOWER']):
        if price_now > last['BB_UPPER']:
            score -= 30
            reasons.append(f"Harga MENEMBUS Band Atas (${last['BB_UPPER']:.2f} / Rp {bb_upper_idr:,.0f}). Potensi overbought, koreksi mungkin terjadi.")
            confidence_points += 1 # Breakout atas adalah sinyal kuat
        elif price_now < last['BB_LOWER']:
            score += 30
            reasons.append(f"Harga MENEMBUS Band Bawah (${last['BB_LOWER']:.2f} / Rp {bb_lower_idr:,.0f}). Potensi oversold, bounce mungkin terjadi.")
            confidence_points += 1 # Breakout bawah adalah sinyal kuat
        else:
            reasons.append(f"Harga berada di dalam Bollinger Bands. Rentang normal (${last['BB_LOWER']:.2f} - ${last['BB_UPPER']:.2f} / Rp {bb_lower_idr:,.0f} - Rp {bb_upper_idr:,.0f}).")

    # 5. ADX (Kekuatan Tren)
    if adx_value > 25:
        if abs(score) > 20: # Jika skor sudah menunjukkan arah jelas
            score = int(max(0, min(100, (50 + score) * 1.1))) # Perkuat sinyal karena tren kuat
            reasons.append(f"ADX menunjukkan tren sangat kuat (>{adx_value:.1f}). Sinyal dipertegas.")
            confidence_points += 1 # Tren kuat meningkatkan kepercayaan
        else:
            reasons.append(f"ADX menunjukkan tren sedang ({adx_value:.1f}). Harap konfirmasi sinyal lain.")
    else:
        reasons.append(f"ADX menunjukkan tren lemah ({adx_value:.1f}). Sinyal bisa jadi tidak akurat.")
        # Tidak menambah confidence_points karena tren lemah


    # --- INOVASI: Logika berdasarkan ATR ---
    # 6. ATR (Average True Range / Volatilitas)
    if atr_value > 0:
        prev_close_idr = convert_price_to_idr(prev['Close'], asset_is_gold, usd_idr_rate)
        price_change_abs = abs(price_now - prev['Close'])
        price_change_abs_idr = abs(price_now_idr - prev_close_idr)
        if price_change_abs > atr_value:
            reasons.append(f"Pergerakan harga (${price_change_abs:.2f} / Rp {price_change_abs_idr:,.0f}) MELEBIHI ATR (${atr_value:.2f} / Rp {atr_value_idr:.0f}), menunjukkan aktivitas tinggi.")
        elif price_change_abs < atr_value * 0.5:
            reasons.append(f"Pergerakan harga (${price_change_abs:.2f} / Rp {price_change_abs_idr:,.0f}) di bawah separuh ATR, menunjukkan konsolidasi.")
        reasons.append(f"Level volatilitas saat ini (ATR 14d): ${atr_value:.2f} / Rp {atr_value_idr:.0f}. Ini penting untuk manajemen risiko (Stop-Loss).")


    # Normalisasi Score 0-100 (akhir setelah semua modifikasi)
    final_score = max(0, min(100, 50 + score))

    # --- INOVASI: Hitung Tingkat Kepercayaan ---
    # Misalnya, 0-2 poin = Rendah, 3-4 = Sedang, 5+ = Tinggi
    if confidence_points >= 5:
        confidence_level = 3 # Tinggi
        confidence_text = "Tinggi"
        confidence_style = "confidence-high"
    elif confidence_points >= 3:
        confidence_level = 2 # Sedang
        confidence_text = "Sedang"
        confidence_style = "confidence-medium"
    else:
        confidence_level = 1 # Rendah
        confidence_text = "Rendah"
        confidence_style = "confidence-low"

    return final_score, reasons, volatility_idr, atr_value_idr, confidence_level


# --- UI VISUALIZATION ---
def main():
    # Header
    st.markdown("<h1 class='main-header'>🦅 GSS QUANTUM ANALYTICS v9</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Gold Standard Society - Enhanced Analysis with Confidence</p>", unsafe_allow_html=True)

    # Sidebar
    st.sidebar.header("🎛️ Kontrol Panel")
    selected_asset_name = st.sidebar.selectbox("Pilih Aset:", list(ASSETS.keys()))
    asset_info = ASSETS[selected_asset_name]

    st.sidebar.markdown("---")

    # Process Data
    with st.spinner("Menghubungkan ke satelit data global..."):
        usd_idr = get_exchange_rate()
        st.sidebar.metric("Kurs USD/IDR Hari Ini", f"Rp {usd_idr:,.0f}")
        df = get_market_data(asset_info['ticker'])

    if df is not None and not df.empty:
        last_close_usd = df['Close'].iloc[-1]
        prev_close_usd = df['Close'].iloc[-2]
        change_pct = ((last_close_usd - prev_close_usd) / prev_close_usd) * 100

        # --- KONVERSI HARGA GLOBAL UNTUK UI ---
        last_close_idr = convert_price_to_idr(last_close_usd, asset_info["is_gold"], usd_idr)
        prev_close_idr = convert_price_to_idr(prev_close_usd, asset_info["is_gold"], usd_idr)
        change_idr = last_close_idr - prev_close_idr

        # --- TAMPILAN HARGA DUAL VERSION (IDR di depan untuk kejelasan) ---
        st.markdown("### 💰 Harga Terkini (Real-Time - USD & IDR)")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])

        with c1:
            st.markdown(f"<div class='price-box'><div class='small-font'>Harga Rupiah (Estimasi)</div><div class='big-font' style='color:#00ff00'>Rp {last_close_idr:,.0f}</div><div class='small-font'>/ unit</div></div>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"<div class='price-box'><div class='small-font'>Harga Global (USD)</div><div class='big-font' style='color:#FFD700'>${last_close_usd:.2f}</div><div class='small-font'>/ unit</div></div>", unsafe_allow_html=True)

        with c3:
            color = "green" if change_pct >= 0 else "red"
            color_idr = "green" if change_idr >= 0 else "red"
            st.markdown(f"<div class='price-box'><div class='small-font'>Perubahan 24 Jam</div><div class='big-font' style='color:{color}'>{change_pct:+.2f}%</div><div class='small-font' style='color:{color_idr}'>Rp {change_idr:,.0f}</div></div>", unsafe_allow_html=True)

        st.markdown("---")

        # 2. ANALISIS QUANTUM SCORE, VOLATILITAS, ATR, dan CONFIDENCE LEVEL
        score, reasons, volatility_idr, atr_idr, confidence_level = analyze_signal(df, asset_info["is_gold"], usd_idr)

        st.markdown("### 🔮 Quantum Signal & Risk Analysis")
        cols_sig1, cols_sig2, cols_risk = st.columns([1, 2, 1])

        with cols_sig1:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Kekuatan Sinyal"},
                gauge={
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

            # --- INOVASI: Tampilkan Tingkat Kepercayaan ---
            if confidence_level == 3:
                conf_text = "Tingkat Kepercayaan: Sangat Tinggi (✅✅✅)"
            elif confidence_level == 2:
                conf_text = "Tingkat Kepercayaan: Sedang (✅✅)"
            else:
                conf_text = "Tingkat Kepercayaan: Rendah (✅)"

            st.markdown(f"<div class='confidence-box {'' if confidence_level == 3 else ('' if confidence_level == 2 else '')}'>{conf_text}</div>", unsafe_allow_html=True)

            st.write(" ")
            st.caption("🔍 **Alasan Logis (Berdasarkan Data Live - USD & IDR):**")
            for reason in reasons:
                 hl_class = ""
                 if "Oversold" in reason or "bounce" in reason.lower():
                     hl_class = "hl-oversold"
                 elif "Overbought" in reason or "koreksi" in reason.lower() or "menembus band atas" in reason.lower():
                     hl_class = "hl-overbought"
                 elif "tren sangat kuat" in reason.lower():
                     hl_class = "hl-strong-trend"
                 elif "ATR" in reason:
                     hl_class = "hl-volatility-info"
                 # --- Gunakan st.markdown dengan kelas CSS ---
                 st.markdown(f"<p class='signal-reason'>• <span class='{hl_class}'>{reason}</span></p>", unsafe_allow_html=True)


        with cols_risk:
             # --- Informasi Risiko & ATR (dengan nilai IDR) ---
             risk_level_str = "N/A"
             risk_style = "risk-medium"
             volatility_raw = df['VOLATILITY_30D'].iloc[-1] if pd.notna(df['VOLATILITY_30D'].iloc[-1]) else 0.0
             if volatility_raw != 0:
                 if volatility_raw < (last_close_usd * 0.02):
                     risk_level_str = "Rendah"
                     risk_style = "risk-low"
                 elif volatility_raw < (last_close_usd * 0.05):
                     risk_level_str = "Sedang"
                     risk_style = "risk-medium"
                 else:
                     risk_level_str = "Tinggi"
                     risk_style = "risk-high"

             st.markdown(f"<div class='info-card'><h4>📊 Risiko (Volatilitas 30D)</h4><p class='medium-font'>{risk_level_str}</p><p class='small-font'>Std Dev: ${volatility_raw:.2f} / Rp {volatility_idr:,.0f}</p></div>", unsafe_allow_html=True)
             
             adx_val = df['ADX'].iloc[-1] if pd.notna(df['ADX'].iloc[-1]) else 0.0
             adx_status = "Lemah" if adx_val < 25 else ("Sedang" if adx_val < 50 else "Kuat")
             st.markdown(f"<div class='info-card'><h4>🧭 Kekuatan Tren (ADX)</h4><p class='medium-font'>{adx_val:.1f}</p><p class='small-font'>{adx_status} ({'<25' if adx_val < 25 else ('25-50' if adx_val < 50 else '>50')})</p></div>", unsafe_allow_html=True)

             # --- INOVASI: Tampilkan ATR ---
             atr_raw = df['ATR'].iloc[-1] if pd.notna(df['ATR'].iloc[-1]) else 0.0
             if atr_raw > 0:
                 st.markdown(f"<div class='info-card'><h4>🌪️ Volatilitas (ATR 14D)</h4><p class='medium-font'>${atr_raw:.2f} / Rp {atr_idr:,.0f}</p><p class='small-font'>Rentang rata-rata pergerakan.</p></div>", unsafe_allow_html=True)
             else:
                 st.markdown(f"<div class='info-card'><h4>🌪️ Volatilitas (ATR 14D)</h4><p class='medium-font'>N/A</p><p class='small-font'>Data tidak tersedia.</p></div>", unsafe_allow_html=True)


        # 3. CHART UTAMA (tetap dalam USD)
        st.markdown("### 📉 Grafik Teknikal Lanjutan (USD)")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price (USD)', opacity=0.8))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='orange', width=1.5), name='EMA 50 (USD)', visible='legendonly'))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='blue', width=2), name='EMA 200 (USD)', visible='legendonly'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_UPPER'], line=dict(color='rgba(255, 0, 0, 0.3)', width=1), name='BB Upper (USD)', fill=None, visible='legendonly'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_LOWER'], line=dict(color='rgba(0, 255, 0, 0.3)', width=1), name='BB Lower (USD)', fill='tonexty', visible='legendonly'))

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=600,
            template="plotly_dark",
            title=f"Pergerakan Global {selected_asset_name} (Basis USD)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- INOVASI: Tabel Data Terbaru (FIXED - Kolom Unik) ---
        st.markdown("### 🧮 Data Terbaru (USD & Estimasi IDR)")
        latest_data_usd = df[['Close', 'EMA_20', 'EMA_50', 'EMA_200', 'RSI', 'MACD', 'BB_UPPER', 'BB_LOWER', 'ADX', 'ATR']].tail(1).round(2)
        latest_data_usd.index = [latest_data_usd.index[-1].strftime('%Y-%m-%d')]

        # Buat DataFrame estimasi IDR dengan nama kolom yang unik
        idr_cols = {}
        # Kolom yang perlu dikonversi ke IDR
        for col in ['Close', 'EMA_20', 'EMA_50', 'EMA_200', 'BB_UPPER', 'BB_LOWER', 'ATR']:
            if col in latest_data_usd.columns:
                original_val = latest_data_usd[col].iloc[0]
                converted_val = convert_price_to_idr(original_val, asset_info["is_gold"], usd_idr)
                idr_cols[f"{col}_Rp"] = converted_val # Simpan sebagai float untuk formatting nanti
        # Kolom yang nilainya tetap (RSI, MACD, ADX), tambahkan akhiran _Rp untuk membedakan
        for col in ['RSI', 'MACD', 'ADX']:
             if col in latest_data_usd.columns:
                idr_cols[f"{col}_Rp"] = latest_data_usd[col].iloc[0]

        latest_data_idr_df = pd.DataFrame([idr_cols], index=latest_data_usd.index)

        # Gabungkan USD dan Estimasi IDR
        latest_data_combined = pd.concat([latest_data_usd.add_suffix('_Usd'), latest_data_idr_df], axis=1)
        # Format ulang kolom Rupiah untuk tampilan (dengan koma)
        cols_to_format = [col for col in latest_data_combined.columns if col.endswith('_Rp')]
        for col in cols_to_format:
            if pd.api.types.is_numeric_dtype(latest_data_combined[col]):
                 if col.startswith('RSI') or col.startswith('MACD') or col.startswith('ADX'):
                     # Format sebagai angka desimal untuk RSI, MACD, ADX
                     latest_data_combined[col] = latest_data_combined[col].round(2)
                 else:
                     # Format sebagai Rupiah untuk harga
                     latest_data_combined[col] = latest_data_combined[col].apply(lambda x: f"Rp {x:,.0f}")

        st.dataframe(latest_data_combined, use_container_width=True)

        # --- INOVASI: Penjelasan Tingkat Kepercayaan ---
        st.markdown("### ℹ️ Panduan Tingkat Kepercayaan")
        st.info(
            "**Tinggi (✅✅✅):** Banyak indikator teknikal (RSI, MACD, EMA, ADX, Bollinger Bands) menunjukkan arah yang sama, meningkatkan probabilitas akurasi sinyal.\n\n"
            "**Sedang (✅✅):** Beberapa indikator mendukung sinyal utama, tetapi ada sedikit ketidakpastian atau konflik minor.\n\n"
            "**Rendah (✅):** Sinyal utama hadir, tetapi kurang didukung oleh indikator lainnya, atau ada banyak konflik antar-indikator. Disarankan untuk menunggu konfirmasi lebih lanjut."
        )


    else:
        st.error("Gagal mengambil data atau data kosong. Silakan refresh halaman atau pilih aset lain.")


if __name__ == "__main__":
    main()