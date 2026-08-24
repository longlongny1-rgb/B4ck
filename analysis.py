import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import pandas_ta as ta


# ==================== BASE INDICATORS (existing) ====================

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical indicators on a DataFrame with OHLCV columns."""
    if df.empty or len(df) < 50:
        return df

    # RSI
    df["RSI"] = ta.rsi(df["Close"], length=14)
    # MACD
    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["MACD"] = macd.get("MACD_12_26_9")
        df["MACD_signal"] = macd.get("MACDs_12_26_9")
        df["MACD_hist"] = macd.get("MACDh_12_26_9")
    # EMAs
    df["EMA_9"] = ta.ema(df["Close"], length=9)
    df["EMA_21"] = ta.ema(df["Close"], length=21)
    df["EMA_50"] = ta.ema(df["Close"], length=50)
    df["EMA_200"] = ta.ema(df["Close"], length=200)
    # ATR
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)
    # Bollinger Bands
    bb = ta.bbands(df["Close"], length=20, std=2)
    if bb is not None:
        # pandas-ta >=0.4.x uses "BBU_20_2.0_2.0" column naming
        df["BB_upper"] = bb.get("BBU_20_2.0") or bb.get("BBU_20_2.0_2.0")
        df["BB_middle"] = bb.get("BBM_20_2.0") or bb.get("BBM_20_2.0_2.0")
        df["BB_lower"] = bb.get("BBL_20_2.0") or bb.get("BBL_20_2.0_2.0")
    # Volume
    df["Volume_SMA"] = ta.sma(df["Volume"], length=20)
    # ADX
    adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)
    if adx is not None:
        df["ADX"] = adx.get("ADX_14")
        df["DMP"] = adx.get("DMP_14")
        df["DMN"] = adx.get("DMN_14")
    # Stochastic
    stoch = ta.stoch(df["High"], df["Low"], df["Close"])
    if stoch is not None:
        df["STOCH_K"] = stoch.get("STOCHk_14_3_3")
        df["STOCH_D"] = stoch.get("STOCHd_14_3_3")
    # Support / Resistance
    df["Resistance"] = df["High"].rolling(window=20).max()
    df["Support"] = df["Low"].rolling(window=20).min()

    # -------- New indicators (pure pandas/numpy, no extra deps) --------
    df = _compute_ichimoku(df)
    df = _compute_vwap(df)
    df = _compute_psar(df)
    df = _compute_cmf(df)

    return df


# ==================== NEW: ICHIMOKU CLOUD ====================

def _compute_ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> pd.DataFrame:
    """Ichimoku Kinko Hyo. Adds Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span."""
    high, low, close = df["High"], df["Low"], df["Close"]

    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_line = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    chikou = close.shift(-kijun)

    df["ICHI_TENKAN"] = tenkan_sen
    df["ICHI_KIJUN"] = kijun_sen
    df["ICHI_SENKOU_A"] = senkou_a
    df["ICHI_SENKOU_B"] = senkou_b_line
    df["ICHI_CHIKOU"] = chikou
    return df


def _ichimoku_signal(df: pd.DataFrame) -> Optional[dict]:
    last = df.iloc[-1]
    close = last["Close"]
    tenkan = last.get("ICHI_TENKAN")
    kijun = last.get("ICHI_KIJUN")
    senkou_a = last.get("ICHI_SENKOU_A")
    senkou_b = last.get("ICHI_SENKOU_B")

    vals = [tenkan, kijun, senkou_a, senkou_b]
    if any(v is None or pd.isna(v) for v in vals):
        return None

    cloud_top = max(senkou_a, senkou_b)
    cloud_bottom = min(senkou_a, senkou_b)
    tk_bull = tenkan > kijun

    if close > cloud_top and tk_bull:
        return {"signal": "BUY", "value": round(close, 2), "reason": "Above cloud + Tenkan>Kijun (strong bullish)"}
    if close < cloud_bottom and not tk_bull:
        return {"signal": "SELL", "value": round(close, 2), "reason": "Below cloud + Tenkan<Kijun (strong bearish)"}
    if close > cloud_top:
        return {"signal": "BUY", "value": round(close, 2), "reason": "Price above Kumo cloud"}
    if close < cloud_bottom:
        return {"signal": "SELL", "value": round(close, 2), "reason": "Price below Kumo cloud"}
    return {"signal": "NEUTRAL", "value": round(close, 2), "reason": "Price inside cloud (indecision zone)"}


# ==================== NEW: FIBONACCI RETRACEMENT ====================

def get_fibonacci_levels(df: pd.DataFrame, lookback: int = 100) -> Optional[dict]:
    """Auto-detect the most recent significant swing high/low and compute Fib retracement levels."""
    window = df.tail(lookback)
    if len(window) < 10:
        return None

    swing_high = window["High"].max()
    swing_low = window["Low"].min()
    high_idx = window["High"].idxmax()
    low_idx = window["Low"].idxmin()
    uptrend = low_idx < high_idx  # low occurred before high => retracement measured downward from high

    diff = swing_high - swing_low
    if diff <= 0:
        return None

    ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    levels = {}
    for r in ratios:
        if uptrend:
            levels[f"{r}"] = round(swing_high - diff * r, 4)
        else:
            levels[f"{r}"] = round(swing_low + diff * r, 4)

    return {
        "direction": "uptrend_retracement" if uptrend else "downtrend_retracement",
        "swing_high": round(swing_high, 4),
        "swing_low": round(swing_low, 4),
        "levels": levels,
    }


def _fibonacci_signal(df: pd.DataFrame) -> Optional[dict]:
    fib = get_fibonacci_levels(df)
    if not fib:
        return None
    close = df.iloc[-1]["Close"]
    levels = fib["levels"]

    # Find nearest fib level to current price
    nearest_key = min(levels, key=lambda k: abs(levels[k] - close))
    nearest_val = levels[nearest_key]
    proximity_pct = abs(close - nearest_val) / close * 100 if close else 100

    golden_zone = (levels["0.618"], levels["0.5"]) if fib["direction"] == "uptrend_retracement" else (levels["0.5"], levels["0.618"])
    in_golden_zone = min(golden_zone) <= close <= max(golden_zone)

    if in_golden_zone and fib["direction"] == "uptrend_retracement":
        return {"signal": "BUY", "value": round(close, 2), "reason": f"Price in golden zone (61.8%-50%) of uptrend retracement"}
    if in_golden_zone and fib["direction"] == "downtrend_retracement":
        return {"signal": "SELL", "value": round(close, 2), "reason": f"Price in golden zone (50%-61.8%) of downtrend retracement"}
    if proximity_pct < 0.3:
        bias = "BUY" if fib["direction"] == "uptrend_retracement" else "SELL"
        return {"signal": bias, "value": round(close, 2), "reason": f"Price at Fib {nearest_key} level (${nearest_val})"}
    return {"signal": "NEUTRAL", "value": round(close, 2), "reason": f"Nearest Fib level: {nearest_key} (${nearest_val})"}


# ==================== NEW: CANDLESTICK PATTERN RECOGNITION ====================

def detect_candlestick_patterns(df: pd.DataFrame, lookback: int = 5) -> list[dict]:
    """Detect common reversal/continuation candlestick patterns in the last `lookback` candles.
    Pure pandas/numpy implementation — no TA-Lib dependency required."""
    if len(df) < lookback + 2:
        return []

    window = df.tail(lookback + 2).copy()
    patterns = []

    o, h, l, c = window["Open"], window["High"], window["Low"], window["Close"]
    body = (c - o).abs()
    candle_range = (h - l).replace(0, np.nan)
    upper_wick = h - np.maximum(o, c)
    lower_wick = np.minimum(o, c) - l
    body_pct = (body / candle_range).fillna(0)

    n = len(window)
    for i in range(2, n):
        idx = window.index[i]
        bp = body_pct.iloc[i]
        rng = candle_range.iloc[i]
        if pd.isna(rng) or rng == 0:
            continue
        is_bull = c.iloc[i] > o.iloc[i]
        is_bear = c.iloc[i] < o.iloc[i]

        # Doji: very small body relative to range
        if bp < 0.1:
            patterns.append({"index": str(idx), "name": "Doji", "type": "NEUTRAL",
                              "note": "Indecision — potential reversal if at trend extreme"})

        # Hammer / Hanging Man: small body near top, long lower wick
        elif lower_wick.iloc[i] > body.iloc[i] * 2 and upper_wick.iloc[i] < body.iloc[i] * 0.5:
            prior_trend_down = c.iloc[i - 2] > c.iloc[i]
            name = "Hammer" if prior_trend_down else "Hanging Man"
            ptype = "BULLISH" if prior_trend_down else "BEARISH"
            patterns.append({"index": str(idx), "name": name, "type": ptype,
                              "note": "Long lower wick rejection"})

        # Shooting Star / Inverted Hammer: small body near bottom, long upper wick
        elif upper_wick.iloc[i] > body.iloc[i] * 2 and lower_wick.iloc[i] < body.iloc[i] * 0.5:
            prior_trend_up = c.iloc[i - 2] < c.iloc[i]
            name = "Shooting Star" if prior_trend_up else "Inverted Hammer"
            ptype = "BEARISH" if prior_trend_up else "BULLISH"
            patterns.append({"index": str(idx), "name": name, "type": ptype,
                              "note": "Long upper wick rejection"})

        # Bullish / Bearish Engulfing
        prev_is_bear = c.iloc[i - 1] < o.iloc[i - 1]
        prev_is_bull = c.iloc[i - 1] > o.iloc[i - 1]
        if is_bull and prev_is_bear and c.iloc[i] > o.iloc[i - 1] and o.iloc[i] < c.iloc[i - 1]:
            patterns.append({"index": str(idx), "name": "Bullish Engulfing", "type": "BULLISH",
                              "note": "Current candle fully engulfs prior bearish candle"})
        elif is_bear and prev_is_bull and o.iloc[i] > c.iloc[i - 1] and c.iloc[i] < o.iloc[i - 1]:
            patterns.append({"index": str(idx), "name": "Bearish Engulfing", "type": "BEARISH",
                              "note": "Current candle fully engulfs prior bullish candle"})

        # Morning Star / Evening Star (3-candle pattern)
        if i >= 2:
            c0_bear = c.iloc[i - 2] < o.iloc[i - 2]
            c0_bull = c.iloc[i - 2] > o.iloc[i - 2]
            small_mid = body_pct.iloc[i - 1] < 0.3
            if c0_bear and small_mid and is_bull and c.iloc[i] > (o.iloc[i - 2] + c.iloc[i - 2]) / 2:
                patterns.append({"index": str(idx), "name": "Morning Star", "type": "BULLISH",
                                  "note": "3-candle bottom reversal"})
            if c0_bull and small_mid and is_bear and c.iloc[i] < (o.iloc[i - 2] + c.iloc[i - 2]) / 2:
                patterns.append({"index": str(idx), "name": "Evening Star", "type": "BEARISH",
                                  "note": "3-candle top reversal"})

    return patterns[-6:]  # most recent findings


def _candlestick_signal(df: pd.DataFrame) -> Optional[dict]:
    patterns = detect_candlestick_patterns(df, lookback=3)
    if not patterns:
        return {"signal": "NEUTRAL", "value": 0, "reason": "No significant pattern detected"}
    recent = patterns[-1]
    sig = "BUY" if recent["type"] == "BULLISH" else "SELL" if recent["type"] == "BEARISH" else "NEUTRAL"
    return {"signal": sig, "value": recent["name"], "reason": f"{recent['name']} — {recent['note']}"}


# ==================== NEW: VWAP ====================

def _compute_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Volume Weighted Average Price, reset daily (grouped by calendar date)."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    tp_vol = typical_price * df["Volume"]
    day_key = df.index.date
    df["VWAP"] = pd.Series(tp_vol, index=df.index).groupby(day_key).cumsum() / \
        pd.Series(df["Volume"], index=df.index).groupby(day_key).cumsum().replace(0, np.nan)
    return df


def _vwap_signal(df: pd.DataFrame) -> Optional[dict]:
    last = df.iloc[-1]
    vwap = last.get("VWAP")
    close = last["Close"]
    if vwap is None or pd.isna(vwap):
        return None
    diff_pct = (close - vwap) / vwap * 100
    if close > vwap:
        return {"signal": "BUY", "value": round(diff_pct, 2), "reason": f"Price {diff_pct:.2f}% above VWAP"}
    else:
        return {"signal": "SELL", "value": round(diff_pct, 2), "reason": f"Price {diff_pct:.2f}% below VWAP"}


# ==================== NEW: PARABOLIC SAR ====================

def _compute_psar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.2) -> pd.DataFrame:
    """Parabolic SAR — manual implementation (Wilder's method)."""
    high, low = df["High"].values, df["Low"].values
    n = len(df)
    psar = np.zeros(n)
    bull = True
    af = af_step
    ep = low[0]
    psar[0] = high[0]

    for i in range(1, n):
        prev_psar = psar[i - 1]
        if bull:
            psar[i] = prev_psar + af * (ep - prev_psar)
            psar[i] = min(psar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < psar[i]:
                bull = False
                psar[i] = ep
                ep = low[i]
                af = af_step
        else:
            psar[i] = prev_psar + af * (ep - prev_psar)
            psar[i] = max(psar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > psar[i]:
                bull = True
                psar[i] = ep
                ep = high[i]
                af = af_step

    df["PSAR"] = psar
    return df


def _psar_signal(df: pd.DataFrame) -> Optional[dict]:
    last = df.iloc[-1]
    psar = last.get("PSAR")
    close = last["Close"]
    if psar is None or pd.isna(psar):
        return None
    if close > psar:
        return {"signal": "BUY", "value": round(psar, 4), "reason": f"Price above PSAR (${psar:.4f}) — uptrend"}
    else:
        return {"signal": "SELL", "value": round(psar, 4), "reason": f"Price below PSAR (${psar:.4f}) — downtrend"}


# ==================== NEW: CHAIKIN MONEY FLOW ====================

def _compute_cmf(df: pd.DataFrame, length: int = 20) -> pd.DataFrame:
    mfm = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"]).replace(0, np.nan)
    mfv = mfm * df["Volume"]
    df["CMF"] = mfv.rolling(length).sum() / df["Volume"].rolling(length).sum().replace(0, np.nan)
    return df


def _cmf_signal(df: pd.DataFrame) -> Optional[dict]:
    last = df.iloc[-1]
    cmf = last.get("CMF")
    if cmf is None or pd.isna(cmf):
        return None
    if cmf > 0.05:
        return {"signal": "BUY", "value": round(cmf, 3), "reason": f"CMF={cmf:.3f} — money flowing in (accumulation)"}
    elif cmf < -0.05:
        return {"signal": "SELL", "value": round(cmf, 3), "reason": f"CMF={cmf:.3f} — money flowing out (distribution)"}
    else:
        return {"signal": "NEUTRAL", "value": round(cmf, 3), "reason": f"CMF={cmf:.3f} — balanced flow"}


# ==================== SIGNAL AGGREGATION (existing + new) ====================

def get_indicator_signals(df: pd.DataFrame) -> Dict[str, dict]:
    """Generate individual buy/sell/neutral signals from each indicator."""
    signals = {}
    if df.empty or len(df) < 50:
        return {"error": "not_enough_data"}

    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = last["Close"]

    # --- RSI ---
    rsi = last.get("RSI")
    if rsi is not None and not pd.isna(rsi):
        if rsi < 30:
            signals["RSI"] = {"signal": "BUY", "value": round(rsi, 1), "reason": f"Oversold (RSI={rsi:.1f})"}
        elif rsi > 70:
            signals["RSI"] = {"signal": "SELL", "value": round(rsi, 1), "reason": f"Overbought (RSI={rsi:.1f})"}
        else:
            signals["RSI"] = {"signal": "NEUTRAL", "value": round(rsi, 1), "reason": f"Neutral (RSI={rsi:.1f})"}

    # --- MACD ---
    macd = last.get("MACD")
    macd_signal = last.get("MACD_signal")
    prev_macd = prev.get("MACD")
    prev_macd_signal = prev.get("MACD_signal")
    if all(v is not None and not pd.isna(v) for v in [macd, macd_signal, prev_macd, prev_macd_signal]):
        if prev_macd < prev_macd_signal and macd > macd_signal:
            signals["MACD"] = {"signal": "BUY", "value": round(macd, 4), "reason": "Bullish crossover"}
        elif prev_macd > prev_macd_signal and macd < macd_signal:
            signals["MACD"] = {"signal": "SELL", "value": round(macd, 4), "reason": "Bearish crossover"}
        elif macd > macd_signal:
            signals["MACD"] = {"signal": "BUY", "value": round(macd, 4), "reason": "Histogram above zero"}
        else:
            signals["MACD"] = {"signal": "SELL", "value": round(macd, 4), "reason": "Histogram below zero"}

    # --- EMA Crossover ---
    ema9 = last.get("EMA_9")
    ema21 = last.get("EMA_21")
    ema50 = last.get("EMA_50")
    ema200 = last.get("EMA_200")
    if all(v is not None and not pd.isna(v) for v in [ema9, ema21, ema50]):
        if ema9 > ema21 > ema50:
            signals["EMA"] = {"signal": "BUY", "value": round(ema9, 2), "reason": "EMA 9 > 21 > 50 (Bullish trend)"}
        elif ema9 < ema21 < ema50:
            signals["EMA"] = {"signal": "SELL", "value": round(ema9, 2), "reason": "EMA 9 < 21 < 50 (Bearish trend)"}
        elif ema9 > ema21:
            signals["EMA"] = {"signal": "BUY", "value": round(ema9, 2), "reason": "EMA 9 above 21 (Short-term bullish)"}
        else:
            signals["EMA"] = {"signal": "SELL", "value": round(ema9, 2), "reason": "EMA 9 below 21 (Short-term bearish)"}

    # --- Bollinger Bands ---
    bb_lower = last.get("BB_lower")
    bb_upper = last.get("BB_upper")
    bb_middle = last.get("BB_middle")
    if all(v is not None and not pd.isna(v) for v in [bb_lower, bb_upper, bb_middle]):
        if close <= bb_lower:
            signals["BB"] = {"signal": "BUY", "value": round(close, 2), "reason": "Price at lower band (oversold)"}
        elif close >= bb_upper:
            signals["BB"] = {"signal": "SELL", "value": round(close, 2), "reason": "Price at upper band (overbought)"}
        elif close > bb_middle:
            signals["BB"] = {"signal": "BUY", "value": round(close, 2), "reason": "Above middle band"}
        else:
            signals["BB"] = {"signal": "SELL", "value": round(close, 2), "reason": "Below middle band"}

    # --- ADX ---
    adx = last.get("ADX")
    dmp = last.get("DMP")
    dmn = last.get("DMN")
    if all(v is not None and not pd.isna(v) for v in [adx, dmp, dmn]):
        if adx > 25:
            if dmp > dmn:
                signals["ADX"] = {"signal": "BUY", "value": round(adx, 1), "reason": f"Strong trend (ADX={adx:.1f}, +DI > -DI)"}
            else:
                signals["ADX"] = {"signal": "SELL", "value": round(adx, 1), "reason": f"Strong trend (ADX={adx:.1f}, -DI > +DI)"}
        else:
            signals["ADX"] = {"signal": "NEUTRAL", "value": round(adx, 1), "reason": f"Weak trend (ADX={adx:.1f}, range market)"}

    # --- Stochastic ---
    stoch_k = last.get("STOCH_K")
    stoch_d = last.get("STOCH_D")
    if all(v is not None and not pd.isna(v) for v in [stoch_k, stoch_d]):
        if stoch_k < 20 and stoch_d < 20:
            signals["STOCH"] = {"signal": "BUY", "value": round(stoch_k, 1), "reason": f"Oversold (K={stoch_k:.1f})"}
        elif stoch_k > 80 and stoch_d > 80:
            signals["STOCH"] = {"signal": "SELL", "value": round(stoch_k, 1), "reason": f"Overbought (K={stoch_k:.1f})"}
        else:
            signals["STOCH"] = {"signal": "NEUTRAL", "value": round(stoch_k, 1), "reason": f"Neutral (K={stoch_k:.1f})"}

    # --- Volume ---
    vol = last.get("Volume")
    vol_sma = last.get("Volume_SMA")
    if vol is not None and vol_sma is not None and not pd.isna(vol_sma) and vol_sma > 0:
        if vol > vol_sma * 1.5:
            signals["VOLUME"] = {"signal": "CONFIRM", "value": round(vol / vol_sma, 1), "reason": f"High volume ({vol/vol_sma:.1f}x avg)"}
        else:
            signals["VOLUME"] = {"signal": "NEUTRAL", "value": round(vol / vol_sma, 1), "reason": f"Normal volume"}

    # --- Price vs EMAs ---
    if ema200 is not None and not pd.isna(ema200):
        if close > ema200:
            signals["TREND_LONG"] = {"signal": "BUY", "value": round(close, 2), "reason": "Price above EMA 200 (Bullish macro)"}
        else:
            signals["TREND_LONG"] = {"signal": "SELL", "value": round(close, 2), "reason": "Price below EMA 200 (Bearish macro)"}

    # --- NEW: Ichimoku Cloud ---
    ichi = _ichimoku_signal(df)
    if ichi:
        signals["ICHIMOKU"] = ichi

    # --- NEW: Fibonacci Retracement ---
    fib = _fibonacci_signal(df)
    if fib:
        signals["FIBONACCI"] = fib

    # --- NEW: Candlestick Pattern ---
    candle = _candlestick_signal(df)
    if candle:
        signals["CANDLESTICK"] = candle

    # --- NEW: VWAP ---
    vwap = _vwap_signal(df)
    if vwap:
        signals["VWAP"] = vwap

    # --- NEW: Parabolic SAR ---
    psar = _psar_signal(df)
    if psar:
        signals["PSAR"] = psar

    # --- NEW: Chaikin Money Flow ---
    cmf = _cmf_signal(df)
    if cmf:
        signals["CMF"] = cmf

    return signals


def get_atr_levels(df: pd.DataFrame) -> Optional[dict]:
    """Extract ATR-based Stop Loss and Take Profit levels."""
    last = df.iloc[-1]
    atr = last.get("ATR")
    close = last["Close"]
    if atr is None or pd.isna(atr) or atr == 0:
        return None
    return {
        "ATR": round(atr, 4),
        "SL_1x": round(close - atr, 2),
        "TP_1x": round(close + atr, 2),
        "TP_1_5x": round(close + atr * 1.5, 2),
        "TP_2x": round(close + atr * 2, 2),
        "SL_1_5x": round(close - atr * 1.5, 2),
    }


def get_support_resistance(df: pd.DataFrame) -> dict:
    """Get recent support and resistance levels."""
    last = df.iloc[-1]
    return {
        "support": round(last.get("Support", last["Low"]), 2),
        "resistance": round(last.get("Resistance", last["High"]), 2),
        "close": round(last["Close"], 2),
    }


def compute_full_analysis(df: pd.DataFrame) -> dict:
    """Run full technical analysis and return structured results."""
    df = compute_all_indicators(df)
    signals = get_indicator_signals(df)
    atr = get_atr_levels(df)
    sr = get_support_resistance(df)
    fib = get_fibonacci_levels(df)
    patterns = detect_candlestick_patterns(df)
    return {
        "signals": signals,
        "atr": atr,
        "support_resistance": sr,
        "fibonacci": fib,
        "candlestick_patterns": patterns,
        "last_price": round(df.iloc[-1]["Close"], 4),
    }
