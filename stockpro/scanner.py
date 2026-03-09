import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict
import concurrent.futures

def get_default_tickers():
    # A mix of popular, volatile, and penny stocks for demonstration
    return [
        "TSLA", "AAPL", "NVDA", "AMD", "AMZN", "MSFT", "GOOGL", "META",
        "GEVO", "PLTR", "SOFI", "LCID", "NIO", "MARA", "RIOT", "DKNG",
        "AMC", "GME", "MULN", "BBIG", "SNDL", "CEI", "IDEX", "XELA",
        "F", "T", "AAL", "CCL", "NCLH", "RCL", "BAC", "WFC", "C",
        "PFE", "MRNA", "BABA", "JD", "BIDU", "XPEV", "LI",
        "SNAP", "PINS", "ROKU", "SQ", "PYPL", "COIN", "HOOD"
    ]

def fetch_yahoo_direct(ticker):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return None
            
        data = r.json()
        if "chart" in data and "result" in data["chart"] and data["chart"]["result"]:
            res = data["chart"]["result"][0]
            if "timestamp" not in res or "indicators" not in res:
                return None
                
            quote = res["indicators"]["quote"][0]
            if "close" not in quote or not quote["close"]:
                return None
                
            closes = [c for c in quote["close"] if c is not None]
            volumes = [v for v in quote["volume"] if v is not None]
            
            if len(closes) < 2:
                return None
                
            return {
                "close": closes,
                "volume": volumes
            }
        return None
    except Exception:
        return None

def scan_market(tickers: List[str], min_price: float, max_price: float, min_volume: int, min_change: float) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    
    results = []
    
    def process_ticker(ticker):
        data = fetch_yahoo_direct(ticker)
        if not data:
            return None
            
        last_close = data["close"][-1]
        prev_close = data["close"][-2]
        volume = data["volume"][-1]
        
        change_pct = ((last_close - prev_close) / prev_close) * 100
        
        if min_price <= last_close <= max_price and volume >= min_volume and change_pct >= min_change:
            return {
                "الرمز": ticker,
                "السعر": round(last_close, 2),
                "التغيير %": round(change_pct, 2),
                "الحجم": volume,
                "الحجم (مليون)": f"{volume/1e6:.2f}M"
            }
        return None

    # Use ThreadPoolExecutor for faster scanning
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_ticker, t): t for t in tickers}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    return pd.DataFrame(results)
