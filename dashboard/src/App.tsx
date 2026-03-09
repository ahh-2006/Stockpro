import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

declare global {
  interface Window {
    LightweightCharts: any
  }
}

type Trade = { p: number; v: number; t: number }

function useFinnhub(symbol: string, onTrade: (trades: Trade[]) => void) {
  useEffect(() => {
    const token = import.meta.env.VITE_FINNHUB_API_KEY as string | undefined
    if (!token || !symbol) return
    const ws = new WebSocket(`wss://ws.finnhub.io?token=${token}`)
    ws.onopen = () => ws.send(JSON.stringify({ type: 'subscribe', symbol }))
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'trade' && Array.isArray(msg.data)) {
        onTrade(msg.data.map((d: any) => ({ p: d.p, v: d.v, t: d.t })))
      }
    }
    return () => {
      try { ws.send(JSON.stringify({ type: 'unsubscribe', symbol })) } catch {}
      ws.close()
    }
  }, [symbol, onTrade])
}

function rsi(values: number[], period = 14) {
  if (values.length < period + 1) return Array(values.length).fill(null)
  const rsis: (number | null)[] = Array(values.length).fill(null)
  let gains = 0, losses = 0
  for (let i = 1; i <= period; i++) {
    const diff = values[i] - values[i - 1]
    gains += diff > 0 ? diff : 0
    losses += diff < 0 ? -diff : 0
  }
  let avgGain = gains / period
  let avgLoss = losses / period
  for (let i = period + 1; i < values.length; i++) {
    const diff = values[i] - values[i - 1]
    avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period
    avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period
    const rs = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
    rsis[i] = rs
  }
  return rsis
}

function vwap(prices: { close: number; volume: number }[]) {
  const out: (number | null)[] = []
  let pv = 0, tv = 0
  for (let i = 0; i < prices.length; i++) {
    const c = prices[i].close
    const v = prices[i].volume
    pv += c * v
    tv += v
    out.push(tv ? pv / tv : null)
  }
  return out
}

function mfi(data: { high: number; low: number; close: number; volume: number }[], period = 14) {
  const out: (number | null)[] = Array(data.length).fill(null)
  const tp = data.map(d => (d.high + d.low + d.close) / 3)
  const pos: number[] = [], neg: number[] = []
  for (let i = 1; i < data.length; i++) {
    const raw = tp[i] * data[i].volume
    if (tp[i] > tp[i - 1]) { pos.push(raw); neg.push(0) } else if (tp[i] < tp[i - 1]) { pos.push(0); neg.push(raw) } else { pos.push(0); neg.push(0) }
    if (i >= period) {
      const ps = pos.slice(i - period, i).reduce((a, b) => a + b, 0)
      const ns = neg.slice(i - period, i).reduce((a, b) => a + b, 0)
      const mr = ns === 0 ? 50 : 100 - 100 / (1 + ps / ns)
      out[i] = mr
    }
  }
  return out
}

