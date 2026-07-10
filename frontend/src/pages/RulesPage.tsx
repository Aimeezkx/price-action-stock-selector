import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookMarked, ExternalLink, ToggleLeft, ToggleRight } from 'lucide-react'
import { api } from '../api'
import { ErrorState, Loading } from '../components/StateViews'
import type { KnowledgeSource, Rule } from '../types'

export function RulesPage() {
  const queryClient = useQueryClient()
  const rules = useQuery({ queryKey: ['rules'], queryFn: () => api.get<Rule[]>('/api/price-action/rules') })
  const sources = useQuery({ queryKey: ['knowledge-sources'], queryFn: () => api.get<KnowledgeSource[]>('/api/knowledge/sources') })
  const toggle = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/api/price-action/rules/${id}`, { enabled }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }) })
  if (rules.isLoading || sources.isLoading) return <Loading label="正在打开规则库…" />
  if (rules.error || sources.error) return <ErrorState error={(rules.error || sources.error) as Error} />
  const totalPages = sources.data!.reduce((total, source) => total + source.pages, 0)
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">RULE LIBRARY</span><h1>可解释的价格行为规则</h1><p>每条规则均包含可调参数、资料页码与结构化评分；启用状态直接影响扫描器。</p></div><div className="source-chip"><BookMarked size={17} />{sources.data!.length} 个本地资料源 · {totalPages.toLocaleString()} 页</div></div>
    <section className="source-catalog panel">
      <div className="section-heading"><div><span className="eyebrow">LOCAL SOURCE CATALOG</span><h2>本地价格行为资料</h2></div><span className="muted">PDF 仅登记路径与指纹，不上传仓库</span></div>
      <div className="source-grid">{sources.data!.map((source) => <article className="source-card" key={source.id}>
        <div className="source-card-head"><span className={`category category-${source.category}`}>{source.category}</span><span className={source.available ? 'source-available' : 'source-missing'}>{source.available ? '本机可用' : '本机缺失'}</span></div>
        <h3>{source.title}</h3><p>{source.pages.toLocaleString()} 页 · {formatSize(source.size_bytes)}</p>
        <small>已规则化 · {source.indexed_rules.length} 条规则 · {source.evidence_pages.length} 个页码证据</small>
        <code title={source.local_path}>{source.local_path}</code>
      </article>)}</div>
    </section>
    <section className="rule-grid">{rules.data!.map((rule) => <article className={rule.enabled ? 'rule-card' : 'rule-card disabled'} key={rule.id}>
      <div className="rule-card-head"><span className={`category category-${rule.category}`}>{rule.category}</span><button className="toggle-button" onClick={() => toggle.mutate({ id: rule.id, enabled: !rule.enabled })} aria-label={`${rule.enabled ? '禁用' : '启用'} ${rule.name}`}>{rule.enabled ? <ToggleRight /> : <ToggleLeft />}</button></div>
      <h2>{rule.name}</h2><p>{rule.description}</p>
      <div className="parameter-list">{Object.entries(rule.parameters).map(([key, value]) => <span key={key}><small>{key.replaceAll('_', ' ')}</small><strong>{value}</strong></span>)}</div>
      <div className="source-block"><span className="eyebrow">SOURCE EVIDENCE</span>{rule.source_references.map((source) => <div key={`${source.source_id}-${source.pages.join('-')}-${source.concept}`}><ExternalLink size={13} /><p><strong>{source.document}</strong><br />{source.page_basis === 'pdf' ? 'PDF 页' : '书籍印刷页'} {source.pages.join(', ')} · {source.section}<br /><span>{source.concept}</span></p></div>)}</div>
    </article>)}</section>
  </div>
}

function formatSize(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(1)} MB` }
