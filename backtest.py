"""
BlackMagicAI OMEGA — Backtest Engine
Walk-forward backtest of the exact signal logic used live in signals.generate_signal(),
so Kelly Criterion / quant_score inputs can be based on real historical performance
instead of hardcoded guesses.

No look-ahead bias: at each historical bar, only data up to and including that bar
is used to compute indicators and generate the signal — exactly what would have been
available in real time.
"""
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import pandas as pd

from market_data import fetch_ohlcv
from analysis import compute_full_analysis
from config import MARKETS


@dataclass
class BacktestTrade:
    entry_index: int
    entry_time: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    result: Optional[str] = None  # WIN, LOSS, OPEN_AT_END
    pnl_pct: Optional[float] = None
    bars_held: int = 0


# Re-implements the scoring logic from signals.generate_signal() so the backtest
# exercises the identical weighting scheme used live (kept in sync manually —
# see NOTE at bottom of file for how to keep this consistent with signals.py).
WEIGHTS = {
    "RSI": 1.5, "MACD": 1.2, "EMA": 1.5, "BB": 0.8, "ADX": 1.0,
    "STOCH": 0.8, "TREND_LONG": 1.2, "VOLUME": 0.5,
    "ICHIMOKU": 1.3, "FIBONACCI": 0.9, "CANDLESTICK": 0.6, "VWAP": 0.9, "PSAR": 1.0, "CMF": 0.7,
}


def _score_signals(signals: dict) -> tuple[str, int]:
    buy_score = sell_score = total_weight = 0.0
    for indicator, data in signals.items():
        w = WEIGHTS.get(indicator, 1.0)
        total_weight += w
        sig = data.get("signal", "NEUTRAL")
        if sig == "BUY":
            buy_score += w
        elif sig == "SELL":
            sell_score += w

    max_score = max(buy_score, sell_score)
    confidence = min(round((max_score / total_weight) * 100), 95) if total_weight > 0 else 50

    if buy_score > sell_score:
        direction = "BUY"
    elif sell_score > buy_score:
        direction = "SELL"
    else:
        direction = "NEUTRAL"

    if min(buy_score, sell_score) > 0 and max_score > 0:
        ratio_diff = abs(buy_score - sell_score) / max_score
        if ratio_diff < 0.2:
            direction = "NEUTRAL"
            confidence = max(round(confidence * 0.6), 30)

    return direction, confidence


def run_backtest(
    symbol_name: str,
    timeframe: str = "1h",
    min_confidence: int = 55,
    max_hold_bars: int = 48,
    warmup_bars: int = 60,
) -> Dict:
    """Walk forward through historical bars, generate a signal at each point (once
    warmup indicators are available), simulate the trade to its SL/TP/timeout outcome,
    and report aggregate performance stats.

    Uses whatever history yfinance returns for the timeframe's configured period
    (see config.TIMEFRAMES) — for longer backtests, call fetch_ohlcv directly with a
    longer period and pass the DataFrame via `_run_backtest_on_df`.
    """
    symbol_name = symbol_name.upper()
    if symbol_name not in MARKETS:
        return {"error": "unknown_symbol"}

    tf_map = {"15m": ("15m", "5d"), "1h": ("1h", "30d"), "4h": ("1h", "60d"), "1d": ("1d", "90d")}
    interval, period = tf_map.get(timeframe, ("1h", "30d"))
    df = fetch_ohlcv(symbol_name, interval=interval, period=period)
    if df is None or len(df) < warmup_bars + 20:
        return {"error": "insufficient_history", "bars_available": 0 if df is None else len(df)}

    return _run_backtest_on_df(symbol_name, df, min_confidence, max_hold_bars, warmup_bars)


