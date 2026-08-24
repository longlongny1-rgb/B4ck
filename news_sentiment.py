"""
BlackMagicAI OMEGA — News & Sentiment Module
Fetches real news headlines and scores market sentiment.

Two data sources (in priority order):
1. NewsAPI.org  (env: NEWS_API_KEY)   — https://newsapi.org  free tier: 100 req/day
2. yfinance ticker.news (no key needed) — used automatically as fallback

Two sentiment scoring tiers:
1. Lexicon-based (default, instant, no extra API call) — finance-specific word lists
2. LLM-refined (optional) — pass an `llm_call` async function (e.g. ai_engine.call_llm)
   to get nuanced sentiment on the headline batch instead of/in addition to the lexicon score.
"""
import os
import re
import httpx
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from config import MARKETS

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Map our symbols to search queries that return relevant financial news
SYMBOL_QUERY_MAP = {
    "XAUUSD": "gold price OR XAU/USD",
    "EURUSD": "EUR/USD OR euro dollar forex",
    "GBPUSD": "GBP/USD OR pound dollar forex",
    "USDJPY": "USD/JPY OR dollar yen forex",
    "AUDUSD": "AUD/USD OR aussie dollar forex",
    "BTCUSDT": "Bitcoin price",
    "ETHUSDT": "Ethereum price",
    "NAS100": "Nasdaq 100",
    "US30": "Dow Jones",
    "US500": "S&P 500",
    "USOIL": "crude oil price WTI",
    "AAPL": "Apple stock AAPL",
    "TSLA": "Tesla stock TSLA",
    "NVDA": "Nvidia stock NVDA",
}

# ==================== LEXICON (finance-specific) ====================

POSITIVE_WORDS = {
    "surge", "surges", "surged", "rally", "rallies", "rallied", "soar", "soars", "soared",
    "jump", "jumps", "jumped", "gain", "gains", "gained", "climb", "climbs", "climbed",
    "bullish", "upbeat", "beat", "beats", "outperform", "outperforms", "strong", "strength",
    "record high", "breakout", "recovery", "recovers", "boost", "boosts", "boosted",
    "optimism", "optimistic", "upgrade", "upgraded", "buy rating", "expansion", "growth",
    "rebound", "rebounds", "positive", "advance", "advances", "advanced", "rate cut",
    "stimulus", "dovish", "easing", "risk-on", "inflow", "inflows", "accumulation",
}

NEGATIVE_WORDS = {
    "plunge", "plunges", "plunged", "crash", "crashes", "crashed", "slump", "slumps",
    "slumped", "tumble", "tumbles", "tumbled", "sink", "sinks", "sank", "drop", "drops",
    "dropped", "fall", "falls", "fell", "bearish", "downbeat", "miss", "misses",
    "underperform", "underperforms", "weak", "weakness", "record low", "breakdown",
    "recession", "downgrade", "downgraded", "sell rating", "contraction", "layoffs",
    "pessimism", "pessimistic", "decline", "declines", "declined", "rate hike",
    "hawkish", "tightening", "risk-off", "outflow", "outflows", "sell-off", "selloff",
    "default", "bankruptcy", "crisis", "turmoil", "volatility spike", "warning",
}

INTENSIFIERS = {"sharply", "significantly", "massively", "dramatically", "steeply"}


def _score_headline(headline: str) -> float:
    """Return a score in [-1, 1] for a single headline using lexicon matching."""
    text = headline.lower()
    words = re.findall(r"[a-z\-]+", text)
    word_set = set(words)

    pos_hits = len(word_set & POSITIVE_WORDS)
    neg_hits = len(word_set & NEGATIVE_WORDS)
    intensity = 1.3 if (word_set & INTENSIFIERS) else 1.0

    if pos_hits == 0 and neg_hits == 0:
        return 0.0

    raw = (pos_hits - neg_hits) / max(pos_hits + neg_hits, 1)
    return max(-1.0, min(1.0, raw * intensity))


def score_headlines_lexicon(headlines: List[str]) -> Dict:
    """Score a batch of headlines and aggregate into an overall sentiment reading."""
    if not headlines:
        return {"score": 0.0, "label": "NEUTRAL", "headline_count": 0, "confidence": "LOW"}

    scores = [_score_headline(h) for h in headlines]
    avg = sum(scores) / len(scores)
    nonzero = [s for s in scores if s != 0]

    if avg > 0.15:
        label = "BULLISH"
    elif avg < -0.15:
        label = "BEARISH"
    else:
        label = "NEUTRAL"

    confidence = "HIGH" if len(nonzero) >= 5 else "MEDIUM" if len(nonzero) >= 2 else "LOW"

    return {
        "score": round(avg, 3),
        "label": label,
        "headline_count": len(headlines),
        "scored_count": len(nonzero),
        "confidence": confidence,
    }


# ==================== NEWS FETCHING ====================

