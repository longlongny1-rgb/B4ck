from dataclasses import dataclass
from typing import Optional, Tuple
import json

from market_data import fetch_ohlcv
from analysis import compute_full_analysis
from config import MARKETS


@dataclass
class TradingSignal:
    symbol: str
    direction: str  # BUY, SELL, NEUTRAL
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: int  # 0-100
    timeframe: str
    indicators: dict
    summary: str
    atr_data: Optional[dict]


def generate_signal(symbol_name: str, timeframe: str = "1h") -> Optional[TradingSignal]:
    """Generate an AI trading signal by aggregating all technical indicators."""
    symbol_name = symbol_name.upper()
    if symbol_name not in MARKETS:
        return None

    market = MARKETS[symbol_name]

    # Map timeframe to yfinance params
    tf_map = {
        "15m": ("15m", "5d"),
        "1h": ("1h", "30d"),
        "4h": ("1h", "60d"),
        "1d": ("1d", "90d"),
    }
    interval, period = tf_map.get(timeframe, ("1h", "30d"))

    df = fetch_ohlcv(symbol_name, interval=interval, period=period)
    if df is None or df.empty or len(df) < 50:
        return None

    analysis = compute_full_analysis(df)
    signals = analysis.get("signals", {})
    atr_data = analysis.get("atr", {})
    sr = analysis.get("support_resistance", {})
    last_price = analysis.get("last_price", df.iloc[-1]["Close"])

    if "error" in signals:
        return None

    # Score each indicator
    buy_score = 0
    sell_score = 0
    total_weight = 0

    weights = {
        "RSI": 1.5,
        "MACD": 1.2,
        "EMA": 1.5,
        "BB": 0.8,
        "ADX": 1.0,
        "STOCH": 0.8,
        "TREND_LONG": 1.2,
        "VOLUME": 0.5,
    }

    for indicator, data in signals.items():
        w = weights.get(indicator, 1.0)
        total_weight += w
        sig = data.get("signal", "NEUTRAL")
        if sig == "BUY":
            buy_score += w
        elif sig == "SELL":
            sell_score += w

    # Calculate confidence as percentage of max possible score
    max_score = max(buy_score, sell_score)
    if total_weight > 0:
        confidence = min(round((max_score / total_weight) * 100), 95)
    else:
        confidence = 50

    # Determine direction
    score_ratio = buy_score / max(sell_score, 0.01)
    if buy_score > sell_score:
        direction = "BUY"
    elif sell_score > buy_score:
        direction = "SELL"
    else:
        direction = "NEUTRAL"

    # If signals are too close, reduce confidence
    if min(buy_score, sell_score) > 0 and max_score > 0:
        ratio_diff = abs(buy_score - sell_score) / max_score
        if ratio_diff < 0.2:
            direction = "NEUTRAL"
            confidence = max(round(confidence * 0.6), 30)

    # Calculate SL/TP using ATR
    if atr_data and direction != "NEUTRAL":
        atr_val = atr_data["ATR"]
        if direction == "BUY":
            stop_loss = round(last_price - atr_val * 1.5, 4)
            take_profit = round(last_price + atr_val * 2.5, 4)
        else:
            stop_loss = round(last_price + atr_val * 1.5, 4)
            take_profit = round(last_price - atr_val * 2.5, 4)
    elif direction != "NEUTRAL":
        sl_mult = 0.01
        tp_mult = 0.025
        if "XAU" in symbol_name:
            sl_mult, tp_mult = 0.005, 0.012
        if direction == "BUY":
            stop_loss = round(last_price * (1 - sl_mult), 4)
            take_profit = round(last_price * (1 + tp_mult), 4)
        else:
            stop_loss = round(last_price * (1 + sl_mult), 4)
            take_profit = round(last_price * (1 - tp_mult), 4)
    else:
        stop_loss = 0
        take_profit = 0

    # Build summary
    strong_signals = [k for k, v in signals.items() if v["signal"] == direction]
    reasons = [f"{k}: {signals[k]['reason']}" for k in strong_signals[:5]]

    if direction == "NEUTRAL":
        summary = f"មិនមានសញ្ញាច្បាស់លាស់ — រង់ចាំមើល\nReasons: {', '.join(reasons) if reasons else 'Mixed signals'}"
    elif direction == "BUY":
        strength = "ខ្លាំង" if confidence >= 70 else "មធ្យម" if confidence >= 50 else "ខ្សោយ"
        summary = f"សញ្ញា {strength} — ទិញ {market.name}\n{', '.join(reasons)}"
    else:
        strength = "ខ្លាំង" if confidence >= 70 else "មធ្យម" if confidence >= 50 else "ខ្សោយ"
        summary = f"សញ្ញា {strength} — លក់ {market.name}\n{', '.join(reasons)}"

    return TradingSignal(
        symbol=symbol_name,
        direction=direction,
        entry_price=round(last_price, 4),
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence=confidence,
        timeframe=timeframe,
        indicators=signals,
        summary=summary,
        atr_data=atr_data,
    )


