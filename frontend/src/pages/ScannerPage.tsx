import { useMutation, useQuery } from '@tanstack/react-query'
import { Filter, Play, RotateCcw } from 'lucide-react'
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
  })
  const scan = useMutation({
    mutationFn: () => api.post<ScanJob>('/api/scanner/jobs', { symbols: selectedSymbols, rule_ids: selectedRules, min_score: minScore }),
    onSuccess: (job) => setActiveJobId(job.id),
  })
  const visible = useMemo(() => (results.data ?? []).filter((item) => item.score >= minScore), [results.data, minScore])
  if (symbols.isLoading || rules.isLoading || results.isLoading) return <Loading label="正在加载扫描器…" />
  if (symbols.error || rules.error || results.error) return <ErrorState error={(symbols.error ?? rules.error ?? results.error) as Error} />
  const toggle = (value: string, selected: string[], setSelected: (items: string[]) => void) => setSelected(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value])
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">DAILY SCANNER</span><h1>价格行为扫描器</h1><p>留空代表扫描全部启用标的或规则；结果按评分自动排序。</p></div><button className="button primary" onClick={() => scan.mutate()} disabled={scan.isPending}><Play size={17} />{scan.isPending ? '扫描中…' : '运行扫描'}</button></div>
    <section className="scanner-layout">
      <aside className="filter-panel">
        <div className="filter-title"><Filter size={17} /><strong>扫描条件</strong><button className="icon-button" onClick={() => { setSelectedSymbols([]); setSelectedRules([]); setMinScore(60) }}><RotateCcw size={15} /></button></div>
        <label className="field-label">最低评分 <strong>{minScore}</strong></label><input className="range" type="range" min="40" max="90" step="5" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
        <fieldset><legend>股票池</legend><div className="check-list">{symbols.data!.map((item) => <label key={item.symbol}><input type="checkbox" checked={selectedSymbols.includes(item.symbol)} onChange={() => toggle(item.symbol, selectedSymbols, setSelectedSymbols)} /><span><strong>{item.symbol}</strong><small>{item.sector ?? item.name}</small></span></label>)}</div></fieldset>
        <fieldset><legend>规则</legend><div className="check-list">{rules.data!.filter((item) => item.enabled).map((item) => <label key={item.id}><input type="checkbox" checked={selectedRules.includes(item.id)} onChange={() => toggle(item.id, selectedRules, setSelectedRules)} /><span><strong>{item.name}</strong><small>{item.category}</small></span></label>)}</div></fieldset>
      </aside>
      <section className="panel results-panel"><div className="section-heading"><div><span className="eyebrow">{scan.data ? `JOB #${scan.data.id} · ${scan.data.status}` : 'LATEST RESULTS'}</span><h2>{visible.length} 个候选</h2></div><span className="muted">Score ≥ {minScore}</span></div>{scan.error && <p className="inline-error">{scan.error.message}</p>}<ResultTable results={visible} /></section>
    </section>
  </div>
}