def fetch_headlines_newsapi(symbol_name: str, limit: int = 15, hours_back: int = 48) -> List[str]:
    """Fetch fresh headlines from NewsAPI.org. Requires NEWS_API_KEY."""
    if not NEWS_API_KEY:
        return []
    query = SYMBOL_QUERY_MAP.get(symbol_name.upper(), symbol_name)
    from_time = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "q": query,
        "from": from_time,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": limit,
        "apiKey": NEWS_API_KEY,
    }
    try:
        resp = httpx.get(NEWS_API_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        return [a["title"] for a in articles if a.get("title")]
    except Exception:
        return []


def fetch_headlines_yfinance(symbol_name: str, limit: int = 15) -> List[str]:
    """Fallback: use the existing yfinance-based headline fetcher (no API key needed)."""
    try:
        from market_data import get_real_news
        raw = get_real_news(symbol_name, limit=limit)
        # raw entries look like "Title (Source: X)" — strip the source suffix for scoring
        return [re.sub(r"\s*\(Source:.*\)$", "", h) for h in raw]
    except Exception:
        return []


def get_headlines(symbol_name: str, limit: int = 15) -> List[str]:
    """Get headlines, preferring NewsAPI, falling back to yfinance."""
    headlines = fetch_headlines_newsapi(symbol_name, limit=limit)
    if not headlines:
        headlines = fetch_headlines_yfinance(symbol_name, limit=limit)
    return headlines


# ==================== PUBLIC API ====================

def get_news_sentiment(symbol_name: str, limit: int = 15) -> Dict:
    """Fetch real headlines for a symbol and return a lexicon-based sentiment reading."""
    symbol_name = symbol_name.upper()
    if symbol_name not in MARKETS:
        return {"error": "unknown_symbol"}

    headlines = get_headlines(symbol_name, limit=limit)
    result = score_headlines_lexicon(headlines)
    result["symbol"] = symbol_name
    result["headlines"] = headlines[:10]
    result["source"] = "newsapi" if NEWS_API_KEY and headlines else "yfinance"
    return result


async def get_news_sentiment_llm(symbol_name: str, llm_call, limit: int = 15) -> Dict:
    """Optional deeper sentiment pass using an LLM (e.g. ai_engine.call_llm).

    `llm_call` must be an async callable with signature:
        await llm_call(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str
    (matches ai_engine.call_llm's signature so it can be passed directly.)
    """
    symbol_name = symbol_name.upper()
    if symbol_name not in MARKETS:
        return {"error": "unknown_symbol"}

    headlines = get_headlines(symbol_name, limit=limit)
    if not headlines:
        return {"score": 0.0, "label": "NEUTRAL", "headline_count": 0, "reasoning": "No headlines available"}

    headline_block = "\n".join(f"- {h}" for h in headlines)
    system_prompt = (
        "You are a financial news sentiment analyst. Given a list of recent headlines about a market, "
        "respond ONLY in JSON: "
        '{"sentiment": "BULLISH"|"BEARISH"|"NEUTRAL", "score": -1.0 to 1.0, '
        '"reasoning": "brief explanation in Khmer and English"}'
    )
    user_prompt = f"SYMBOL: {symbol_name}\nRECENT HEADLINES:\n{headline_block}"

    try:
        raw = await llm_call(system_prompt, user_prompt, 0.2, 400)
        import json
        cleaned = raw.strip().strip("```json").strip("```").strip()
        parsed = json.loads(cleaned)
        return {
            "symbol": symbol_name,
            "score": parsed.get("score", 0.0),
            "label": parsed.get("sentiment", "NEUTRAL"),
            "reasoning": parsed.get("reasoning", ""),
            "headline_count": len(headlines),
            "headlines": headlines[:10],
            "source": "llm",
        }
    except Exception:
        # Fall back to lexicon scoring if the LLM call/parse fails
        fallback = score_headlines_lexicon(headlines)
        fallback["symbol"] = symbol_name
        fallback["headlines"] = headlines[:10]
        fallback["source"] = "lexicon_fallback"
        return fallback


def format_sentiment_message(sentiment: Dict) -> str:
    """Format a sentiment reading as a Telegram Markdown message."""
    if "error" in sentiment:
        return f"❌ {sentiment['error']}"

    label = sentiment.get("label", "NEUTRAL")
    icon = "🟢" if label == "BULLISH" else "🔴" if label == "BEARISH" else "⚪"
    score = sentiment.get("score", 0.0)

    msg = f"""{icon} *NEWS SENTIMENT — {sentiment.get('symbol', '')}*
━━━━━━━━━━━━━━━━━━━
📊 Sentiment: *{label}* ({score:+.2f})
📰 Headlines analyzed: {sentiment.get('headline_count', 0)}
🔎 Source: {sentiment.get('source', 'unknown')}
"""
    if sentiment.get("reasoning"):
        msg += f"\n💭 {sentiment['reasoning']}\n"

    headlines = sentiment.get("headlines", [])
    if headlines:
        msg += "\n━━━━━━━━━━━━━━━━━━━\n📰 *Recent headlines:*\n"
        for h in headlines[:5]:
            msg += f"• {h}\n"

    msg += "\n⚠️ _Sentiment is directional context only, not financial advice._"
    return msg


def sentiment_to_indicator_signal(sentiment: Dict) -> Optional[dict]:
    """Convert a sentiment reading into the same {signal, value, reason} shape used by
    analysis.get_indicator_signals(), so it can be merged into signals.generate_signal()'s
    weighted scoring as an extra "NEWS" indicator."""
    if "error" in sentiment or sentiment.get("headline_count", 0) == 0:
        return None
    label = sentiment.get("label", "NEUTRAL")
    score = sentiment.get("score", 0.0)
    sig = "BUY" if label == "BULLISH" else "SELL" if label == "BEARISH" else "NEUTRAL"
    return {
        "signal": sig,
        "value": round(score, 3),
        "reason": f"News sentiment {label} (score={score:+.2f}, {sentiment.get('headline_count', 0)} headlines)",
    }