function computeADX(bars: { high: number; low: number; close: number }[], period = 14) {
  const n = bars.length
  if (n < period + 1) return { plus: null as number | null, minus: null as number | null, adx: null as number | null }
  const trArr: number[] = []
  const plusDMArr: number[] = []
  const minusDMArr: number[] = []
  for (let i = 1; i < n; i++) {
    const hi = bars[i].high, lo = bars[i].low, prevClose = bars[i - 1].close
    const tr = Math.max(hi - lo, Math.abs(hi - prevClose), Math.abs(lo - prevClose))
    trArr.push(tr)
    const upMove = hi - bars[i - 1].high
    const downMove = bars[i - 1].low - lo
    plusDMArr.push((upMove > downMove && upMove > 0) ? upMove : 0)
    minusDMArr.push((downMove > upMove && downMove > 0) ? downMove : 0)
  }
  const alpha = 1 / period
  const ema = (arr: number[]) => {
    const out: number[] = []
    let val = arr[0]
    out.push(val)
    for (let i = 1; i < arr.length; i++) {
      val = alpha * arr[i] + (1 - alpha) * val
      out.push(val)
    }
    return out
  }
  const atrArr = ema(trArr)
  const plusSm = ema(plusDMArr)
  const minusSm = ema(minusDMArr)
  const plusDI: number[] = []
  const minusDI: number[] = []
  for (let i = 0; i < atrArr.length; i++) {
    const atr = atrArr[i] || 1e-9
    plusDI.push(100 * (plusSm[i] / atr))
    minusDI.push(100 * (minusSm[i] / atr))
  }
  const dxArr: number[] = []
  for (let i = 0; i < plusDI.length; i++) {
    const s = plusDI[i] + minusDI[i]
    dxArr.push(s === 0 ? 0 : 100 * Math.abs(plusDI[i] - minusDI[i]) / s)
  }
  const adxArr = ema(dxArr)
  const idx = adxArr.length - 1
  return { plus: plusDI[idx], minus: minusDI[idx], adx: adxArr[idx] }
}

