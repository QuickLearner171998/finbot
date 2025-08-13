import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import numpy as np
import pandas as pd

from schemas import BacktestResult, Trade
from tools.prices import fetch_history


logger = logging.getLogger("finbot.tools.backtest")


@dataclass
class Strategy:
    name: str
    generate_signals: Callable[[pd.DataFrame], pd.Series]


def macd_strategy() -> Strategy:
    def gen(df: pd.DataFrame) -> pd.Series:
        close = df["Close"].astype(float)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        # Buy when MACD crosses above signal; sell when below
        state = (macd > signal).astype(int)
        return state.diff().fillna(0)  # +1 buy, -1 sell

    return Strategy(name="MACD", generate_signals=gen)


def run_backtest(symbol: str, start: Optional[str] = None, end: Optional[str] = None, strategy: Optional[Strategy] = None, initial_equity: float = 1.0, trade_size: float = 1.0) -> Optional[BacktestResult]:
    df = fetch_history(symbol, period="max")
    if df is None or len(df) < 60:
        logger.warning("Backtest: insufficient data for %s", symbol)
        return None
    if start:
        df = df[df.index >= start]
    if end:
        df = df[df.index <= end]
    if len(df) < 60:
        logger.warning("Backtest: insufficient filtered data for %s", symbol)
        return None

    strategy = strategy or macd_strategy()
    signals = strategy.generate_signals(df)

    equity = initial_equity
    position = 0.0
    trades: List[Trade] = []
    equity_curve = []

    for ts, row in df.iterrows():
        price = float(row["Close"])
        signal = float(signals.loc[ts]) if ts in signals.index else 0.0

        # Enter/exit on signals
        if signal > 0.5 and position == 0.0:
            # Buy
            size = trade_size
            position = size
            trades.append(Trade(date=str(ts.date()), symbol=symbol, side="buy", price=price, size=size))
        elif signal < -0.5 and position > 0.0:
            # Sell
            trades.append(Trade(date=str(ts.date()), symbol=symbol, side="sell", price=price, size=position))
            position = 0.0

        # Daily MTM equity
        equity_curve.append(equity * (1 + position * 0))  # simple, no pnl until sell

    # Compute simple PnL as difference between last sell and buy prices times size
    # For a more accurate backtest, track PnL throughout, but we keep it simple here
    pnl = 0.0
    last_buy_price = None
    for t in trades:
        if t.side == "buy":
            last_buy_price = t.price
        elif t.side == "sell" and last_buy_price is not None:
            pnl += (t.price - last_buy_price) / last_buy_price * t.size
            last_buy_price = None

    cum_return = pnl
    arr = cum_return  # not annualized; placeholder for simplicity
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252) if not returns.empty else 0.0
    running_max = pd.Series(equity_curve).cummax()
    dd = (pd.Series(equity_curve) / running_max - 1.0).min() if len(equity_curve) > 0 else 0.0

    return BacktestResult(
        symbol=symbol,
        start=str(df.index[0].date()),
        end=str(df.index[-1].date()),
        strategy=strategy.name,
        cumulative_return_pct=round(cum_return * 100, 2),
        annual_return_pct=round(arr * 100, 2),
        sharpe_ratio=float(sharpe),
        max_drawdown_pct=round(dd * 100, 2),
        num_trades=len(trades),
        trades=trades,
    )


