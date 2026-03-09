import pandas as pd
import numpy as np
from typing import Optional, Dict


def sma(series: pd.Series, window: int) -> pd.Series:
    s = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
    return s.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    s = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
    return s.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    s = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
    delta = s.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=s.index).ewm(alpha=1 / window, adjust=False).mean()
    roll_down = pd.Series(down, index=s.index).ewm(alpha=1 / window, adjust=False).mean()
    rs = roll_up / roll_down
    out = 100.0 - (100.0 / (1.0 + rs))
    return out


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    s = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd(macd_line, fast=signal, slow=signal, signal=signal) if False else macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bbands(series: pd.Series, window: int = 20, n_std: float = 2.0) -> pd.DataFrame:
    s = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
    m = sma(s, window)
    sd = s.rolling(window=window, min_periods=window).std()
    upper = m + n_std * sd
    lower = m - n_std * sd
    pctb = (s - lower) / (upper - lower)
    width = (upper - lower) / m
    return pd.DataFrame({"bb_mid": m, "bb_upper": upper, "bb_lower": lower, "bb_pctb": pctb, "bb_width": width})


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    h = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
    l = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    prev_close = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.DataFrame:
    h = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
    l = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=h.index).ewm(alpha=1 / window, adjust=False).mean()
    minus_dm = pd.Series(minus_dm, index=h.index).ewm(alpha=1 / window, adjust=False).mean()
    a = atr(h, l, c, window)
    plus_di = 100 * (plus_dm / a.replace(0, np.nan))
    minus_di = 100 * (minus_dm / a.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_series = dx.ewm(alpha=1 / window, adjust=False).mean()
    return pd.DataFrame({"plus_di": plus_di, "minus_di": minus_di, "adx": adx_series})


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    h = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
    l = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    ll = l.rolling(k_period, min_periods=k_period).min()
    hh = h.rolling(k_period, min_periods=k_period).max()
    k = 100 * (c - ll) / (hh - ll)
    d = k.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    h = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
    l = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    v = volume.iloc[:, 0] if isinstance(volume, pd.DataFrame) else volume
    tp = (h + l + c) / 3.0
    pv = (tp * v).cumsum()
    vv = v.cumsum().replace(0, np.nan)
    return pv / vv


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    v = volume.iloc[:, 0] if isinstance(volume, pd.DataFrame) else volume
    sign = np.sign(c.diff())
    sign = np.where(sign > 0, 1, np.where(sign < 0, -1, 0))
    return pd.Series(sign, index=c.index).fillna(0).astype(int).mul(v).cumsum()


def keltner(high: pd.Series, low: pd.Series, close: pd.Series, window_ema: int = 20, window_atr: int = 10, mult: float = 2.0) -> pd.DataFrame:
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    mid = ema(c, window_ema)
    a = atr(high, low, close, window_atr)
    upper = mid + mult * a
    lower = mid - mult * a
    return pd.DataFrame({"kel_mid": mid, "kel_upper": upper, "kel_lower": lower})


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    h = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
    l = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
    c = close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
    conv = (h.rolling(9, min_periods=9).max() + l.rolling(9, min_periods=9).min()) / 2.0
    base = (h.rolling(26, min_periods=26).max() + l.rolling(26, min_periods=26).min()) / 2.0
    span_a = ((conv + base) / 2.0).shift(-26)
    span_b = ((h.rolling(52, min_periods=52).max() + l.rolling(52, min_periods=52).min()) / 2.0).shift(-26)
    chikou = c.shift(26)
    return pd.DataFrame({"ichi_conv": conv, "ichi_base": base, "ichi_span_a": span_a, "ichi_span_b": span_b, "ichi_chikou": chikou})


def add_indicators(df: pd.DataFrame, params: Optional[Dict] = None) -> pd.DataFrame:
    p = params or {}
    sma_short = int(p.get("sma_short", 20))
    sma_long = int(p.get("sma_long", 50))
    ema_win = int(p.get("ema_win", 20))
    rsi_win = int(p.get("rsi_win", 14))
    macd_fast = int(p.get("macd_fast", 12))
    macd_slow = int(p.get("macd_slow", 26))
    macd_signal_win = int(p.get("macd_signal", 9))
    bb_win = int(p.get("bb_win", 20))
    bb_std = float(p.get("bb_std", 2.0))
    atr_win = int(p.get("atr_win", 14))
    adx_win = int(p.get("adx_win", 14))
    stoch_k = int(p.get("stoch_k", 14))
    stoch_d = int(p.get("stoch_d", 3))
    kel_ema = int(p.get("kel_ema", 20))
    kel_atr = int(p.get("kel_atr", 10))
    kel_mult = float(p.get("kel_mult", 2.0))
    df = df.copy()
    close = df["close"]
    df[f"sma_{sma_short}"] = sma(close, sma_short)
    df[f"sma_{sma_long}"] = sma(close, sma_long)
    df[f"ema_{ema_win}"] = ema(close, ema_win)
    df[f"rsi_{rsi_win}"] = rsi(close, rsi_win)
    macd_df = macd(close, macd_fast, macd_slow, macd_signal_win)
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["signal"]
    df["macd_hist"] = macd_df["hist"]
    bb = bbands(close, bb_win, bb_std)
    df["bb_mid"] = bb["bb_mid"]
    df["bb_upper"] = bb["bb_upper"]
    df["bb_lower"] = bb["bb_lower"]
    df["bb_pctb"] = bb["bb_pctb"]
    df["bb_width"] = bb["bb_width"]
    df[f"atr_{atr_win}"] = atr(df["high"], df["low"], close, atr_win)
    adx_df = adx(df["high"], df["low"], close, adx_win)
    df["plus_di"] = adx_df["plus_di"]
    df["minus_di"] = adx_df["minus_di"]
    df[f"adx_{adx_win}"] = adx_df["adx"]
    stoch_df = stochastic(df["high"], df["low"], close, stoch_k, stoch_d)
    df["stoch_k"] = stoch_df["stoch_k"]
    df["stoch_d"] = stoch_df["stoch_d"]
    df["vwap"] = vwap(df["high"], df["low"], close, df["volume"])
    df["obv"] = obv(close, df["volume"])
    
    # EMAs for specific strategy (EMA 5/20)
    df["ema_5"] = ema(close, 5)
    df["ema_20"] = ema(close, 20)
    
    kel = keltner(df["high"], df["low"], close, kel_ema, kel_atr, kel_mult)
    df["kel_mid"] = kel["kel_mid"]
    df["kel_upper"] = kel["kel_upper"]
    df["kel_lower"] = kel["kel_lower"]
    ichi = ichimoku(df["high"], df["low"], close)
    df["ichi_conv"] = ichi["ichi_conv"]
    df["ichi_base"] = ichi["ichi_base"]
    df["ichi_span_a"] = ichi["ichi_span_a"]
    df["ichi_span_b"] = ichi["ichi_span_b"]
    df["ichi_chikou"] = ichi["ichi_chikou"]
    return df
