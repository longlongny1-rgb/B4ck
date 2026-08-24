"""
BlackMagicAI OMEGA — Institutional Quant Engine
Copyright (c) 2026 BlackMagicAI. All Rights Reserved.

Hedge Fund-Grade Quantitative Analysis:
- Monte Carlo Price Simulation (Geometric Brownian Motion)
- Value at Risk (VaR) — Parametric + Historical
- Kelly Criterion Position Sizing
- Volatility Regime Detection (GARCH-like)
- Mean Reversion Detection (Ornstein-Uhlenbeck)
- Sharpe / Sortino / Calmar Ratios
- Correlation Matrix & Risk Parity
- Maximum Drawdown & Stress Testing
"""

import math
import random
import statistics
from typing import List, Dict, Optional, Tuple
from collections import deque


# ==================== STATISTICAL HELPERS ====================

def _returns(prices: List[float]) -> List[float]:
    """Log returns from price series."""
    if len(prices) < 2:
        return []
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


def _simple_returns(prices: List[float]) -> List[float]:
    if len(prices) < 2:
        return []
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


def _annualized_volatility(returns: List[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    return statistics.stdev(returns) * math.sqrt(periods_per_year)


def _standard_normal() -> float:
    """Box-Muller transform for standard normal random variable."""
    u1 = random.random()
    u2 = random.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# ==================== MONTE CARLO SIMULATION ====================

def monte_carlo_simulation(
    current_price: float,
    daily_returns: List[float],
    num_simulations: int = 1000,
    forecast_days: int = 30,
    confidence_levels: List[int] = [68, 95, 99]
) -> Dict:
    """
    Geometric Brownian Motion Monte Carlo simulation.

    Returns forecasted price distribution, confidence intervals,
    and probability of price reaching targets.
    """
    if len(daily_returns) < 10:
        return {"error": "Not enough data", "min_days_required": 10, "provided": len(daily_returns)}

    mu = statistics.mean(daily_returns) if daily_returns else 0.0
    sigma = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.01
    dt = 1.0

    final_prices = []
    paths_sample = []  # Store first 5 paths for visualization

    for sim in range(num_simulations):
        price = current_price
        path = [price]
        for _ in range(forecast_days):
            drift = (mu - 0.5 * sigma ** 2) * dt
            shock = sigma * math.sqrt(dt) * _standard_normal()
            price *= math.exp(drift + shock)
            path.append(price)

        final_prices.append(price)
        if sim < 5:
            paths_sample.append(path)

    final_prices.sort()

    # Statistics
    mean_final = statistics.mean(final_prices)
    median_final = statistics.median(final_prices)
    std_final = statistics.stdev(final_prices) if len(final_prices) > 1 else 0.0
    min_final = min(final_prices)
    max_final = max(final_prices)

    # Confidence intervals
    ci = {}
    for cl in confidence_levels:
        tail = (100 - cl) / 2 / 100
        lower_idx = int(tail * num_simulations)
        upper_idx = int((1 - tail) * num_simulations)
        ci[str(cl)] = {
            "lower": round(final_prices[max(0, lower_idx)], 2),
            "upper": round(final_prices[min(num_simulations - 1, upper_idx)], 2),
        }

    # Probability of being above current price
    prob_up = sum(1 for p in final_prices if p > current_price) / num_simulations * 100
    prob_down = 100 - prob_up

    # Target probabilities
    target_5pct = current_price * 1.05
    target_10pct = current_price * 1.10
    target_neg5pct = current_price * 0.95
    prob_5pct_up = sum(1 for p in final_prices if p >= target_5pct) / num_simulations * 100
    prob_10pct_up = sum(1 for p in final_prices if p >= target_10pct) / num_simulations * 100
    prob_5pct_down = sum(1 for p in final_prices if p <= target_neg5pct) / num_simulations * 100

    drift_annual = mu * 252 * 100
    vol_annual = sigma * math.sqrt(252) * 100

    return {
        "model": "Geometric Brownian Motion",
        "simulations": num_simulations,
        "forecast_days": forecast_days,
        "current_price": round(current_price, 4),
        "drift_annual_pct": round(drift_annual, 2),
        "volatility_annual_pct": round(vol_annual, 2),
        "forecast_mean": round(mean_final, 4),
        "forecast_median": round(median_final, 4),
        "forecast_std": round(std_final, 4),
        "forecast_min": round(min_final, 4),
        "forecast_max": round(max_final, 4),
        "probability_up": round(prob_up, 1),
        "probability_down": round(prob_down, 1),
        "prob_+5pct": round(prob_5pct_up, 1),
        "prob_+10pct": round(prob_10pct_up, 1),
        "prob_-5pct": round(prob_5pct_down, 1),
        "confidence_intervals": ci,
        "sample_paths": [[round(p, 2) for p in path] for path in paths_sample],
    }


# ==================== VALUE AT RISK (VaR) ====================

def calculate_var(
    returns: List[float],
    confidence: float = 0.95,
    position_value: float = 10000.0,
    method: str = "parametric"
) -> Dict:
    """
    Value at Risk calculation.

    Args:
        returns: List of periodic returns
        confidence: Confidence level (0.95 = 95%)
        position_value: Value of the position
        method: "parametric" (normal dist) or "historical"
    """
    if len(returns) < 10:
        return {"error": "Need at least 10 return observations"}

    mu = statistics.mean(returns)
    sigma = statistics.stdev(returns)

    results = {
        "confidence_pct": confidence * 100,
        "position_value": round(position_value, 2),
        "mean_return_pct": round(mu * 100, 4),
        "volatility_pct": round(sigma * 100, 4),
    }

    if method == "parametric":
        # Parametric VaR (assumes normal distribution)
        import scipy.stats as stats_import
        z_score = abs(stats_import.norm.ppf(1 - confidence))
        var_pct = z_score * sigma - mu
        var_amount = position_value * var_pct
        results["method"] = "Parametric (Normal)"
        results["z_score"] = round(z_score, 4)
        results["var_pct"] = round(var_pct * 100, 4)
        results["var_amount"] = round(var_amount, 2)

    elif method == "historical":
        # Historical VaR
        sorted_returns = sorted(returns)
        idx = int((1 - confidence) * len(sorted_returns))
        var_ret = abs(sorted_returns[max(0, idx)])
        var_amount = position_value * var_ret
        results["method"] = "Historical"
        results["var_pct"] = round(var_ret * 100, 4)
        results["var_amount"] = round(var_amount, 2)

    # CVaR (Expected Shortfall)
    if method == "historical":
        tail_losses = [r for r in sorted_returns if r <= sorted_returns[max(0, idx)]]
        if tail_losses:
            cvar = abs(statistics.mean(tail_losses))
            results["cvar_pct"] = round(cvar * 100, 4)
            results["cvar_amount"] = round(position_value * cvar, 2)

    # Daily VaR interpretation
    results["interpretation"] = (
        f"With {confidence*100:.0f}% confidence, the maximum "
        f"expected loss over the next period is ${results['var_amount']:,.2f} "
        f"({results['var_pct']:.2f}% of position)"
    )

    return results


# ==================== KELLY CRITERION ====================

def kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    max_allocation_pct: float = 25.0
) -> Dict:
    """
    Kelly Criterion for optimal position sizing.

    f* = (p * b - q) / b
    where p = win probability, q = 1-p, b = avg_win / avg_loss
    """
    avg_loss_abs = abs(avg_loss) if avg_loss != 0 else 1.0
    b = avg_win / avg_loss_abs
    p = win_rate / 100.0 if win_rate > 1 else win_rate
    q = 1 - p

    if b <= 0:
        return {
            "error": "Invalid win/loss ratio",
            "recommendation": "Do not trade — expected value is negative"
        }

    f_star = (p * b - q) / b if b != 0 else 0.0
    f_star_pct = f_star * 100

    # Conservative: Half Kelly, Quarter Kelly
    half_kelly = f_star_pct / 2
    quarter_kelly = f_star_pct / 4

    # Cap at max allocation
    recommended = min(f_star_pct, max_allocation_pct)
    conservative = min(half_kelly, max_allocation_pct)

    return {
        "win_rate_pct": round(p * 100, 1),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(abs(avg_loss), 4),
        "win_loss_ratio": round(b, 2),
        "full_kelly_pct": round(f_star_pct, 2),
        "half_kelly_pct": round(half_kelly, 2),
        "quarter_kelly_pct": round(quarter_kelly, 2),
        "recommended_allocation_pct": round(conservative, 2),
        "aggressive_allocation_pct": round(recommended, 2),
        "interpretation": (
            f"Kelly suggests allocating {conservative:.1f}% of capital per trade "
            f"(conservative Half-Kelly). Full Kelly: {f_star_pct:.1f}%. "
            f"{'Positive edge — trade!' if f_star > 0 else 'Negative edge — avoid!'}"
        )
    }


# ==================== VOLATILITY REGIME ====================

def detect_volatility_regime(
    returns: List[float],
    window: int = 20,
    high_vol_threshold: float = 1.5,
) -> Dict:
    """
    Detect current volatility regime (Low / Normal / High / Extreme).

    Uses rolling volatility compared to long-term average.
    """
    if len(returns) < window:
        return {"error": f"Need at least {window} returns", "provided": len(returns)}

    long_term_vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
    recent_vol = statistics.stdev(returns[-window:]) if len(returns) >= window else long_term_vol

    if long_term_vol == 0:
        regime = "Unknown"
        ratio = 1.0
    else:
        ratio = recent_vol / long_term_vol

        if ratio < 0.5:
            regime = "🟢 Low Vol (Consolidation)"
        elif ratio < 1.0:
            regime = "🔵 Normal Vol"
        elif ratio < high_vol_threshold:
            regime = "🟡 High Vol (Trending)"
        elif ratio < 2.5:
            regime = "🟠 Very High Vol (Breakout)"
        else:
            regime = "🔴 Extreme Vol (Crisis/Black Swan)"

    return {
        "regime": regime,
        "vol_ratio": round(ratio, 2),
        "long_term_vol_pct": round(long_term_vol * 100, 4),
        "recent_vol_pct": round(recent_vol * 100, 4),
        "window": window,
        "interpretation": (
            f"Current volatility is {ratio:.1f}x the long-term average. "
            f"Regime: {regime}. "
            f"{'Use tighter stops' if ratio > 1.5 else 'Normal risk management applies' if ratio >= 0.5 else 'Consolidation — wait for breakout'}"
        )
    }


# ==================== MEAN REVERSION (Ornstein-Uhlenbeck) ====================

def mean_reversion_test(prices: List[float], window: int = 20) -> Dict:
    """
    Test for mean reversion using simplified Ornstein-Uhlenbeck process.

    Estimates half-life of mean reversion using linear regression on
    price changes vs price level.
    """
    if len(prices) < window + 10:
        return {"error": f"Need at least {window + 10} price points"}

    # Calculate moving average
    ma = [statistics.mean(prices[max(0, i - window):i + 1]) for i in range(len(prices))]
    spreads = [prices[i] - ma[i] for i in range(len(prices))]

    # Regression: spread_t = a + b * spread_{t-1} + error
    x = spreads[:-1]
    y = spreads[1:]

    if len(x) < 10:
        return {"error": "Not enough data for regression"}

    n = len(x)
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    x_var = sum((xi - x_mean) ** 2 for xi in x)

    if x_var == 0:
        return {"error": "Zero variance — price is flat"}

    b = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n)) / x_var
    a = y_mean - b * x_mean

    # Half-life = -ln(2) / b
    half_life = abs(-math.log(2) / b) if b != 0 else float('inf')

    # Current distance from mean
    current_spread = spreads[-1]
    spread_pct = (current_spread / prices[-1]) * 100 if prices[-1] != 0 else 0

    if half_life > 200:
        direction = "Strong Trend — not mean-reverting"
    elif half_life > 50:
        direction = "Weak mean reversion"
    elif half_life > 20:
        direction = "Moderate mean reversion"
    else:
        direction = "Strong mean reversion"

    return {
        "current_price": round(prices[-1], 4),
        "moving_average": round(ma[-1], 4),
        "spread_from_mean": round(current_spread, 4),
        "spread_pct": round(spread_pct, 3),
        "half_life_bars": round(half_life, 1),
        "ou_beta": round(b, 4),
        "regime": direction,
        "interpretation": (
            f"Mean reversion half-life: {half_life:.1f} periods. "
            f"{direction}. "
            f"Current spread: {spread_pct:+.3f}% from mean. "
            f"{'Potential reversal signal' if abs(spread_pct) > 2 else 'Near equilibrium'}"
        )
    }


