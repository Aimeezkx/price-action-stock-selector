import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookMarked, ExternalLink, ToggleLeft, ToggleRight } from 'lucide-react'
import { api } from '../api'
import { ErrorState, Loading } from '../components/StateViews'
import type { Rule } from '../types'

export function RulesPage() {
  const queryClient = useQueryClient()
  const rules = useQuery({ queryKey: ['rules'], queryFn: () => api.get<Rule[]>('/api/price-action/rules') })
  const toggle = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api.patch(`/api/price-action/rules/${id}`, { enabled }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }) })
  if (rules.isLoading) return <Loading label="正在打开规则库…" />
  if (rules.error) return <ErrorState error={rules.error} />
  return <div className="page-stack">
    <div className="page-heading"><div><span className="eyebrow">RULE LIBRARY</span><h1>可解释的价格行为规则</h1><p>每条规则均包含可调参数、资料页码与结构化评分；启用状态直接影响扫描器。</p></div><div className="source-chip"><BookMarked size={17} />1 个本地资料源 · 5,414 页</div></div>
    <section className="rule-grid">{rules.data!.map((rule) => <article className={rule.enabled ? 'rule-card' : 'rule-card disabled'} key={rule.id}>
      <div className="rule-card-head"><span className={`category category-${rule.category}`}>{rule.category}</span><button className="toggle-button" onClick={() => toggle.mutate({ id: rule.id, enabled: !rule.enabled })} aria-label={`${rule.enabled ? '禁用' : '启用'} ${rule.name}`}>{rule.enabled ? <ToggleRight /> : <ToggleLeft />}</button></div>
      <h2>{rule.name}</h2><p>{rule.description}</p>
      <div className="parameter-list">{Object.entries(rule.parameters).map(([key, value]) => <span key={key}><small>{key.replaceAll('_', ' ')}</small><strong>{value}</strong></span>)}</div>
      <div className="source-block"><span className="eyebrow">SOURCE EVIDENCE</span>{rule.source_references.map((source) => <div key={`${source.pages.join('-')}-${source.concept}`}><ExternalLink size={13} /><p><strong>{source.document}</strong><br />p. {source.pages.join(', ')} · {source.concept}</p></div>)}</div>
    </article>)}</section>
  </div>
}
