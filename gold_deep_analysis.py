"""
BlackMagicAI OMEGA — XAUUSD Deep Analysis Engine
=================================================
A specialized, gold-only analysis layer that sits ON TOP of the generic
analysis.py / signals.py pipeline. Gold trades on a different set of drivers
than a generic equity or forex pair, so a generic multi-market signal engine
under-uses information that's specific and well-documented for XAUUSD:

  1. US Dollar Index (DXY)        — gold is priced in USD; near-permanent inverse correlation
  2. US 10Y Treasury yield        — proxy for real yields; gold is a zero-yield asset,
                                     so rising real yields raise the opportunity cost of holding it
  3. VIX (risk sentiment)         — gold's "safe haven" bid strengthens in risk-off regimes
  4. Gold/Silver ratio            — relative strength between precious metals; extremes tend
                                     to mean-revert and often lead broader metals-complex moves
  5. Seasonality                  — gold has a well-documented historical seasonal bias
                                     (e.g. strength around late summer / early autumn, and
                                     January), useful as a *minor* tilt, never a standalone signal
  6. Multi-timeframe confluence   — run the technical engine on 15m/1h/4h/1d simultaneously
                                     and require agreement across timeframes for high-confidence calls

None of this replaces analysis.py's technical indicators — it wraps them in a
gold-specific composite score. Every sub-score is transparent (reason strings)
so the final output can be audited, not just trusted blindly.
"""
import statistics
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import pandas as pd
import numpy as np

from market_data import fetch_ohlcv
from analysis import compute_full_analysis
from signals import generate_signal, TradingSignal
from config import MARKETS

GOLD_SYMBOL = "XAUUSD"

# yfinance tickers for intermarket instruments (not in config.MARKETS because
# they're inputs to the gold model, not tradable symbols the bot quotes directly)
INTERMARKET_TICKERS = {
    "DXY": "DX-Y.NYB",   # US Dollar Index
    "US10Y": "^TNX",     # 10-Year Treasury yield (CBOE, in tenths of a percent)
    "VIX": "^VIX",       # CBOE Volatility Index
    "SILVER": "SI=F",    # Silver futures, for Gold/Silver ratio
}

TIMEFRAMES_FOR_CONFLUENCE = ["15m", "1h", "4h", "1d"]

# Historically, gold has shown a seasonal bias in these months (Northern Hemisphere
# jewelry/festival demand cycles + year-end positioning). Kept as a MINOR tilt only.
SEASONAL_STRONG_MONTHS = {1, 8, 9, 11}   # Jan, Aug, Sep, Nov
SEASONAL_WEAK_MONTHS = {3, 6}            # Mar, Jun


# ==================== 1. INTERMARKET DATA ====================

def _fetch_intermarket_series(ticker: str, period: str = "30d", interval: str = "1d") -> Optional[pd.DataFrame]:
    import yfinance as yf
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def fetch_intermarket_snapshot() -> Dict[str, Optional[dict]]:
    """Pull the latest value + short-term trend (5-bar slope) for each intermarket driver."""
    snapshot = {}
    for name, ticker in INTERMARKET_TICKERS.items():
        df = _fetch_intermarket_series(ticker)
        if df is None or len(df) < 6:
            snapshot[name] = None
            continue
        last = df["Close"].iloc[-1]
        prior5 = df["Close"].iloc[-6]
        change_pct = (last - prior5) / prior5 * 100 if prior5 else 0
        snapshot[name] = {
            "last": round(float(last), 4),
            "change_5bar_pct": round(float(change_pct), 3),
        }
    return snapshot


# ==================== 2. MACRO REGIME SCORE ====================

