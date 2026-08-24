"""
BlackMagicAI OMEGA AI Engine — Elite Multi-Capability System
Copyright (c) 2026 BlackMagicAI. All Rights Reserved.
Licensed for commercial sale. See LICENSE file for terms.

Supports: DeepSeek, Groq, OpenAI, Google Gemini
Capabilities: Commander, Signal, Scan, Confluence, Strategy, Sentiment, Pattern, Psychology, Correlation
"""
import os
import json
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# API keys from environment
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def get_active_provider() -> tuple[str, str, str]:
    if DEEPSEEK_API_KEY:
        return ("deepseek", DEEPSEEK_API_KEY, "https://api.deepseek.com/v1")
    if GROQ_API_KEY:
        return ("groq", GROQ_API_KEY, "https://api.groq.com/openai/v1")
    if OPENAI_API_KEY:
        return ("openai", OPENAI_API_KEY, "https://api.openai.com/v1")
    if GEMINI_API_KEY:
        return ("gemini", GEMINI_API_KEY, "https://generativelanguage.googleapis.com/v1beta")
    return ("none", "", "")

PROVIDER, API_KEY, BASE_URL = get_active_provider()

MODELS = {
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}

AI_AVAILABLE = API_KEY != ""


# ==================== DATA CLASSES ====================

@dataclass
class AIAnalysis:
    symbol: str
    direction: str
    confidence: int
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: str
    risk_level: str
    key_factors: List[str] = field(default_factory=list)
    timeframe: str = "1h"
    raw_response: str = ""

@dataclass
class ConfluenceAnalysis:
    symbol: str
    overall_bias: str  # BULLISH, BEARISH, NEUTRAL
    confidence: int
    timeframes: Dict[str, dict] = field(default_factory=dict)
    confluence_score: int = 0  # 0-100, how many TFs agree
    reasoning: str = ""
    recommendation: str = ""

@dataclass
class StrategyPlan:
    name: str
    market_type: str
    timeframes: List[str]
    indicators_used: List[str]
    entry_rules: str
    exit_rules: str
    risk_rules: str
    expected_win_rate: str
    reasoning: str


# ==================== SYSTEM PROMPTS ====================

SYSTEM_PROMPT = """You are an elite AI trading analyst specializing in technical and fundamental analysis across Gold, Forex, Crypto, Stocks, and Indices markets.

Your analysis combines:
1. Technical indicators (RSI, MACD, EMA, Bollinger Bands, ADX, Stochastic, Volume, Support/Resistance)
2. Price action and market structure
3. Risk/reward evaluation
4. Multi-timeframe context

You MUST respond ONLY in this exact JSON format, no other text:
{
  "direction": "BUY" | "SELL" | "NEUTRAL",
  "confidence": 0-100,
  "entry_price": number,
  "stop_loss": number,
  "take_profit": number,
  "reasoning": "your detailed analysis in Khmer and English, explain WHY this signal",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "key_factors": ["factor1", "factor2", "factor3"],
  "market_bias": "Bullish above EMA200, but short-term correction likely"
}

Key rules:
- confidence below 40 = NEUTRAL direction
- SL must be at least 1.5x ATR away
- R:R ratio must be at least 1:1.5
- If indicators conflict heavily, set NEUTRAL
- Consider support/resistance levels for SL/TP placement
- ADX above 25 means trending market, below 25 means range-bound"""

CONFLUENCE_PROMPT = """You are a multi-timeframe confluence expert. Analyze the same market across 4 timeframes and identify:
1. Overall bias (bullish/bearish/neutral)
2. Which timeframes agree (confluence)
3. Where the strongest signal is
4. Whether to trade or wait

Respond ONLY in JSON:
{
  "overall_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confluence_score": 0-100,
  "confidence": 0-100,
  "timeframes": {
    "15m": {"bias": "...", "strength": 0-100, "key_level": number},
    "1h":  {"bias": "...", "strength": 0-100, "key_level": number},
    "4h":  {"bias": "...", "strength": 0-100, "key_level": number},
    "1d":  {"bias": "...", "strength": 0-100, "key_level": number}
  },
  "reasoning": "detailed multi-TF reasoning in Khmer + English",
  "recommendation": "TRADE" | "WAIT" | "CAUTIOUS",
  "best_timeframe": "1h",
  "entry_zone": "price zone description",
  "invalidation": "what would invalidate this setup"
}"""

STRATEGY_PROMPT = """You are a professional trading strategy designer. Design a COMPLETE, actionable trading strategy based on user preferences.

Respond ONLY in JSON:
{
  "name": "strategy name",
  "market_type": "Forex/Gold/Crypto/etc",
  "timeframes": ["1h", "4h"],
  "indicators_used": ["RSI", "EMA200", "MACD"],
  "entry_rules": "detailed entry conditions in Khmer + English",
  "exit_rules": "take profit and stop loss rules",
  "risk_rules": "position sizing and risk per trade",
  "expected_win_rate": "realistic estimate",
  "reasoning": "why this strategy works for this market and style"
}"""

SENTIMENT_PROMPT = """You are a market sentiment analyst. Analyze the sentiment based on technical data.

Respond ONLY in JSON:
{
  "overall_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "sentiment_score": 0-100,
  "fear_greed_index": 0-100,
  "technical_sentiment": "description",
  "volume_sentiment": "high/low/neutral volume analysis",
  "trend_strength": "WEAK" | "MODERATE" | "STRONG" | "EXTREME",
  "divergence_warning": true/false,
  "key_observations": ["obs1", "obs2", "obs3"],
  "reasoning": "full sentiment analysis in Khmer + English"
}"""

