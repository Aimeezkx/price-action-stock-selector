import { useMutation, useQuery } from '@tanstack/react-query'
import { BarChart3, Play } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'
import { ErrorState, Loading } from '../components/StateViews'
import type { BacktestRun, Rule } from '../types'

export function BacktestPage() {
  const rules = useQuery({ queryKey: ['rules'], queryFn: () => api.get<Rule[]>('/api/price-action/rules') })
  const [ruleId, setRuleId] = useState('resistance_breakout_volume')
  const [holdingDays, setHoldingDays] = useState(10)
  const [targetR, setTargetR] = useState(2)
  const run = useMutation({ mutationFn: () => api.post<BacktestRun>('/api/backtests', { rule_id: ruleId, symbols: [], holding_days: holdingDays, target_r: targetR }) })
  if (rules.isLoading) return <Loading label="正在准备回测引擎…" />
  if (rules.error) return <ErrorState error={rules.error} />
  const metrics = run.data?.metrics
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">EVENT-DRIVEN BACKTEST</span><h1>用历史样本约束主观判断</h1><p>信号次日开始检查止损/目标；否则按固定持仓日收盘退出，结果以 R 倍数计量。</p></div></div>
    <section className="backtest-config panel"><label><span>规则</span><select value={ruleId} onChange={(event) => setRuleId(event.target.value)}>{rules.data!.filter((item) => item.direction === 'long').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label><span>最长持仓天数</span><input type="number" min="1" max="120" value={holdingDays} onChange={(event) => setHoldingDays(Number(event.target.value))} /></label><label><span>目标 R</span><input type="number" min="0.25" max="10" step="0.25" value={targetR} onChange={(event) => setTargetR(Number(event.target.value))} /></label><button className="button primary" onClick={() => run.mutate()} disabled={run.isPending}><Play size={17} />{run.isPending ? '计算中…' : '运行回测'}</button></section>
    {run.error && <div className="state-card error-state"><strong>回测失败</strong><p>{run.error.message}</p></div>}
    {metrics ? <>
      <section className="metric-grid backtest-metrics"><Metric label="交易样本" value={metrics.sample_size.toString()} /><Metric label="胜率" value={`${metrics.win_rate}%`} /><Metric label="平均 R" value={metrics.average_r.toFixed(2)} /><Metric label="Profit Factor" value={metrics.profit_factor.toFixed(2)} /><Metric label="最大回撤" value={`${metrics.max_drawdown_r.toFixed(2)}R`} /><Metric label="Sharpe-like" value={metrics.sharpe_like.toFixed(2)} /></section>
      <section className="panel"><div className="section-heading"><div><span className="eyebrow">TRADE LOG</span><h2>最近 {Math.min(run.data!.trades.length, 250)} 笔信号</h2></div><span className="muted">Run #{run.data!.id}</span></div><div className="table-scroll"><table><thead><tr><th>Symbol</th><th>Entry Date</th><th>Exit Date</th><th>Entry</th><th>Exit</th><th>Score</th><th>R</th></tr></thead><tbody>{run.data!.trades.slice().reverse().map((trade, index) => <tr key={`${trade.symbol}-${trade.entry_date}-${index}`}><td><strong className="ticker">{trade.symbol}</strong></td><td>{trade.entry_date}</td><td>{trade.exit_date}</td><td>{trade.entry.toFixed(2)}</td><td>{trade.exit.toFixed(2)}</td><td>{trade.score.toFixed(0)}</td><td><strong className={trade.r >= 0 ? 'positive' : 'negative'}>{trade.r >= 0 ? '+' : ''}{trade.r.toFixed(2)}R</strong></td></tr>)}</tbody></table></div></section>
    </> : <section className="backtest-empty panel"><BarChart3 size={36} /><h2>选择参数并运行第一次回测</h2><p>演示数据库包含 6 只股票约 280 个交易日，可立即验证整个流程。</p></section>}
  </div>
}

function Metric({ label, value }: { label: string; value: string }) { return <article className="metric-card"><div><span>{label}</span><strong>{value}</strong><small>历史模拟</small></div></article> }