def compute_macro_score(intermarket: Dict[str, Optional[dict]]) -> dict:
    """Combine DXY, US10Y, VIX into a single macro tailwind/headwind score for gold.
    Score range roughly [-3, +3]: positive = macro tailwind for gold (bullish),
    negative = macro headwind (bearish)."""
    score = 0.0
    reasons = []
    weight_used = 0.0

    dxy = intermarket.get("DXY")
    if dxy:
        w = 1.3
        weight_used += w
        if dxy["change_5bar_pct"] < -0.3:
            score += w
            reasons.append(f"DXY weakening ({dxy['change_5bar_pct']:+.2f}% / 5 bars) — tailwind for gold")
        elif dxy["change_5bar_pct"] > 0.3:
            score -= w
            reasons.append(f"DXY strengthening ({dxy['change_5bar_pct']:+.2f}% / 5 bars) — headwind for gold")
        else:
            reasons.append("DXY roughly flat — neutral")

    us10y = intermarket.get("US10Y")
    if us10y:
        w = 1.2
        weight_used += w
        if us10y["change_5bar_pct"] < -1.0:
            score += w
            reasons.append(f"US10Y yield falling ({us10y['change_5bar_pct']:+.2f}% / 5 bars) — lowers opportunity cost of gold")
        elif us10y["change_5bar_pct"] > 1.0:
            score -= w
            reasons.append(f"US10Y yield rising ({us10y['change_5bar_pct']:+.2f}% / 5 bars) — raises opportunity cost of gold")
        else:
            reasons.append("US10Y yield roughly flat — neutral")

    vix = intermarket.get("VIX")
    if vix:
        w = 1.0
        weight_used += w
        if vix["last"] > 22 and vix["change_5bar_pct"] > 5:
            score += w
            reasons.append(f"VIX elevated & rising (level={vix['last']}) — risk-off safe-haven bid for gold")
        elif vix["last"] < 15:
            score -= w * 0.5
            reasons.append(f"VIX low (level={vix['last']}) — complacent risk-on, reduces safe-haven demand")
        else:
            reasons.append(f"VIX neutral (level={vix['last']})")

    label = "TAILWIND" if score > 0.5 else "HEADWIND" if score < -0.5 else "NEUTRAL"
    return {
        "score": round(score, 2),
        "max_possible": round(weight_used, 2),
        "label": label,
        "reasons": reasons,
    }


# ==================== 3. GOLD / SILVER RATIO ====================

def compute_gold_silver_ratio(gold_price: float, intermarket: Dict) -> Optional[dict]:
    silver = intermarket.get("SILVER")
    if not silver or not silver.get("last"):
        return None
    ratio = gold_price / silver["last"]

    # Historical long-run range is roughly 60-90; >85 = gold expensive vs silver (silver may
    # outperform / gold may lag), <65 = gold cheap vs silver. Treated as a mean-reversion tilt.
    if ratio > 85:
        signal = "SELL"
        reason = f"Gold/Silver ratio elevated ({ratio:.1f}) — gold rich vs silver, mean-reversion risk"
    elif ratio < 65:
        signal = "BUY"
        reason = f"Gold/Silver ratio low ({ratio:.1f}) — gold cheap vs silver, historically supportive"
    else:
        signal = "NEUTRAL"
        reason = f"Gold/Silver ratio in normal range ({ratio:.1f})"

    return {"ratio": round(ratio, 2), "signal": signal, "reason": reason}


# ==================== 4. SEASONALITY (minor tilt) ====================

def compute_seasonality_tilt(month: int) -> dict:
    if month in SEASONAL_STRONG_MONTHS:
        return {"signal": "BUY", "weight": 0.4, "reason": f"Month {month}: historically seasonally strong for gold (minor tilt)"}
    if month in SEASONAL_WEAK_MONTHS:
        return {"signal": "SELL", "weight": 0.4, "reason": f"Month {month}: historically seasonally weak for gold (minor tilt)"}
    return {"signal": "NEUTRAL", "weight": 0.2, "reason": f"Month {month}: no strong historical seasonal bias"}


# ==================== 5. MULTI-TIMEFRAME CONFLUENCE ====================

