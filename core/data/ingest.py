"""
Yahoo Finance data ingestion for StockPro
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Optional

def fetch_prices_yahoo(
    symbol: str, 
    period: str = "1mo", 
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch historical prices from Yahoo Finance using direct API calls
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        start: Start date in YYYY-MM-DD format (optional)
        end: End date in YYYY-MM-DD format (optional)
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        # Construct the Yahoo Finance API URL
        base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"
        
        params = {
            'symbol': symbol,
            'period1': '',
            'period2': '',
            'interval': interval,
            'includePrePost': 'false',
            'events': 'div,splits'
        }
        
        # Handle date ranges
        if start and end:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            params['period1'] = str(int(start_dt.timestamp()))
            params['period2'] = str(int(end_dt.timestamp()))
        else:
            # Use period parameter
            params['range'] = period
        
        url = f"{base_url}{symbol}"
        
        # Make the request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse the response
        if 'chart' not in data or 'result' not in data['chart']:
            raise ValueError("Invalid response format from Yahoo Finance")
        
        result = data['chart']['result'][0]
        
        # Extract timestamps and convert to datetime
        timestamps = result['timestamp']
        dates = [datetime.fromtimestamp(ts) for ts in timestamps]
        
        # Extract OHLCV data
        quote = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'date': dates,
            'open': quote['open'],
            'high': quote['high'],
            'low': quote['low'],
            'close': quote['close'],
            'volume': quote['volume']
        })
        
        # Handle dividends and splits if available
        if 'events' in result:
            if 'dividends' in result['events']:
                df['Dividend'] = 0.0
            if 'splits' in result['events']:
                df['Split'] = 1.0
        
        df.set_index('date', inplace=True)
        df.dropna(inplace=True)
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching data for {symbol}: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error parsing data for {symbol}: {e}")
        return pd.DataFrame()

def fetch_and_save(symbol: str, filename: str, **kwargs):
    """
    Fetch data and save to CSV file
    """
    df = fetch_prices_yahoo(symbol, **kwargs)
    if not df.empty:
        df.to_csv(filename)
        print(f"Saved {len(df)} rows to {filename}")
    return df

def get_multiple_symbols(symbols: List[str], **kwargs) -> dict:
    """
    Fetch data for multiple symbols
    """
    results = {}
    for symbol in symbols:
        df = fetch_prices_yahoo(symbol, **kwargs)
        if not df.empty:
            results[symbol] = df
    return results