# ==================== RATIOS (Sharpe, Sortino, Calmar) ====================

def calculate_ratios(returns: List[float], risk_free_rate: float = 0.04) -> Dict:
    """
    Calculate Sharpe, Sortino, and Calmar ratios.
    Assumes returns are already annualized compatible.
    """
    if len(returns) < 10:
        return {"error": "Need at least 10 returns"}

    mu = statistics.mean(returns)
    sigma = statistics.stdev(returns)
    rf_daily = risk_free_rate / 252

    # Sharpe Ratio
    excess = mu - rf_daily
    sharpe = excess / sigma * math.sqrt(252) if sigma > 0 else 0

    # Sortino Ratio (downside deviation only)
    downside_returns = [r - rf_daily for r in returns if r < rf_daily]
    if downside_returns and len(downside_returns) > 1:
        downside_dev = math.sqrt(sum((d) ** 2 for d in downside_returns) / len(downside_returns))
        sortino = excess * 252 / (downside_dev * math.sqrt(252)) if downside_dev > 0 else 0
    else:
        sortino = 0
        downside_dev = 0

    # Maximum Drawdown
    peak = returns[0]
    max_dd = 0
    for r in returns:
        if r > peak:
            peak = r
        dd = (peak - r) / (1 + peak) if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Calmar Ratio
    calmar = (mu * 252) / max_dd if max_dd > 0 else 0

    return {
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3) if sortino else None,
        "calmar_ratio": round(calmar, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "annualized_return_pct": round(mu * 252 * 100, 2),
        "annualized_vol_pct": round(sigma * math.sqrt(252) * 100, 2),
        "interpretation": (
            f"Sharpe: {sharpe:.2f} {'— Excellent!' if sharpe > 2 else '— Good' if sharpe > 1 else '— Below 1 — needs improvement'}. "
            f"Max DD: {max_dd*100:.1f}%. "
            f"{'Strong risk-adjusted returns' if sharpe > 1.5 else 'Acceptable' if sharpe > 0.8 else 'High risk for return'}"
        )
    }


