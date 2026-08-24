# BlackMagicAI OMEGA — Analysis Upgrade Roadmap

សេចក្តីសង្ខេប៖ ប្រព័ន្ធបច្ចុប្បន្ន (analysis.py, quant_engine.py, ai_engine.py, multi_llm.py, signals.py) មានមូលដ្ឋានល្អរួចហើយ —
technical indicators ស្តង់ដារ, Monte Carlo / VaR / Kelly, និង multi-LLM prompt framework។ ខាងក្រោមនេះជា roadmap
ជាដំណាក់កាល ដើម្បីធ្វើឱ្យសមត្ថភាពវិភាគខ្លាំងជាងមុន ដោយមិនបំបែក interface ដែលមានស្រាប់ (bot.py អាចហៅ function ដដែល)។

ឯកសារកូដដែលភ្ជាប់មកជាមួយ roadmap នេះ (ត្រៀមរួចរាល់ ប្រើបានភ្លាមៗ)៖
- `analysis.py` (upgraded) — បន្ថែម Ichimoku Cloud, Fibonacci Retracement, Candlestick Pattern Recognition, VWAP, Parabolic SAR, Chaikin Money Flow
- `news_sentiment.py` (new) — real news headlines + lexicon-based sentiment scoring, optional LLM-refined sentiment
- `backtest.py` (new) — event-driven backtest engine ដើម្បីវាស់ win-rate/Sharpe/Drawdown ជាក់ស្តែងលើទិន្នន័យប្រវត្តិសាស្ត្រ

---

## Phase 1 — Technical Analysis Depth (បញ្ចប់ក្នុងកញ្ចប់នេះ)

| Feature | ស្ថានភាព | មូលហេតុ |
|---|---|---|
| Ichimoku Cloud (Tenkan/Kijun/Senkou A&B/Chikou) | ✅ ភ្ជាប់មកជាមួយ | ផ្តល់ trend + support/resistance ថ្នាក់ត្រូវគ្នា timeframe ធំ |
| Fibonacci Retracement (auto swing high/low) | ✅ ភ្ជាប់មកជាមួយ | កំណត់ entry zone ច្បាស់ជាង static support/resistance |
| Candlestick Pattern Recognition (Doji, Engulfing, Hammer, Shooting Star, Morning/Evening Star) | ✅ ភ្ជាប់មកជាមួយ | បន្ថែម price-action confirmation មិនត្រូវការ pandas_ta |
| VWAP (Volume Weighted Average Price) | ✅ ភ្ជាប់មកជាមួយ | សំខាន់សម្រាប់ intraday (15m/1h) — institutional benchmark |
| Parabolic SAR | ✅ ភ្ជាប់មកជាមួយ | Trailing stop / trend reversal signal |
| Chaikin Money Flow (CMF) | ✅ ភ្ជាប់មកជាមួយ | Volume-confirmed accumulation/distribution |
| Divergence Detection (RSI/MACD vs Price) | 🔲 ជំហានបន្ទាប់ | ត្រូវការ peak/trough detection algorithm — មិនស្មុគស្មាញ តែត្រូវ tune threshold លើទិន្នន័យពិត |
| Multi-timeframe auto-confluence (គណនាដោយស្វ័យប្រវត្តិ មិនមែនពឹង LLM) | 🔲 ជំហានបន្ទាប់ | ហៅ `generate_signal()` លើ 4 timeframes ក្នុងពេលតែមួយ ហើយបូក weighted score |

## Phase 2 — Quant Engine: ភស្តុតាងជាក់ស្តែង (backtest.py ភ្ជាប់មកជាមួយ)

បញ្ហាធំបំផុតឥឡូវនេះ៖ `signals.py` និង `quant_engine.py` **មិនដែលត្រូវបានធ្វើតេស្តលើទិន្នន័យប្រវត្តិសាស្ត្រ** —
`kelly_criterion()` ប្រើ win_rate/avg_win/avg_loss ជា **default hardcoded values** (0.55 / 0.02 / 0.015)
មិនមែនមកពីលទ្ធផលពិតរបស់ strategy ទេ។ នេះមានន័យថា Kelly sizing និង quant_score បច្ចុប្បន្នមិនអាចទុកចិត្តបានពេញលេញ។

`backtest.py` ដែលភ្ជាប់មកជាមួយ ដោះស្រាយបញ្ហានេះ៖
1. ដំណើរការ `generate_signal()` ឡើងវិញលើគ្រប់ bar ប្រវត្តិសាស្ត្រ (walk-forward, គ្មាន look-ahead bias)
2. កត់ត្រា entry/SL/TP/result ជាក់ស្តែងតាម `database.py` schema ដដែល (`SignalRecord`)
3. គណនា real win_rate, avg_win, avg_loss → ចាក់ចូល `kelly_criterion()` ជំនួស default guess
4. ចេញ report: total trades, win rate, profit factor, max consecutive losses, equity curve data

**ជំហានបន្ទាប់ (មិនទាន់ធ្វើ)**: parameter optimization (grid search លើ ATR multiplier, RSI thresholds)
ដើម្បីរក config ល្អបំផុតក្នុងមួយ market — នេះត្រូវការ compute timeច្រើន គួរដំណើរការ offline មិនមែនក្នុង bot ទេ។

## Phase 3 — Real News & Fundamental Data (news_sentiment.py ភ្ជាប់មកជាមួយ)

អ្នកបានជ្រើសរើសបន្ថែម real news sentiment។ ការអនុវត្ត៖