PATTERN_PROMPT = """You are a chart pattern recognition expert. Identify technical chart patterns from the data.

Respond ONLY in JSON:
{
  "patterns_found": [
    {"name": "pattern name", "type": "BULLISH"|"BEARISH"|"NEUTRAL", "confidence": 0-100, "description": "..."}
  ],
  "candlestick_patterns": ["doji", "engulfing", ...],
  "key_levels": {"support": [level1, level2], "resistance": [level1, level2]},
  "trend_structure": "description of higher highs/lows",
  "breakout_risk": "LOW"|"MEDIUM"|"HIGH",
  "reasoning": "pattern analysis in Khmer + English"
}"""

PSYCHOLOGY_PROMPT = """You are a trading psychology coach. Help traders manage emotions and improve discipline.

Respond ONLY in JSON:
{
  "topic": "the psychology topic",
  "key_lesson": "main takeaway",
  "practical_tips": ["tip1", "tip2", "tip3", "tip4", "tip5"],
  "common_mistakes": ["mistake1", "mistake2"],
  "mindset_shift": "how to reframe thinking",
  "daily_affirmation": "a powerful trading affirmation",
  "advice_khmer": "full advice in Khmer language",
  "advice_english": "full advice in English"
}"""

CORRELATION_PROMPT = """You are a cross-market correlation analyst. Find correlated markets and intermarket relationships.

Respond ONLY in JSON:
{
  "primary_market": "symbol",
  "correlated_markets": [
    {"symbol": "...", "correlation": "POSITIVE"|"NEGATIVE", "strength": 0-100, "reason": "why correlated"}
  ],
  "leading_indicators": ["market1", "market2"],
  "lagging_indicators": ["market1", "market2"],
  "divergence_alert": true/false,
  "intermarket_analysis": "full intermarket analysis in Khmer + English",
  "trading_implication": "how to use this info"
}"""


# ==================== PROMPT BUILDERS ====================

def build_analysis_prompt(symbol: str, price_data: dict, indicators: dict,
                          atr_data: dict, sr_data: dict, timeframe: str) -> str:
    indicator_summary = []
    for name, data in indicators.items():
        sig = data.get("signal", "N/A")
        reason = data.get("reason", "")
        val = data.get("value", "")
        indicator_summary.append(f"  - {name}: {sig} | {reason} | Value: {val}")

    return f"""📊 MARKET ANALYSIS REQUEST
━━━━━━━━━━━━━━━━━━━

SYMBOL: {symbol}
TIMEFRAME: {timeframe}
CURRENT PRICE: ${price_data.get('price', 'N/A')}
PREV CLOSE: ${price_data.get('prev_close', 'N/A')}
DAILY CHANGE: {price_data.get('change_pct', 0):+.2f}%
CATEGORY: {price_data.get('category', 'N/A')}

TECHNICAL INDICATORS:
{chr(10).join(indicator_summary)}

ATR DATA:
  ATR(14): {atr_data.get('ATR', 'N/A')}
  TP 1xATR: {atr_data.get('TP_1x', 'N/A')}
  TP 1.5xATR: {atr_data.get('TP_1_5x', 'N/A')}
  TP 2xATR: {atr_data.get('TP_2x', 'N/A')}

SUPPORT/RESISTANCE:
  Support: ${sr_data.get('support', 'N/A')}
  Resistance: ${sr_data.get('resistance', 'N/A')}
  Close: ${sr_data.get('close', 'N/A')}

Analyze this market and output your trading signal in the required JSON format.
Provide reasoning in both Khmer and English for maximum detail.
"""


# ==================== LLM CALLER ====================

async def call_llm(system_prompt: str, user_prompt: str, provider: str = None,
                   model: str = None, temperature: float = 0.2, max_tokens: int = 1000) -> Optional[str]:
    p = provider or PROVIDER
    m = model or MODELS.get(p, "gpt-3.5-turbo")
    key = API_KEY
    url = BASE_URL

    if p == "none" or not key:
        return None

    try:
        if p == "gemini":
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": f"System: {system_prompt}\n\nUser: {user_prompt}"}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(gemini_url, json=payload)
                data = resp.json()
                return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        else:
            endpoint = f"{url}/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"LLM call error ({p}): {e}")
        return None


def parse_json_response(response: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    if not response:
        return None
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[^{}]*\{[^}]*\}[^{}]*\}', text, re.DOTALL)
        if not match:
            match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


def parse_ai_response(response: str, default_price: float) -> Optional[AIAnalysis]:
    data = parse_json_response(response)
    if not data:
        return None

    direction = data.get("direction", "NEUTRAL").upper()
    if direction not in ("BUY", "SELL", "NEUTRAL"):
        direction = "NEUTRAL"

    return AIAnalysis(
        symbol=data.get("symbol", ""),
        direction=direction,
        confidence=min(int(data.get("confidence", 50)), 100),
        entry_price=float(data.get("entry_price", default_price)),
        stop_loss=float(data.get("stop_loss", default_price * 0.99)),
        take_profit=float(data.get("take_profit", default_price * 1.02)),
        reasoning=data.get("reasoning", "AI analysis unavailable"),
        risk_level=data.get("risk_level", "MEDIUM").upper(),
        key_factors=data.get("key_factors", []),
        raw_response=response,
    )