# ==================== CORRELATION MATRIX ====================

def correlation_matrix(
    symbol_prices: Dict[str, List[float]],
    min_periods: int = 20
) -> Dict:
    """
    Build correlation matrix between multiple assets.

    Args:
        symbol_prices: Dict[symbol -> list of closing prices]
        min_periods: Minimum common periods required
    """
    symbols = list(symbol_prices.keys())
    if len(symbols) < 2:
        return {"error": "Need at least 2 symbols for correlation"}

    # Calculate returns for each symbol
    returns_map = {}
    for sym, prices in symbol_prices.items():
        rets = _simple_returns(prices) if len(prices) > 1 else []
        returns_map[sym] = rets

    # Find common length
    min_len = min(len(r) for r in returns_map.values())
    if min_len < min_periods:
        return {"error": f"Need {min_periods} common periods, found {min_len}"}

    # Truncate all to same length
    for sym in returns_map:
        returns_map[sym] = returns_map[sym][-min_len:]

    # Calculate correlations
    n = len(symbols)
    matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i, n):
            if i == j:
                matrix[i][j] = 1.0
            else:
                x = returns_map[symbols[i]]
                y = returns_map[symbols[j]]
                corr = _pearson_correlation(x, y)
                matrix[i][j] = round(corr, 4)
                matrix[j][i] = round(corr, 4)

    # Find strongest/weakest correlations
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((symbols[i], symbols[j], matrix[i][j]))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    strong_corr = [{"pair": f"{p[0]}/{p[1]}", "correlation": p[2]} for p in pairs[:5] if abs(p[2]) > 0.5]
    weak_corr = [{"pair": f"{p[0]}/{p[1]}", "correlation": p[2]} for p in pairs[-3:] if abs(p[2]) < 0.3]

    return {
        "symbols": symbols,
        "periods": min_len,
        "correlation_matrix": {symbols[i]: {symbols[j]: matrix[i][j] for j in range(n)} for i in range(n)},
        "strong_correlations": strong_corr,
        "weak_correlations": weak_corr,
        "average_correlation": round(sum(p[2] for p in pairs) / len(pairs), 4) if pairs else 0,
        "interpretation": (
            f"{len(strong_corr)} strong correlation pairs found. "
            f"{'Diversification benefits exist' if len(weak_corr) > 0 else 'Highly correlated — poor diversification'}"
        )
    }


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    x_std = statistics.stdev(x)
    y_std = statistics.stdev(y)
    if x_std == 0 or y_std == 0:
        return 0.0
    cov = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n)) / (n - 1)
    return cov / (x_std * y_std)


