#!/usr/bin/env python3
"""
BlackMagicAI OMEGA — AI-Powered Telegram Trading Bot
Copyright (c) 2026 BlackMagicAI. All Rights Reserved.
Licensed for commercial sale. See LICENSE file for terms.

AI Trading Signals | Technical Analysis | Track Record | Journal | Alerts
8 AI Engines | OMEGA Commander | Multi-Timeframe Confluence
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from config import MARKETS, CATEGORIES, COMMANDS, TIMEFRAMES
from database import (
    SessionLocal, save_signal, get_track_record, update_signal_result,
    TradeJournal, AlertConfig, UserSettings
)
from market_data import fetch_ohlcv, get_current_price, get_live_ticker_text, get_multi_prices
from analysis import compute_full_analysis
from signals import generate_signal, format_signal_message, format_analysis_message
from license_manager import is_license_valid, validate_key as validate_license_key, save_activated_license, check_license_on_startup, generate_key as generate_license_key
from ai_engine import (
    ai_analyze_market, ai_scan_markets, format_ai_signal_message,
    format_ai_scan_message, AI_AVAILABLE, PROVIDER as AI_PROVIDER,
    ai_confluence, ai_build_strategy, ai_sentiment, ai_detect_patterns,
    ai_psychology, ai_correlated_markets,
    format_confluence_message, format_strategy_message,
    format_sentiment_message, format_pattern_message,
    format_psychology_message, format_correlation_message,
    ai_commander_analyze, format_commander_message
)
from quant_engine import (
    monte_carlo_simulation, calculate_var, kelly_criterion,
    detect_volatility_regime, mean_reversion_test, calculate_ratios,
    full_quant_report, correlation_matrix,
    format_quant_report, format_var_report, format_mc_summary
)
from multi_llm import (
    multi_model_consensus, analyze_news_sentiment, macro_fundamental_analysis,
    format_consensus_message, format_news_sentiment_message, format_macro_message,
    get_available_models
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@TradekhmerAI")

# --- Pricing Plans ---
PRICING_PLANS = {
    "monthly": {"name": "1 ខែ Monthly", "days": 30, "price": 29, "emoji": "🥉"},
    "quarterly": {"name": "3 ខែ Quarterly", "days": 90, "price": 69, "emoji": "🥈"},
    "yearly": {"name": "1 ឆ្នាំ Yearly", "days": 365, "price": 199, "emoji": "🥇"},
    "lifetime": {"name": " Lifetime អចិន្ត្រៃ", "days": 9999, "price": 399, "emoji": "💎"},
}

PAYMENT_METHODS = [
    "🏦 ABA: 00XXXXXX (BlackMagicAI)",
    "🏦 ACLEDA: 00XXXXXX (BlackMagicAI)",
    "📱 Wing: 0XX XXX XXX",
    "💵 Binance Pay: @TradekhmerAI",
]

# -------------------- Keyboards --------------------

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🔮 OMEGA Commander ⚡"],
            ["🧠 AI Analysis", "🔎 AI Scanner"],
            ["🔗 Confluence", "💭 Sentiment"],
            ["📐 Patterns", "📐 Strategy"],
            ["🧠 Psychology", "🔗 Correlation"],
            ["🏦 Quant Report", "🧠 Consensus"],
            ["📊 Markets", "💹 Live Price"],
            ["📋 Track Record", "📓 Journal"],
            ["⚖️ Risk Calc", "🔔 Alert"],
            ["📰 News", "🏛️ Macro"],
            ["💳 Buy License", "❓ Help"]
        ],
        resize_keyboard=True
    )


def markets_inline_keyboard():
    buttons = []
    for cat, symbols in CATEGORIES.items():
        buttons.append([InlineKeyboardButton(f"📂 {cat}", callback_data=f"cat_{cat}")])
    buttons.append([InlineKeyboardButton("🔄 Refresh All Prices", callback_data="refresh_all")])
    return InlineKeyboardMarkup(buttons)


def symbol_list_keyboard(category: str):
    symbols = CATEGORIES.get(category, [])
    buttons = []
    for sym in symbols:
        m = MARKETS.get(sym)
        if m:
            buttons.append([InlineKeyboardButton(
                f"{m.emoji} {m.symbol} — {m.name}",
                callback_data=f"price_{sym}"
            )])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="markets_menu")])
    return InlineKeyboardMarkup(buttons)


def signal_timeframe_keyboard():
    buttons = [
        [
            InlineKeyboardButton("⏱ 15m", callback_data="sig_tf_15m"),
            InlineKeyboardButton("⏱ 1H", callback_data="sig_tf_1h"),
        ],
        [
            InlineKeyboardButton("⏱ 4H", callback_data="sig_tf_4h"),
            InlineKeyboardButton("⏱ 1D", callback_data="sig_tf_1d"),
        ],
        [InlineKeyboardButton("🔙 Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def journal_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ បន្ថែម Add Trade", callback_data="journal_add")],
        [InlineKeyboardButton("📋 មើល View History", callback_data="journal_view")],
        [InlineKeyboardButton("🔙 Back", callback_data="cancel")],
    ])


# -------------------- Helper --------------------

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        return None


# -------------------- Command Handlers --------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lic_valid, lic_msg = is_license_valid()
    if lic_valid:
        lic_line = lic_msg
        buy_line = ""
    else:
        lic_line = "⚠️ *TRIAL MODE* — ប្រើបាន 7 ថ្ងៃ"
        buy_line = "\n💳 ចុច `💳 Buy License` ខាងក្រោម ឬ `/buy` ដើម្បីទិញ"

    welcome = f"""
🚀 *សួស្តី {user.first_name}! ស្វាគមន៍មកកាន់ BlackMagicAI OMEGA*

🔮 ខ្ញុំជា AI Trading Commander ជំនាន់ OMEGA!

🔐 {lic_line}{buy_line}

🏦 *INSTITUTIONAL AI ENGINES*
├ 🎲 Monte Carlo Simulation (GBM)
├ ⚠️ Value at Risk (VaR + CVaR)
├ 💰 Kelly Criterion Position Sizing
├ 📈 Volatility Regime Detection
├ 🔄 Mean Reversion (Ornstein-Uhlenbeck)
├ 📐 Sharpe/Sortino/Calmar Ratios
├ 🧠 Multi-LLM Consensus (3+ AI models)
└ 📰 News Sentiment + Macro Analysis

⚡ *OMEGA Commander* — 8 AI Engines ក្នុងការវិភាគតែមួយ
├ 🔗 Multi-TF Confluence (15m/1H/4H/1D)
├ 💭 Market Sentiment Analysis
├ 📐 Chart Pattern Recognition
├ 📐 Personalized Strategy Builder
├ 🧠 Trading Psychology Coach
├ 🔗 Cross-Market Correlation
├ 📊 Full Technical Analysis (RSI/MACD/EMA/ADX/BB)
└ 🕐 Timing & Schedule Optimizer

📊 *មុខងារផ្សេងទៀត:*
│ 💹 Live Prices — Gold, Forex, Crypto, Indices
│ 📋 Track Record — តាមដាម Win Rate
│ 📓 Trade Journal — កំណត់ហេតុ
│ ⚖️ Risk Calculator — គណនា Risk/Reward
│ 🔔 Price Alerts — ជូនដំណឹងតម្លៃ

📌 ប្រើ /help សម្រាប់ពាក្យបញ្ជាទាំងអស់

⚠️ _For educational purposes only. Not financial advice._
"""
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=main_keyboard())


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate bot with a license key."""
    args = context.args
    if not args:
        lic_valid, lic_msg = is_license_valid()
        if lic_valid:
            await update.message.reply_text(
                f"{lic_msg}\n\n✅ Bot របស់អ្នកមាន License រួចហើយ!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "🔐 *ACTIVATE LICENSE*\n\n"
                "សូមទិញ License Key ពីអ្នកលក់ រួចប្រើ៖\n"
                "`/activate BlackMagicAI-XXXX-XXXX-XXXX`\n\n"
                "📌 តម្លៃ៖\n"
                "• 1 ខែ: $29\n"
                "• 3 ខែ: $69\n"
                "• 1 ឆ្នាំ: $199\n\n"
                "ទំនាក់ទំនង: @TradekhmerAI",
                parse_mode="Markdown"
            )
        return

    key = " ".join(args).strip()
    processing = await update.message.reply_text("🔐 កំពុងផ្ទៀងផ្ទាត់ License Key... ⏳")

    valid, msg, expiry_ts = validate_license_key(key)

    if valid and expiry_ts:
        save_activated_license(key, expiry_ts, msg)
        await processing.edit_text(
            f"🎉 *ACTIVATED SUCCESSFULLY!*\n\n{msg}\n\n"
            f"🔮 OMEGA Commander រួចរាល់! ប្រើ /start ដើម្បីចាប់ផ្តើម។",
            parse_mode="Markdown"
        )
    else:
        await processing.edit_text(
            f"{msg}\n\nសូមពិនិត្យ Key ឡើងវិញ ឬទាក់ទងអ្នកលក់។\n📞 @TradekhmerAI",
            parse_mode="Markdown"
        )