def _run_backtest_on_df(
    symbol_name: str,
    df: pd.DataFrame,
    min_confidence: int,
    max_hold_bars: int,
    warmup_bars: int,
) -> Dict:
    trades: List[BacktestTrade] = []
    open_trade: Optional[BacktestTrade] = None
    n = len(df)

    for i in range(warmup_bars, n):
        window = df.iloc[: i + 1]  # only past + current bar — no look-ahead
        bar = df.iloc[i]

        # --- manage an open trade first: check if this bar hits SL/TP/timeout ---
        if open_trade:
            hit_sl = (bar["Low"] <= open_trade.stop_loss) if open_trade.direction == "BUY" else (bar["High"] >= open_trade.stop_loss)
            hit_tp = (bar["High"] >= open_trade.take_profit) if open_trade.direction == "BUY" else (bar["Low"] <= open_trade.take_profit)
            open_trade.bars_held += 1

            exit_now = False
            if hit_sl and hit_tp:
                # both touched in the same bar — assume the worse outcome (conservative)
                open_trade.exit_price = open_trade.stop_loss
                open_trade.result = "LOSS"
                exit_now = True
            elif hit_sl:
                open_trade.exit_price = open_trade.stop_loss
                open_trade.result = "LOSS"
                exit_now = True
            elif hit_tp:
                open_trade.exit_price = open_trade.take_profit
                open_trade.result = "WIN"
                exit_now = True
            elif open_trade.bars_held >= max_hold_bars:
                open_trade.exit_price = bar["Close"]
                open_trade.result = "WIN" if (
                    (open_trade.direction == "BUY" and bar["Close"] > open_trade.entry_price) or
                    (open_trade.direction == "SELL" and bar["Close"] < open_trade.entry_price)
                ) else "LOSS"
                exit_now = True

            if exit_now:
                if open_trade.direction == "BUY":
                    open_trade.pnl_pct = round((open_trade.exit_price - open_trade.entry_price) / open_trade.entry_price * 100, 3)
                else:
                    open_trade.pnl_pct = round((open_trade.entry_price - open_trade.exit_price) / open_trade.entry_price * 100, 3)
                open_trade.exit_time = str(df.index[i])
                trades.append(open_trade)
                open_trade = None
            continue  # don't open a new trade the same bar we're managing one

        # --- no open trade: evaluate a new signal ---
        analysis = compute_full_analysis(window)
        signals = analysis.get("signals", {})
        if "error" in signals or not signals:
            continue

        direction, confidence = _score_signals(signals)
        if direction == "NEUTRAL" or confidence < min_confidence:
            continue

        atr_data = analysis.get("atr")
        entry_price = analysis.get("last_price", bar["Close"])
        if not atr_data:
            continue
        atr_val = atr_data["ATR"]
        if direction == "BUY":
            stop_loss = round(entry_price - atr_val * 1.5, 4)
            take_profit = round(entry_price + atr_val * 2.5, 4)
        else:
            stop_loss = round(entry_price + atr_val * 1.5, 4)
            take_profit = round(entry_price - atr_val * 2.5, 4)

        open_trade = BacktestTrade(
            entry_index=i,
            entry_time=str(df.index[i]),
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    # close any trade still open at the end of history
    if open_trade:
        last_close = df.iloc[-1]["Close"]
        open_trade.exit_price = last_close
        open_trade.result = "OPEN_AT_END"
        if open_trade.direction == "BUY":
            open_trade.pnl_pct = round((last_close - open_trade.entry_price) / open_trade.entry_price * 100, 3)
        else:
            open_trade.pnl_pct = round((open_trade.entry_price - last_close) / open_trade.entry_price * 100, 3)
        trades.append(open_trade)

    return _summarize(symbol_name, trades)


def _summarize(symbol_name: str, trades: List[BacktestTrade]) -> Dict:
    closed = [t for t in trades if t.result in ("WIN", "LOSS")]
    wins = [t for t in closed if t.result == "WIN"]
    losses = [t for t in closed if t.result == "LOSS"]

    total = len(closed)
    win_rate = round(len(wins) / total * 100, 2) if total else 0.0
    avg_win_pct = round(statistics.mean([t.pnl_pct for t in wins]), 3) if wins else 0.0
    avg_loss_pct = round(abs(statistics.mean([t.pnl_pct for t in losses])), 3) if losses else 0.0

    gross_profit = sum(t.pnl_pct for t in wins)
    gross_loss = abs(sum(t.pnl_pct for t in losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    # equity curve (cumulative pnl_pct, simple additive approximation)
    equity = 0.0
    equity_curve = []
    max_equity = 0.0
    max_drawdown = 0.0
    consecutive_losses = 0
    max_consecutive_losses = 0
    for t in closed:
        equity += t.pnl_pct
        equity_curve.append(round(equity, 3))
        max_equity = max(max_equity, equity)
        max_drawdown = min(max_drawdown, equity - max_equity)
        if t.result == "LOSS":
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    return {
        "symbol": symbol_name,
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "profit_factor": profit_factor,
        "net_pnl_pct": round(equity, 3),
        "max_drawdown_pct": round(max_drawdown, 3),
        "max_consecutive_losses": max_consecutive_losses,
        "still_open_at_end": len(trades) - total,
        "equity_curve": equity_curve,
        # Ready to feed directly into quant_engine.kelly_criterion():
        "kelly_inputs": {
            "win_rate": win_rate,
            "avg_win": avg_win_pct / 100,   # kelly_criterion expects fractional returns
            "avg_loss": avg_loss_pct / 100,
        },
    }


def format_backtest_report(report: Dict) -> str:
    """Format a backtest report as a Telegram Markdown message."""
    if "error" in report:
        return f"❌ Backtest error: {report['error']}"

    pf = report["profit_factor"]
    pf_str = "∞" if pf == float("inf") else f"{pf}"

    msg = f"""🧪 *BACKTEST REPORT — {report['symbol']}*
━━━━━━━━━━━━━━━━━━━━━━
📊 Total Trades: {report['total_trades']} ({report['wins']}W / {report['losses']}L)
🎯 Win Rate: *{report['win_rate']}%*
💰 Avg Win: +{report['avg_win_pct']}% | Avg Loss: -{report['avg_loss_pct']}%
⚖️ Profit Factor: {pf_str}
📈 Net PnL: {report['net_pnl_pct']:+.2f}%
📉 Max Drawdown: {report['max_drawdown_pct']:.2f}%
🔻 Max Consecutive Losses: {report['max_consecutive_losses']}

⚠️ _Backtested on available yfinance history for this timeframe. Past performance ≠ future results._
_Use `kelly_inputs` from this report as real inputs to quant_engine.kelly_criterion() instead of hardcoded defaults._
"""
    return msg


# NOTE ON KEEPING THIS IN SYNC WITH signals.py:
# `_score_signals()` above mirrors the weighting logic inside signals.generate_signal().
# If you change the WEIGHTS dict or scoring rules in signals.py, update WEIGHTS and
# _score_signals() here too, or the backtest will silently diverge from live behavior.
# (A follow-up refactor could extract this scoring function into signals.py and import
# it here instead of duplicating it — recommended next step.)