# ==================== CORE AI FUNCTIONS ====================

async def ai_analyze_market(symbol_name: str, price_data: dict, indicators: dict,
                             atr_data: dict, sr_data: dict, timeframe: str = "1h") -> Optional[AIAnalysis]:
    if not AI_AVAILABLE:
        return None
    user_prompt = build_analysis_prompt(symbol_name, price_data, indicators, atr_data, sr_data, timeframe)
    response = await call_llm(SYSTEM_PROMPT, user_prompt)
    if not response:
        return None
    return parse_ai_response(response, price_data.get("price", 0))


async def ai_scan_markets(price_data_list: List[dict], top_n: int = 5) -> Optional[dict]:
    if not AI_AVAILABLE:
        return None
    market_list = "\n".join([
        f"{i+1}. {d['symbol']} ${d['price']:,.2f} ({d['change_pct']:+.2f}%) - {d.get('category', '')}"
        for i, d in enumerate(price_data_list)
    ])
    scan_prompt = f"""Scan the following markets and identify the TOP {top_n} trading opportunities right now.

CURRENT MARKET PRICES:
{market_list}

For each opportunity, explain WHY in 1-2 sentences (Khmer + English).
Output in this JSON format:
{{
  "opportunities": [
    {{"symbol": "XAUUSD", "direction": "BUY", "confidence": 75, "reason": "Gold breaking resistance with strong volume..."}}
  ],
  "market_summary": "brief overall market summary in Khmer"
}}
"""
    response = await call_llm(
        "You are an elite market scanner. Find the best trading opportunities from the given list.",
        scan_prompt, temperature=0.3, max_tokens=1500
    )
    return parse_json_response(response)


# ==================== NEW AI CAPABILITIES ====================

async def ai_confluence(symbol: str, tf_data: Dict[str, dict], current_price: float) -> Optional[ConfluenceAnalysis]:
    """Multi-timeframe confluence analysis — analyzes 4 TFs together."""
    if not AI_AVAILABLE:
        return None

    tf_summary = []
    for tf, data in tf_data.items():
        tf_summary.append(f"{tf}: Price ${data.get('price', 'N/A')} | "
                         f"RSI={data.get('rsi', 'N/A')} | "
                         f"Trend={data.get('trend', 'N/A')} | "
                         f"EMA50/200: {'Above' if data.get('above_ema', True) else 'Below'}")

    prompt = f"""MULTI-TIMEFRAME CONFLUENCE ANALYSIS
━━━━━━━━━━━━━━━━━━━
SYMBOL: {symbol}
CURRENT PRICE: ${current_price:,.2f}

TIMEFRAME DATA:
{chr(10).join(tf_summary)}

Analyze all timeframes together. Find where they AGREE (confluence) and DISAGREE (divergence).
The strongest signals come when 3+ timeframes align. Output the JSON."""

    response = await call_llm(CONFLUENCE_PROMPT, prompt, temperature=0.2, max_tokens=1200)
    data = parse_json_response(response)
    if not data:
        return None

    return ConfluenceAnalysis(
        symbol=symbol,
        overall_bias=data.get("overall_bias", "NEUTRAL"),
        confidence=data.get("confidence", 50),
        timeframes=data.get("timeframes", {}),
        confluence_score=data.get("confluence_score", 0),
        reasoning=data.get("reasoning", ""),
        recommendation=data.get("recommendation", "WAIT"),
    )


async def ai_build_strategy(market_type: str, trading_style: str, experience: str,
                            capital: str, risk_tolerance: str) -> Optional[dict]:
    """AI generates a personalized trading strategy."""
    if not AI_AVAILABLE:
        return None

    prompt = f"""Design a COMPLETE trading strategy for:
- Market: {market_type}
- Trading Style: {trading_style} (scalping/day/swing/position)
- Experience Level: {experience}
- Capital: {capital}
- Risk Tolerance: {risk_tolerance}

Make it REALISTIC and ACTIONABLE. Include specific indicator settings, entry/exit rules, and risk management.
Provide all rules in both Khmer and English so Cambodian traders can understand.
Output the JSON format specified."""

    response = await call_llm(STRATEGY_PROMPT, prompt, temperature=0.5, max_tokens=1500)
    return parse_json_response(response)


async def ai_sentiment(symbol: str, price_data: dict, indicators: dict,
                       volume_data: dict) -> Optional[dict]:
    """AI market sentiment analysis."""
    if not AI_AVAILABLE:
        return None

    ind_summary = "\n".join([
        f"  {name}: {data.get('signal', 'N/A')} (value: {data.get('value', 'N/A')})"
        for name, data in indicators.items()
    ])

    prompt = f"""SENTIMENT ANALYSIS REQUEST
━━━━━━━━━━━━━━━━━━━
SYMBOL: {symbol}
PRICE: ${price_data.get('price', 'N/A')}
24H CHANGE: {price_data.get('change_pct', 0):+.2f}%
VOLUME: {volume_data.get('volume', 'N/A')}
VOLUME RATIO: {volume_data.get('volume_ratio', 'N/A')}

INDICATORS:
{ind_summary}

Analyze the overall market sentiment. Is the market fearful or greedy? Are indicators showing hidden divergence?
Output the JSON format."""

    response = await call_llm(SENTIMENT_PROMPT, prompt, temperature=0.3, max_tokens=1000)
    return parse_json_response(response)


