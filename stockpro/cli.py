import os
from datetime import datetime
from typing import Optional, List
import click
import pandas as pd
from stockpro.data.ingest import fetch_and_save, fetch_prices_yahoo
from stockpro.indicators.tech import add_indicators
from stockpro.signals.rules import basic_signals


@click.group()
def cli():
    pass


@cli.command()
@click.option("--tickers", required=False, help="Comma-separated tickers, e.g., AAPL,MSFT,TSLA")
@click.option("--tickers-file", required=False, type=click.Path(exists=True, dir_okay=False), help="Path to a text file with one ticker per line")
@click.option("--start", default=None, help="YYYY-MM-DD")
@click.option("--end", default=None, help="YYYY-MM-DD")
@click.option("--interval", default="1d", type=click.Choice(["1d", "1h", "30m", "15m", "5m", "1m"]))
@click.option("--out", default="data", help="Output directory")
def ingest(tickers: Optional[str], tickers_file: Optional[str], start: Optional[str], end: Optional[str], interval: str, out: str):
    tickers_list: List[str] = []
    if tickers_file:
        with open(tickers_file, "r", encoding="utf-8") as f:
            tickers_list = [ln.strip() for ln in f if ln.strip()]
    elif tickers:
        tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
    else:
        raise click.UsageError("Provide --tickers or --tickers-file")
    saved = fetch_and_save(tickers_list, out, start=start, end=end, interval=interval)
    if saved:
        click.echo("\n".join(saved))
    else:
        click.echo("No files saved")


@cli.command()
@click.option("--ticker", required=True, help="Single ticker, e.g., AAPL")
@click.option("--start", default=None, help="YYYY-MM-DD")
@click.option("--end", default=None, help="YYYY-MM-DD")
@click.option("--interval", default="1d", type=click.Choice(["1d", "1h", "30m", "15m", "5m", "1m"]))
@click.option("--out", default="data", help="Output directory")
def analyze(ticker: str, start: Optional[str], end: Optional[str], interval: str, out: str):
    df = fetch_prices_yahoo(ticker, start=start, end=end, interval=interval)
    if df.empty:
        click.echo("No data")
        return
    df = add_indicators(df)
    df = basic_signals(df)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{ticker}_{interval}_indicators_signals.csv")
    df.to_csv(path, index=False)
    click.echo(path)
    click.echo(df.tail(5).to_string(index=False))


@cli.command()
@click.option("--tickers", required=False, help="Comma-separated tickers")
@click.option("--tickers-file", required=False, type=click.Path(exists=True, dir_okay=False))
@click.option("--start", default=None, help="YYYY-MM-DD")
@click.option("--end", default=None, help="YYYY-MM-DD")
@click.option("--interval", default="1d", type=click.Choice(["1d", "1h", "30m", "15m", "5m", "1m"]))
@click.option("--out", default="data", help="Output directory")
@click.option("--top", default=20, type=int, help="Number of top results to show")
def scan(tickers: Optional[str], tickers_file: Optional[str], start: Optional[str], end: Optional[str], interval: str, out: str, top: int):
    tickers_list: List[str] = []
    if tickers_file:
        with open(tickers_file, "r", encoding="utf-8") as f:
            tickers_list = [ln.strip() for ln in f if ln.strip()]
    elif tickers:
        tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
    else:
        raise click.UsageError("Provide --tickers or --tickers-file")
    rows = []
    for t in tickers_list:
        try:
            df = fetch_prices_yahoo(t, start=start, end=end, interval=interval)
            if df.empty:
                continue
            df = basic_signals(add_indicators(df))
            last = df.iloc[-1]
            rows.append({
                "ticker": t,
                "date": str(last["date"]),
                "close": float(last["close"]),
                "volume": float(last.get("volume", 0) or 0),
                "rsi_14": float(last.get("rsi_14", float("nan"))),
                "sma_50": float(last.get("sma_50", float("nan"))),
                "above_ma50": bool(last.get("close") > last.get("sma_50")) if pd.notnull(last.get("sma_50")) else False,
                "signal": int(last.get("signal", 0)),
                "sig_ma50_up": int(last.get("sig_ma50_up", 0)),
                "sig_rsi_oversold": int(last.get("sig_rsi_oversold", 0)),
            })
        except Exception as e:
            click.echo(f"Error processing {t}: {e}", err=True)
            continue
    if not rows:
        click.echo("No results")
        return
    res = pd.DataFrame(rows).sort_values(["signal", "volume"], ascending=[False, False])
    os.makedirs(out, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d")
    path = os.path.join(out, f"scan_{interval}_{stamp}.csv")
    res.to_csv(path, index=False)
    click.echo(path)
    click.echo(res.head(top).to_string(index=False))


if __name__ == "__main__":
    cli()
