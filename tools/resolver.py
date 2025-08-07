import logging
from typing import List, Optional
import re

import yfinance as yf

logger = logging.getLogger("finbot.tools.resolver")


def normalize_company_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def guess_india_symbols(name: str) -> List[str]:
    # Try both NSE (.NS) and BSE (.BO); if name is already a symbol, append suffixes
    base = re.sub(r"\s+", "", name.upper())
    candidates = [f"{base}.NS", f"{base}.BO"]
    return candidates


def resolve_to_ticker(name: str) -> Optional[str]:
    """Resolve a company name to a Yahoo Finance ticker for India (NSE/BSE).
    Strategy:
      1) Try direct symbol with .NS / .BO
      2) If fails, try yfinance Ticker with common aliases (e.g., removing spaces)
    Returns first symbol with valid recent price data, else None.
    """
    norm = normalize_company_name(name)
    trial_symbols: List[str] = []

    # 1) Try direct uppercase symbol with suffix
    trial_symbols.extend(guess_india_symbols(name))

    # 2) Try removing words like limited, ltd, incorporated, etc.
    simplified = re.sub(r"\b(limited|ltd|inc|plc|corp|corporation)\b", "", norm).strip()
    if simplified and simplified != norm:
        trial_symbols.extend(guess_india_symbols(simplified))

    # 3) Try no-space variant
    compact = re.sub(r"\s+", "", simplified or norm).upper()
    trial_symbols.extend(guess_india_symbols(compact))

    logger.debug("Resolver: trials for '%s' -> %s", name, trial_symbols)
    seen = set()
    for sym in trial_symbols:
        if sym in seen:
            continue
        seen.add(sym)
        try:
            hist = yf.Ticker(sym).history(period="1mo")
            if hist is not None and len(hist) > 0:
                logger.debug("Resolver: selected symbol %s", sym)
                return sym
        except Exception as e:
            logger.debug("Resolver trial failed for %s: %s", sym, e)
    logger.debug("Resolver: no valid symbol found for '%s'", name)
    return None