async def ai_detect_patterns(symbol: str, price_data: dict, ohlc_summary: str,
                              sr_data: dict) -> Optional[dict]:
    """AI chart pattern detection."""
    if not AI_AVAILABLE:
        return None

    prompt = f"""CHART PATTERN DETECTION
━━━━━━━━━━━━━━━━━━━
SYMBOL: {symbol}
PRICE: ${price_data.get('price', 'N/A')}
CATEGORY: {price_data.get('category', 'N/A')}

RECENT PRICE ACTION:
{ohlc_summary}

SUPPORT/RESISTANCE:
  Support: ${sr_data.get('support', 'N/A')}
  Resistance: ${sr_data.get('resistance', 'N/A')}

Identify ALL chart patterns present: double top/bottom, head & shoulders, triangles, flags, wedges, channels, etc.
Also identify candlestick patterns: doji, engulfing, hammer, shooting star, morning/evening star.
Output the JSON format."""

    response = await call_llm(PATTERN_PROMPT, prompt, temperature=0.2, max_tokens=1000)
    return parse_json_response(response)


async def ai_psychology(topic: str = "general") -> Optional[dict]:
    """AI trading psychology coach."""
    if not AI_AVAILABLE:
        return None

    topics = {
        "general": "General trading psychology and discipline",
        "revenge": "Revenge trading after a loss — how to stop",
        "fomo": "FOMO (Fear Of Missing Out) — how to control it",
        "greed": "Greed and overtrading — setting realistic targets",
        "fear": "Fear of entering trades — building confidence",
        "discipline": "Building trading discipline and routine",
        "loss": "Dealing with losing streaks",
        "mindset": "The winning trader's mindset",
    }
    topic_desc = topics.get(topic, topics["general"])

    prompt = f"""TOPIC: {topic_desc}

Provide practical, actionable trading psychology advice. Be direct and honest.
Give examples from real trading situations. Help the trader improve their mental game.
IMPORTANT: Provide the full advice in both Khmer language and English.
Output the JSON format."""

    response = await call_llm(PSYCHOLOGY_PROMPT, prompt, temperature=0.7, max_tokens=1200)
    return parse_json_response(response)


async def ai_correlated_markets(symbol: str, all_prices: List[dict]) -> Optional[dict]:
    """AI correlation analysis — find intermarket relationships."""
    if not AI_AVAILABLE:
        return None

    market_list = "\n".join([
        f"{d['symbol']} ${d['price']:,.2f} ({d['change_pct']:+.2f}%) - {d.get('category', '')}"
        for d in all_prices if d['symbol'] != symbol
    ])

    prompt = f"""CROSS-MARKET CORRELATION ANALYSIS
━━━━━━━━━━━━━━━━━━━
PRIMARY MARKET: {symbol}

OTHER MARKETS:
{market_list}

Analyze how {symbol} is correlated with other markets. Which markets lead {symbol}?
Which follow it? Are there any divergences? How can traders use this information?
Output the JSON format."""

    response = await call_llm(CORRELATION_PROMPT, prompt, temperature=0.3, max_tokens=1200)
    return parse_json_response(response)


# ==================== MESSAGE FORMATTERS ====================