# ==================== COMPREHENSIVE QUANT REPORT ====================

def full_quant_report(
    symbol: str,
    prices: List[float],
    returns: Optional[List[float]] = None,
    position_value: float = 10000.0,
    win_rate: float = 0.55,
    avg_win: float = 0.02,
    avg_loss: float = 0.015,
) -> Dict:
    """
    Generate a comprehensive institutional quant report.

    Combines Monte Carlo, VaR, Kelly, Vol Regime, Mean Reversion,
    and Sharpe/Sortino/Calmar into one report.
    """
    if returns is None:
        returns = _simple_returns(prices)

    if len(prices) < 20:
        return {"error": "Need at least 20 price points for comprehensive analysis"}

    current_price = prices[-1]

    mc = monte_carlo_simulation(current_price, returns, num_simulations=500, forecast_days=30)
    var_result = calculate_var(returns, confidence=0.95, position_value=position_value, method="historical")
    kelly = kelly_criterion(win_rate, avg_win, avg_loss)
    vol_regime = detect_volatility_regime(returns)
    mean_rev = mean_reversion_test(prices)
    ratios = calculate_ratios(returns)

    # Aggregate score
    score = 50  # Neutral baseline

    if isinstance(mc, dict) and "forecast_mean" in mc:
        if mc["forecast_mean"] > current_price:
            score += 10
        else:
            score -= 10

    kelly_rec = kelly.get("recommended_allocation_pct", 0)
    if kelly_rec > 10:
        score += 10
    elif kelly_rec > 5:
        score += 5

    vol_ratio = vol_regime.get("vol_ratio", 1.0)
    if vol_ratio < 0.7:
        score += 5
    elif vol_ratio > 2.0:
        score -= 10

    sharpe = ratios.get("sharpe_ratio", 0)
    if sharpe > 1.5:
        score += 10
    elif sharpe > 0.8:
        score += 5

    score = max(0, min(100, score))

    if score >= 70:
        rating = "⭐⭐⭐⭐⭐ INSTITUTIONAL BUY"
    elif score >= 55:
        rating = "⭐⭐⭐⭐ STRONG"
    elif score >= 45:
        rating = "⭐⭐⭐ NEUTRAL"
    elif score >= 35:
        rating = "⭐⭐ WEAK"
    else:
        rating = "⭐ AVOID"

    return {
        "symbol": symbol,
        "current_price": round(current_price, 4),
        "quant_score": score,
        "rating": rating,
        "monte_carlo": mc,
        "value_at_risk": var_result,
        "kelly_criterion": kelly,
        "volatility_regime": vol_regime,
        "mean_reversion": mean_rev,
        "ratios": ratios,
    }