def compute_multi_timeframe_confluence() -> dict:
    """Run the full technical signal engine independently on 15m/1h/4h/1d and measure
    how much they agree. Agreement across timeframes is one of the strongest known
    filters for reducing false signals in discretionary and systematic trading alike."""
    results = {}
    for tf in TIMEFRAMES_FOR_CONFLUENCE:
        try:
            sig = generate_signal(GOLD_SYMBOL, timeframe=tf)
            if sig:
                results[tf] = {"direction": sig.direction, "confidence": sig.confidence}
            else:
                results[tf] = None
        except Exception:
            results[tf] = None

    valid = {tf: r for tf, r in results.items() if r is not None}
    if not valid:
        return {"per_timeframe": results, "agreement": "NONE", "aligned_direction": "NEUTRAL", "alignment_score": 0}

    buy_tfs = [tf for tf, r in valid.items() if r["direction"] == "BUY"]
    sell_tfs = [tf for tf, r in valid.items() if r["direction"] == "SELL"]

    total = len(valid)
    if len(buy_tfs) >= len(sell_tfs) and len(buy_tfs) > 0:
        aligned_direction = "BUY"
        agree_count = len(buy_tfs)
    elif len(sell_tfs) > 0:
        aligned_direction = "SELL"
        agree_count = len(sell_tfs)
    else:
        aligned_direction = "NEUTRAL"
        agree_count = 0

    agreement_pct = round(agree_count / total * 100, 1) if total else 0
    if agreement_pct >= 75:
        agreement = "STRONG"
    elif agreement_pct >= 50:
        agreement = "MODERATE"
    else:
        agreement = "WEAK"

    return {
        "per_timeframe": results,
        "agreement": agreement,
        "agreement_pct": agreement_pct,
        "aligned_direction": aligned_direction if agreement != "WEAK" else "NEUTRAL",
        "agree_count": agree_count,
        "total_timeframes": total,
    }


# ==================== 6. MASTER COMPOSITE ====================

@dataclass
class GoldDeepAnalysis:
    direction: str
    confidence: int
    entry_price: float
    stop_loss: float
    take_profit: float
    technical: Optional[TradingSignal]
    macro: dict
    gold_silver: Optional[dict]
    seasonality: dict
    confluence: dict
    news: Optional[dict]
    composite_reasons: List[str] = field(default_factory=list)


def deep_xauusd_analysis(timeframe: str = "1h", include_news: bool = True, month: Optional[int] = None) -> Optional[GoldDeepAnalysis]:
    """The master function: combines technical + macro + intermarket + seasonality +
    multi-timeframe confluence + (optional) news sentiment into one composite call.

    This is intentionally MORE conservative than the base signal engine — it only
    escalates confidence when independent layers agree, and it explicitly penalizes
    confidence when layers conflict, rather than averaging blindly.
    """
    import datetime
    if month is None:
        month = datetime.datetime.utcnow().month

    # --- Layer 1: base technical signal on the requested timeframe ---
    technical = generate_signal(GOLD_SYMBOL, timeframe=timeframe)
    if not technical:
        return None

    # --- Layer 2: intermarket macro regime ---
    intermarket = fetch_intermarket_snapshot()
    macro = compute_macro_score(intermarket)

    # --- Layer 3: gold/silver ratio ---
    gold_silver = compute_gold_silver_ratio(technical.entry_price, intermarket)

    # --- Layer 4: seasonality ---
    seasonality = compute_seasonality_tilt(month)

    # --- Layer 5: multi-timeframe confluence ---
    confluence = compute_multi_timeframe_confluence()

    # --- Layer 6 (optional): news sentiment ---
    news = None
    if include_news:
        try:
            from news_sentiment import get_news_sentiment
            news = get_news_sentiment(GOLD_SYMBOL)
        except Exception:
            news = None

    # ---------------- Composite scoring ----------------
    # Start from the technical engine's own direction/confidence as the base,
    # then adjust with independent evidence. Each layer can only ADD or SUBTRACT
    # a bounded amount — no single layer can flip a strong technical signal alone,
    # but several agreeing layers can meaningfully raise confidence, and several
    # disagreeing layers will pull it down (or force NEUTRAL).
    direction = technical.direction
    confidence = float(technical.confidence)
    reasons = [f"Base technical ({timeframe}): {direction} @ {technical.confidence}%"]

    agree_bonus = 0.0
    disagree_penalty = 0.0

    def _apply(layer_signal: str, weight: float, reason: str):
        nonlocal agree_bonus, disagree_penalty
        if direction == "NEUTRAL" or layer_signal == "NEUTRAL":
            return
        if layer_signal == direction:
            agree_bonus += weight
            reasons.append(f"✅ Agrees: {reason}")
        else:
            disagree_penalty += weight
            reasons.append(f"⚠️ Conflicts: {reason}")

    if macro["label"] != "NEUTRAL":
        macro_signal = "BUY" if macro["score"] > 0 else "SELL"
        _apply(macro_signal, min(abs(macro["score"]) * 3, 12), "; ".join(macro["reasons"][:2]))

    if gold_silver and gold_silver["signal"] != "NEUTRAL":
        _apply(gold_silver["signal"], 6, gold_silver["reason"])

    if seasonality["signal"] != "NEUTRAL":
        _apply(seasonality["signal"], seasonality["weight"] * 10, seasonality["reason"])

    if confluence["aligned_direction"] != "NEUTRAL":
        conf_weight = {"STRONG": 15, "MODERATE": 8, "WEAK": 0}.get(confluence["agreement"], 0)
        _apply(confluence["aligned_direction"], conf_weight,
               f"{confluence['agree_count']}/{confluence['total_timeframes']} timeframes aligned ({confluence['agreement']})")

    if news and news.get("headline_count", 0) > 0 and news.get("label") != "NEUTRAL":
        news_signal = "BUY" if news["label"] == "BULLISH" else "SELL"
        _apply(news_signal, 5, f"News sentiment {news['label']} ({news['score']:+.2f}, {news['headline_count']} headlines)")

    confidence = confidence + agree_bonus - disagree_penalty
    confidence = max(5, min(round(confidence), 98))

    # If disagreement dominates agreement significantly, de-escalate to NEUTRAL —
    # a high-conviction technical call surrounded by conflicting macro/confluence
    # evidence is exactly the situation that produces false signals.
    if disagree_penalty > agree_bonus + 10:
        reasons.append("🚫 Net conflict across layers exceeds agreement — downgraded to NEUTRAL")
        direction = "NEUTRAL"
        confidence = max(30, round(confidence * 0.5))

    return GoldDeepAnalysis(
        direction=direction,
        confidence=confidence,
        entry_price=technical.entry_price,
        stop_loss=technical.stop_loss,
        take_profit=technical.take_profit,
        technical=technical,
        macro=macro,
        gold_silver=gold_silver,
        seasonality=seasonality,
        confluence=confluence,
        news=news,
        composite_reasons=reasons,
    )