def format_ai_signal_message(ai: AIAnalysis, symbol: str, market_name: str, emoji: str) -> str:
    dir_map = {"BUY": "ទិញ ⬆️🟢", "SELL": "លក់ ⬇️🔴", "NEUTRAL": "រង់ចាំ ⏸️🟡"}
    risk_map = {"LOW": "ទាប 🟢", "MEDIUM": "មធ្យម 🟡", "HIGH": "ខ្ពស់ 🔴"}
    conf_bar = "█" * (ai.confidence // 10) + "░" * (10 - ai.confidence // 10)

    msg = f"""🧠{emoji} *AI DEEP ANALYSIS — {symbol}* {emoji}🧠
━━━━━━━━━━━━━━━━━━━
📊 *{market_name}*
⏱ Timeframe: {ai.timeframe}
🔮 Powered by: {PROVIDER.upper()} AI

*សញ្ញា / SIGNAL:* {dir_map.get(ai.direction, ai.direction)}

⚡ ទំនុកចិត្ត AI / AI Confidence: *{ai.confidence}%*
[{conf_bar}]

⚠️ កម្រិតហានិភ័យ / Risk: {risk_map.get(ai.risk_level, ai.risk_level)}

━━━━━━━━━━━━━━━━━━━
💰 *តម្លៃចូល / Entry:* `${ai.entry_price:,.4f}`
🛑 *Stop Loss:* `${ai.stop_loss:,.4f}`
🎯 *Take Profit:* `${ai.take_profit:,.4f}`
"""
    if ai.direction != "NEUTRAL":
        if ai.direction == "BUY":
            risk = round(ai.entry_price - ai.stop_loss, 4)
            reward = round(ai.take_profit - ai.entry_price, 4)
        else:
            risk = round(ai.stop_loss - ai.entry_price, 4)
            reward = round(ai.entry_price - ai.take_profit, 4)
        rr = round(reward / risk, 2) if risk > 0 else 0
        rr_emoji = "✅" if rr >= 2 else "👍" if rr >= 1.5 else "⚠️"
        msg += f"""{rr_emoji} *Risk/Reward:* 1:{rr}
📉 Risk: ${risk:,.4f}
📈 Reward: ${reward:,.4f}
"""
    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 *AI Reasoning / ការវិភាគ AI:*
{ai.reasoning}
"""
    if ai.key_factors:
        msg += "\n*🔑 Key Factors:*\n"
        for i, factor in enumerate(ai.key_factors, 1):
            msg += f"  {i}. {factor}\n"
    msg += f"\n🚀 _{PROVIDER.upper()} AI-enhanced analysis. Combine with your own research._"
    return msg


def format_ai_scan_message(scan_data: dict) -> str:
    opportunities = scan_data.get("opportunities", [])
    summary = scan_data.get("market_summary", "")

    msg = f"""🧠🔍 *AI MARKET SCAN — TOP OPPORTUNITIES*
━━━━━━━━━━━━━━━━━━━
📊 {summary}

"""
    for i, opp in enumerate(opportunities, 1):
        dir_emoji = "🟢" if opp.get("direction") == "BUY" else "🔴" if opp.get("direction") == "SELL" else "⚪"
        conf = opp.get("confidence", 0)
        conf_stars = "⭐" * min(5, max(1, conf // 20))
        msg += f"""{i}. {dir_emoji} *{opp['symbol']}* — {opp.get('direction', 'N/A')} ({conf}%) {conf_stars}
   💬 _{opp.get('reason', '')}_

"""
    msg += "\n💡 ប្រើ `/ai_signal <symbol>` សម្រាប់ការវិភាគ AI លម្អិត"
    msg += "\n⚠️ _AI analysis for educational purposes only_"
    return msg


def format_confluence_message(c: ConfluenceAnalysis, symbol: str, emoji: str, market_name: str) -> str:
    bias_map = {"BULLISH": "ឡើង 📈🟢", "BEARISH": "ធ្លាក់ 📉🔴", "NEUTRAL": "ចំហៀង ⏸️🟡"}
    rec_map = {"TRADE": "✅ អាចចូលបាន", "WAIT": "⏳ រង់ចាំ", "CAUTIOUS": "⚠️ ប្រយ័ត្ន"}
    conf_bar = "█" * (c.confidence // 10) + "░" * (10 - c.confidence // 10)

    msg = f"""🧠🔗 *MULTI-TIMEFRAME CONFLUENCE — {symbol}* {emoji}
━━━━━━━━━━━━━━━━━━━
📊 *{market_name}*
⚡ Confluence Score: *{c.confluence_score}%*
🎯 Overall Bias: {bias_map.get(c.overall_bias, c.overall_bias)}

⚡ AI Confidence: *{c.confidence}%*
[{conf_bar}]

📌 Recommendation: {rec_map.get(c.recommendation, c.recommendation)}

━━━━━━━━━━━━━━━━━━━
📐 *TIMEFRAME BREAKDOWN:*
"""
    for tf, data in c.timeframes.items():
        bias_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(data.get("bias", ""), "⚪")
        strength = data.get("strength", 0)
        bar = "▓" * (strength // 10) + "░" * (10 - strength // 10)
        msg += f"  {tf}: {bias_emoji} {data.get('bias', 'N/A')} [{bar}] {strength}%\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 *AI Multi-TF Reasoning / ការវិភាគ:*
{c.reasoning}

🚀 _Multi-timeframe confluence gives higher probability setups._
"""
    return msg


def format_strategy_message(data: dict) -> str:
    if not data:
        return "❌ AI could not generate a strategy."

    timeframes = ", ".join(data.get("timeframes", []))
    indicators = ", ".join(data.get("indicators_used", []))

    msg = f"""🧠📐 *AI STRATEGY BUILDER*
━━━━━━━━━━━━━━━━━━━
🏷 *Strategy:* {data.get('name', 'Custom Strategy')}
📊 Market: {data.get('market_type', 'Any')}
⏱ Timeframes: {timeframes}
📐 Indicators: {indicators}

━━━━━━━━━━━━━━━━━━━
🚪 *ENTRY RULES:*
{data.get('entry_rules', 'N/A')}

🚪 *EXIT RULES:*
{data.get('exit_rules', 'N/A')}

⚖️ *RISK MANAGEMENT:*
{data.get('risk_rules', 'N/A')}

📈 Expected Win Rate: {data.get('expected_win_rate', 'N/A')}

━━━━━━━━━━━━━━━━━━━
🧠 *STRATEGY REASONING:*
{data.get('reasoning', 'N/A')}

⚠️ _Backtest before live trading. Not financial advice._
"""
    return msg


def format_sentiment_message(data: dict, symbol: str, emoji: str) -> str:
    if not data:
        return "❌ AI could not analyze sentiment."

    sent_map = {"BULLISH": "🟢 Bullish ឡើង", "BEARISH": "🔴 Bearish ធ្លាក់", "NEUTRAL": "⚪ Neutral ចំហៀង"}
    trend_map = {"WEAK": "ខ្សោយ", "MODERATE": "មធ្យម", "STRONG": "ខ្លាំង", "EXTREME": "ខ្លាំងខ្លាំង"}
    score_bar = "█" * (data.get("sentiment_score", 50) // 10) + "░" * (10 - data.get("sentiment_score", 50) // 10)
    fg_bar = "█" * (data.get("fear_greed_index", 50) // 10) + "░" * (10 - data.get("fear_greed_index", 50) // 10)

    msg = f"""🧠💭 *AI SENTIMENT ANALYSIS — {symbol}* {emoji}
━━━━━━━━━━━━━━━━━━━
{sent_map.get(data.get('overall_sentiment', 'NEUTRAL'), 'NEUTRAL')}

📊 Sentiment Score: *{data.get('sentiment_score', 50)}%*
[{score_bar}]

😱 Fear & Greed Index: *{data.get('fear_greed_index', 50)}%*
[{fg_bar}]

📈 Trend Strength: {trend_map.get(data.get('trend_strength', 'MODERATE'), 'មធ្យម')}

{'⚠️ DIVERGENCE DETECTED!' if data.get('divergence_warning') else '✅ No divergence detected'}

━━━━━━━━━━━━━━━━━━━
📝 Technical Sentiment: {data.get('technical_sentiment', 'N/A')}
📊 Volume: {data.get('volume_sentiment', 'N/A')}

🔑 *Key Observations:*
"""
    for obs in data.get("key_observations", []):
        msg += f"  • {obs}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 *AI Reasoning:*
{data.get('reasoning', 'N/A')}

🚀 _Sentiment analysis helps gauge market psychology._
"""
    return msg


def format_pattern_message(data: dict, symbol: str, emoji: str) -> str:
    if not data:
        return "❌ AI could not detect patterns."

    msg = f"""🧠📐 *AI PATTERN RECOGNITION — {symbol}* {emoji}
━━━━━━━━━━━━━━━━━━━
"""
    patterns = data.get("patterns_found", [])
    if patterns:
        msg += "*📊 Chart Patterns Detected:*\n"
        for p in patterns:
            type_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(p.get("type", ""), "⚪")
            msg += f"  {type_emoji} *{p.get('name', 'Unknown')}* ({p.get('confidence', 0)}%)\n"
            msg += f"     {p.get('description', '')}\n"

    candlesticks = data.get("candlestick_patterns", [])
    if candlesticks:
        msg += f"\n🕯 *Candlestick Patterns:* {', '.join(candlesticks)}\n"

    levels = data.get("key_levels", {})
    if levels:
        msg += "\n📏 *Key Levels:*\n"
        msg += f"  Support: ${', $'.join(str(x) for x in levels.get('support', []))}\n"
        msg += f"  Resistance: ${', $'.join(str(x) for x in levels.get('resistance', []))}\n"

    msg += f"""
📐 Trend Structure: {data.get('trend_structure', 'N/A')}
⚠️ Breakout Risk: {data.get('breakout_risk', 'N/A')}

━━━━━━━━━━━━━━━━━━━
🧠 *AI Pattern Analysis:*
{data.get('reasoning', 'N/A')}

🚀 _Pattern recognition improves entry timing._
"""
    return msg


def format_psychology_message(data: dict) -> str:
    if not data:
        return "❌ AI could not generate psychology advice."

    msg = f"""🧠💪 *AI TRADING PSYCHOLOGY COACH*
━━━━━━━━━━━━━━━━━━━
📌 *{data.get('topic', 'Trading Psychology')}*

💡 *Key Lesson:*
_{data.get('key_lesson', '')}_

━━━━━━━━━━━━━━━━━━━
✅ *Practical Tips:*
"""
    for i, tip in enumerate(data.get("practical_tips", []), 1):
        msg += f"  {i}. {tip}\n"

    msg += f"""
❌ *Common Mistakes:*
"""
    for i, m in enumerate(data.get("common_mistakes", []), 1):
        msg += f"  {i}. {m}\n"

    msg += f"""
🧠 *Mindset Shift:*
_{data.get('mindset_shift', '')}_

💬 *Daily Affirmation:*
> {data.get('daily_affirmation', '')}

━━━━━━━━━━━━━━━━━━━
🇰🇭 *ដំបូន្មានជាភាសាខ្មែរ:*
{data.get('advice_khmer', '')}

🇬🇧 *Advice in English:*
{data.get('advice_english', '')}

💪 _Master your mind, master the markets._
"""
    return msg


def format_correlation_message(data: dict, symbol: str, emoji: str) -> str:
    if not data:
        return "❌ AI could not analyze correlations."

    msg = f"""🧠🔗 *AI CROSS-MARKET CORRELATION — {symbol}* {emoji}
━━━━━━━━━━━━━━━━━━━

📊 *Correlated Markets:*
"""
    for c in data.get("correlated_markets", []):
        corr_emoji = "🟢 +" if c.get("correlation") == "POSITIVE" else "🔴 -"
        strength = c.get("strength", 0)
        bar = "█" * (strength // 10) + "░" * (10 - strength // 10)
        msg += f"  {corr_emoji} *{c['symbol']}* → {c.get('correlation', '')} [{bar}] {strength}%\n"
        msg += f"     _{c.get('reason', '')}_\n"

    leading = data.get("leading_indicators", [])
    lagging = data.get("lagging_indicators", [])
    if leading:
        msg += f"\n⬆️ *Leading Markets (move first):* {', '.join(leading)}"
    if lagging:
        msg += f"\n⬇️ *Lagging Markets (follow):* {', '.join(lagging)}"

    if data.get("divergence_alert"):
        msg += "\n\n⚠️ *DIVERGENCE ALERT!* Markets are moving unusually!"

    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 *Intermarket Analysis:*
{data.get('intermarket_analysis', 'N/A')}

💡 *Trading Implication:*
{data.get('trading_implication', 'N/A')}

🚀 _Understanding correlations helps manage portfolio risk._
"""
    return msg

# ==================== UNIFIED AI COMMANDER ====================

UNIFIED_COMMANDER_PROMPT = """You are OMEGA — the world's most advanced AI trading commander. You integrate 8 analysis engines simultaneously:

1. TECHNICAL ANALYSIS: RSI, MACD, EMA, ADX, Bollinger Bands, Stochastic, Volume, ATR
2. MULTI-TIMEFRAME CONFLUENCE: 15m, 1H, 4H, 1D alignment
3. SENTIMENT ANALYSIS: Fear & Greed, volume sentiment, divergence
4. PATTERN RECOGNITION: Chart patterns, candlestick patterns, harmonics
5. STRATEGY OPTIMIZATION: Optimal entry/exit based on all factors
6. CORRELATION ANALYSIS: Intermarket relationships
7. PSYCHOLOGY: Read the market's "mood" — greedy or fearful?
8. PRICE ACTION: Market structure, order flow, liquidity zones

You MUST respond in this EXACT JSON format:
{
  "signal": "STRONG_BUY" | "BUY" | "WEAK_BUY" | "NEUTRAL" | "WEAK_SELL" | "SELL" | "STRONG_SELL",
  "confidence": 0-100,
  "direction_khmer": "ទិញ" or "លក់" or "រង់ចាំ",
  "entry_zone": {"low": number, "high": number, "optimal": number},
  "stop_loss": number,
  "take_profits": [
    {"price": number, "reason": "why this level", "pct": percentage_from_entry},
    {"price": number, "reason": "why this level", "pct": percentage_from_entry},
    {"price": number, "reason": "why this level", "pct": percentage_from_entry}
  ],
  "risk_reward": "1:X.X",
  "confluence_summary": "brief 4-TF alignment summary in Khmer",
  "sentiment_summary": "market psychology summary in Khmer",
  "patterns_detected": ["pattern1", "pattern2"],
  "key_levels": {"support": [s1, s2], "resistance": [r1, r2]},
  "timing": {
    "best_entry_time": "London Open / NY Open / Asia / etc",
    "best_session": "London / New York / Asian / etc",
    "hold_time": "Scalping (mins) / Intraday / Swing (days) / Position (weeks)"
  },
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "EXTREME",
  "probability_summary": "win probability breakdown",
  "analysis_full": "FULL detailed analysis in BOTH Khmer and English — at least 3 paragraphs explaining WHY this trade, what confirms it, what invalidates it, and the full reasoning",
  "invalid_condition": "what would invalidate this setup",
  "power_score": 0-100
}

CRITICAL RULES:
- confidence below 35 = NEUTRAL signal
- R:R MUST be at least 1:1.5 for any signal
- TP1 at 1:1.5, TP2 at 1:2.5, TP3 at 1:4+ zones
- SL at logical invalidation level, not random
- If 3+ indicators conflict = NEUTRAL
- Include SPECIFIC prices, not ranges for entry/sl
- Always provide reasoning in both Khmer and English
- Be honest — if the setup is weak, say so
"""


UNIFIED_ANALYSIS_PROMPT = """🔮 OMEGA COMMANDER — ALL-ENGINE MARKET ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 TARGET: {symbol} | {market_name}
💵 CURRENT PRICE: ${current_price:,.2f}
📊 24H CHANGE: {change_pct:+.2f}%
📂 CATEGORY: {category}
🕐 TIME: {current_time}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 TECHNICAL INDICATORS:
{indicators_text}

📏 SUPPORT / RESISTANCE:
{pivots_text}

🔗 MULTI-TIMEFRAME SNAPSHOT:
{multi_tf_text}

📊 VOLUME DATA:
{volume_text}

📈 RECENT PRICE ACTION (Last 20 candles):
{price_action_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run ALL 8 analysis engines simultaneously. Provide the COMPLETE JSON response
with specific BUY/SELL signal, entry zone, 3 take profits, stop loss, timing schedule,
and full analysis in both Khmer and English."""


async def ai_commander_analyze(
    symbol: str,
    market_name: str,
    current_price: float,
    change_pct: float,
    category: str,
    indicators: dict,
    pivots: dict,
    multi_tf_data: dict,
    volume_data: dict,
    price_action_text: str = ""
) -> Optional[dict]:
    """OMEGA UNIFIED COMMANDER — all 8 AI engines merged into one super-analysis."""
    if not AI_AVAILABLE:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Build indicators summary
    ind_lines = []
    for name, data in indicators.items():
        sig = data.get("signal", "N/A")
        val = data.get("value", "N/A")
        reason = data.get("reason", "")
        ind_lines.append(f"  {name}: {sig} | Value={val} | {reason}")
    indicators_text = "\n".join(ind_lines)

    # Build pivots
    pivots_text = f"  Support: ${pivots.get('support', 'N/A')}\n  Resistance: ${pivots.get('resistance', 'N/A')}"

    # Build multi-TF
    if multi_tf_data:
        tf_lines = []
        for tf, d in multi_tf_data.items():
            tf_lines.append(f"  {tf}: ${d.get('price', 0):,.2f} | RSI={d.get('rsi', 'N/A')} | Trend={d.get('trend', 'N/A')}")
        multi_tf_text = "\n".join(tf_lines)
    else:
        multi_tf_text = "  Data unavailable"

    # Volume
    volume_text = f"  Volume: {volume_data.get('volume', 'N/A')}\n  Ratio: {volume_data.get('volume_ratio', 'N/A')}" if volume_data else "  Data unavailable"

    # Price action
    if not price_action_text:
        price_action_text = "  Data unavailable"

    prompt = UNIFIED_ANALYSIS_PROMPT.format(
        symbol=symbol,
        market_name=market_name,
        current_price=current_price,
        change_pct=change_pct,
        category=category,
        current_time=now,
        indicators_text=indicators_text,
        pivots_text=pivots_text,
        multi_tf_text=multi_tf_text,
        volume_text=volume_text,
        price_action_text=price_action_text,
    )

    response = await call_llm(UNIFIED_COMMANDER_PROMPT, prompt, temperature=0.3, max_tokens=2500)
    return parse_json_response(response)


# ==================== OMEGA COMMANDER MESSAGE FORMATTER ====================

def format_commander_message(data: dict, symbol: str, emoji: str, market_name: str) -> str:
    """Format the OMEGA Commander unified analysis — premium, modern, elite design."""
    if not data:
        return "❌ OMEGA Commander could not generate analysis."

    signal = data.get("signal", "NEUTRAL")
    confidence = data.get("confidence", 50)

    # Signal badge
    signal_map = {
        "STRONG_BUY": ("🟢🟢🟢", "STRONG BUY — ទិញខ្លាំង", "✅"),
        "BUY": ("🟢🟢", "BUY — ទិញ", "✅"),
        "WEAK_BUY": ("🟢", "WEAK BUY — ទិញតិច", "⚠️"),
        "NEUTRAL": ("⚪", "NEUTRAL — រង់ចាំ", "⏳"),
        "WEAK_SELL": ("🔴", "WEAK SELL — លក់តិច", "⚠️"),
        "SELL": ("🔴🔴", "SELL — លក់", "❌"),
        "STRONG_SELL": ("🔴🔴🔴", "STRONG SELL — លក់ខ្លាំង", "❌"),
    }
    sig_badge, sig_label, sig_icon = signal_map.get(signal, ("⚪", "NEUTRAL", "⏳"))

    conf_bar_filled = "▓" * (confidence // 10)
    conf_bar_empty = "░" * (10 - confidence // 10)
    conf_color = "🟢" if confidence >= 70 else "🟡" if confidence >= 50 else "🟠" if confidence >= 30 else "🔴"

    power = data.get("power_score", 50)
    power_bar = "⚡" * min(5, max(1, power // 20))

    msg = f"""╔══════════════════════════════╗
║  🔮 *OMEGA COMMANDER* 🔮  ║
╚══════════════════════════════╝

{emoji} *{symbol}* — {market_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━

{sig_badge} *{sig_label}*
{conf_color} Confidence: {confidence}%  |  {power_bar} Power: {power}/100
[{conf_bar_filled}{conf_bar_empty}]

━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 *ENTRY ZONE*
   Low:  ${data.get('entry_zone', {}).get('low', 'N/A'):,.4f}
   Optimal: *${data.get('entry_zone', {}).get('optimal', 'N/A'):,.4f}*
   High: ${data.get('entry_zone', {}).get('high', 'N/A'):,.4f}

🛑 *STOP LOSS:* *${data.get('stop_loss', 'N/A'):,.4f}*
"""

    tps = data.get("take_profits", [])
    if tps:
        msg += "🎯 *TAKE PROFITS:*\n"
        tp_emojis = ["🥇", "🥈", "🥉"]
        for i, tp in enumerate(tps):
            e = tp_emojis[i] if i < 3 else "📍"
            msg += f"   {e} TP{i+1}: *${tp.get('price', 0):,.4f}* (+{tp.get('pct', '?')}%)\n"
            msg += f"      _{tp.get('reason', '')}_\n"

    msg += f"""
⚖️ *RISK/REWARD:* {data.get('risk_reward', '1:X')}
⚠️ Risk Level: {data.get('risk_level', 'MEDIUM')}

━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 *CONFLUENCE (4-TF):*
{data.get('confluence_summary', 'N/A')}

💭 *SENTIMENT:*
{data.get('sentiment_summary', 'N/A')}

📐 *PATTERNS:* {', '.join(data.get('patterns_detected', ['None']))}

━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    levels = data.get("key_levels", {})
    if levels:
        supports = levels.get("support", [])
        resistances = levels.get("resistance", [])
        if supports:
            msg += f"📏 *SUPPORTS:* {', '.join(f'${s:,.2f}' for s in supports)}\n"
        if resistances:
            msg += f"📏 *RESISTANCES:* {', '.join(f'${r:,.2f}' for r in resistances)}\n"

    timing = data.get("timing", {})
    if timing:
        msg += f"""
🕐 *TIMING SCHEDULE:*
   Best Entry: {timing.get('best_entry_time', 'N/A')}
   Best Session: {timing.get('best_session', 'N/A')}
   Hold Time: {timing.get('hold_time', 'N/A')}
"""

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 *WIN PROBABILITY:*
{data.get('probability_summary', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 *FULL AI ANALYSIS:*
{data.get('analysis_full', 'N/A')}

🚫 *INVALIDATION:*
{data.get('invalid_condition', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 _OMEGA Commander — 8 AI Engines Unified_
🚀 _Powered by {PROVIDER.upper()} AI_
"""
    return msg
