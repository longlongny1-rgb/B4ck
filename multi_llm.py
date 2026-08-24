"""
BlackMagicAI OMEGA — Multi-LLM Consensus Engine
Copyright (c) 2026 BlackMagicAI. All Rights Reserved.

Multi-Model AI Analysis:
- DeepSeek R1 (reasoning) via OpenRouter
- OpenAI GPT-4o / GPT-4 Turbo
- Anthropic Claude 3.5 Sonnet
- Google Gemini 2.0 Flash
- Groq Llama 3.3 70B (existing)
- Multi-Model Consensus (ensemble voting)
- News Sentiment Analysis
- Macro-Fundamental Analysis
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)

# ==================== MODEL PROVIDERS ====================

PROVIDER_CONFIGS = {
    "openrouter": {
        "models": {
            "deepseek-r1": "deepseek/deepseek-r1",
            "claude-sonnet": "anthropic/claude-3.5-sonnet",
            "gpt-4o": "openai/gpt-4o",
            "gemini-flash": "google/gemini-2.0-flash-001",
            "llama-405b": "meta-llama/llama-3.1-405b-instruct",
        },
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
    "openai": {
        "models": {"gpt-4o": "gpt-4o", "gpt-4-turbo": "gpt-4-turbo"},
        "base_url": "https://api.openai.com/v1/chat/completions",
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
    "deepseek": {
        "models": {"deepseek-r1": "deepseek-reasoner", "deepseek-chat": "deepseek-chat"},
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
    "anthropic": {
        "models": {"claude-sonnet": "claude-3-5-sonnet-20241022"},
        "base_url": "https://api.anthropic.com/v1/messages",
        "header_key": "x-api-key",
        "header_prefix": "",
    },
    "google": {
        "models": {"gemini-flash": "gemini-2.0-flash"},
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
        "header_key": "key",
        "header_prefix": "",
    },
}


def _get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider from environment variables."""
    key_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    env_var = key_map.get(provider, "")
    return os.getenv(env_var)


def get_available_models() -> Dict[str, List[str]]:
    """Discover which models are available based on configured API keys."""
    available = {}
    for provider, config in PROVIDER_CONFIGS.items():
        key = _get_api_key(provider)
        if key:
            available[provider] = list(config["models"].keys())
    return available


# ==================== SINGLE MODEL CALL ====================