# ==================== FORMATTING ====================

def format_gold_deep_message(result: GoldDeepAnalysis) -> str:
    dir_map = {"BUY": "ទិញ ⬆️🟢", "SELL": "លក់ ⬇️🔴", "NEUTRAL": "រង់ចាំ ⏸️🟡"}
    conf_bar = "█" * (result.confidence // 10) + "░" * (10 - result.confidence // 10)

    msg = f"""🥇 *XAUUSD DEEP ANALYSIS — MULTI-LAYER COMPOSITE* 🥇
━━━━━━━━━━━━━━━━━━━━━━
*សញ្ញា / SIGNAL:* {dir_map.get(result.direction, result.direction)}
⚡ Composite Confidence: *{result.confidence}%*
[{conf_bar}]

💰 Entry: `${result.entry_price:,.2f}`
🛑 SL: `${result.stop_loss:,.2f}`   🎯 TP: `${result.take_profit:,.2f}`

━━━━━━━━━━━━━━━━━━━━━━
🌐 *MACRO REGIME:* {result.macro['label']} (score {result.macro['score']:+.2f}/{result.macro['max_possible']:.2f})
"""
    for r in result.macro["reasons"]:
        msg += f"  • {r}\n"

    if result.gold_silver:
        msg += f"\n⚖️ *GOLD/SILVER RATIO:* {result.gold_silver['ratio']} — {result.gold_silver['reason']}\n"

    msg += f"\n📅 *SEASONALITY:* {result.seasonality['reason']}\n"

    c = result.confluence
    msg += f"\n⏱ *MULTI-TIMEFRAME CONFLUENCE:* {c['agreement']} ({c.get('agree_count', 0)}/{c.get('total_timeframes', 0)} aligned → {c['aligned_direction']})\n"
    for tf, r in c.get("per_timeframe", {}).items():
        if r:
            icon = "🟢" if r["direction"] == "BUY" else "🔴" if r["direction"] == "SELL" else "⚪"
            msg += f"  {icon} {tf}: {r['direction']} ({r['confidence']}%)\n"
        else:
            msg += f"  ⚫ {tf}: no data\n"

    if result.news and result.news.get("headline_count", 0) > 0:
        msg += f"\n📰 *NEWS SENTIMENT:* {result.news['label']} ({result.news['score']:+.2f}, {result.news['headline_count']} headlines)\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━\n🧠 *ហេតុផលសមាសភាគ / Composite reasoning:*\n"
    for r in result.composite_reasons:
        msg += f"{r}\n"

    msg += "\n⚠️ _Educational purposes only. Not financial advice._"
    return msg
