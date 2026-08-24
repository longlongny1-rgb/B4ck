import os
from dataclasses import dataclass
from typing import Dict

# -------------------- Market Definitions --------------------
@dataclass
class Market:
    symbol: str
    yahoo_symbol: str
    category: str
    name: str
    emoji: str

MARKETS: Dict[str, Market] = {
    # Gold
    "XAUUSD": Market("XAUUSD", "GC=F", "Commodities", "Gold / XAUUSD", "🥇"),
    # Forex
    "EURUSD": Market("EURUSD", "EURUSD=X", "Forex", "Euro / US Dollar", "💶"),
    "GBPUSD": Market("GBPUSD", "GBPUSD=X", "Forex", "British Pound / US Dollar", "💷"),
    "USDJPY": Market("USDJPY", "USDJPY=X", "Forex", "US Dollar / Japanese Yen", "💴"),
    "AUDUSD": Market("AUDUSD", "AUDUSD=X", "Forex", "Australian Dollar / US Dollar", "🇦🇺"),
    # Crypto
    "BTCUSDT": Market("BTCUSDT", "BTC-USD", "Crypto", "Bitcoin / USDT", "₿"),
    "ETHUSDT": Market("ETHUSDT", "ETH-USD", "Crypto", "Ethereum / USDT", "Ξ"),
    # Indices
    "NAS100": Market("NAS100", "^NDX", "Indices", "NASDAQ 100", "📊"),
    "US30": Market("US30", "^DJI", "Indices", "Dow Jones 30", "🏭"),
    "US500": Market("US500", "^GSPC", "Indices", "S&P 500", "📈"),
    # Oil
    "USOIL": Market("USOIL", "CL=F", "Commodities", "US Crude Oil", "🛢️"),
    # Stocks
    "AAPL": Market("AAPL", "AAPL", "Stocks", "Apple Inc.", "🍎"),
    "TSLA": Market("TSLA", "TSLA", "Stocks", "Tesla Inc.", "🚗"),
    "NVDA": Market("NVDA", "NVDA", "Stocks", "NVIDIA Corp.", "💻"),
}

CATEGORIES = {
    "Commodities": ["XAUUSD", "USOIL"],
    "Forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
    "Crypto": ["BTCUSDT", "ETHUSDT"],
    "Indices": ["NAS100", "US30", "US500"],
    "Stocks": ["AAPL", "TSLA", "NVDA"],
}

TIMEFRAMES = {
    "15m": {"interval": "15m", "period": "5d", "name": "15 Minutes"},
    "1h": {"interval": "1h", "period": "30d", "name": "1 Hour"},
    "4h": {"interval": "1h", "period": "60d", "name": "4 Hours (resampled)"},
    "1d": {"interval": "1d", "period": "90d", "name": "1 Day"},
}

# Bot commands
COMMANDS = [
    ("start", "🚀 ចាប់ផ្តើម / Main Menu"),
    ("markets", "📊 ទីផ្សារទាំងអស់ / All Markets"),
    ("signal", "🤖 សញ្ញា AI / AI Signal (ឧ. /signal XAUUSD)"),
    ("price", "💹 តម្លៃផ្សាយផ្ទាល់ / Live Price"),
    ("analysis", "🔍 វិភាគបច្ចេកទេស / Technical Analysis"),
    ("trackrecord", "📋 កំណត់ត្រាឈ្នះ-ចាញ់ / Track Record"),
    ("winrate", "📈 អត្រាឈ្នះ / Win Rate"),
    ("risk", "⚖️ គណនា Risk/Reward / Risk Calculator"),
    ("journal", "📓 កំណត់ហេតុជួញដូរ / Trade Journal"),
    ("alert", "🔔 ដំឡើងការជូនដំណឹង / Set Alert"),
    ("help", "❓ ជំនួយ / Help"),
]

# Trading terms in Khmer
KH_SIGNAL = {
    "BUY": "ទិញ ⬆️",
    "SELL": "លក់ ⬇️",
    "NEUTRAL": "រង់ចាំ ⏸️",
    "STRONG": "ខ្លាំង 💪",
    "MODERATE": "មធ្យម",
    "WEAK": "ខ្សោយ",
}