1. **Headline source**: ប្រើ `yfinance` news ដែលមានស្រាប់ (`market_data.get_real_news`) ជា fallback ឥតគិតថ្លៃ,
   និងបន្ថែម optional NewsAPI.org / Finnhub integration (ត្រូវការ `NEWS_API_KEY` / `FINNHUB_API_KEY` ក្នុង `.env`)
   សម្រាប់ headlines ស៊ីជម្រៅជាង និង coverage ធំជាង។
2. **Sentiment scoring — 2 tiers**:
   - **Tier 1 (ឥតគិតថ្លៃ, លឿន)**: lexicon-based scoring (positive/negative finance-specific word lists) — ដំណើរការក្នុង milliseconds គ្មានត្រូវការ API call បន្ថែម។
   - **Tier 2 (ជ្រៅជាង, ជាជម្រើស)**: ហៅ `ai_engine.call_llm()` ដែលមានស្រាប់ជាមួយ `SENTIMENT_PROMPT` ដើម្បីវិភាគ headlines ជាក្រុម — ផ្តល់ context/nuance ល្អជាង lexicon។
3. **Integration point**: `signals.generate_signal()` អាចទទួល `news_sentiment` score ថែម ជា weight ថ្មីមួយក្នុង `weights` dict (ឧ. `"NEWS": 0.8`) ដូច្នេះសញ្ញា technical + sentiment ក្លាយជា confluence ពិតប្រាកដ មិនមែនគ្រាន់តែបង្ហាញដាច់ដោយឡែក។

**កំណត់សំខាន់**: `NEWS_API_KEY` ត្រូវការចុះឈ្មោះនៅ https://newsapi.org (free tier: 100 req/day) ឬ
https://finnhub.io (free tier ក៏មាន)។ បើគ្មាន key ទេ ប្រព័ន្ធ fallback ទៅ yfinance headlines ដោយស្វ័យប្រវត្តិ។

## Phase 4 — AI/LLM Engine Reliability (ជំហានបន្ទាប់ — មិនទាន់សរសេរកូដ)

ការសង្កេតលើ `ai_engine.py` / `multi_llm.py`៖
- `ai_commander_analyze()` និង prompt ជាច្រើនត្រូវការ provider តែមួយ (whichever key ដំបូងគេរកឃើញ) — មិនមាន automatic fallback ទៅ provider ទី២ បើ provider ទី១ fail ឬ rate-limited។
- `multi_llm.py` មាន consensus framework រួចហើយ (Multi-Model Consensus) — គួរភ្ជាប់ជាមួយ `ai_commander_analyze()` ដើម្បីឱ្យ Commander report ជា **ensemble** ជំនួសឱ្យពឹងលើ model តែមួយ (កាត់បន្ថយ hallucination និង bias របស់ model មួយៗ)។
- គ្មាន caching — real-time analysis ហៅ LLM API រាល់ request សូម្បីតែ 2 requests ជាប់គ្នាក្នុងរយៈពេលខ្លីលើ symbol/timeframe ដូចគ្នា។ គួរបន្ថែម short TTL cache (ឧ. 60-120s) ដើម្បីសន្សំ cost និង latency។
- `parse_json_response()` (មិនបានឃើញកូដពេញ តែត្រូវហៅជានិច្ច) គួរមាន retry + schema validation ដើម្បីទប់ LLM response មិនត្រឹមត្រូវ format។

**អនុសាសន៍ អនុវត្តលំដាប់**៖ (1) provider fallback chain, (2) response caching, (3) ភ្ជាប់ multi_llm consensus ចូល commander។

---

## របៀបប្រើឯកសារថ្មី

```python
# analysis.py — indicators ថ្មីត្រូវបានបញ្ចូលស្វ័យប្រវត្តិក្នុង compute_full_analysis()
from analysis import compute_full_analysis
result = compute_full_analysis(df)
result["signals"]["ICHIMOKU"]   # signal ថ្មី
result["signals"]["FIBONACCI"]
result["signals"]["CANDLESTICK"]
result["signals"]["VWAP"]
result["signals"]["PSAR"]
result["signals"]["CMF"]

# news_sentiment.py
from news_sentiment import get_news_sentiment
sentiment = get_news_sentiment("XAUUSD")
# {"score": -0.42, "label": "BEARISH", "headline_count": 8, "headlines": [...]}

# backtest.py
from backtest import run_backtest
report = run_backtest("XAUUSD", timeframe="1h", lookback_days=180)
# {"total_trades": 64, "win_rate": 57.8, "profit_factor": 1.34, ...}
# ចាក់លទ្ធផលនេះទៅ kelly_criterion(win_rate=report["win_rate"], avg_win=..., avg_loss=...)
```

## អាទិភាពស្នើ (បើនឹងធ្វើបន្តបន្ទាប់)

1. **Backtest engine → Kelly** (Phase 2) — កែតម្រូវ position sizing ឱ្យផ្អែកលើទិន្នន័យពិត មិនមែន guess។ ជះឥទ្ធិពលដល់ real money risk ដូច្នេះជាអាទិភាពខ្ពស់បំផុត។
2. **News sentiment integration into signal scoring** (Phase 3) — ធ្វើឱ្យ signal មិនពឹងតែលើ technical.
3. **Divergence detection + auto multi-TF confluence** (Phase 1 remainder) — បង្កើន precision.
4. **LLM provider fallback + caching + consensus merge** (Phase 4) — បង្កើន reliability/cost efficiency.