async def _call_openrouter(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    api_key = _get_api_key("openrouter")
    if not api_key:
        return None

    config = PROVIDER_CONFIGS["openrouter"]
    model_id = config["models"].get(model, model)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config["base_url"],
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    text = await resp.text()
                    logger.warning(f"OpenRouter {model} error {resp.status}: {text[:200]}")
                    return None
    except Exception as e:
        logger.warning(f"OpenRouter call failed: {e}")
        return None


async def _call_openai(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    api_key = _get_api_key("openai")
    if not api_key:
        return None

    config = PROVIDER_CONFIGS["openai"]
    model_id = config["models"].get(model, model)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config["base_url"],
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    text = await resp.text()
                    logger.warning(f"OpenAI {model} error {resp.status}: {text[:200]}")
                    return None
    except Exception as e:
        logger.warning(f"OpenAI call failed: {e}")
        return None


async def _call_groq_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    """Use existing Groq key for direct comparison."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                return None
    except Exception as e:
        logger.warning(f"Groq call failed: {e}")
        return None


# ==================== MULTI-MODEL CONSENSUS ====================

CONSENSUS_SYSTEM_PROMPT = """You are a professional institutional trading analyst with 20+ years experience at top hedge funds.
Analyze the market data and provide:

1. DIRECTION: BUY, SELL, or HOLD (exactly one)
2. CONFIDENCE: 1-100
3. KEY REASONS: 2-3 bullet points
4. RISK LEVEL: Low/Medium/High
5. STOP LOSS SUGGESTION
6. TAKE PROFIT SUGGESTION

Be concise and data-driven. Respond in this exact JSON format:
{
  "direction": "BUY|SELL|HOLD",
  "confidence": 75,
  "reasons": ["reason1", "reason2", "reason3"],
  "risk_level": "Medium",
  "stop_loss": "price or %",
  "take_profit": "price or %",
  "summary": "one-line trade thesis"
  "gpt-4o": 1.5,          # Tier 1 - Smartest
    "deepseek-r1": 1.5,     # Tier 1 - Strong reasoning
    "claude-sonnet": 1.4,   # Tier 1.5
    "gpt-4-turbo": 1.3,
    "gemini-flash": 1.2,    # Tier 2 - Fast
    "llama3.3-70b": 1.0,    # Tier 3 - Baseline
    "default": 1.0
}
MODEL_WEIGHTS = {
    "gpt-4o": 1.5,          # Tier 1 - Smartest
    "deepseek-r1": 1.5,     # Tier 1 - Strong reasoning
    "claude-sonnet": 1.4,   # Tier 1.5
    "gpt-4-turbo": 1.3,
    "gemini-flash": 1.2,    # Tier 2 - Fast
    "llama3.3-70b": 1.0,    # Tier 3 - Baseline
    "default": 1.0
    }
"""

async def multi_model_consensus(
    
    symbol: str,
    market_name: str,
    price: float,
    change_pct: float,
    timeframe: str = "1d",
    additional_context: str = "",
) -> Dict:
    """
    Run analysis across multiple available LLMs and build a consensus using Weighted Conviction Score.
    """
    user_prompt = f"""Analyze {symbol} ({market_name}):

Current Price: ${price:,.4f}
24h Change: {change_pct:+.2f}%
Timeframe: {timeframe}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

{additional_context}

Provide your trading analysis in the specified JSON format."""

    available = get_available_models()
    results = {}

    # Always include Groq (we know it works)
    groq_result = await _call_groq_llm(CONSENSUS_SYSTEM_PROMPT, user_prompt)
    if groq_result:
        parsed = _parse_consensus_response(groq_result, "groq-llama3.3-70b")
        if parsed:
            results["groq-llama3.3-70b"] = parsed

    # Try OpenRouter models
    if "openrouter" in available:
        for model_key in available["openrouter"][:3]:  # Max 3 for speed
            result = await _call_openrouter(model_key, CONSENSUS_SYSTEM_PROMPT, user_prompt)
            if result:
                parsed = _parse_consensus_response(result, model_key)
                if parsed:
                    results[f"openrouter-{model_key}"] = parsed

    # Try OpenAI direct
    if "openai" in available:
        for model_key in available["openai"][:1]:
            result = await _call_openai(model_key, CONSENSUS_SYSTEM_PROMPT, user_prompt)
            if result:
                parsed = _parse_consensus_response(result, model_key)
                if parsed:
                    results[f"openai-{model_key}"] = parsed

    if not results:
        return {"error": "No models available. Add API keys to .env", "available_providers": list(available.keys())}

    # ==========================================
    # យន្តការថ្មី: Weighted Conviction Scoring
    # ==========================================
    buy_conviction = 0.0
    sell_conviction = 0.0
    hold_conviction = 0.0
    
    buy_count, sell_count, hold_count = 0, 0, 0
    total_confidence = 0

    for model_name, r in results.items():
        # កំណត់ទម្ងន់ផ្អែកលើឈ្មោះម៉ូដែល
        weight = MODEL_WEIGHTS.get("default", 1.0)
        for key, w in MODEL_WEIGHTS.items():
            if key in model_name.lower():
                weight = w
                break
        
        confidence = r.get("confidence", 50)
        total_confidence += confidence
        
        # ពិន្ទុភាពជឿជាក់ = ទម្ងន់ x ភាគរយទំនុកចិត្ត
        score = weight * confidence
        
        direction = r["direction"]
        if direction == "BUY":
            buy_conviction += score
            buy_count += 1
        elif direction == "SELL":
            sell_conviction += score
            sell_count += 1
        else:
            hold_conviction += score
            hold_count += 1

    # គណនាទិសដៅចុងក្រោយដោយពឹងផ្អែកលើពិន្ទុ
    total_conviction = buy_conviction + sell_conviction + hold_conviction
    max_conviction = max(buy_conviction, sell_conviction, hold_conviction)

    if max_conviction == buy_conviction and buy_conviction > 0:
        consensus_dir = "BUY"
    elif max_conviction == sell_conviction and sell_conviction > 0:
        consensus_dir = "SELL"
    else:
        consensus_dir = "HOLD"

    # គណនាភាគរយនៃការយល់ស្រប (Agreement) ផ្អែកលើទម្ងន់
    agreement = (max_conviction / total_conviction * 100) if total_conviction > 0 else 0
    avg_confidence = total_confidence / len(results) if results else 50
    weighted_score = ((buy_conviction - sell_conviction) / max(total_conviction, 1)) * 100

    # Collect all reasons
    all_reasons = []
    for model, r in results.items():
        for reason in r.get("reasons", []):
            all_reasons.append(f"[{model}] {reason}")

    return {
        "symbol": symbol,
        "models_used": len(results),
        "model_names": list(results.keys()),
        "consensus_direction": consensus_dir,
        "agreement_pct": round(agreement, 1),
        "avg_confidence": round(avg_confidence, 1),
        "weighted_score": round(weighted_score, 1),
        "vote_breakdown": {"BUY": buy_count, "SELL": sell_count, "HOLD": hold_count},
        "per_model": results,
        "key_reasons": all_reasons[:8],
        "strength": (
            "🔥 VERY STRONG" if agreement >= 75 and avg_confidence >= 70
            else "💪 STRONG" if agreement >= 55
            else "⚖️ MIXED" if agreement >= 40
            else "🤔 WEAK — Model Disagreement"
        ),
        "timestamp": datetime.now().isoformat(),
    }

    }


def _parse_consensus_response(text: str, model_name: str) -> Optional[Dict]:
    """Parse JSON from model response."""
    try:
        # Find JSON block
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            json_str = text[start:end].strip()
        elif "{" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
        else:
            json_str = text

        data = json.loads(json_str)

        return {
            "direction": data.get("direction", "HOLD").upper(),
            "confidence": max(0, min(100, int(data.get("confidence", 50)))),
            "reasons": data.get("reasons", ["No reasons provided"])[:3],
            "risk_level": data.get("risk_level", "Medium"),
            "stop_loss": data.get("stop_loss", "N/A"),
            "take_profit": data.get("take_profit", "N/A"),
            "summary": data.get("summary", ""),
            "model": model_name,
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse response from {model_name}: {e}")
        # Fallback: extract direction from raw text
        text_upper = text.upper()
        if "BUY" in text_upper and "SELL" not in text_upper:
            direction = "BUY"
        elif "SELL" in text_upper and "BUY" not in text_upper:
            direction = "SELL"
        else:
            direction = "HOLD"
        return {
            "direction": direction,
            "confidence": 50,
            "reasons": ["Could not parse structured output"],
            "risk_level": "Unknown",
            "stop_loss": "N/A",
            "take_profit": "N/A",
            "summary": text[:200],
            "model": model_name,
        }


# ==================== NEWS SENTIMENT ANALYSIS ====================

NEWS_SENTIMENT_PROMPT = """You are a financial news sentiment analyst for a hedge fund.
Analyze the following headline/text for its impact on the market.

Return JSON:
{
  "sentiment": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 85,
  "impact_score": 7,
  "key_drivers": ["factor1", "factor2"],
  "affected_sectors": ["tech", "finance"],
  "summary": "one-line interpretation",
  "trade_implication": "what this means for trading"
}

Impact scores: 1-3 (minor), 4-6 (moderate), 7-8 (significant), 9-10 (major/crisis)
"""


async def analyze_news_sentiment(
    headlines: List[str],
    symbol: str = "",
) -> Dict:
    """
    Analyze sentiment of news headlines for market impact.

    Args:
        headlines: List of news headlines/texts to analyze
        symbol: Optional market symbol for context
    """
    if not headlines:
        return {"error": "No headlines provided"}

    news_text = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines[:10]))

    user_prompt = f"""Analyze the following news for trading impact:
Symbol: {symbol or 'General Market'}

HEADLINES:
{news_text}

Provide sentiment analysis in the JSON format."""

    response = await _call_groq_llm(NEWS_SENTIMENT_PROMPT, user_prompt)

    if not response:
        # Try OpenRouter fallback
        response = await _call_openrouter("deepseek-r1", NEWS_SENTIMENT_PROMPT, user_prompt)

    if not response:
        return {"error": "No AI model available for news analysis"}

    result = _parse_news_response(response)
    result["headlines_analyzed"] = len(headlines[:10])
    result["timestamp"] = datetime.now().isoformat()

    return result


def _parse_news_response(text: str) -> Dict:
    """Parse news sentiment response."""
    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            json_str = text[start:end].strip()
        elif "{" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
        else:
            return {"error": "Could not parse response", "raw": text[:500]}

        data = json.loads(json_str)
        return {
            "sentiment": data.get("sentiment", "NEUTRAL"),
            "confidence": int(data.get("confidence", 50)),
            "impact_score": int(data.get("impact_score", 5)),
            "key_drivers": data.get("key_drivers", []),
            "affected_sectors": data.get("affected_sectors", []),
            "summary": data.get("summary", ""),
            "trade_implication": data.get("trade_implication", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {"sentiment": "NEUTRAL", "confidence": 40, "summary": text[:300]}


# ==================== MACRO-FUNDAMENTAL ANALYSIS ====================

MACRO_PROMPT = """You are a macro-economic strategist at a top-tier hedge fund.
Analyze the interplay of economic factors affecting the given asset.

Consider:
- Interest rates & monetary policy
- Inflation trends
- Geopolitical risks
- Supply/demand dynamics
- Institutional flows
- Seasonality
- Intermarket relationships (DXY, Bonds, Equities, Commodities)

Provide JSON:
{
  "macro_outlook": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 70,
  "key_factors": ["factor1", "factor2", "factor3"],
  "risk_scenarios": ["risk1", "risk2"],
  "catalyst_events": ["event1"],
  "institutional_view": "How big money is positioned",
  "summary": "2-3 sentence macro thesis"
}
"""


async def macro_fundamental_analysis(
    symbol: str,
    market_name: str,
    price: float,
    timeframe: str = "1w",
) -> Dict:
    """Macro/fundamental analysis for institutional context."""
    user_prompt = f"""Analyze macro-fundamental factors for:
Symbol: {symbol} ({market_name})
Current Price: ${price:,.4f}
Timeframe: {timeframe}
Date: {datetime.now().strftime('%Y-%m-%d')}

What macro factors should traders consider right now?"""

    response = await _call_groq_llm(MACRO_PROMPT, user_prompt)

    if not response:
        response = await _call_openrouter("deepseek-r1", MACRO_PROMPT, user_prompt)

    if not response:
        return {"error": "No AI available for macro analysis", "symbol": symbol}

    return _parse_macro_response(response)


def _parse_macro_response(text: str) -> Dict:
    """Parse macro analysis response."""
    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            json_str = text[start:end].strip()
        elif "{" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
        else:
            return {"macro_outlook": "NEUTRAL", "summary": text[:500]}

        data = json.loads(json_str)
        return {
            "macro_outlook": data.get("macro_outlook", "NEUTRAL"),
            "confidence": int(data.get("confidence", 50)),
            "key_factors": data.get("key_factors", []),
            "risk_scenarios": data.get("risk_scenarios", []),
            "catalyst_events": data.get("catalyst_events", []),
            "institutional_view": data.get("institutional_view", ""),
            "summary": data.get("summary", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {"macro_outlook": "NEUTRAL", "confidence": 40, "summary": text[:500]}


# ==================== FORMATTERS ====================

def format_consensus_message(consensus: Dict) -> str:
    """Format multi-model consensus as Telegram message."""
    if "error" in consensus:
        return f"❌ {consensus['error']}"

    direction_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}
    dir_emoji = direction_emoji.get(consensus["consensus_direction"], "⚪")

    msg = f"""🧠 *MULTI-LLM CONSENSUS REPORT*
━━━━━━━━━━━━━━━━━━━━━━

📊 *{consensus['symbol']}* — {consensus['strength']}

{dir_emoji} *Consensus: {consensus['consensus_direction']}*
├ Agreement: {consensus['agreement_pct']}%
├ Avg Confidence: {consensus['avg_confidence']}%
├ Weighted Score: {consensus['weighted_score']}
└ Models: {consensus['models_used']} AI engines

━━━━━━━━━━━━━━━━━━━━━━
🗳️ *VOTE BREAKDOWN*
├ 🟢 BUY: {consensus['vote_breakdown']['BUY']}
├ 🔴 SELL: {consensus['vote_breakdown']['SELL']}
└ ⚪ HOLD: {consensus['vote_breakdown']['HOLD']}

━━━━━━━━━━━━━━━━━━━━━━
📋 *PER-MODEL ANALYSIS*
"""

    for model, result in consensus.get("per_model", {}).items():
        d_emoji = direction_emoji.get(result["direction"], "⚪")
        msg += f"""
*{model}*: {d_emoji} {result['direction']} ({result['confidence']}%)
├ Risk: {result['risk_level']}
├ SL: {result['stop_loss']} | TP: {result['take_profit']}
└ {result.get('summary', '')[:100]}
"""

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
🔑 *KEY REASONS*
"""
    for reason in consensus.get("key_reasons", [])[:6]:
        msg += f"├ {reason}\n"

    msg += """
━━━━━━━━━━━━━━━━━━━━━━
🔮 _Powered by BlackMagicAI OMEGA Multi-LLM Engine_
"""
    return msg


def format_news_sentiment_message(sentiment: Dict, symbol: str = "") -> str:
    """Format news sentiment analysis."""
    if "error" in sentiment:
        return f"❌ News Analysis: {sentiment['error']}"

    s_emoji = {"BULLISH": "🟢📈", "BEARISH": "🔴📉", "NEUTRAL": "⚪📊"}
    emoji = s_emoji.get(sentiment.get("sentiment", "NEUTRAL"), "⚪")

    impact_bars = "█" * min(10, sentiment.get("impact_score", 5))

    msg = f"""📰 *NEWS SENTIMENT ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━━

{f"{emoji} *{sentiment['sentiment']}*" if symbol else f"📊 *Market Sentiment*"}
├ Confidence: {sentiment.get('confidence', '?')}%
├ Impact: [{impact_bars}] {sentiment.get('impact_score', '?')}/10
└ Analyzed: {sentiment.get('headlines_analyzed', '?')} headlines

━━━━━━━━━━━━━━━━━━━━━━
📝 *Summary*
_{sentiment.get('summary', 'No summary')}_

"""

    if sentiment.get("key_drivers"):
        msg += "🔑 *Key Drivers*\n"
        for driver in sentiment["key_drivers"]:
            msg += f"├ {driver}\n"
        msg += "\n"

    if sentiment.get("affected_sectors"):
        msg += "📊 *Affected Sectors*\n"
        msg += "├ " + ", ".join(sentiment["affected_sectors"][:5]) + "\n\n"

    if sentiment.get("trade_implication"):
        msg += f"💡 *Trade Implication*\n├ {sentiment['trade_implication']}\n\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🔮 _BlackMagicAI OMEGA News Engine_\n"
    return msg


def format_macro_message(macro: Dict) -> str:
    """Format macro analysis."""
    if "error" in macro:
        return f"❌ Macro Analysis: {macro['error']}"

    m_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}
    emoji = m_emoji.get(macro.get("macro_outlook", "NEUTRAL"), "⚪")

    msg = f"""🏛️ *MACRO-FUNDAMENTAL ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━━

{emoji} *Outlook: {macro.get('macro_outlook', 'NEUTRAL')}*
├ Confidence: {macro.get('confidence', '?')}%

"""

    if macro.get("key_factors"):
        msg += "🔑 *Key Factors*\n"
        for f in macro["key_factors"]:
            msg += f"├ {f}\n"
        msg += "\n"

    if macro.get("risk_scenarios"):
        msg += "⚠️ *Risk Scenarios*\n"
        for r in macro["risk_scenarios"]:
            msg += f"├ {r}\n"
        msg += "\n"

    if macro.get("catalyst_events"):
        msg += "📅 *Catalysts to Watch*\n"
        for c in macro["catalyst_events"]:
            msg += f"├ {c}\n"
        msg += "\n"

    if macro.get("institutional_view"):
        msg += f"🏦 *Institutional View*\n├ {macro['institutional_view']}\n\n"

    msg += f"📝 *Thesis*\n├ {macro.get('summary', 'No summary')}\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🔮 _BlackMagicAI OMEGA Macro Engine_\n"

    return msg