# ==================== FORMATTERS ====================

def format_quant_report(report: Dict) -> str:
    """Format quant report as Telegram Markdown message."""
    if "error" in report:
        return f"❌ {report['error']}"

    mc = report.get("monte_carlo", {})
    var_r = report.get("value_at_risk", {})
    kelly = report.get("kelly_criterion", {})
    vr = report.get("volatility_regime", {})
    mr = report.get("mean_reversion", {})
    ratios = report.get("ratios", {})

    msg = f"""🏦 *INSTITUTIONAL QUANT REPORT*
━━━━━━━━━━━━━━━━━━━━━━

📊 *{report['symbol']}* — ${report['current_price']:,.4f}

⚡ *Quant Score: {report['quant_score']}/100*
🎯 *Rating: {report['rating']}*

━━━━━━━━━━━━━━━━━━━━━━
🎲 *MONTE CARLO ({mc.get('simulations', '?')} sims, {mc.get('forecast_days', '?')}d)*
├ Forecast Mean: ${mc.get('forecast_mean', 0):,.4f}
├ Forecast Median: ${mc.get('forecast_median', 0):,.4f}
├ Std Dev: ${mc.get('forecast_std', 0):,.2f}
├ P(Up): {mc.get('probability_up', 0)}%
├ P(+5%): {mc.get('prob_+5pct', 0)}% | P(-5%): {mc.get('prob_-5pct', 0)}%
└ Range: ${mc.get('forecast_min', 0):,.2f} – ${mc.get('forecast_max', 0):,.2f}

{_format_confidence_intervals(mc.get('confidence_intervals', {}))}

━━━━━━━━━━━━━━━━━━━━━━
⚠️ *VALUE AT RISK ({var_r.get('confidence_pct', 0)}% confidence)*
├ Method: {var_r.get('method', '?')}
├ VaR: ${var_r.get('var_amount', 0):,.2f} ({var_r.get('var_pct', 0):.2f}%)
├ CVaR (Expected Shortfall): ${var_r.get('cvar_amount', 0):,.2f} ({var_r.get('cvar_pct', 0):.2f}%)
└ _{var_r.get('interpretation', '')}_

━━━━━━━━━━━━━━━━━━━━━━
💰 *KELLY POSITION SIZING*
├ Win Rate: {kelly.get('win_rate_pct', 0)}%
├ W/L Ratio: {kelly.get('win_loss_ratio', 0)}
├ Full Kelly: {kelly.get('full_kelly_pct', 0):.1f}%
├ Half Kelly (Rec): {kelly.get('recommended_allocation_pct', 0):.1f}%
└ _{kelly.get('interpretation', '')}_

━━━━━━━━━━━━━━━━━━━━━━
📈 *VOLATILITY REGIME*
├ {vr.get('regime', '?')}
├ Ratio: {vr.get('vol_ratio', 0)}x LT average
└ _{vr.get('interpretation', '')}_

━━━━━━━━━━━━━━━━━━━━━━
🔄 *MEAN REVERSION*
├ Current: ${mr.get('current_price', 0):,.4f}
├ MA: ${mr.get('moving_average', 0):,.4f}
├ Spread: {mr.get('spread_pct', 0):+.3f}%
├ Half-Life: {mr.get('half_life_bars', 0)} bars
└ {mr.get('regime', '?')}

━━━━━━━━━━━━━━━━━━━━━━
📐 *RISK-ADJUSTED RATIOS*
├ Sharpe: {ratios.get('sharpe_ratio', '?')}
├ Sortino: {ratios.get('sortino_ratio', '?')}
├ Calmar: {ratios.get('calmar_ratio', '?')}
├ Max DD: {ratios.get('max_drawdown_pct', 0)}%
└ Ann. Return: {ratios.get('annualized_return_pct', 0)}%

━━━━━━━━━━━━━━━━━━━━━━
🔮 _Powered by BlackMagicAI OMEGA Quant Engine_
"""

    return msg


