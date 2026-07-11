import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, BookOpenCheck, Cable, Clock3, Mail, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorState, Loading } from '../components/StateViews'
import { ResultTable } from '../components/ResultTable'
import type { DashboardData } from '../types'

export function DashboardPage() {
  const queryClient = useQueryClient()
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<DashboardData>('/api/dashboard') })
  const connect = useMutation({ mutationFn: () => api.post('/api/market/ibkr/connect'), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dashboard'] }) })
  if (dashboard.isLoading) return <Loading />
  if (dashboard.error) return <ErrorState error={dashboard.error} />
  const data = dashboard.data!
  return <div className="page-stack">
    <section className="hero-panel">
      <div><span className="eyebrow">PRICE ACTION COMMAND CENTER</span><h1>从结构中筛出<br /><em>值得等待的交易。</em></h1><p>日线价格行为、IBKR 数据、可解释规则与风险优先的交易计划。</p><div className="hero-actions"><Link className="button primary" to="/scanner"><Sparkles size={17} />开始扫描</Link><button className="button secondary" onClick={() => connect.mutate()} disabled={connect.isPending}><Cable size={17} />{data.ibkr.connected ? 'IBKR 已连接' : '连接 IBKR'}</button></div></div>
      <div className="hero-visual"><div className="pulse-ring"><Activity size={38} /><span>{data.high_score_count}</span><small>高分候选</small></div><div className="visual-note"><ShieldCheck size={17} />研究模式 · 不下单</div></div>
    </section>
    <section className="metric-grid">
      <Metric icon={<Activity />} label="累计信号" value={data.signal_count} hint="可回溯解释" />
      <Metric icon={<Sparkles />} label="80+ 高分" value={data.high_score_count} hint="优先审阅" />
      <Metric icon={<BookOpenCheck />} label="启用规则" value={data.active_rule_count} hint="资料驱动" />
      <Metric icon={<RefreshCw />} label="股票池" value={data.symbol_count} hint={data.latest_job ? `Job #${data.latest_job.id} ${data.latest_job.status}` : '等待扫描'} />
    </section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">RANKED SETUPS</span><h2>当前最高质量候选</h2></div><Link className="text-link" to="/scanner">查看全部 →</Link></div><ResultTable results={data.top_results} /></section>
    <section className="connection-strip"><span className={data.ibkr.connected ? 'connection-icon online' : 'connection-icon'}><Cable size={18} /></span><div><strong>IBKR {data.ibkr.connected ? '在线' : '离线'}</strong><p>{data.ibkr.message} · {data.ibkr.host}:{data.ibkr.port} · Market data type {data.ibkr.market_data_type}</p></div></section>
    <section className="connection-strip"><span className="connection-icon online"><Clock3 size={18} /></span><div><strong>日线自动更新 · {data.sync.daily_time} {data.sync.timezone}</strong><p>美股交易日运行（自动跳过周末和交易所休市日） · 每只股票保留最近 {data.sync.retention_trading_days} 个交易日 · {data.sync.running ? `同步中 ${data.sync.processed}/${data.sync.total}` : `下次 ${formatNextRun(data.sync.next_run_at)}`}</p></div></section>
    <section className="connection-strip"><span className={data.digest.configured && data.digest.enabled ? 'connection-icon online' : 'connection-icon'}><Mail size={18} /></span><div><strong>候选邮件 · 美股交易日 {data.digest.daily_time} {data.digest.timezone}</strong><p>收件人 {data.digest.recipient} · {data.digest.configured ? (data.digest.enabled ? `已启用，下次 ${formatNextRun(data.digest.next_run_at)}` : 'SMTP 已配置，调度未启用') : '等待安全配置 Gmail SMTP 应用密码'}</p></div></section>
  </div>
}

function Metric({ icon, label, value, hint }: { icon: React.ReactNode; label: string; value: number; hint: string }) {
  return <article className="metric-card"><div className="metric-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{hint}</small></div></article>
}

function formatNextRun(value: string | null) { return value ? new Date(value).toLocaleString('zh-CN') : '等待调度器启动' }