async def cmd_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check license status."""
    lic_valid, lic_msg = is_license_valid()
    await update.message.reply_text(
        f"🔐 *LICENSE STATUS*\n━━━━━━━━━━━━━━━━\n{lic_msg}",
        parse_mode="Markdown"
    )


# ==================== PURCHASE & LICENSE SYSTEM ====================

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pricing plans & purchase flow."""
    lic_valid, lic_msg = is_license_valid()
    if lic_valid:
        await update.message.reply_text(
            f"{lic_msg}\n\n✅ អ្នកមាន License រួចហើយ! មិនចាំបាច់ទិញទៀតទេ។\n\n"
            "ប្រើ /license ដើម្បីពិនិត្យស្ថានភាព",
            parse_mode="Markdown"
        )
        return

    plans_kb = []
    for plan_id, plan in PRICING_PLANS.items():
        plans_kb.append([InlineKeyboardButton(
            f"{plan['emoji']} {plan['name']} — ${plan['price']}",
            callback_data=f"buy_{plan_id}"
        )])
    plans_kb.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])

    await update.message.reply_text(
        "╔══════════════════════════╗\n"
        "║  💳 *BlackMagicAI LICENSE*    ║\n"
        "╚══════════════════════════╝\n\n"
        "🔮 *OMEGA Commander* — 8 AI Engines\n"
        "📊 វិភាគគ្រប់ទីផ្សារ Gold, Forex, Crypto\n"
        "🤖 សញ្ញា AI ទិញ/លក់ + Risk Management\n"
        "📈 Multi-Timeframe Confluence\n\n"
        "👇 *ជ្រើសរើស Plan ដែលអ្នកចង់ទិញ:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(plans_kb)
    )


async def cmd_genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Generate a license key after receiving payment."""
    user = update.effective_user
    user_id = user.id if user else 0
    is_admin = (ADMIN_ID and user_id == ADMIN_ID) or (not ADMIN_ID)

    if not is_admin:
        await update.message.reply_text("⛔ សម្រាប់តែ Admin ប៉ុណ្ណោះ!")
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "🔑 *ADMIN: Generate License Key*\n\n"
            "ប្រើ: `/genkey <plan> [customer]`\n\n"
            "Plans:\n"
            "• monthly (30d, $29)\n"
            "• quarterly (90d, $69)\n"
            "• yearly (365d, $199)\n"
            "• lifetime (9999d, $399)\n\n"
            "ឧទាហរណ៍: `/genkey monthly @customer`",
            parse_mode="Markdown"
        )
        return

    plan_id = args[0].lower()
    customer_tag = args[1] if len(args) > 1 else ""

    if plan_id not in PRICING_PLANS:
        await update.message.reply_text(f"❌ Plan មិនត្រឹមត្រូវ: {plan_id}\nប្រើ: monthly, quarterly, yearly, lifetime")
        return

    plan = PRICING_PLANS[plan_id]
    key = generate_license_key(
        duration_days=plan["days"],
        customer_id=customer_tag or f"user{user_id}",
        price=plan["price"]
    )

    valid, msg, expiry_ts = validate_license_key(key)

    # Delivery message
    delivery = f"""🎉 *🎫 LICENSE KEY ថ្មី!*

📦 Plan: {plan['emoji']} {plan['name']}
💰 តម្លៃ: ${plan['price']}
📅 រយៈពេល: {plan['days']} ថ្ងៃ

🔑 *License Key:*
`{key}`

{msg}

━━━━━━━━━━━━━━━━━━━━━━
📋 *របៀបប្រើ (អតិថិជន):*
1. ចូល Bot @TradekhmerAI_bot
2. `/activate {key}`
3. ប្រើប្រាស់បានភ្លាម! 🔮

━━━━━━━━━━━━━━━━━━━━━━
📞 {ADMIN_USERNAME}
"""

    await update.message.reply_text(delivery, parse_mode="Markdown")

    # If customer tag is a @user, try to notify admin to forward
    if customer_tag and customer_tag.startswith("@"):
        await update.message.reply_text(
            f"📤 សូមផ្ញើ Key ទៅ {customer_tag}\nឬចម្លង Key ខាងលើផ្ញើដោយផ្ទាល់។"
        )


async def cmd_quant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Institutional Quant Analysis: Monte Carlo, VaR, Kelly, Vol Regime, Mean Reversion."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើងទេ!*\nដាក់ `GROQ_API_KEY` ក្នុង `.env` ហើយ restart bot ។",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if not args:
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"quant_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🏦 *INSTITUTIONAL QUANT LAB*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគ៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    market = MARKETS[symbol]
    processing = await update.message.reply_text(
        f"🏦 *កំពុងដំណើរការ Quant Analysis សម្រាប់ {symbol}...*\n"
        f"Monte Carlo • VaR • Kelly • Vol Regime • Mean Reversion ⏳",
        parse_mode="Markdown"
    )

    try:
        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is None or df.empty or len(df) < 30:
            await processing.edit_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
            return

        prices = df["close"].tolist()
        price_data = get_current_price(symbol)
        current_price = price_data["price"] if price_data else prices[-1]

        report = full_quant_report(symbol, prices, position_value=10000.0)
        msg = format_quant_report(report)
        await processing.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Quant error for {symbol}: {e}")
        await processing.edit_text(f"❌ មានបញ្ហាក្នុងការវិភាគ {symbol}\n`{str(e)[:200]}`", parse_mode="Markdown")


async def cmd_consensus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Multi-LLM Consensus: Multiple AI models vote on direction."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើងទេ!*\nដាក់ `GROQ_API_KEY` ក្នុង `.env` ហើយ restart bot ។",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if not args:
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"consensus_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🧠 *MULTI-LLM CONSENSUS*\nជ្រើសរើសទីផ្សារ — AI ច្រើននឹងបោះឆ្នោត៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    market = MARKETS[symbol]
    processing = await update.message.reply_text(
        f"🧠 *កំពុងប្រមូល AI Consensus សម្រាប់ {symbol}...*\n"
        f"កំពុងសួរ AI models ជាច្រើន ⏳",
        parse_mode="Markdown"
    )

    try:
        price_data = get_current_price(symbol)
        if not price_data:
            await processing.edit_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
            return

        consensus = await multi_model_consensus(
            symbol,
            market.name,
            price_data["price"],
            price_data.get("change_pct", 0),
        )
        msg = format_consensus_message(consensus)
        await processing.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Consensus error for {symbol}: {e}")
        await processing.edit_text(f"❌ មានបញ្ហាក្នុងការវិភាគ {symbol}\n`{str(e)[:200]}`", parse_mode="Markdown")


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """News Sentiment Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើងទេ!*\nដាក់ `GROQ_API_KEY` ក្នុង `.env` ហើយ restart bot ។",
            parse_mode="Markdown"
        )
        return

    args = context.args
    symbol = args[0].upper() if args else ""
    if symbol and symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    processing = await update.message.reply_text(
        f"📰 *កំពុងទាញយក និងវិភាគព័ត៌មានពិត{'សម្រាប់ ' + symbol if symbol else 'ទីផ្សារទូទៅ'}...*\nសូមរង់ចាំ ⏳",
        parse_mode="Markdown"
    )

    try:
        # ១. ទាញយកព័ត៌មានពិតពី market_data.py
        from market_data import get_real_news
        headlines = get_real_news(symbol, limit=10)
        
        # ២. ប្រសិនបើអ៊ីនធឺណិតមានបញ្ហា ប្រើ Fallback កុំឱ្យគាំង
        if not headlines:
            headlines = [f"{symbol} market analysis and trends today"] if symbol else ["Forex gold crypto market news today"]

        # ៣. បញ្ជូន Headlines ពិតទៅឱ្យ AI វិភាគមនោសញ្ចេតនា (Sentiment)
        sentiment = await analyze_news_sentiment(headlines, symbol)
        msg = format_news_sentiment_message(sentiment, symbol)
        
        await processing.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"News error: {e}")
        await processing.edit_text(f"❌ មានបញ្ហាក្នុងការវិភាគព័ត៌មាន\n`{str(e)[:200]}`", parse_mode="Markdown")


