import type { Annotation, DailyBar } from '../types'

interface Props {
  bars: DailyBar[]
  annotations?: Annotation[]
  entry?: number
  stop?: number
  target?: number
}

export function KlineChart({ bars, annotations = [], entry, stop, target }: Props) {
  const data = bars.slice(-90)
  if (!data.length) return <div className="chart-empty">暂无 K 线数据</div>
  const width = 980
  const height = 500
  const pad = { top: 24, right: 76, bottom: 62, left: 18 }
  const volumeHeight = 72
  const chartBottom = height - pad.bottom - volumeHeight
  const low = Math.min(...data.map((item) => item.low), stop ?? Infinity) * 0.995
  const high = Math.max(...data.map((item) => item.high), target ?? -Infinity) * 1.005
  const range = Math.max(high - low, 0.01)
  const maxVolume = Math.max(...data.map((item) => item.volume), 1)
  const step = (width - pad.left - pad.right) / data.length
  const y = (value: number) => pad.top + ((high - value) / range) * (chartBottom - pad.top)
  const candleWidth = Math.max(2.8, step * 0.58)
  const levels = [
    ...(entry ? [{ price: entry, label: 'ENTRY', color: '#54d6be' }] : []),
    ...(stop ? [{ price: stop, label: 'STOP', color: '#f16d7a' }] : []),
    ...(target ? [{ price: target, label: 'TARGET', color: '#f2b84b' }] : []),
    ...annotations.filter((item) => item.type === 'line' && item.price).map((item) => ({ price: item.price!, label: item.label, color: '#7895ff' })),
  ]
  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="日线 K 线图">
        <defs>
          <linearGradient id="chartBg" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#111f31" /><stop offset="1" stopColor="#091524" /></linearGradient>
        </defs>
        <rect width={width} height={height} rx="14" fill="url(#chartBg)" />
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const price = high - range * tick
          const py = y(price)
          return <g key={tick}><line x1={pad.left} y1={py} x2={width - pad.right} y2={py} stroke="#26364a" strokeWidth="1" /><text x={width - pad.right + 8} y={py + 4} fill="#8090a5" fontSize="11">{price.toFixed(2)}</text></g>
        })}
        {annotations.filter((item) => item.type === 'zone' && item.low && item.high).map((zone) => (
          <g key={zone.label}><rect x={pad.left} y={y(zone.high!)} width={width - pad.left - pad.right} height={Math.max(3, y(zone.low!) - y(zone.high!))} fill="#7895ff" opacity="0.09" /><text x={pad.left + 8} y={y(zone.high!) - 5} fill="#9eaeff" fontSize="11">{zone.label}</text></g>
        ))}
        {data.map((bar, index) => {
          const x = pad.left + step * index + step / 2
          const bullish = bar.close >= bar.open
          const color = bullish ? '#35c7a5' : '#e55b6b'
          const bodyY = Math.min(y(bar.open), y(bar.close))
          const bodyHeight = Math.max(1.5, Math.abs(y(bar.open) - y(bar.close)))
          const vh = (bar.volume / maxVolume) * volumeHeight
          return <g key={bar.bar_date}>
            <line x1={x} y1={y(bar.high)} x2={x} y2={y(bar.low)} stroke={color} strokeWidth="1.1" />
            <rect x={x - candleWidth / 2} y={bodyY} width={candleWidth} height={bodyHeight} fill={color} rx="0.6" />
            <rect x={x - candleWidth / 2} y={height - pad.bottom - vh + volumeHeight} width={candleWidth} height={vh} fill={color} opacity="0.22" />
            {index % 18 === 0 && <text x={x} y={height - 17} fill="#6f8197" fontSize="10" textAnchor="middle">{bar.bar_date.slice(5)}</text>}
          </g>
        })}
        {levels.map((level) => level.price >= low && level.price <= high && (
          <g key={`${level.label}-${level.price}`}><line x1={pad.left} y1={y(level.price)} x2={width - pad.right} y2={y(level.price)} stroke={level.color} strokeDasharray="6 5" opacity="0.82" /><rect x={width - pad.right + 2} y={y(level.price) - 10} width={68} height={18} rx="4" fill={level.color} /><text x={width - pad.right + 36} y={y(level.price) + 3} fill="#07111f" fontSize="9" fontWeight="700" textAnchor="middle">{level.label} {level.price.toFixed(2)}</text></g>
        ))}
      </svg>
    </div>
  )
}