def format_signal_message(sig: TradingSignal) -> str:
    """Format a signal as a beautiful Telegram message (Khmer/English bilingual)."""
    market = MARKETS.get(sig.symbol)
    emoji = market.emoji if market else "📊"
    name = market.name if market else sig.symbol

    dir_map = {"BUY": "ទិញ ⬆️🟢", "SELL": "លក់ ⬇️🔴", "NEUTRAL": "រង់ចាំ ⏸️🟡"}
    conf_bar = "█" * (sig.confidence // 10) + "░" * (10 - sig.confidence // 10)

    msg = f"""{emoji} *AI SIGNAL — {sig.symbol}* {emoji}
━━━━━━━━━━━━━━━━━━━
📊 *{name}*
⏱ Timeframe: {sig.timeframe}

*សញ្ញា / SIGNAL:* {dir_map.get(sig.direction, sig.direction)}

⚡ ទំនុកចិត្ត / Confidence: *{sig.confidence}%*
[{conf_bar}]

━━━━━━━━━━━━━━━━━━━
💰 *តម្លៃចូល / Entry:* `${sig.entry_price:,.4f}`
🛑 *Stop Loss:* `${sig.stop_loss:,.4f}`
🎯 *Take Profit:* `${sig.take_profit:,.4f}`
"""

    if sig.direction != "NEUTRAL":
        if sig.direction == "BUY":
            risk = round(sig.entry_price - sig.stop_loss, 4)
            reward = round(sig.take_profit - sig.entry_price, 4)
        else:
            risk = round(sig.stop_loss - sig.entry_price, 4)
            reward = round(sig.entry_price - sig.take_profit, 4)
        rr = round(reward / risk, 2) if risk > 0 else 0
        msg += f"""━━━━━━━━━━━━━━━━━━━
⚖️ *Risk / Reward:* 1:{rr}
📉 Risk: ${risk:,.4f}
📈 Reward: ${reward:,.4f}
"""

    # Indicator breakdown
    msg += "\n━━━━━━━━━━━━━━━━━━━\n🔍 *ការវិភាគ / Analysis:*\n"
    for ind, data in sig.indicators.items():
        icon = "🟢" if data["signal"] == "BUY" else "🔴" if data["signal"] == "SELL" else "⚪"
        msg += f"{icon} *{ind}:* {data['reason']}\n"

    msg += f"\n📝 *សង្ខេប:* {sig.summary}\n"
    msg += f"\n⚠️ _Signals are for educational purposes only. Not financial advice._"

    return msg


def format_analysis_message(analysis: dict, symbol_name: str) -> str:
    """Format full technical analysis as a Telegram message."""
    market = MARKETS.get(symbol_name.upper())
    emoji = market.emoji if market else ""
    name = market.name if market else symbol_name

    signals = analysis.get("signals", {})
    atr = analysis.get("atr", {})
    sr = analysis.get("support_resistance", {})
    price = analysis.get("last_price", 0)

    buy_count = sum(1 for v in signals.values() if v["signal"] == "BUY")
    sell_count = sum(1 for v in signals.values() if v["signal"] == "SELL")
    neutral_count = sum(1 for v in signals.values() if v["signal"] == "NEUTRAL")

    msg = f"""{emoji} *ការវិភាគបច្ចេកទេស / TECHNICAL ANALYSIS*
━━━━━━━━━━━━━━━━━━━
📊 *{name} ({symbol_name})*
💰 តម្លៃ: ${price:,.4f}

📈 សញ្ញាទិញ: {buy_count}  |  📉 សញ្ញាលក់: {sell_count}  |  ⏸️ Neutral: {neutral_count}

━━━━━━━━━━━━━━━━━━━
*INDICATORS:*
"""

    for ind, data in signals.items():
        icon = "🟢" if data["signal"] == "BUY" else "🔴" if data["signal"] == "SELL" else "⚪"
        val = data.get("value", "")
        val_str = f" ({val})" if val else ""
        msg += f"{icon} *{ind}*{val_str}: {data['reason']}\n"

    if atr:
        msg += f"""
━━━━━━━━━━━━━━━━━━━
*ATR LEVELS:*
📏 ATR(14): {atr['ATR']}
🛑 SL 1x ATR: ${atr['SL_1x']:,}
🎯 TP 1x ATR: ${atr['TP_1x']:,}
🎯 TP 1.5x ATR: ${atr['TP_1_5x']:,}
🎯 TP 2x ATR: ${atr['TP_2x']:,}
"""

    if sr:
        s = sr["support"]
        r = sr["resistance"]
        c = sr["close"]
        msg += f"""
━━━━━━━━━━━━━━━━━━━
*SUPPORT / RESISTANCE:*
🔻 Support: ${s:,}
🔺 Resistance: ${r:,}
📍 Current: ${c:,}
📏 Range: ${round(r - s, 2):,}
"""

    msg += "\n⚠️ _For educational purposes only. Not financial advice._"
    return msg
