import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, ShieldAlert, Target } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { KlineChart } from '../components/KlineChart'
import { ErrorState, Loading, ScoreBadge } from '../components/StateViews'
import type { DailyBar, ScanResult, SymbolItem } from '../types'

export function ChartPage() {
  const { symbol = 'AAPL' } = useParams()
  const [search] = useSearchParams()
  const resultId = search.get('result')
  const chart = useQuery({ queryKey: ['bars', symbol], queryFn: () => api.get<{ symbol: SymbolItem; bars: DailyBar[] }>(`/api/market/data/daily/${symbol}`) })
  const result = useQuery({ queryKey: ['result', resultId], queryFn: () => api.get<ScanResult>(`/api/scanner/results/${resultId}`), enabled: Boolean(resultId) })
  const fallback = useQuery({ queryKey: ['symbol-results', symbol], queryFn: () => api.get<ScanResult[]>(`/api/scanner/results?symbol=${symbol}&min_score=0`), enabled: !resultId })
  if (chart.isLoading || result.isLoading || fallback.isLoading) return <Loading label={`正在绘制 ${symbol} 日线…`} />
  if (chart.error || result.error || fallback.error) return <ErrorState error={(chart.error ?? result.error ?? fallback.error) as Error} />
  const signal = result.data ?? fallback.data?.[0]
  const bars = chart.data!.bars
  const current = bars.at(-1)
  const previous = bars.at(-2)
  const change = current && previous ? ((current.close / previous.close) - 1) * 100 : 0
  return <div className="page-stack">
    <div className="page-heading compact"><div><span className="eyebrow">DAILY STRUCTURE</span><h1>{symbol} <span className="company-name">{chart.data!.symbol.name}</span></h1><p>{current?.close.toFixed(2)} <span className={change >= 0 ? 'positive' : 'negative'}>{change >= 0 ? '+' : ''}{change.toFixed(2)}%</span> · {current?.bar_date} · {current?.source}</p></div><div className="symbol-switcher">{['AAPL', 'MSFT', 'NVDA', 'META'].map((item) => <Link key={item} className={item === symbol ? 'active' : ''} to={`/chart/${item}`}>{item}</Link>)}</div></div>
    <section className="chart-layout"><div className="panel chart-panel"><KlineChart bars={bars} annotations={signal?.annotations} entry={signal?.direction === 'long' ? signal.entry : undefined} stop={signal?.direction === 'long' ? signal.stop : undefined} target={signal?.direction === 'long' ? signal.target : undefined} /></div>
      <aside className="signal-panel">{signal ? <>
        <div className="signal-head"><div><span className="eyebrow">MATCHED RULE</span><h2>{signal.rule_name}</h2></div><ScoreBadge score={signal.score} /></div>
        <div className="trade-plan"><Plan icon={<ArrowUp />} label="Entry" value={signal.entry} tone="green" /><Plan icon={<ShieldAlert />} label="Stop" value={signal.stop} tone="red" /><Plan icon={<Target />} label="Target" value={signal.target} tone="amber" /><Plan icon={<ArrowDown />} label="Risk / Reward" text={`${signal.risk_reward.toFixed(2)}R`} tone="blue" /></div>
        <div className="explanation"><span className="eyebrow">WHY IT MATCHED</span><ol>{signal.explanation.map((line) => <li key={line}>{line}</li>)}</ol></div>
      </> : <div className="empty-panel"><strong>当前无扫描信号</strong><p>先运行扫描，或在规则库对该标的进行测试。</p><Link className="button primary" to="/scanner">前往扫描器</Link></div>}</aside>
    </section>
  </div>
}

function Plan({ icon, label, value, text, tone }: { icon: React.ReactNode; label: string; value?: number; text?: string; tone: string }) {
  return <div className="plan-row"><span className={`plan-icon ${tone}`}>{icon}</span><span>{label}</span><strong>{text ?? value?.toFixed(2) ?? '—'}</strong></div>
}
