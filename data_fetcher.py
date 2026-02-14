"""
Market data fetching with yfinance (free, no API key).
Caches results for 5–10 minutes to avoid rate limits and speed up repeated requests.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Predefined stocks: Finnish + global (tickers that work with yfinance)
DEFAULT_SYMBOLS = [
    "NOK",       # Nokia
    "NDA-FI.HE", # Nordea (Helsinki)
    "FORTUM.HE", # Fortum
    "UPM.HE",    # UPM
    "KONE.HE",   # Kone
    "AAPL",      # Apple
    "GOOGL",     # Google
    "MSFT",      # Microsoft
    "AMZN",      # Amazon
    "TSLA",      # Tesla
]

# Predefined stock lists for quick selection (id -> list of symbols)
PREDEFINED_LISTS: dict[str, list[str]] = {
    "finnish": ["NOK", "NDA-FI.HE", "FORTUM.HE", "UPM.HE", "KONE.HE", "KESKOB.HE"],
    "tech_giants": ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA"],
    "eu_banks": ["NDA-FI.HE", "DBK.DE", "BNP.PA", "SAN.MC", "INGA.AS", "GLE.PA"],
    "all": DEFAULT_SYMBOLS,
}

CACHE_TTL_SECONDS = 300  # 5 minutes
HISTORY_DAYS = 60
ANNUALIZATION = 252


@dataclass
class AssetData:
    """Data for one asset: prices and derived expected return & volatility."""
    symbol: str
    name: str
    current_price: float
    previous_close: float
    day_change: float
    day_change_percent: float
    expected_return: float  # annualized
    volatility: float       # annualized std
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "currentPrice": self.current_price,
            "previousClose": self.previous_close,
            "dayChange": self.day_change,
            "dayChangePercent": self.day_change_percent,
            "expectedReturn": self.expected_return,
            "volatility": self.volatility,
            "lastUpdated": self.last_updated,
        }


def _calculate_returns_and_volatility(prices: pd.Series) -> tuple[float, float]:
    """Annualized expected return and volatility from daily close prices."""
    if prices is None or len(prices) < 2:
        return 0.0, 0.01
    returns = prices.pct_change().dropna()
    if len(returns) == 0:
        return 0.0, 0.01
    mean_daily = returns.mean()
    std_daily = returns.std()
    if std_daily == 0 or np.isnan(std_daily):
        std_daily = 0.01
    annual_return = mean_daily * ANNUALIZATION
    annual_vol = std_daily * np.sqrt(ANNUALIZATION)
    return float(annual_return), float(annual_vol)


class DataFetcher:
    """Fetches and caches market data using yfinance."""

    def __init__(self, cache_ttl_seconds: int = CACHE_TTL_SECONDS):
        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[AssetData, float]] = {}
        self._cov_cache: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}  # key -> (mu, sigma, ts)

    def _is_stale(self, cached_at: float) -> bool:
        return (time.time() - cached_at) > self.cache_ttl

    def get_asset(self, symbol: str, use_cache: bool = True) -> Optional[AssetData]:
        """Fetch one asset; return from cache if fresh."""
        if use_cache and symbol in self._cache:
            data, cached_at = self._cache[symbol]
            if not self._is_stale(cached_at):
                return data
        try:
            data = self._fetch_one(symbol)
            if data:
                self._cache[symbol] = (data, time.time())
            return data
        except Exception as e:
            logger.exception("Failed to fetch %s: %s", symbol, e)
            return self._fallback_asset(symbol)

    def _fetch_one(self, symbol: str) -> Optional[AssetData]:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period=f"{HISTORY_DAYS}d")
        if hist is None or hist.empty:
            return self._fallback_asset(symbol)
        closes = hist["Close"]
        current = float(closes.iloc[-1]) if len(closes) > 0 else 0.0
        prev = float(closes.iloc[-2]) if len(closes) > 1 else current
        day_change = current - prev
        day_change_pct = (day_change / prev * 100) if prev else 0.0
        exp_ret, vol = _calculate_returns_and_volatility(closes)
        name = info.get("shortName") or info.get("longName") or symbol
        return AssetData(
            symbol=symbol,
            name=str(name)[:80],
            current_price=current,
            previous_close=prev,
            day_change=day_change,
            day_change_percent=day_change_pct,
            expected_return=exp_ret,
            volatility=max(vol, 0.01),
        )

    def _fallback_asset(self, symbol: str) -> AssetData:
        """Return synthetic data when API fails so the app still runs."""
        return AssetData(
            symbol=symbol,
            name=symbol,
            current_price=100.0,
            previous_close=99.0,
            day_change=1.0,
            day_change_percent=1.01,
            expected_return=0.05,
            volatility=0.15,
        )

    def get_assets(self, symbols: list[str], use_cache: bool = True) -> list[AssetData]:
        """Fetch multiple assets; preserves order."""
        out = []
        for s in symbols:
            a = self.get_asset(s, use_cache=use_cache)
            if a:
                out.append(a)
        return out

    def get_expected_returns_and_covariance(
        self, symbols: list[str], use_cache: bool = True
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Expected return vector (mu) and covariance matrix (sigma) for portfolio optimization.
        Uses historical daily returns annualized.
        """
        cache_key = ",".join(sorted(symbols))
        if use_cache and cache_key in self._cov_cache:
            mu, sigma, ts = self._cov_cache[cache_key]
            if not self._is_stale(ts):
                return mu, sigma
        try:
            import yfinance as yf
            dfs = []
            for sym in symbols:
                t = yf.Ticker(sym)
                h = t.history(period=f"{HISTORY_DAYS}d")
                if h is not None and not h.empty and "Close" in h.columns:
                    dfs.append(h["Close"].rename(sym))
            if not dfs:
                raise ValueError("No history")
            prices = pd.concat(dfs, axis=1).dropna(how="all").ffill().bfill()
            if len(prices) < 2:
                raise ValueError("Not enough history")
            returns = prices.pct_change().dropna()
            mu = returns.mean().values * ANNUALIZATION
            sigma = returns.cov().values * ANNUALIZATION
            mu = np.asarray(mu, dtype=float)
            sigma = np.asarray(sigma, dtype=float)
            # Ensure sigma is positive semi-definite
            if sigma.shape[0] > 0:
                min_eig = np.min(np.linalg.eigvalsh(sigma))
                if min_eig < 1e-8:
                    sigma += (1e-8 - min_eig) * np.eye(sigma.shape[0])
            self._cov_cache[cache_key] = (mu, sigma, time.time())
            return mu, sigma
        except Exception as e:
            logger.exception("Covariance computation failed: %s", e)
            n = len(symbols)
            mu = np.zeros(n)
            sigma = np.eye(n) * 0.04
            return mu, sigma

    def get_historical_returns(
        self, symbols: list[str], days: int = 90
    ) -> Optional[dict]:
        """
        Fetch historical daily close prices. Returns dates, daily returns per symbol,
        and cumulative returns per symbol (for charts).
        """
        try:
            import yfinance as yf
            period = f"{min(days, 365)}d"
            dfs = []
            for sym in symbols:
                t = yf.Ticker(sym)
                h = t.history(period=period)
                if h is not None and not h.empty and "Close" in h.columns:
                    dfs.append(h["Close"].rename(sym))
            if not dfs:
                return None
            prices = pd.concat(dfs, axis=1).dropna(how="all").ffill().bfill()
            if len(prices) < 5:
                return None
            returns = prices.pct_change().dropna()
            dates = returns.index.strftime("%Y-%m-%d").tolist()
            daily: dict[str, list[float]] = {}
            cum_series: dict[str, list[float]] = {}
            for sym in returns.columns:
                dr = returns[sym].values
                daily[sym] = dr.tolist()
                cum_series[sym] = ((1 + pd.Series(dr)).cumprod().values - 1.0).tolist()
            return {
                "dates": dates,
                "daily": daily,
                "series": cum_series,
                "symbols": list(returns.columns),
            }
        except Exception as e:
            logger.exception("Historical returns failed: %s", e)
            return None

    def get_benchmark_series(self, days: int = 90) -> Optional[dict]:
        """S&P 500 cumulative returns for benchmark (^GSPC)."""
        return self.get_historical_returns(["^GSPC"], days=days)

    def get_backtest_curves(
        self,
        symbols: list[str],
        quantum_indices: list[int],
        classical_indices: list[int],
        days: int = 90,
    ) -> Optional[dict]:
        """
        Compute cumulative return curves for quantum portfolio, classical portfolio,
        and equal-weight of selected symbols, plus S&P 500 benchmark.
        Returns { dates, quantum, classical, equalWeight, benchmark } (each list of floats).
        """
        hist = self.get_historical_returns(symbols, days=days)
        if not hist or not hist.get("daily"):
            return None
        dates = hist["dates"]
        daily = hist["daily"]
        sym_list = hist["symbols"]
        n = len(sym_list)
        T = len(dates)
        if n == 0 or T == 0:
            return None

        def portfolio_cumulative(indices: list[int]) -> list[float]:
            if not indices:
                return [0.0] * T
            valid = [i for i in indices if i < n and sym_list[i] in daily]
            if not valid:
                return [0.0] * T
            arr = np.array([daily[sym_list[i]] for i in valid])
            min_len = min(len(a) for a in arr)
            arr = np.array([a[:min_len] for a in arr])
            port_daily = np.mean(arr, axis=0)
            cum = np.cumprod(1.0 + port_daily) - 1.0
            out = cum.tolist()
            if len(out) < T:
                out.extend([out[-1]] * (T - len(out)))
            return out[:T]

        quantum_curve = portfolio_cumulative(quantum_indices)
        classical_curve = portfolio_cumulative(classical_indices)
        equal_curve = portfolio_cumulative(list(range(n)))

        bench = self.get_benchmark_series(days=days)
        benchmark_curve = [0.0] * T
        if bench and "series" in bench and "^GSPC" in bench["series"]:
            b = bench["series"]["^GSPC"]
            benchmark_curve = b[:T] if len(b) >= T else b + [b[-1]] * (T - len(b))

        return {
            "dates": dates,
            "quantum": quantum_curve,
            "classical": classical_curve,
            "equalWeight": equal_curve,
            "benchmark": benchmark_curve,
        }
