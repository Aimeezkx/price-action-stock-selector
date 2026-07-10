import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type CandlestickData,
  type Time,
} from 'lightweight-charts'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Annotation, DailyBar } from '../types'

interface Props {
  bars: DailyBar[]
  annotations?: Annotation[]
  entry?: number
  stop?: number
  target?: number
}

interface HoverBar extends DailyBar {
  ema20: number | null
}

export function KlineChart({ bars, annotations = [], entry, stop, target }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ema20 = useMemo(() => calculateEma(bars, 20), [bars])
  const [hovered, setHovered] = useState<HoverBar | null>(() => withEma(bars.at(-1), ema20.at(-1)))

  useEffect(() => {
    setHovered(withEma(bars.at(-1), ema20.at(-1)))
  }, [bars, ema20])

  useEffect(() => {
    if (!containerRef.current || !bars.length) return
    const chart = createChart(containerRef.current, {
      autoSize: true,
      height: 560,
      layout: {
        background: { type: ColorType.Solid, color: '#091524' },
        textColor: '#91a3b7',
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1a2b3e' },
        horzLines: { color: '#203247' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#7895ff88', labelBackgroundColor: '#4965b8' },
        horzLine: { color: '#7895ff88', labelBackgroundColor: '#4965b8' },
      },
      rightPriceScale: {
        borderColor: '#2a3c50',
        scaleMargins: { top: 0.08, bottom: 0.27 },
        minimumWidth: 76,
      },
      timeScale: {
        borderColor: '#2a3c50',
        timeVisible: false,
        rightOffset: 5,
        barSpacing: 7,
        minBarSpacing: 2,
      },
      localization: {
        locale: 'zh-CN',
        priceFormatter: (price: number) => price.toFixed(price >= 1000 ? 1 : 2),
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#35c7a5',
      downColor: '#e55b6b',
      borderVisible: false,
      wickUpColor: '#35c7a5',
      wickDownColor: '#e55b6b',
      priceLineVisible: false,
    })
    candleSeries.setData(bars.map((bar) => ({
      time: bar.bar_date as Time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    })))

    const emaSeries = chart.addSeries(LineSeries, {
      color: '#f2b84b',
      lineWidth: 2,
      title: 'EMA20',
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    })
    emaSeries.setData(bars.flatMap((bar, index) => (
      ema20[index] === null ? [] : [{ time: bar.bar_date as Time, value: ema20[index]! }]
    )))

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      priceFormat: { type: 'volume' },
      priceLineVisible: false,
      lastValueVisible: false,
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeries.setData(bars.map((bar) => ({
      time: bar.bar_date as Time,
      value: bar.volume,
      color: bar.close >= bar.open ? '#35c7a536' : '#e55b6b36',
    })))

    const levels = [
      ...(entry !== undefined ? [{ price: entry, title: 'ENTRY', color: '#54d6be' }] : []),
      ...(stop !== undefined ? [{ price: stop, title: 'STOP', color: '#f16d7a' }] : []),
      ...(target !== undefined ? [{ price: target, title: 'TARGET', color: '#f2b84b' }] : []),
      ...annotations.flatMap((annotation) => {
        if (annotation.type === 'line' && annotation.price !== undefined) {
          return [{ price: annotation.price, title: annotation.label, color: '#7895ff' }]
        }
        if (annotation.type === 'zone' && annotation.low !== undefined && annotation.high !== undefined) {
          return [
            { price: annotation.low, title: `${annotation.label} L`, color: '#7895ff88' },
            { price: annotation.high, title: `${annotation.label} H`, color: '#7895ff88' },
          ]
        }
        return []
      }),
    ]
    levels.forEach((level) => candleSeries.createPriceLine({
      price: level.price,
      title: level.title,
      color: level.color,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
    }))

    const barByDate = new Map(bars.map((bar, index) => [bar.bar_date, withEma(bar, ema20[index])]))
    const crosshairHandler = (param: { time?: Time; seriesData: Map<unknown, unknown> }) => {
      if (!param.time) {
        setHovered(withEma(bars.at(-1), ema20.at(-1)))
        return
      }
      const date = String(param.time)
      const candle = param.seriesData.get(candleSeries) as CandlestickData<Time> | undefined
      const source = barByDate.get(date)
      if (source && candle) setHovered({ ...source, ...candle, bar_date: date })
    }
    chart.subscribeCrosshairMove(crosshairHandler)
    chart.timeScale().setVisibleLogicalRange({
      from: Math.max(0, bars.length - 120),
      to: bars.length + 4,
    })

    return () => {
      chart.unsubscribeCrosshairMove(crosshairHandler)
      chart.remove()
    }
  }, [annotations, bars, ema20, entry, stop, target])

  if (!bars.length) return <div className="chart-empty">暂无 K 线数据</div>
  return <div className="chart-wrap">
    <div className="chart-legend" aria-live="polite">
      <strong>{hovered?.bar_date ?? '—'}</strong>
      <span>O <b>{formatPrice(hovered?.open)}</b></span>
      <span>H <b>{formatPrice(hovered?.high)}</b></span>
      <span>L <b>{formatPrice(hovered?.low)}</b></span>
      <span>C <b>{formatPrice(hovered?.close)}</b></span>
      <span>EMA20 <b>{formatPrice(hovered?.ema20)}</b></span>
      <span>Vol <b>{formatVolume(hovered?.volume)}</b></span>
    </div>
    <div className="chart-canvas" ref={containerRef} aria-label="可缩放日线 K 线图" />
    <p className="chart-hint">滚轮缩放 · 拖动平移 · 悬停查看 OHLC / EMA20 / 成交量</p>
  </div>
}

function calculateEma(bars: DailyBar[], period: number): Array<number | null> {
  if (!bars.length) return []
  const multiplier = 2 / (period + 1)
  let ema = bars[0].close
  return bars.map((bar, index) => {
    ema = index === 0 ? bar.close : (bar.close - ema) * multiplier + ema
    return index < period - 1 ? null : ema
  })
}

function withEma(bar: DailyBar | undefined, ema: number | null | undefined): HoverBar | null {
  return bar ? { ...bar, ema20: ema ?? null } : null
}

function formatPrice(value: number | null | undefined) {
  return value == null ? '—' : value.toFixed(value >= 1000 ? 1 : 2)
}

function formatVolume(value: number | undefined) {
  if (value == null) return '—'
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toFixed(0)
}
