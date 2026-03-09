from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import requests
import pandas as pd
import time


def _map_interval_to_polygon(interval: str) -> tuple[int, str]:
    if interval in ["1m", "1min"]:
        return 1, "minute"
    if interval in ["5m", "5min"]:
        return 5, "minute"
    if interval in ["15m", "15min"]:
        return 15, "minute"
    if interval in ["1h", "60m"]:
        return 1, "hour"
    return 1, "minute"


def _map_interval_to_alpaca(interval: str) -> str:
    if interval in ["1m", "1min"]:
        return "1Min"
    if interval in ["5m", "5min"]:
        return "5Min"
    if interval in ["15m", "15min"]:
        return "15Min"
    if interval in ["1h", "60m"]:
        return "1Hour"
    return "1Min"


def fetch_intraday_polygon(ticker: str, interval: str = "1m", lookback_minutes: int = 300, api_key: Optional[str] = None) -> pd.DataFrame:
    key = api_key or os.environ.get("POLYGON_API_KEY", "")
    if not key:
        raise RuntimeError("Missing POLYGON_API_KEY")
    mult, span = _map_interval_to_polygon(interval)
    to_ts = datetime.now(timezone.utc)
    frm = to_ts - timedelta(minutes=lookback_minutes if "minute" in span else 60 * (lookback_minutes // 60 or 5))
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{mult}/{span}/{frm.isoformat()}/{to_ts.isoformat()}"
    params = {"apiKey": key, "sort": "asc", "limit": 50000}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert(None)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df["adj_close"] = df["close"]
    df = df[["date", "open", "high", "low", "close", "adj_close", "volume"]]
    return df


def fetch_intraday_alpaca(ticker: str, interval: str = "1m", limit: int = 1000, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> pd.DataFrame:
    key = api_key or os.environ.get("ALPACA_API_KEY_ID", "")
    sec = api_secret or os.environ.get("ALPACA_API_SECRET_KEY", "")
    if not key or not sec:
        raise RuntimeError("Missing Alpaca API credentials")
    tf = _map_interval_to_alpaca(interval)
    url = "https://data.alpaca.markets/v2/stocks/bars"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}
    params = {"symbols": ticker, "timeframe": tf, "limit": limit, "adjustment": "raw", "feed": "iex"}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    bars = (data.get("bars") or {}).get(ticker, [])
    if not bars:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])
    df = pd.DataFrame(bars)
    df["date"] = pd.to_datetime(df["t"]).dt.tz_localize(None, nonexistent="shift_forward", ambiguous="NaT")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df["adj_close"] = df["close"]
    df = df[["date", "open", "high", "low", "close", "adj_close", "volume"]]
    return df


def fetch_intraday(provider: str, ticker: str, interval: str = "1m", lookback_minutes: int = 300) -> pd.DataFrame:
    pr = provider.lower()
    if pr == "polygon":
        return fetch_intraday_polygon(ticker, interval=interval, lookback_minutes=lookback_minutes)
    if pr == "alpaca":
        return fetch_intraday_alpaca(ticker, interval=interval, limit=min(1000, lookback_minutes))
    if pr == "alpha vantage" or pr == "alphavantage":
        key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        if not key:
            raise RuntimeError("Missing ALPHAVANTAGE_API_KEY")
        ivmap = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "60min", "60m": "60min"}
        iv = ivmap.get(interval, "1min")
        url = "https://www.alphavantage.co/query"
        params = {"function": "TIME_SERIES_INTRADAY", "symbol": ticker, "interval": iv, "outputsize": "compact", "datatype": "json", "apikey": key}
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        k = f"Time Series ({iv})"
        ts = data.get(k, {})
        if not ts:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])
        rows = []
        for ts_str, v in ts.items():
            rows.append({
                "date": pd.to_datetime(ts_str),
                "open": float(v.get("1. open", 0)),
                "high": float(v.get("2. high", 0)),
                "low": float(v.get("3. low", 0)),
                "close": float(v.get("4. close", 0)),
                "adj_close": float(v.get("4. close", 0)),
                "volume": float(v.get("5. volume", 0)),
            })
        df = pd.DataFrame(rows).sort_values("date")
        return df
    if pr == "finnhub":
        key = os.environ.get("FINNHUB_API_KEY", "")
        if not key:
            raise RuntimeError("Missing FINNHUB_API_KEY")
        resmap = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "60m": 60}
        res = resmap.get(interval, 1)
        now = int(time.time())
        frm = now - lookback_minutes * 60
        url = "https://finnhub.io/api/v1/stock/candle"
        params = {"symbol": ticker, "resolution": res, "from": frm, "to": now, "token": key}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("s") != "ok":
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume"])
        df = pd.DataFrame({"date": pd.to_datetime(data["t"], unit="s"), "open": data["o"], "high": data["h"], "low": data["l"], "close": data["c"], "volume": data["v"]})
        df["adj_close"] = df["close"]
        df = df.sort_values("date")
        return df
    raise ValueError("Unsupported provider")