async def cmd_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Macro-Fundamental Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើងទេ!*\nដាក់ `GROQ_API_KEY` ក្នុង `.env` ហើយ restart bot ។",
            parse_mode="Markdown"
        )
        return

    args = context.args
    symbol = args[0].upper() if args else ""
    if symbol and symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    display_symbol = symbol if symbol else "គ្រប់ទីផ្សារ"
    processing = await update.message.reply_text(
        f"🏛️ *កំពុងវិភាគ Macro-Fundamental សម្រាប់ {display_symbol}...*\nសូមរង់ចាំ ⏳",
        parse_mode="Markdown"
    )

    try:
        market_name = MARKETS[symbol].name if symbol else "General Market"
        price = get_current_price(symbol)["price"] if symbol else 0

        macro = await macro_fundamental_analysis(symbol or "MARKETS", market_name, price)
        msg = format_macro_message(macro)
        await processing.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Macro error: {e}")
        await processing.edit_text(f"❌ មានបញ្ហាក្នុងការវិភាគ Macro\n`{str(e)[:200]}`", parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai_status = f"✅ AI Active ({AI_PROVIDER})" if AI_AVAILABLE else "⚠️ AI Not Configured (add API key to .env)"
    lic_valid, _ = is_license_valid()
    lic_status = "✅ Licensed" if lic_valid else "⚠️ Trial Mode (7 days)"

    models = get_available_models()
    model_count = sum(len(v) for v in models.values()) + 1

    help_text = f"""*📖 ពាក្យបញ្ជា / COMMANDS*

🏦 *INSTITUTIONAL AI ({ai_status})*
/quant <symbol> — Monte Carlo, VaR, Kelly, Vol Regime, Mean Reversion
/consensus <symbol> — Multi-LLM Consensus ({model_count} AI models vote)
/news [symbol] — News Sentiment Analysis (AI)
/macro [symbol] — Macro-Fundamental Analysis (AI)

🔮 *OMEGA COMMANDER ({ai_status})*
/ai_complete <symbol> — 8 AI Engines វិភាគក្នុងពេលតែមួយ
/omega <symbol> — Alias for OMEGA Commander

🧠 *AI DEEP ANALYSIS*
/ai_signal <symbol> — AI វិភាគស៊ីជម្រៅដោយ LLM
/ai_scan — AI ស្កេនទីផ្សាររកឱកាសល្អបំផុត

🔗 *AI CONFLUENCE*
/ai_confluence <symbol> — វិភាគ 4 Timeframes (15m/1H/4H/1D)

💭 *AI SENTIMENT*
/ai_sentiment <symbol> — វិភាគមនោសញ្ចេតនាទីផ្សារ

📐 *AI PATTERNS*
/ai_pattern <symbol> — AI រក Chart Patterns ស្វ័យប្រវត្តិ

📐 *AI STRATEGY BUILDER*
/ai_strategy — AI បង្កើត Trading Strategy ផ្ទាល់ខ្លួន

🧠 *AI PSYCHOLOGY*
/ai_psychology [topic] — គ្រូបង្វឹកចិត្តសាស្ត្រ Trading

🔗 *AI CORRELATION*
/ai_correlate <symbol> — វិភាគទំនាក់ទំនងរវាងទីផ្សារ

🤖 *សញ្ញា & វិភាគ*
/signal <symbol> — សញ្ញា 8 Indicators
/analysis <symbol> — វិភាគបច្ចេកទេសពេញ
/price <symbol> — តម្លៃផ្សាយផ្ទាល់

📊 *ទីផ្សារ*
/markets — បញ្ជីទីផ្សារទាំងអស់
/scan — ស្កេនសញ្ញាគ្រប់ទីផ្សារ

📋 *Track Record & Journal*
/trackrecord — មើលកំណត់ត្រាឈ្នះ-ចាញ់
/journal — កំណត់ហេតុជួញដូរ

⚖️ *Risk & Alerts*
/risk <entry> <sl> <tp> — គណនា Risk/Reward
/alert <symbol> <above|below> <price> — ដំឡើង Alert

🔐 *License ({lic_status})*
/activate <key> — បញ្ចូល License Key
/license — ពិនិត្យស្ថានភាព License
/buy — ទិញ License

💡 ដាក់ GROQ_API_KEY ក្នុង .env ដើម្បីប្រើ AI
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_markets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 *ទីផ្សារ / MARKETS*\nជ្រើសរើសប្រភេទទីផ្សារ៖",
        parse_mode="Markdown",
        reply_markup=markets_inline_keyboard()
    )


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        # Show popular prices
        popular = ["XAUUSD", "BTCUSDT", "ETHUSDT", "EURUSD", "NAS100"]
        results = get_multi_prices(popular)
        msg = "*💹 តម្លៃផ្សាយផ្ទាល់ / LIVE PRICES*\n━━━━━━━━━━━━━━━━\n"
        for r in results:
            arrow = "🟢" if r["change_pct"] >= 0 else "🔴"
            msg += f"{r['emoji']} *{r['symbol']}*: ${r['price']:,.2f} {arrow} {r['change_pct']:+,.2f}%\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        await update.message.reply_text(
            "💡 វាយ /price <symbol> សម្រាប់តម្លៃលម្អិត\nឧទាហរណ៍: /price XAUUSD",
            parse_mode="Markdown"
        )
        return

    symbol = args[0].upper()
    msg = get_live_ticker_text(symbol)
    if msg:
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"❌ រកមិនឃើញទីផ្សារ: {symbol}\nប្រើ /markets ដើម្បីមើលបញ្ជី"
        )


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        # Ask for symbol selection
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"sig_sel_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🤖 *AI SIGNAL*\nជ្រើសរើសទីផ្សារដើម្បីទទួលសញ្ញា AI៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    symbol = args[0].upper()
    timeframe = args[1].lower() if len(args) > 1 else "1h"

    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    processing_msg = await update.message.reply_text(
        f"🤖 កំពុងវិភាគ {symbol}... សូមរង់ចាំបន្តិច ⏳"
    )

    sig = generate_signal(symbol, timeframe)
    if sig:
        # Save to database
        try:
            db = get_db()
            if db:
                import json
                ind_json = json.dumps({k: v["signal"] for k, v in sig.indicators.items()})
                save_signal(db, sig.symbol, sig.direction, sig.entry_price,
                           sig.stop_loss, sig.take_profit, sig.confidence,
                           sig.timeframe, ind_json, sig.summary)
                db.close()
        except Exception:
            pass

        msg = format_signal_message(sig)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟢 ឈ្នះ WIN", callback_data=f"result_{sig.symbol}_WIN"),
                InlineKeyboardButton("🔴 ចាញ់ LOSS", callback_data=f"result_{sig.symbol}_LOSS"),
            ],
            [InlineKeyboardButton("📊 វិភាគលម្អិត", callback_data=f"analysis_{sig.symbol}_{timeframe}")],
        ])
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
    else:
        await processing_msg.edit_text(
            f"❌ មិនអាចទាញទិន្នន័យសម្រាប់ {symbol} បានទេ។ សូមព្យាយាមម្តងទៀត។"
        )


async def cmd_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔍 ប្រើ /analysis <symbol>\nឧទាហរណ៍: /analysis XAUUSD"
        )
        return

    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    processing_msg = await update.message.reply_text(f"🔍 កំពុងវិភាគ {symbol}... ⏳")

    df = fetch_ohlcv(symbol, interval="1h", period="30d")
    if df is None or df.empty:
        await processing_msg.edit_text(f"❌ មិនអាចទាញទិន្នន័យសម្រាប់ {symbol}")
        return

    analysis = compute_full_analysis(df)
    msg = format_analysis_message(analysis, symbol)

    await processing_msg.delete()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_trackrecord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    if not db:
        await update.message.reply_text("❌ មានបញ្ហាជាមួយ database")
        return

    record = get_track_record(db)
    db.close()

    if record["total"] == 0:
        await update.message.reply_text(
            "📋 មិនទាន់មានកំណត់ត្រានៅឡើយទេ។\nប្រើ /signal ដើម្បីបង្កើតសញ្ញា រួចចុច WIN/LOSS ដើម្បីតាមដាន។"
        )
        return

    msg = f"""📋 *TRACK RECORD*
━━━━━━━━━━━━━━━━━━━
📊 សរុប / Total: *{record['total']}*
🟢 ឈ្នះ / Wins: *{record['wins']}*
🔴 ចាញ់ / Losses: *{record['losses']}*
⚪ Breakeven: *{record['breakeven']}*
📈 អត្រាឈ្នះ / Win Rate: *{record['win_rate']}%*
"""

    if record["by_symbol"]:
        msg += "\n━━━━━━━━━━━━━━━━━━━\n*តាមទីផ្សារ / By Symbol:*\n"
        for sym, data in sorted(record["by_symbol"].items(), key=lambda x: x[1]["win_rate"], reverse=True):
            emoji = MARKETS[sym].emoji if sym in MARKETS else ""
            msg += f"{emoji} *{sym}*: {data['wins']}/{data['total']} — {data['win_rate']}%\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_winrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_trackrecord(update, context)


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📓 *TRADE JOURNAL*\nកំណត់ហេតុការជួញដូរ",
        parse_mode="Markdown",
        reply_markup=journal_keyboard()
    )


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "⚖️ *RISK CALCULATOR*\nប្រើ: /risk <entry> <stop_loss> <take_profit>\n"
            "ឧទាហរណ៍: /risk 4000 3980 4050\n\n"
            "សម្រាប់ BUY:\n"
            "- Entry: 4000\n"
            "- SL: 3980 (risk = 20)\n"
            "- TP: 4050 (reward = 50)\n"
            "- R:R = 1:2.5",
            parse_mode="Markdown"
        )
        return

    try:
        entry = float(args[0])
        sl = float(args[1])
        tp = float(args[2])
    except ValueError:
        await update.message.reply_text("❌ សូមបញ្ចូលលេខត្រឹមត្រូវ")
        return

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = round(reward / risk, 2) if risk > 0 else 0
    direction = "BUY" if tp > entry else "SELL"

    risk_pct = round(risk / entry * 100, 2)
    reward_pct = round(reward / entry * 100, 2)

    msg = f"""⚖️ *RISK / REWARD CALCULATOR*
━━━━━━━━━━━━━━━━━━━
📊 ទិសដៅ: *{direction}*
💰 Entry: *${entry:,.4f}*
🛑 SL: *${sl:,.4f}* (Risk: ${risk:,.4f} / {risk_pct}%)
🎯 TP: *${tp:,.4f}* (Reward: ${reward:,.4f} / {reward_pct}%)

⚖️ *R:R Ratio = 1:{rr}*
"""

    if rr >= 2:
        verdict = "✅ ល្អ! R:R ខ្ពស់ជាង 1:2"
        emoji = "🟢"
    elif rr >= 1.5:
        verdict = "👍 ល្អ អាចទទួលយកបាន"
        emoji = "🟡"
    elif rr >= 1:
        verdict = "⚠️ យ៉ាងហោច 1:1 — ប្រយ័ត្ន"
        emoji = "🟠"
    else:
        verdict = "❌ មិនល្អ R:R តិចជាង 1:1 — មិនគួរចូល"
        emoji = "🔴"

    msg += f"\n{emoji} {verdict}"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "🔔 *PRICE ALERT*\nប្រើ: /alert <symbol> <above|below> <price>\n"
            "ឧទាហរណ៍: /alert XAUUSD above 4050\n"
            "ឧទាហរណ៍: /alert BTCUSDT below 60000",
            parse_mode="Markdown"
        )
        return

    symbol = args[0].upper()
    condition = args[1].lower()
    try:
        price = float(args[2])
    except ValueError:
        await update.message.reply_text("❌ សូមបញ្ចូលតម្លៃជាលេខ")
        return

    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    if condition not in ("above", "below"):
        await update.message.reply_text("❌ ប្រើ 'above' ឬ 'below'")
        return

    chat_id = str(update.effective_chat.id)
    db = get_db()
    if not db:
        await update.message.reply_text("❌ មានបញ្ហាជាមួយ database")
        return

    alert = AlertConfig(chat_id=chat_id, symbol=symbol, condition=condition.upper(), price=price)
    db.add(alert)
    db.commit()
    db.close()

    dir_kh = "ឡើងដល់" if condition == "above" else "ធ្លាក់ដល់"
    await update.message.reply_text(
        f"🔔 *Alert បានដំឡើង!*\n"
        f"📊 {MARKETS[symbol].emoji} *{symbol}*\n"
        f"📌 {dir_kh} `${price:,.2f}`\n\n"
        f"អ្នកនឹងទទួលការជូនដំណឹងនៅពេលតម្លៃ{dir_kh}តម្លៃនេះ។",
        parse_mode="Markdown"
    )


# ==================== AI-POWERED COMMANDS ====================

async def cmd_ai_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-powered deep analysis signal using LLM."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើងទេ!*\n\n"
            "ដើម្បីប្រើ AI Deep Analysis សូមដាក់ API Key មួយក្នុងចំណោម៖\n"
            "• `DEEPSEEK_API_KEY` (ឥតគិតថ្លៃ — https://platform.deepseek.com)\n"
            "• `GROQ_API_KEY` (ឥតគិតថ្លៃ — https://console.groq.com)\n"
            "• `OPENAI_API_KEY`\n"
            "• `GEMINI_API_KEY`\n\n"
            "បន្ថែមក្នុង `.env` file រួច restart bot ។\n"
            "ឥឡូវនេះអាចប្រើ `/signal XAUUSD` ជំនួសបាន។",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if not args:
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"ai_sig_sel_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🧠 *AI DEEP ANALYSIS*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគដោយ AI៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    symbol = args[0].upper()
    timeframe = args[1].lower() if len(args) > 1 else "1h"

    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    market = MARKETS[symbol]
    processing_msg = await update.message.reply_text(
        f"🧠 AI កំពុងវិភាគ {symbol} យ៉ាងស៊ីជម្រៅ...\nសូមរង់ចាំ 15-30 វិនាទី ⏳"
    )

    # Get full technical data first
    df = fetch_ohlcv(symbol, interval="1h", period="30d")
    if df is None or df.empty or len(df) < 50:
        await processing_msg.edit_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
        return

    analysis = compute_full_analysis(df)
    price_data = get_current_price(symbol)
    if not price_data:
        await processing_msg.edit_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
        return

    # Run AI analysis
    ai_result = await ai_analyze_market(
        symbol, price_data,
        analysis.get("signals", {}),
        analysis.get("atr", {}),
        analysis.get("support_resistance", {}),
        timeframe
    )

    if ai_result:
        msg = format_ai_signal_message(ai_result, symbol, market.name, market.emoji)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 សញ្ញាបច្ចេកទេស Technical", callback_data=f"sig_sel_{symbol}")],
            [InlineKeyboardButton("📊 វិភាគបច្ចេកទេស Analysis", callback_data=f"analysis_{symbol}_{timeframe}")],
        ])
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
    else:
        await processing_msg.edit_text(
            f"❌ AI មិនអាចវិភាគបាន។ សូមព្យាយាមម្តងទៀត។\n"
            f"អាចប្រើ `/signal {symbol}` ជំនួសបាន។"
        )


async def cmd_ai_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI scans all markets for best opportunities."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ AI មិនទាន់បានដំឡើង!\nដាក់ DEEPSEEK_API_KEY ឬ GROQ_API_KEY ក្នុង .env",
        )
        return

    processing_msg = await update.message.reply_text(
        "🧠🔍 AI កំពុងស្កេនទីផ្សារទាំង 14...\nរកឱកាសល្អបំផុត ⏳ (30-60 វិនាទី)"
    )

    # Get all prices
    all_symbols = list(MARKETS.keys())
    price_data_list = []
    for sym in all_symbols:
        data = get_current_price(sym)
        if data:
            price_data_list.append(data)

    if len(price_data_list) < 3:
        await processing_msg.edit_text("❌ មិនអាចទាញទិន្នន័យទីផ្សារ")
        return

    # AI scan
    scan_data = await ai_scan_markets(price_data_list, top_n=5)

    if scan_data and scan_data.get("opportunities"):
        msg = format_ai_scan_message(scan_data)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text(
            "❌ AI មិនអាចស្កេនបាន។ ប្រើ `/scan` ជំនួសបាន។"
        )


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan all markets for signals (slower, use sparingly)."""
    await update.message.reply_text(
        "🔍 កំពុងស្កេនគ្រប់ទីផ្សារ... សូមរង់ចាំ 1-2 នាទី ⏳"
    )

    results = []
    for sym in MARKETS.keys():
        sig = generate_signal(sym, "1h")
        if sig and sig.direction != "NEUTRAL":
            results.append(sig)

    if not results:
        await update.message.reply_text("📊 មិនមានសញ្ញាច្បាស់លាស់នៅពេលនេះ")
        return

    msg = "🔍 *ស្កេនសញ្ញា / MARKET SCAN*\n━━━━━━━━━━━━━━━━\n"
    for sig in sorted(results, key=lambda x: x.confidence, reverse=True):
        emoji = MARKETS[sig.symbol].emoji
        dir_kh = "ទិញ" if sig.direction == "BUY" else "លក់"
        msg += f"{emoji} *{sig.symbol}*: {dir_kh} — {sig.confidence}% confidence\n"

    msg += f"\n📊 សរុប: {len(results)} សញ្ញា\n💡 ប្រើ /signal <symbol> សម្រាប់សញ្ញាលម្អិត"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ==================== NEW AI COMMANDS ====================

async def cmd_ai_confluence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Multi-Timeframe Confluence Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    args = context.args
    if not args:
        buttons = []
        for sym in MARKETS:
            m = MARKETS[sym]
            buttons.append([InlineKeyboardButton(f"{m.emoji} {m.symbol}", callback_data=f"ai_conf_{sym}")])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🔗 *AI MULTI-TIMEFRAME CONFLUENCE*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគ 4 Timeframes ក្នុងពេលតែមួយ៖",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return
    m = MARKETS[symbol]
    processing_msg = await update.message.reply_text(f"🔗 AI កំពុងវិភាគ {symbol} លើ 4 Timeframes... ⏳")
    tf_data = {}
    for tf in ["15m", "1h", "4h", "1d"]:
        df = fetch_ohlcv(symbol, interval=tf, period="30d")
        if df is not None and not df.empty and len(df) >= 10:
            analysis = compute_full_analysis(df)
            price = get_current_price(symbol)
            tf_data[tf] = {
                "price": price["price"] if price else 0,
                "rsi": analysis.get("signals", {}).get("RSI", {}).get("value", "N/A"),
                "trend": analysis.get("signals", {}).get("ADX", {}).get("signal", "N/A"),
                "above_ema": analysis.get("signals", {}).get("EMA", {}).get("signal", "") == "BUY",
            }
    if len(tf_data) < 2:
        await processing_msg.edit_text(f"❌ មិនអាចទាញទិន្នន័យគ្រប់ TF សម្រាប់ {symbol}")
        return
    price_data = get_current_price(symbol)
    result = await ai_confluence(symbol, tf_data, price_data["price"] if price_data else 0)
    if result:
        msg = format_confluence_message(result, symbol, m.emoji, m.name)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text(f"❌ AI មិនអាចវិភាគ {symbol}")


async def cmd_ai_sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Market Sentiment Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    args = context.args
    if not args:
        buttons = []
        for sym in MARKETS:
            m = MARKETS[sym]
            buttons.append([InlineKeyboardButton(f"{m.emoji} {m.symbol}", callback_data=f"ai_sent_{sym}")])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "💭 *AI SENTIMENT ANALYSIS*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគមនោសញ្ចេតនា៖",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return
    m = MARKETS[symbol]
    processing_msg = await update.message.reply_text(f"💭 AI កំពុងវិភាគមនោសញ្ចេតនា {symbol}... ⏳")
    df = fetch_ohlcv(symbol, interval="1h", period="30d")
    if df is None or df.empty:
        await processing_msg.edit_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
        return
    analysis = compute_full_analysis(df)
    price_data = get_current_price(symbol)
    if not price_data:
        await processing_msg.edit_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
        return
    vol_data = {"volume": price_data.get("volume", "N/A"), "volume_ratio": "N/A"}
    result = await ai_sentiment(symbol, price_data, analysis.get("signals", {}), vol_data)
    if result:
        msg = format_sentiment_message(result, symbol, m.emoji)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text(f"❌ AI មិនអាចវិភាគ sentiment សម្រាប់ {symbol}")


async def cmd_ai_pattern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Chart Pattern Detection."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    args = context.args
    if not args:
        buttons = []
        for sym in MARKETS:
            m = MARKETS[sym]
            buttons.append([InlineKeyboardButton(f"{m.emoji} {m.symbol}", callback_data=f"ai_pat_{sym}")])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "📐 *AI PATTERN RECOGNITION*\nជ្រើសរើសទីផ្សារដើម្បីរក Chart Patterns៖",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return
    m = MARKETS[symbol]
    processing_msg = await update.message.reply_text(f"📐 AI កំពុងរក Chart Patterns លើ {symbol}... ⏳")
    df = fetch_ohlcv(symbol, interval="1h", period="30d")
    if df is None or df.empty:
        await processing_msg.edit_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
        return
    recent = df.tail(20)
    ohlc_summary = "\n".join([
        f"  {i}: O={row['Open']:.2f} H={row['High']:.2f} L={row['Low']:.2f} C={row['Close']:.2f}"
        for i, row in recent.iterrows()
    ])
    analysis = compute_full_analysis(df)
    price_data = get_current_price(symbol)
    if not price_data:
        await processing_msg.edit_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
        return
    sr = analysis.get("support_resistance", {})
    result = await ai_detect_patterns(symbol, price_data, ohlc_summary, sr)
    if result:
        msg = format_pattern_message(result, symbol, m.emoji)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text(f"❌ AI មិនអាចរក Patterns សម្រាប់ {symbol}")


async def cmd_ai_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Strategy Builder."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🥇 Gold Scalping", callback_data="ai_strat_gold_scalping")],
        [InlineKeyboardButton("💹 Forex Day Trading", callback_data="ai_strat_forex_day")],
        [InlineKeyboardButton("₿ Crypto Swing", callback_data="ai_strat_crypto_swing")],
        [InlineKeyboardButton("📊 Indices Position", callback_data="ai_strat_indices_position")],
        [InlineKeyboardButton("🎯 Custom", callback_data="ai_strat_custom")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="cancel")],
    ])
    await update.message.reply_text(
        "📐 *AI STRATEGY BUILDER*\nអោយ AI បង្កើត Trading Strategy អោយអ្នក!\nជ្រើសរើសប្រភេទទីផ្សារ៖",
        parse_mode="Markdown", reply_markup=kb
    )


