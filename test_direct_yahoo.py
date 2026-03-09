import requests
import pandas as pd
from datetime import datetime

def fetch_yahoo_direct(ticker, interval="1d", range="5d"):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range}"
    
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        
        if "chart" in data and "result" in data["chart"] and data["chart"]["result"]:
            res = data["chart"]["result"][0]
            timestamp = res["timestamp"]
            quote = res["indicators"]["quote"][0]
            
            df = pd.DataFrame({
                "date": [datetime.fromtimestamp(ts) for ts in timestamp],
                "Open": quote["open"],
                "High": quote["high"],
                "Low": quote["low"],
                "Close": quote["close"],
                "Volume": quote["volume"]
            })
            return df
        else:
            print(f"No data for {ticker}: {data}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()

# Test it
df = fetch_yahoo_direct("AAPL")
print(df.head())
print(df.tail())
