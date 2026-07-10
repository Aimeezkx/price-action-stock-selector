import { useMutation, useQuery } from '@tanstack/react-query'
import { Filter, Play, RefreshCw, RotateCcw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../api'
import { ResultTable } from '../components/ResultTable'
import { ErrorState, Loading } from '../components/StateViews'
import type { Rule, ScanResult, SymbolItem } from '../types'

interface ScanJob { id: number; status: string }

export function ScannerPage() {
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [selectedRules, setSelectedRules] = useState<string[]>([])
  const [minScore, setMinScore] = useState(60)
  const [targetR, setTargetR] = useState(2)
  const [symbolSearch, setSymbolSearch] = useState('')
  const [activeJobId, setActiveJobId] = useState<number | null>(null)
  const symbols = useQuery({ queryKey: ['symbols'], queryFn: () => api.get<SymbolItem[]>('/api/market/symbols') })
  const rules = useQuery({ queryKey: ['rules'], queryFn: () => api.get<Rule[]>('/api/price-action/rules') })
  const results = useQuery({
    queryKey: ['scan-results', activeJobId],
    queryFn: () => api.get<ScanResult[]>(
      activeJobId === null
        ? '/api/scanner/results?min_score=0'
        : `/api/scanner/results?job_id=${activeJobId}&min_score=0`,
    ),
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: 'always',
  })
  const scan = useMutation({
    mutationFn: () => api.post<ScanJob>('/api/scanner/jobs', { symbols: selectedSymbols, rule_ids: selectedRules, min_score: minScore, target_r: targetR }),
    onSuccess: (job) => setActiveJobId(job.id),
  })
  const visible = useMemo(() => [...(results.data ?? [])]
    .filter((item) => item.score >= minScore)
    .sort((left, right) => right.score - left.score
      || (left.market_cap_rank ?? Number.MAX_SAFE_INTEGER) - (right.market_cap_rank ?? Number.MAX_SAFE_INTEGER)
      || right.id - left.id), [results.data, minScore])
  const filteredSymbols = useMemo(() => (symbols.data ?? []).filter((item) => `${item.symbol} ${item.name}`.toLowerCase().includes(symbolSearch.toLowerCase())), [symbols.data, symbolSearch])
  const displayedJobId = scan.data?.id ?? visible[0]?.scan_job_id
  const latestSignalDate = visible.reduce((latest, item) => item.signal_date > latest ? item.signal_date : latest, '')
  if (symbols.isLoading || rules.isLoading || results.isLoading) return <Loading label="正在加载扫描器…" />
  if (symbols.error || rules.error || results.error) return <ErrorState error={(symbols.error ?? rules.error ?? results.error) as Error} />
  const toggle = (value: string, selected: string[], setSelected: (items: string[]) => void) => setSelected(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value])
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">DAILY SCANNER</span><h1>价格行为扫描器</h1><p>留空代表扫描全部启用标的或规则；结果先按 Score、再按市值由大到小排序。</p></div><button className="button primary" onClick={() => scan.mutate()} disabled={scan.isPending}><Play size={17} />{scan.isPending ? '扫描中…' : '运行扫描'}</button></div>
    <section className="scanner-layout">
      <aside className="filter-panel">
        <div className="filter-title"><Filter size={17} /><strong>扫描条件</strong><button className="icon-button" onClick={() => { setSelectedSymbols([]); setSelectedRules([]); setMinScore(60); setTargetR(2) }}><RotateCcw size={15} /></button></div>
        <label className="field-label">最低评分 <strong>{minScore}</strong></label><input className="range" type="range" min="40" max="90" step="5" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
        <label className="field-label">最低结构风险收益比 <strong>{targetR.toFixed(2)}R</strong></label><input className="range" type="range" min="0.5" max="10" step="0.25" value={targetR} onChange={(event) => setTargetR(Number(event.target.value))} /><p className="filter-help">结构目标空间 ÷ 入场止损风险；阈值越高，候选通常越少。</p>
        <fieldset><legend>股票池 · {symbols.data!.length}</legend><input className="symbol-search" value={symbolSearch} onChange={(event) => setSymbolSearch(event.target.value)} placeholder="搜索 ticker / 公司" /><div className="check-list">{filteredSymbols.map((item) => <label key={item.symbol}><input type="checkbox" checked={selectedSymbols.includes(item.symbol)} onChange={() => toggle(item.symbol, selectedSymbols, setSelectedSymbols)} /><span><strong>{item.symbol}</strong><small>{item.sector ?? item.name}</small></span></label>)}</div></fieldset>
        <fieldset><legend>规则</legend><div className="check-list">{rules.data!.filter((item) => item.enabled).map((item) => <label key={item.id}><input type="checkbox" checked={selectedRules.includes(item.id)} onChange={() => toggle(item.id, selectedRules, setSelectedRules)} /><span><strong>{item.name}</strong><small>{item.category}</small></span></label>)}</div></fieldset>
      </aside>
      <section className="panel results-panel"><div className="section-heading"><div><span className="eyebrow">{displayedJobId ? `JOB #${displayedJobId}${scan.data ? ` · ${scan.data.status}` : ''}` : 'LATEST RESULTS'}</span><h2>{visible.length} 个候选</h2><small className="muted">{latestSignalDate ? `数据日期 ${latestSignalDate}` : '当前任务没有命中候选'}</small></div><div className="results-actions"><span className="muted">Score ≥ {minScore}</span><button className="icon-button" aria-label="刷新最新扫描结果" title="刷新最新扫描结果" onClick={() => results.refetch()} disabled={results.isFetching}><RefreshCw size={15} className={results.isFetching ? 'spin' : ''} /></button></div></div>{scan.error && <p className="inline-error">{scan.error.message}</p>}<ResultTable results={visible} /></section>
    </section>
  </div>
}