async def cmd_ai_psychology(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Trading Psychology Coach."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    args = context.args
    topic = args[0].lower() if args else "general"
    processing_msg = await update.message.reply_text("🧠 AI Coach កំពុងរៀបចំដំបូន្មាន... ⏳")
    result = await ai_psychology(topic)
    if result:
        msg = format_psychology_message(result)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text("❌ AI មិនអាចបង្កើតដំបូន្មានបាន")


async def cmd_ai_correlate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI Cross-Market Correlation Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text("⚠️ AI មិនទាន់បានដំឡើង! ដាក់ GROQ_API_KEY ក្នុង .env")
        return
    args = context.args
    if not args:
        buttons = []
        for sym in MARKETS:
            m = MARKETS[sym]
            buttons.append([InlineKeyboardButton(f"{m.emoji} {m.symbol}", callback_data=f"ai_corr_{sym}")])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🔗 *AI CROSS-MARKET CORRELATION*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគទំនាក់ទំនង៖",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return
    m = MARKETS[symbol]
    processing_msg = await update.message.reply_text(f"🔗 AI កំពុងវិភាគទំនាក់ទំនង {symbol} ជាមួយទីផ្សារផ្សេង... ⏳")
    all_prices = []
    for s in MARKETS:
        p = get_current_price(s)
        if p:
            all_prices.append(p)
    result = await ai_correlated_markets(symbol, all_prices)
    if result:
        msg = format_correlation_message(result, symbol, m.emoji)
        await processing_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await processing_msg.edit_text(f"❌ AI មិនអាចវិភាគ correlation សម្រាប់ {symbol}")


# ==================== OMEGA COMMANDER ====================

async def cmd_commander(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OMEGA Unified Commander — All 8 AI Engines in One Analysis."""
    if not AI_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *AI មិនទាន់បានដំឡើង!*\nដាក់ `GROQ_API_KEY` ក្នុង `.env` ដើម្បីប្រើ OMEGA Commander",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if not args:
        # Premium symbol selector
        buttons = []
        for cat, symbols in CATEGORIES.items():
            row = []
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    row.append(InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"omega_{sym}"
                    ))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "╔══════════════════════╗\n"
            "║  🔮 *OMEGA COMMANDER*  ║\n"
            "╚══════════════════════╝\n\n"
            "*8 AI Engines — 1 Ultimate Analysis*\n"
            "• Multi-TF Confluence\n• Market Sentiment\n• Pattern Recognition\n"
            "• Strategy Builder\n• Trading Psychology\n• Correlation Matrix\n"
            "• Technical Analysis\n• Timing Optimizer\n\n"
            "ជ្រើសរើសទីផ្សារ៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    symbol = args[0].upper()
    if symbol not in MARKETS:
        await update.message.reply_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
        return

    await _run_commander(update, context, symbol)


async def _run_commander(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
    """Run OMEGA Commander analysis."""
    m = MARKETS[symbol]
    is_callback = hasattr(update, 'callback_query') and update.callback_query

    if is_callback:
        msg_obj = update.callback_query
        await msg_obj.edit_message_text(f"🔮 OMEGA កំពុងដំណើរការ 8 AI Engines លើ {symbol}...\n⏳ សូមរង់ចាំ 20-40 វិនាទី")
    else:
        msg_obj = await update.message.reply_text(f"🔮 OMEGA កំពុងដំណើរការ 8 AI Engines លើ {symbol}...\n⏳ សូមរង់ចាំ 20-40 វិនាទី")

    # Gather all data
    df = fetch_ohlcv(symbol, interval="1h", period="30d")
    if df is None or df.empty or len(df) < 20:
        await msg_obj.edit_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
        return

    analysis = compute_full_analysis(df)
    price_data = get_current_price(symbol)
    if not price_data:
        await msg_obj.edit_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
        return

    # Multi-TF data
    tf_data = {}
    for tf in ["15m", "1h", "4h", "1d"]:
        tf_df = fetch_ohlcv(symbol, interval=tf, period="30d")
        if tf_df is not None and not tf_df.empty and len(tf_df) >= 10:
            tf_analysis = compute_full_analysis(tf_df)
            tf_price = get_current_price(symbol)
            tf_data[tf] = {
                "price": tf_price["price"] if tf_price else 0,
                "rsi": tf_analysis.get("signals", {}).get("RSI", {}).get("value", "N/A"),
                "trend": tf_analysis.get("signals", {}).get("ADX", {}).get("signal", "N/A"),
                "above_ema": tf_analysis.get("signals", {}).get("EMA", {}).get("signal", "") == "BUY",
            }

    # Price action: last 15 candles
    recent = df.tail(15)
    pa_lines = []
    for i, row in recent.iterrows():
        pa_lines.append(f"  {i}: O={row['Open']:.2f} H={row['High']:.2f} L={row['Low']:.2f} C={row['Close']:.2f}")
    price_action_text = "\n".join(pa_lines)

    # Run unified analysis
    result = await ai_commander_analyze(
        symbol=symbol,
        market_name=m.name,
        current_price=price_data["price"],
        change_pct=price_data.get("change_pct", 0),
        category=price_data.get("category", "N/A"),
        indicators=analysis.get("signals", {}),
        pivots=analysis.get("support_resistance", {}),
        multi_tf_data=tf_data,
        volume_data={"volume": price_data.get("volume", "N/A"), "volume_ratio": "N/A"},
        price_action_text=price_action_text,
    )

    if result:
        msg = format_commander_message(result, symbol, m.emoji, m.name)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🤖 Technical Signal", callback_data=f"sig_sel_{symbol}"),
                InlineKeyboardButton("📊 Analysis", callback_data=f"analysis_{symbol}_1h"),
            ],
            [InlineKeyboardButton("🔄 New Symbol", callback_data="omega_menu")],
        ])
        if is_callback:
            try:
                await update.callback_query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
                await update.callback_query.delete_message()
            except Exception:
                await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await msg_obj.delete()
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
    else:
        await msg_obj.edit_text(
            f"❌ OMEGA Commander មិនអាចវិភាគ {symbol} បាន។\nសូមប្រើ `/ai_signal {symbol}` ជំនួស។",
            parse_mode="Markdown"
        )


# -------------------- Message Handler (keyboard buttons) --------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "💳 Buy License":
        await cmd_buy(update, context)
    elif text == "🔮 OMEGA Commander ⚡":
        buttons = []
        for cat, symbols in CATEGORIES.items():
            row = []
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    row.append(InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"omega_{sym}"
                    ))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "╔══════════════════════╗\n"
            "║  🔮 *OMEGA COMMANDER*  ║\n"
            "╚══════════════════════╝\n\n"
            "*8 AI Engines — 1 Ultimate Analysis*\n\n"
            "✅ ជ្រើសរើសទីផ្សារដើម្បីចាប់ផ្តើម៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "📊 Markets":
        await cmd_markets(update, context)
    elif text == "🧠 AI Analysis":
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"ai_sig_sel_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🧠 *AI DEEP ANALYSIS*\nជ្រើសរើសទីផ្សារដើម្បីវិភាគដោយ AI៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "🔎 AI Scanner":
        await cmd_ai_scan(update, context)
    elif text == "🔗 Confluence":
        await cmd_ai_confluence(update, context)
    elif text == "💭 Sentiment":
        await cmd_ai_sentiment(update, context)
    elif text == "📐 Patterns":
        await cmd_ai_pattern(update, context)
    elif text == "📐 Strategy":
        await cmd_ai_strategy(update, context)
    elif text == "🧠 Psychology":
        await cmd_ai_psychology(update, context)
    elif text == "🔗 Correlation":
        await cmd_ai_correlate(update, context)
    elif text in ("🤖 AI Signal", "🔗 AI Confluence", "💭 AI Sentiment", "📐 AI Patterns", "📐 AI Strategy"):
        # Show symbol selector
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"sig_sel_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🤖 *AI SIGNAL*\nជ្រើសរើសទីផ្សារ៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "💹 Live Price" or text == "💹 តម្លៃផ្សាយ Live Price":
        # Show popular prices
        popular = ["XAUUSD", "BTCUSDT", "ETHUSDT", "EURUSD", "NAS100"]
        results = get_multi_prices(popular)
        msg = "*💹 តម្លៃផ្សាយផ្ទាល់*\n━━━━━━━━━━━━━━━━\n"
        for r in results:
            arrow = "🟢" if r["change_pct"] >= 0 else "🔴"
            msg += f"{r['emoji']} *{r['symbol']}*: ${r['price']:,.2f} {arrow} {r['change_pct']:+,.2f}%\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif text in ("🔍 វិភាគ Analysis", "🔍 Analysis"):
        buttons = []
        for sym in MARKETS:
            m = MARKETS[sym]
            buttons.append([InlineKeyboardButton(
                f"{m.emoji} {m.symbol}",
                callback_data=f"analysis_req_{sym}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🔍 ជ្រើសរើសទីផ្សារសម្រាប់វិភាគបច្ចេកទេស៖",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "📋 Track Record":
        await cmd_trackrecord(update, context)
    elif text in ("📓 Trade Journal", "📓 Journal"):
        await update.message.reply_text(
            "📓 *TRADE JOURNAL*",
            parse_mode="Markdown",
            reply_markup=journal_keyboard()
        )
    elif text in ("⚖️ Risk Calculator", "⚖️ Risk Calc"):
        await update.message.reply_text(
            "⚖️ *RISK CALCULATOR*\n\n"
            "ប្រើ: `/risk <entry> <sl> <tp>`\n"
            "ឧទាហរណ៍: `/risk 4000 3980 4050`",
            parse_mode="Markdown"
        )
    elif text in ("🔔 Set Alert", "🔔 Alert"):
        await update.message.reply_text(
            "🔔 *PRICE ALERT*\n\n"
            "ប្រើ: `/alert <symbol> <above|below> <price>`\n"
            "ឧទាហរណ៍: `/alert XAUUSD above 4050`",
            parse_mode="Markdown"
        )
    elif text == "🏦 Quant Report":
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"quant_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🏦 *INSTITUTIONAL QUANT LAB*\nMonte Carlo • VaR • Kelly • Vol Regime • Mean Reversion\n\nជ្រើសរើសទីផ្សារ៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "🧠 Consensus":
        buttons = []
        for cat, symbols in CATEGORIES.items():
            for sym in symbols:
                m = MARKETS.get(sym)
                if m:
                    buttons.append([InlineKeyboardButton(
                        f"{m.emoji} {m.symbol}",
                        callback_data=f"consensus_{sym}"
                    )])
        buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
        await update.message.reply_text(
            "🧠 *MULTI-LLM CONSENSUS*\nAI Models ច្រើនបោះឆ្នោត BUY/SELL/NEUTRAL\n\nជ្រើសរើសទីផ្សារ៖",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif text == "📰 News":
        await cmd_news(update, context)
    elif text == "🏛️ Macro":
        await cmd_macro(update, context)
    elif text in ("❓ Help ជំនួយ", "❓ Help"):
        await cmd_help(update, context)
    else:
        # Unknown command – check if it looks like a symbol
        upper = text.upper().strip()
        if upper in MARKETS:
            processing = await update.message.reply_text(f"🤖 កំពុងវិភាគ {upper}... ⏳")
            sig = generate_signal(upper, "1h")
            if sig:
                msg = format_signal_message(sig)
                await processing.delete()
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await processing.edit_text(f"❌ មិនអាចវិភាគ {upper}")
        else:
            await update.message.reply_text(
                "សូមប្រើប៊ូតុងឬពាក្យបញ្ជា (/help សម្រាប់ជំនួយ)"
            )


# -------------------- Callback Handlers --------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Category selection
    if data.startswith("cat_"):
        category = data[4:]
        if category in CATEGORIES:
            await query.edit_message_text(
                f"📂 *{category}*\nជ្រើសរើសទីផ្សារ៖",
                parse_mode="Markdown",
                reply_markup=symbol_list_keyboard(category)
            )
        else:
            await query.edit_message_text("❌ មិនមានប្រភេទនេះ")

    # Price lookup
    elif data.startswith("price_"):
        symbol = data[6:]
        msg = get_live_ticker_text(symbol)
        if msg:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Get AI Signal", callback_data=f"sig_sel_{symbol}")],
                [InlineKeyboardButton("🔙 Back", callback_data="markets_menu")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")

    # Markets menu
    elif data == "markets_menu":
        await query.edit_message_text(
            "📊 *ទីផ្សារ*\nជ្រើសរើសប្រភេទ៖",
            parse_mode="Markdown",
            reply_markup=markets_inline_keyboard()
        )

    # Signal symbol selection
    elif data.startswith("sig_sel_"):
        symbol = data[8:]
        context.user_data["signal_symbol"] = symbol
        await query.edit_message_text(
            f"🤖 *AI SIGNAL — {symbol}*\nជ្រើសរើស Timeframe៖",
            parse_mode="Markdown",
            reply_markup=signal_timeframe_keyboard()
        )

    # Signal timeframe selection
    elif data.startswith("sig_tf_"):
        tf = data[7:]
        symbol = context.user_data.get("signal_symbol", "XAUUSD")

        # Edit to "analyzing" message
        await query.edit_message_text(f"🤖 កំពុងវិភាគ {symbol} ({tf})... ⏳")

        sig = generate_signal(symbol, tf)
        if sig:
            try:
                db = get_db()
                if db:
                    import json
                    ind_json = json.dumps({k: v["signal"] for k, v in sig.indicators.items()})
                    save_signal(db, sig.symbol, sig.direction, sig.entry_price,
                               sig.stop_loss, sig.take_profit, sig.confidence,
                               sig.timeframe, ind_json, sig.summary)
                    db.close()
            except Exception:
                pass

            msg = format_signal_message(sig)
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🟢 ឈ្នះ WIN", callback_data=f"result_{sig.symbol}_WIN"),
                    InlineKeyboardButton("🔴 ចាញ់ LOSS", callback_data=f"result_{sig.symbol}_LOSS"),
                ],
                [
                    InlineKeyboardButton("🔄 New Signal", callback_data=f"sig_sel_{symbol}"),
                    InlineKeyboardButton("📊 Analysis", callback_data=f"analysis_{symbol}_{tf}"),
                ],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យសម្រាប់ {symbol}")

    # --- AI Signal Callbacks ---

    elif data.startswith("ai_sig_sel_"):
        symbol = data[11:]
        context.user_data["ai_signal_symbol"] = symbol
        m = MARKETS.get(symbol)
        label = f"{m.emoji} {symbol}" if m else symbol
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏱ 15m", callback_data=f"ai_sig_tf_{symbol}_15m"),
                InlineKeyboardButton("⏱ 1H", callback_data=f"ai_sig_tf_{symbol}_1h"),
            ],
            [
                InlineKeyboardButton("⏱ 4H", callback_data=f"ai_sig_tf_{symbol}_4h"),
                InlineKeyboardButton("⏱ 1D", callback_data=f"ai_sig_tf_{symbol}_1d"),
            ],
            [InlineKeyboardButton("🔙 Cancel", callback_data="cancel")],
        ])
        await query.edit_message_text(
            f"🧠 *AI DEEP ANALYSIS*\n{label}\nជ្រើសរើស Timeframe៖",
            parse_mode="Markdown",
            reply_markup=kb
        )

    elif data.startswith("ai_sig_tf_"):
        parts = data[10:].split("_")
        symbol = parts[0]
        tf = parts[1] if len(parts) > 1 else "1h"
        m = MARKETS.get(symbol)
        label = f"{m.emoji} {symbol}" if m else symbol

        await query.edit_message_text(f"🧠 AI កំពុងវិភាគ {label} ({tf}) យ៉ាងស៊ីជម្រៅ...\nសូមរង់ចាំ 15-30 វិនាទី ⏳")

        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is None or df.empty or len(df) < 50:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
            return

        analysis = compute_full_analysis(df)
        price_data = get_current_price(symbol)
        if not price_data:
            await query.edit_message_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
            return

        ai_result = await ai_analyze_market(
            symbol, price_data,
            analysis.get("signals", {}),
            analysis.get("atr", {}),
            analysis.get("support_resistance", {}),
            tf
        )

        if ai_result:
            msg = format_ai_signal_message(ai_result, symbol, m.name if m else symbol, m.emoji if m else "")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Technical Signal", callback_data=f"sig_sel_{symbol}")],
                [InlineKeyboardButton("📊 Analysis", callback_data=f"analysis_{symbol}_{tf}")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(
                f"❌ AI មិនអាចវិភាគបាន។\nសូមប្រើ Technical Signal ជំនួស។",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 Technical Signal", callback_data=f"sig_sel_{symbol}")]
                ])
            )

    # Result reporting
    elif data.startswith("result_"):
        parts = data[7:].split("_")
        symbol = parts[0]
        result = parts[1] if len(parts) > 1 else "WIN"

        db = get_db()
        if db:
            # Find last signal for this symbol with PENDING status
            from database import SignalRecord
            last_sig = db.query(SignalRecord).filter(
                SignalRecord.symbol == symbol,
                SignalRecord.result == "PENDING"
            ).order_by(SignalRecord.created_at.desc()).first()

            if last_sig:
                current = get_current_price(symbol)
                exit_price = current["price"] if current else last_sig.entry_price
                if result == "WIN":
                    pnl = abs(last_sig.take_profit - last_sig.entry_price) / last_sig.entry_price * 100
                elif result == "LOSS":
                    pnl = -abs(last_sig.stop_loss - last_sig.entry_price) / last_sig.entry_price * 100
                else:
                    pnl = 0
                update_signal_result(db, last_sig.id, result, exit_price, round(pnl, 2))

                # Show updated track record
                record = get_track_record(db)
                db.close()

                await query.edit_message_text(
                    f"✅ បានកត់ត្រា! *{result}*\n"
                    f"📊 អត្រាឈ្នះថ្មី: *{record['win_rate']}%* ({record['wins']}/{record['total']})",
                    parse_mode="Markdown"
                )
            else:
                db.close()
                await query.edit_message_text("❌ មិនមានកំណត់ត្រាសញ្ញាដែលត្រូវបញ្ជាក់")

    # Analysis request
    elif data.startswith("analysis_"):
        # analysis_XAUUSD_1h or analysis_req_XAUUSD
        parts = data[9:].split("_")
        symbol = parts[0]
        tf = parts[1] if len(parts) > 1 else "1h"

        await query.edit_message_text(f"🔍 កំពុងវិភាគ {symbol}... ⏳")

        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is not None and not df.empty:
            analysis = compute_full_analysis(df)
            msg = format_analysis_message(analysis, symbol)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Get Signal", callback_data=f"sig_sel_{symbol}")],
                [InlineKeyboardButton("🔙 Back", callback_data="markets_menu")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")

    elif data.startswith("analysis_req_"):
        symbol = data[13:]
        await query.edit_message_text(f"🔍 កំពុងវិភាគ {symbol}... ⏳")

        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is not None and not df.empty:
            analysis = compute_full_analysis(df)
            msg = format_analysis_message(analysis, symbol)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Get Signal", callback_data=f"sig_sel_{symbol}")],
                [InlineKeyboardButton("🔙 Back", callback_data="cancel")],
            ])
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        else:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")

    # Refresh all prices
    elif data == "refresh_all":
        results = get_multi_prices(list(MARKETS.keys()))
        if results:
            msg = "*💹 តម្លៃផ្សាយផ្ទាល់ទាំងអស់*\n━━━━━━━━━━━━━━━━\n"
            for r in results:
                arrow = "🟢" if r["change_pct"] >= 0 else "🔴"
                msg += f"{r['emoji']} *{r['symbol']}*: ${r['price']:,.2f} {arrow} {r['change_pct']:+,.2f}%\n"
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=markets_inline_keyboard())
        else:
            await query.edit_message_text("❌ មិនអាចទាញទិន្នន័យ", reply_markup=markets_inline_keyboard())

    # Journal
    elif data == "journal_add":
        context.user_data["journal_step"] = "symbol"
        await query.edit_message_text(
            "📓 *បន្ថែម Trade ថ្មី*\nសូមវាយបញ្ចូល Symbol របស់អ្នក (ឧ. XAUUSD)៖",
            parse_mode="Markdown"
        )

    elif data == "journal_view":
        db = get_db()
        if db:
            trades = db.query(TradeJournal).order_by(TradeJournal.created_at.desc()).limit(10).all()
            db.close()
            if trades:
                msg = "📓 *TRADE JOURNAL — កំណត់ត្រា 10 ចុងក្រោយ*\n━━━━━━━━━━━━━━━━\n"
                for t in trades:
                    dir_emoji = "🟢" if t.direction == "BUY" else "🔴"
                    status = "OPEN" if t.status == "OPEN" else "CLOSED"
                    pnl_str = f" | PnL: ${t.pnl:,.2f}" if t.pnl else ""
                    msg += f"{dir_emoji} *{t.symbol}* {t.direction} @ {t.entry_price}{pnl_str} — {t.created_at.strftime('%d/%m/%y')}\n"
                await query.edit_message_text(msg, parse_mode="Markdown")
            else:
                await query.edit_message_text("📓 មិនទាន់មានកំណត់ត្រា។")

    # --- NEW AI Callbacks ---

    elif data.startswith("ai_conf_"):
        symbol = data[8:]
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        m = MARKETS[symbol]
        await query.edit_message_text(f"🔗 AI កំពុងវិភាគ {symbol} លើ 4 Timeframes... ⏳")
        tf_data = {}
        for tf in ["15m", "1h", "4h", "1d"]:
            df = fetch_ohlcv(symbol, interval=tf, period="30d")
            if df is not None and not df.empty and len(df) >= 10:
                analysis = compute_full_analysis(df)
                price = get_current_price(symbol)
                tf_data[tf] = {
                    "price": price["price"] if price else 0,
                    "rsi": analysis.get("signals", {}).get("RSI", {}).get("value", "N/A"),
                    "trend": analysis.get("signals", {}).get("ADX", {}).get("signal", "N/A"),
                    "above_ema": analysis.get("signals", {}).get("EMA", {}).get("signal", "") == "BUY",
                }
        if len(tf_data) < 2:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យគ្រប់ TF សម្រាប់ {symbol}")
            return
        price_data = get_current_price(symbol)
        result = await ai_confluence(symbol, tf_data, price_data["price"] if price_data else 0)
        if result:
            msg = format_confluence_message(result, symbol, m.emoji, m.name)
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ AI មិនអាចវិភាគ {symbol}")

    elif data.startswith("ai_sent_"):
        symbol = data[8:]
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        m = MARKETS[symbol]
        await query.edit_message_text(f"💭 AI កំពុងវិភាគមនោសញ្ចេតនា {symbol}... ⏳")
        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is None or df.empty:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
            return
        analysis = compute_full_analysis(df)
        price_data = get_current_price(symbol)
        if not price_data:
            await query.edit_message_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
            return
        vol_data = {"volume": price_data.get("volume", "N/A"), "volume_ratio": "N/A"}
        result = await ai_sentiment(symbol, price_data, analysis.get("signals", {}), vol_data)
        if result:
            msg = format_sentiment_message(result, symbol, m.emoji)
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ AI មិនអាចវិភាគ sentiment សម្រាប់ {symbol}")

    elif data.startswith("ai_pat_"):
        symbol = data[7:]
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        m = MARKETS[symbol]
        await query.edit_message_text(f"📐 AI កំពុងរក Chart Patterns លើ {symbol}... ⏳")
        df = fetch_ohlcv(symbol, interval="1h", period="30d")
        if df is None or df.empty:
            await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
            return
        recent = df.tail(20)
        ohlc_summary = "\n".join([
            f"  {i}: O={row['Open']:.2f} H={row['High']:.2f} L={row['Low']:.2f} C={row['Close']:.2f}"
            for i, row in recent.iterrows()
        ])
        analysis = compute_full_analysis(df)
        price_data = get_current_price(symbol)
        if not price_data:
            await query.edit_message_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
            return
        sr = analysis.get("support_resistance", {})
        result = await ai_detect_patterns(symbol, price_data, ohlc_summary, sr)
        if result:
            msg = format_pattern_message(result, symbol, m.emoji)
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ AI មិនអាចរក Patterns សម្រាប់ {symbol}")

    elif data.startswith("ai_strat_"):
        strat_type = data[9:]
        strat_map = {
            "gold_scalping": ("Gold/XAUUSD", "scalping", "beginner", "$100-$500", "medium"),
            "forex_day": ("Forex", "day trading", "intermediate", "$500-$2000", "medium"),
            "crypto_swing": ("Crypto", "swing trading", "intermediate", "$1000-$5000", "high"),
            "indices_position": ("Indices", "position trading", "advanced", "$5000+", "low"),
            "custom": ("Any", "swing trading", "intermediate", "$500-$5000", "medium"),
        }
        market, style, exp, cap, risk = strat_map.get(strat_type, strat_map["custom"])
        await query.edit_message_text(f"📐 AI កំពុងបង្កើត Strategy សម្រាប់ {market} ({style})... ⏳")
        result = await ai_build_strategy(market, style, exp, cap, risk)
        if result:
            msg = format_strategy_message(result)
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ AI មិនអាចបង្កើត Strategy បាន")

    elif data.startswith("ai_corr_"):
        symbol = data[8:]
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        m = MARKETS[symbol]
        await query.edit_message_text(f"🔗 AI កំពុងវិភាគទំនាក់ទំនង {symbol}... ⏳")
        all_prices = []
        for s in MARKETS:
            p = get_current_price(s)
            if p:
                all_prices.append(p)
        result = await ai_correlated_markets(symbol, all_prices)
        if result:
            msg = format_correlation_message(result, symbol, m.emoji)
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ AI មិនអាចវិភាគ correlation សម្រាប់ {symbol}")

    # --- OMEGA Commander Callback ---

    elif data.startswith("buy_"):
        plan_id = data[4:]
        if plan_id == "menu":
            plans_kb = []
            for pid, plan in PRICING_PLANS.items():
                plans_kb.append([InlineKeyboardButton(
                    f"{plan['emoji']} {plan['name']} — ${plan['price']}",
                    callback_data=f"buy_{pid}"
                )])
            plans_kb.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
            await query.edit_message_text(
                "👇 *ជ្រើសរើស Plan ដែលអ្នកចង់ទិញ:*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(plans_kb)
            )
            return

        plan = PRICING_PLANS.get(plan_id)
        if not plan:
            await query.edit_message_text("❌ Plan មិនត្រឹមត្រូវ")
            return

        user = update.effective_user
        username = f"@{user.username}" if user and user.username else f"user{user.id if user else ''}"
        payment_text = "\n".join(PAYMENT_METHODS)

        invoice = f"""💳 *បញ្ជាក់ការទិញ*
━━━━━━━━━━━━━━━━━━━━━━

📦 *Plan:* {plan['emoji']} {plan['name']}
💰 *តម្លៃ:* ${plan['price']}
📅 *រយៈពេល:* {plan['days']} ថ្ងៃ
👤 *អ្នកទិញ:* {username}

━━━━━━━━━━━━━━━━━━━━━━
🏦 *វិធីបង់ប្រាក់:*
{payment_text}

━━━━━━━━━━━━━━━━━━━━━━
📋 *របៀបទិញ:*
1️⃣ ផ្ញើប្រាក់តាមគណនីខាងលើ
2️⃣ ផ្ញើរូបភស្តុតាង (Screenshot) មក {ADMIN_USERNAME}
3️⃣ Admin នឹងផ្ញើ License Key អោយអ្នក
4️⃣ ប្រើ `/activate <key>` ដើម្បីដំណើរការ

━━━━━━━━━━━━━━━━━━━━━━
📞 *ទំនាក់ទំនង:* {ADMIN_USERNAME}
🔮 _BlackMagicAI OMEGA — 8 AI Engines_
"""

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📞 ទំនាក់ទំនង {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("🔄 មើល Plans ផ្សេង", callback_data="buy_menu")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="cancel")],
        ])
        await query.edit_message_text(invoice, parse_mode="Markdown", reply_markup=kb)

        # Notify admin
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🛒 *NEW PURCHASE!*\n\n"
                         f"📦 Plan: {plan['name']} — ${plan['price']}\n"
                         f"👤 Customer: {username}\n"
                         f"🆔 User ID: {user.id if user else '?'}\n\n"
                         f"Generate key: `/genkey {plan_id} {username}`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Failed to notify admin: {e}")

        return

    elif data.startswith("omega_"):
        symbol = data[6:]
        if symbol == "menu":
            # Show symbol selector again
            buttons = []
            for cat, symbols in CATEGORIES.items():
                row = []
                for sym in symbols:
                    m = MARKETS.get(sym)
                    if m:
                        row.append(InlineKeyboardButton(
                            f"{m.emoji} {m.symbol}",
                            callback_data=f"omega_{sym}"
                        ))
                    if len(row) == 2:
                        buttons.append(row)
                        row = []
                if row:
                    buttons.append(row)
            buttons.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
            await query.edit_message_text(
                "🔮 *OMEGA COMMANDER*\nជ្រើសរើសទីផ្សារថ្មី៖",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        await _run_commander(update, context, symbol)

    elif data.startswith("quant_"):
        symbol = data.replace("quant_", "")
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        processing = await query.edit_message_text(
            f"🏦 *កំពុងដំណើរការ Quant Analysis សម្រាប់ {symbol}...*\nMonte Carlo • VaR • Kelly • Vol Regime • Mean Reversion ⏳",
            parse_mode="Markdown"
        )
        try:
            df = fetch_ohlcv(symbol, interval="1h", period="30d")
            if df is None or df.empty or len(df) < 30:
                await query.edit_message_text(f"❌ មិនអាចទាញទិន្នន័យ {symbol}")
                return
            prices = df["close"].tolist()
            report = full_quant_report(symbol, prices, position_value=10000.0)
            msg = format_quant_report(report)
            await query.delete_message()
            await query.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Quant callback error for {symbol}: {e}")
            await query.edit_message_text(f"❌ មានបញ្ហា: `{str(e)[:150]}`", parse_mode="Markdown")

    elif data.startswith("consensus_"):
        symbol = data.replace("consensus_", "")
        if symbol not in MARKETS:
            await query.edit_message_text(f"❌ មិនស្គាល់ទីផ្សារ: {symbol}")
            return
        market = MARKETS[symbol]
        processing = await query.edit_message_text(
            f"🧠 *កំពុងប្រមូល AI Consensus សម្រាប់ {symbol}...*\nMultiple AI models voting ⏳",
            parse_mode="Markdown"
        )
        try:
            price_data = get_current_price(symbol)
            if not price_data:
                await query.edit_message_text(f"❌ មិនអាចទាញតម្លៃ {symbol}")
                return
            consensus = await multi_model_consensus(
                symbol, market.name, price_data["price"], price_data.get("change_pct", 0)
            )
            msg = format_consensus_message(consensus)
            await query.delete_message()
            await query.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Consensus callback error for {symbol}: {e}")
            await query.edit_message_text(f"❌ មានបញ្ហា: `{str(e)[:150]}`", parse_mode="Markdown")

    elif data == "cancel":
        try:
            await query.delete_message()
        except Exception:
            await query.edit_message_text("✅ បានបោះបង់")


# -------------------- Journal Conversation --------------------

async def handle_journal_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle multi-step journal entry."""
    step = context.user_data.get("journal_step")
    if not step:
        return  # not in journal mode, let main handler deal with it

    text = update.message.text.strip()

    if step == "symbol":
        context.user_data["j_symbol"] = text.upper()
        context.user_data["journal_step"] = "direction"
        await update.message.reply_text(
            "ទិសដៅ? វាយ BUY ឬ SELL៖"
        )
    elif step == "direction":
        direction = text.upper()
        if direction not in ("BUY", "SELL"):
            await update.message.reply_text("សូមវាយ BUY ឬ SELL៖")
            return
        context.user_data["j_direction"] = direction
        context.user_data["journal_step"] = "entry"
        await update.message.reply_text("តម្លៃចូល (Entry Price)? ឧ. 4000៖")
    elif step == "entry":
        try:
            context.user_data["j_entry"] = float(text)
            context.user_data["journal_step"] = "exit"
            await update.message.reply_text("តម្លៃចេញ (Exit Price)? ឧ. 4050 (ឬ វាយ 'skip' បើមិនទាន់)៖")
        except ValueError:
            await update.message.reply_text("សូមបញ្ចូលលេខ៖")
    elif step == "exit":
        if text.lower() == "skip":
            context.user_data["j_exit"] = None
        else:
            try:
                context.user_data["j_exit"] = float(text)
            except ValueError:
                await update.message.reply_text("សូមបញ្ចូលលេខ ឬ 'skip'៖")
                return
        context.user_data["journal_step"] = "notes"
        await update.message.reply_text("មូលហេតុ/កំណត់សម្គាល់? (ឬវាយ 'skip')៖")
    elif step == "notes":
        notes = text if text.lower() != "skip" else ""
        symbol = context.user_data.get("j_symbol", "UNKNOWN")
        direction = context.user_data.get("j_direction", "BUY")
        entry = context.user_data.get("j_entry", 0)
        exit_price = context.user_data.get("j_exit")

        # Calculate PnL
        pnl = None
        pnl_pct = None
        status = "OPEN"
        if exit_price:
            if direction == "BUY":
                pnl = exit_price - entry
            else:
                pnl = entry - exit_price
            if entry > 0:
                pnl_pct = round(pnl / entry * 100, 2)
            pnl = round(pnl, 4)
            status = "CLOSED"

        db = get_db()
        if db:
            trade = TradeJournal(
                symbol=symbol,
                direction=direction,
                entry_price=entry,
                exit_price=exit_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason=notes,
                status=status,
            )
            db.add(trade)
            db.commit()
            db.close()

            msg = f"✅ *បានកត់ត្រា Trade!*\n"
            msg += f"📊 {MARKETS.get(symbol, {}).emoji if symbol in MARKETS else ''} *{symbol}* — {direction}\n"
            msg += f"💰 Entry: ${entry:,.2f}\n"
            if exit_price:
                msg += f"💰 Exit: ${exit_price:,.2f}\n"
                pnl_emoji = "🟢" if pnl and pnl > 0 else "🔴"
                pnl_str = f"+${pnl:,.2f} ({pnl_pct:+,.2f}%)" if pnl else "$0.00"
                msg += f"{pnl_emoji} PnL: {pnl_str}\n"
            msg += f"📝 Notes: {notes}" if notes else ""

            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ មានបញ្ហា database")

        # Clear journal state
        for key in ["journal_step", "j_symbol", "j_direction", "j_entry", "j_exit"]:
            context.user_data.pop(key, None)


# -------------------- Alert Checker (Background) --------------------

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job to check price alerts."""
    db = SessionLocal()
    try:
        active_alerts = db.query(AlertConfig).filter(AlertConfig.active == True).all()
        if not active_alerts:
            return

        checked_symbols = set(a.symbol for a in active_alerts)
        prices = {}
        for sym in checked_symbols:
            data = get_current_price(sym)
            if data:
                prices[sym] = data["price"]

        for alert in active_alerts:
            current = prices.get(alert.symbol)
            if not current:
                continue

            triggered = False
            if alert.condition == "ABOVE" and current >= alert.price:
                triggered = True
            elif alert.condition == "BELOW" and current <= alert.price:
                triggered = True

            if triggered:
                emoji = MARKETS[alert.symbol].emoji if alert.symbol in MARKETS else ""
                dir_kh = "ឡើងដល់" if alert.condition == "ABOVE" else "ធ្លាក់ដល់"
                await context.bot.send_message(
                    chat_id=alert.chat_id,
                    text=f"🔔 *ALERT TRIGGERED!*\n{emoji} *{alert.symbol}* {dir_kh} `${alert.price:,.2f}`\n"
                         f"💰 តម្លៃបច្ចុប្បន្ន: `${current:,.2f}`",
                    parse_mode="Markdown"
                )
                alert.active = False
                db.commit()
    except Exception as e:
        logger.error(f"Alert check error: {e}")
    finally:
        db.close()


# -------------------- Main --------------------

def main():
    if not BOT_TOKEN:
        print("❌ សូមដំឡើង TELEGRAM_BOT_TOKEN ក្នុង .env file!")
        print("   បើក .env រួចបំពេញ: TELEGRAM_BOT_TOKEN=YOUR_TOKEN")
        return

    # License check on startup
    check_license_on_startup()

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("markets", cmd_markets))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("ai_signal", cmd_ai_signal))
    app.add_handler(CommandHandler("ai_scan", cmd_ai_scan))
    app.add_handler(CommandHandler("analysis", cmd_analysis))
    app.add_handler(CommandHandler("trackrecord", cmd_trackrecord))
    app.add_handler(CommandHandler("winrate", cmd_winrate))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("risk", cmd_risk))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("ai_confluence", cmd_ai_confluence))
    app.add_handler(CommandHandler("ai_sentiment", cmd_ai_sentiment))
    app.add_handler(CommandHandler("ai_pattern", cmd_ai_pattern))
    app.add_handler(CommandHandler("ai_strategy", cmd_ai_strategy))
    app.add_handler(CommandHandler("ai_psychology", cmd_ai_psychology))
    app.add_handler(CommandHandler("ai_correlate", cmd_ai_correlate))
    app.add_handler(CommandHandler("ai_complete", cmd_commander))
    app.add_handler(CommandHandler("omega", cmd_commander))
    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CommandHandler("license", cmd_license))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("genkey", cmd_genkey))
    app.add_handler(CommandHandler("quant", cmd_quant))
    app.add_handler(CommandHandler("consensus", cmd_consensus))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("macro", cmd_macro))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Message handlers (must be last – catches journal input first, then general)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_journal_input), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message), group=2)

    # Alert checker - every 5 minutes
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_alerts, interval=300, first=10)

    print("🤖 BlackMagicAI Trading Bot is running...")
    print("Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
