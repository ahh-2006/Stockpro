import pandas as pd


def cross_over(a: pd.Series, b: pd.Series) -> pd.Series:
    s1 = a.iloc[:, 0] if isinstance(a, pd.DataFrame) else a
    s2 = b.iloc[:, 0] if isinstance(b, pd.DataFrame) else b
    prev = s1.shift(1) <= s2.shift(1)
    curr = s1 > s2
    return prev & curr


def cross_under(a: pd.Series, b: pd.Series) -> pd.Series:
    s1 = a.iloc[:, 0] if isinstance(a, pd.DataFrame) else a
    s2 = b.iloc[:, 0] if isinstance(b, pd.DataFrame) else b
    prev = s1.shift(1) >= s2.shift(1)
    curr = s1 < s2
    return prev & curr


def basic_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sig_ma50_up"] = cross_over(df["close"], df["sma_50"]).astype(int)
    df["sig_ma50_down"] = (-cross_under(df["close"], df["sma_50"]).astype(int))
    df["sig_rsi_oversold"] = (df["rsi_14"] < 30).astype(int)
    df["sig_rsi_overbought"] = (-(df["rsi_14"] > 70).astype(int))
    df["signal"] = (
        df["sig_ma50_up"]
        + df["sig_ma50_down"]
        + df["sig_rsi_oversold"]
        + df["sig_rsi_overbought"]
    )
    return df