function App() {
  const [symbol, setSymbol] = useState('')
  const [risk, setRisk] = useState<number>(100)
  const [stop, setStop] = useState<number | ''>('')
  const [position, setPosition] = useState<{ side: 'long' | 'short' | null; qty: number; entry: number }>({ side: null, qty: 0, entry: 0 })
  const [pnl, setPnl] = useState(0)
  const [maxLoss, setMaxLoss] = useState(500)
  const [orders, setOrders] = useState<{ side: 'long' | 'short'; qty: number; entry: number; time: string }[]>([])
  const [tape, setTape] = useState<Trade[]>([])
  const chartRef = useRef<HTMLDivElement>(null)
  const seriesRef = useRef<any>(null)
  const vwapSeriesRef = useRef<any>(null)
  const adxSeriesRef = useRef<any>(null)
  const pdiSeriesRef = useRef<any>(null)
  const mdiSeriesRef = useRef<any>(null)
  const stopLine = useRef<any>(null)
  const tpLine = useRef<any>(null)
  const sugEL = useRef<any>(null)
  const sugSL = useRef<any>(null)
  const sugT1 = useRef<any>(null)
  const sugT2 = useRef<any>(null)
  const [sugg, setSugg] = useState<{ eL: number, sL: number, t1L: number, t2L: number, eS: number, sS: number, t1S: number, t2S: number } | null>(null)
  const [atrBuf, setAtrBuf] = useState(0.1)
  const [t1R, setT1R] = useState(1)
  const [t2R, setT2R] = useState(2)
  const [mobile, setMobile] = useState(false)
  const [history, setHistory] = useState<string[]>([])
  const data = useRef<{ time: number; open: number; high: number; low: number; close: number; volume: number }[]>([])

  useEffect(() => {
    if (!chartRef.current) return
    const chart = window.LightweightCharts.createChart(chartRef.current, {
      layout: { background: { color: '#0b1220' }, textColor: '#e5e7eb' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: chartRef.current.clientWidth,
      height: chartRef.current.clientHeight,
      timeScale: { timeVisible: true, secondsVisible: true }
    })
    const series = chart.addCandlestickSeries({ upColor: '#16a34a', downColor: '#ef4444', borderVisible: false, wickUpColor: '#16a34a', wickDownColor: '#ef4444' })
    const vwapS = chart.addLineSeries({ color: '#60a5fa', lineWidth: 2 })
    seriesRef.current = series
    vwapSeriesRef.current = vwapS
    const adxS = chart.addLineSeries({ color: '#eab308', lineWidth: 1 })
    const pdiS = chart.addLineSeries({ color: '#22c55e', lineWidth: 1, lineStyle: 1 })
    const mdiS = chart.addLineSeries({ color: '#ef4444', lineWidth: 1, lineStyle: 1 })
    adxSeriesRef.current = adxS
    pdiSeriesRef.current = pdiS
    mdiSeriesRef.current = mdiS
    const handleResize = () => chart.applyOptions({ width: chartRef.current?.clientWidth || 800 })
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize) }
  }, [])

  useFinnhub(symbol, (trades) => {
    setTape(ts => {
      const merged = [...trades.reverse(), ...ts].slice(0, 200)
      return merged
    })
    const t = trades[0]
    if (!t) return
    const ts = Math.floor(t.t / 1000)
    const last = data.current[data.current.length - 1]
    if (last && last.time === ts) {
      last.high = Math.max(last.high, t.p)
      last.low = Math.min(last.low, t.p)
      last.close = t.p
      last.volume += t.v
      seriesRef.current?.update({ time: ts, open: last.open, high: last.high, low: last.low, close: last.close })
    } else {
      const bar = { time: ts, open: t.p, high: t.p, low: t.p, close: t.p, volume: t.v }
      data.current.push(bar)
      seriesRef.current?.update(bar)
    }
    const vwapArr = vwap(data.current.map(d => ({ close: d.close, volume: d.volume })))
    const v = vwapArr[vwapArr.length - 1]
    if (v) vwapSeriesRef.current?.update({ time: ts, value: v })
    const adx = computeADX(data.current, 14)
    if (adx.adx != null) adxSeriesRef.current?.update({ time: ts, value: adx.adx })
    if (adx.plus != null) pdiSeriesRef.current?.update({ time: ts, value: adx.plus })
    if (adx.minus != null) mdiSeriesRef.current?.update({ time: ts, value: adx.minus })
    if (position.side) {
      const lastPrice = t.p
      const u = position.side === 'long' ? (lastPrice - position.entry) * position.qty : (position.entry - lastPrice) * position.qty
      setPnl(u)
    }
    const n = data.current.length
    if (n >= 20) {
      const win = 10
      let h = -Infinity, l = Infinity
      for (let i = n - win; i < n; i++) {
        h = Math.max(h, data.current[i].high)
        l = Math.min(l, data.current[i].low)
      }
      let atr = 0
      const p = 14
      for (let i = n - p + 1; i < n; i++) {
        const hi = data.current[i].high
        const lo = data.current[i].low
        const pc = data.current[i - 1].close
        const tr = Math.max(hi - lo, Math.abs(hi - pc), Math.abs(lo - pc))
        atr += tr
      }
      atr = atr / (p - 1)
      const eL = h + atrBuf * atr
      const sL = l
      const r = eL - sL
      const t1 = eL + t1R * r
      const t2 = eL + t2R * r
      sugEL.current?.remove?.()
      sugSL.current?.remove?.()
      sugT1.current?.remove?.()
      sugT2.current?.remove?.()
      if (seriesRef.current) {
        sugEL.current = seriesRef.current.createPriceLine({ price: eL, color: '#60a5fa', axisLabelVisible: true, title: 'Entry L' })
        sugSL.current = seriesRef.current.createPriceLine({ price: sL, color: '#ef4444', axisLabelVisible: true, title: 'Stop L' })
        sugT1.current = seriesRef.current.createPriceLine({ price: t1, color: '#22c55e', axisLabelVisible: true, title: 'TP1' })
        sugT2.current = seriesRef.current.createPriceLine({ price: t2, color: '#22c55e', axisLabelVisible: true, title: 'TP2' })
      }
      const eS = l - atrBuf * atr
      const sS = h
      const rS = sS - eS
      const t1S = eS - t1R * rS
      const t2S = eS - t2R * rS
      setSugg({ eL, sL, t1L: t1, t2L: t2, eS, sS, t1S, t2S })
    }
  })

  const rsiVal = useMemo(() => {
    const arr = rsi(data.current.map(d => d.close), 14)
    const v = arr[arr.length - 1]
    return typeof v === 'number' ? v : null
  }, [tape.length])

  const mfiVal = useMemo(() => {
    const arr = mfi(data.current, 14)
    const v = arr[arr.length - 1]
    return typeof v === 'number' ? v : null
  }, [tape.length])
  const adxVals = useMemo(() => {
    return computeADX(data.current, 14)
  }, [tape.length])

  const lastPrice = data.current.length ? data.current[data.current.length - 1].close : null
  const shares = useMemo(() => {
    if (!lastPrice || !stop || stop === 0) return 0
    const riskPerShare = Math.abs(lastPrice - Number(stop))
    if (riskPerShare <= 0) return 0
    return Math.floor(risk / riskPerShare)
  }, [risk, stop, lastPrice])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.shiftKey && (e.key === 'B' || e.key === 'b')) handleBuy()
      if (e.shiftKey && (e.key === 'S' || e.key === 's')) handleSell()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  useEffect(() => {
    const raw = localStorage.getItem('symbol_history')
    if (raw) setHistory(JSON.parse(raw))
  }, [])
  const addToHistory = (s: string) => {
    if (!s) return
    const list = [s, ...history.filter(x => x !== s)].slice(0, 10)
    setHistory(list)
    localStorage.setItem('symbol_history', JSON.stringify(list))
  }
  const onSymbolChange = (val: string) => {
    setSymbol(val.toUpperCase())
  }
  const onSymbolEnter: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === 'Enter') addToHistory(symbol.trim().toUpperCase())
  }

  const placeBracket = (entry: number, side: 'long' | 'short') => {
    const sl = Number(stop)
    if (!seriesRef.current || !sl || !entry) return
    const riskPerShare = Math.abs(entry - sl)
    const tp = side === 'long' ? entry + 2 * riskPerShare : entry - 2 * riskPerShare
    stopLine.current?.remove?.()
    tpLine.current?.remove?.()
    stopLine.current = seriesRef.current.createPriceLine({ price: sl, color: '#ef4444', lineWidth: 1, axisLabelVisible: true, title: 'SL' })
    tpLine.current = seriesRef.current.createPriceLine({ price: tp, color: '#22c55e', lineWidth: 1, axisLabelVisible: true, title: 'TP' })
  }

  const handleBuy = () => {
    if (!lastPrice || shares <= 0) return
    setPosition({ side: 'long', qty: shares, entry: lastPrice })
    placeBracket(lastPrice, 'long')
    setOrders(o => [{ side: 'long', qty: shares, entry: lastPrice, time: new Date().toLocaleTimeString() }, ...o].slice(0, 50))
  }
  const handleSell = () => {
    if (!lastPrice || shares <= 0) return
    setPosition({ side: 'short', qty: shares, entry: lastPrice })
    placeBracket(lastPrice, 'short')
    setOrders(o => [{ side: 'short', qty: shares, entry: lastPrice, time: new Date().toLocaleTimeString() }, ...o].slice(0, 50))
  }
  const applyLong = () => {
    if (!sugg) return
    setStop(sugg.sL)
    placeBracket(sugg.eL, 'long')
  }
  const applyShort = () => {
    if (!sugg) return
    setStop(sugg.sS)
    placeBracket(sugg.eS, 'short')
  }
  const handleFlatten = () => {
    setPosition({ side: null, qty: 0, entry: 0 })
    setPnl(0)
    stopLine.current?.remove?.()
    tpLine.current?.remove?.()
  }

  const gaugePct = Math.max(0, Math.min(1, (pnl + maxLoss) / (2 * maxLoss)))
  const alertLoss = pnl <= -maxLoss
  const DonutGauge = ({ pct }: { pct: number }) => {
    const r = 40
    const c = 2 * Math.PI * r
    const v = Math.max(0, Math.min(100, Math.round(pct * 100)))
    const offset = c * (1 - v / 100)
    const color = pct >= 0.5 ? '#22c55e' : '#f59e0b'
    return (
      <svg width="120" height="120">
        <circle cx="60" cy="60" r={r} stroke="#1f2937" strokeWidth="12" fill="none" />
        <circle cx="60" cy="60" r={r} stroke={color} strokeWidth="12" fill="none" strokeDasharray={c} strokeDashoffset={offset} transform="rotate(-90 60 60)" />
        <text x="60" y="65" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">{v}%</text>
      </svg>
    )
  }

  const MobileView = () => {
    const pct = rsiVal ? Math.min(1, Math.max(0, rsiVal / 100)) : 0.5
    return (
      <div className="mobile">
        <div className="mHeader">
          <div>←</div>
          <div className="mTitle">{symbol || 'Symbol'} <span style={{ color: '#f43f5e', fontSize: 12, marginInlineStart: 6 }}>{lastPrice ? lastPrice.toFixed(2) : '--'}</span></div>
          <div onClick={() => setMobile(false)} style={{ cursor: 'pointer' }}>☰</div>
        </div>
        <div className="mTabs">
          <div className="mTab active">الأسعار</div>
          <div className="mTab">المعاملات</div>
          <div className="mTab">المخططات</div>
        </div>
        <div className="mSection">
          <div className="statsGrid">
            <div className="statCard"><div className="statLabel">السعر الحالي</div><div className="statValue">{lastPrice ? lastPrice.toFixed(2) : '--'}</div></div>
            <div className="statCard"><div className="statLabel">الإغلاق أمس</div><div className="statValue">{data.current.length > 1 ? data.current[data.current.length - 2].close.toFixed(2) : '--'}</div></div>
            <div className="statCard"><div className="statLabel">أعلى اليوم</div><div className="statValue">{data.current.length ? Math.max(...data.current.slice(-50).map(d => d.high)).toFixed(2) : '--'}</div></div>
            <div className="statCard"><div className="statLabel">أدنى اليوم</div><div className="statValue">{data.current.length ? Math.min(...data.current.slice(-50).map(d => d.low)).toFixed(2) : '--'}</div></div>
          </div>
        </div>
        <div className="donutWrap"><DonutGauge pct={pct} /></div>
        <div className="mSection">
          <div className="miniChart" ref={chartRef} />
        </div>
        <div className="bottomBar">
          <div className="qtyRow">
            <input placeholder="الكمية" type="number" value={shares} onChange={e => { const v = Number(e.target.value); if (position.side) setPosition({ ...position, qty: v }); }} />
            <div style={{ textAlign: 'left', color: '#9ca3af', paddingTop: 10 }}>‎P&L: ${pnl.toFixed(2)}</div>
          </div>
          <div className="actions">
            <button className="button sell" onClick={handleSell} disabled={alertLoss}>بيع</button>
            <button className="button buy" onClick={handleBuy} disabled={alertLoss}>شراء</button>
          </div>
        </div>
      </div>
    )
  }

  return mobile ? <MobileView /> : (
    <div className="app">
      <div className="header">
        <div className="brand">Day Trading Dashboard</div>
        <div className="search">
          <input placeholder="Symbol e.g. AAPL" value={symbol} onChange={e => onSymbolChange(e.target.value)} onKeyDown={onSymbolEnter} />
          <div className="chips">
            {history.map(h => (
              <span key={h} className="chip" onClick={() => { setSymbol(h); addToHistory(h) }}>{h}</span>
            ))}
          </div>
        </div>
        <button className="button flatten" onClick={() => setMobile(true)} style={{ marginInlineStart: 8 }}>Mobile Preview (AR)</button>
      </div>
      <div className="chartWrap">
        <div ref={chartRef} className="chart" />
      </div>
      <div className="panel">
        <div className="card">
          <div className="row">
            <input type="number" placeholder="Risk $ (e.g. 100)" value={risk} onChange={e => setRisk(Number(e.target.value))} />
            <input type="number" placeholder="Stop Loss Price" value={stop} onChange={e => setStop(e.target.value === '' ? '' : Number(e.target.value))} />
          </div>
          <div style={{ marginTop: 8 }}>Shares: {shares}</div>
        </div>
        <div className="card">
          <div style={{ marginBottom: 6 }}>Suggested Levels</div>
          <div style={{ fontSize: 14 }}>Blue: Entry L, Red: Stop, Green: TP1/TP2</div>
          <div className="row" style={{ marginTop: 8 }}>
            <input type="number" step="0.05" value={atrBuf} onChange={e => setAtrBuf(Number(e.target.value))} placeholder="ATR Buffer" />
            <input type="number" step="0.1" value={t1R} onChange={e => setT1R(Number(e.target.value))} placeholder="T1 R" />
          </div>
          <div className="row">
            <input type="number" step="0.5" value={t2R} onChange={e => setT2R(Number(e.target.value))} placeholder="T2 R" />
          </div>
          {sugg && (
            <div style={{ marginTop: 6, fontSize: 12 }}>
              <div>Long: E {sugg.eL.toFixed(2)} / S {sugg.sL.toFixed(2)} / T1 {sugg.t1L.toFixed(2)} / T2 {sugg.t2L.toFixed(2)}</div>
              <div>Short: E {sugg.eS.toFixed(2)} / S {sugg.sS.toFixed(2)} / T1 {sugg.t1S.toFixed(2)} / T2 {sugg.t2S.toFixed(2)}</div>
            </div>
          )}
        </div>
        <button className="button buy" onClick={applyLong} disabled={alertLoss}>Apply Long Suggestion</button>
        <button className="button sell" onClick={applyShort} disabled={alertLoss}>Apply Short Suggestion</button>
        <button className="button buy" onClick={handleBuy} disabled={alertLoss}>Market Buy</button>
        <button className="button sell" onClick={handleSell} disabled={alertLoss}>Market Sell</button>
        <button className="button flatten" onClick={handleFlatten}>Flatten</button>
        <div className="card">
          <div style={{ marginBottom: 6 }}>Session P&L: ${pnl.toFixed(2)}</div>
          <div className="gauge">
            <div className="gaugeFill" style={{ width: `${gaugePct * 100}%`, background: alertLoss ? '#ef4444' : '#22c55e' }} />
          </div>
          <div style={{ marginTop: 6 }}>Max Daily Loss: ${maxLoss}</div>
          {alertLoss && <div style={{ color: '#ef4444', marginTop: 6 }}>Max loss reached</div>}
        </div>
        <div className="card">
          <div style={{ marginBottom: 6 }}>Orders</div>
          {orders.slice(0, 20).map((o, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span>{o.time}</span>
              <span>{o.side.toUpperCase()}</span>
              <span>@ {o.entry.toFixed(2)}</span>
              <span>x {o.qty}</span>
            </div>
          ))}
          <div style={{ marginTop: 8 }}>
            <button className="button flatten" onClick={() => setOrders([])}>Clear</button>
          </div>
        </div>
        <div className="card">
          <div>VWAP: {(() => { const arr = vwap(data.current.map(d => ({ close: d.close, volume: d.volume }))); const v = arr[arr.length - 1]; return v ? v.toFixed(2) : '--' })()}</div>
          <div>RSI(14): {rsiVal ? rsiVal.toFixed(2) : '--'}</div>
          <div>MFI(14): {mfiVal ? mfiVal.toFixed(2) : '--'}</div>
          <div>ADX(14): {adxVals.adx != null ? adxVals.adx.toFixed(2) : '--'} | +DI {adxVals.plus != null ? adxVals.plus.toFixed(1) : '--'} | -DI {adxVals.minus != null ? adxVals.minus.toFixed(1) : '--'}</div>
        </div>
        <div className="card">
          <div style={{ marginBottom: 6 }}>Time & Sales</div>
          <div className="tape">
            {tape.slice(0, 50).map((t, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{new Date(t.t).toLocaleTimeString()}</span>
                <span>{t.p.toFixed(2)}</span>
                <span>{t.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