def _format_confidence_intervals(ci: Dict) -> str:
    """Format confidence intervals for the report."""
    lines = []
    for cl, vals in sorted(ci.items(), key=lambda x: int(x[0]), reverse=True):
        lines.append(f"├ {cl}% CI: ${vals['lower']:,.2f} – ${vals['upper']:,.2f}")
    return "\n".join(lines) if lines else ""


def format_var_report(var_result: Dict, symbol: str) -> str:
    """Short VaR-only format."""
    msg = f"""⚠️ *VaR ANALYSIS — {symbol}*
━━━━━━━━━━━━━━━━━━━━━━
Confidence: {var_result.get('confidence_pct', 0)}%
Method: {var_result.get('method', '?')}
Position: ${var_result.get('position_value', 0):,.2f}

📊 VaR: ${var_result.get('var_amount', 0):,.2f} ({var_result.get('var_pct', 0):.2f}%)
📊 CVaR: ${var_result.get('cvar_amount', 0):,.2f} ({var_result.get('cvar_pct', 0):.2f}%)

_{var_result.get('interpretation', '')}_
"""
    return msg


def format_mc_summary(mc: Dict, symbol: str) -> str:
    """Short Monte Carlo summary."""
    msg = f"""🎲 *MONTE CARLO — {symbol}*
━━━━━━━━━━━━━━━━━━━━━━
Sims: {mc.get('simulations', '?')} | Horizon: {mc.get('forecast_days', '?')} days

📊 Forecast Mean: ${mc.get('forecast_mean', 0):,.4f}
📊 Range: ${mc.get('forecast_min', 0):,.2f} – ${mc.get('forecast_max', 0):,.2f}
📊 P(Up): {mc.get('probability_up', 0)}% | P(+5%): {mc.get('prob_+5pct', 0)}%
📊 P(Down): {mc.get('probability_down', 0)}% | P(-5%): {mc.get('prob_-5pct', 0)}%

{_format_confidence_intervals(mc.get('confidence_intervals', {}))}

Drift (Ann): {mc.get('drift_annual_pct', 0):.2f}% | Vol (Ann): {mc.get('volatility_annual_pct', 0):.2f}%
"""
    return msg
