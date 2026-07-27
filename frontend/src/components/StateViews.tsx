export function Loading({ label = '正在加载市场结构…' }: { label?: string }) {
  return <div className="state-card"><span className="spinner" /><p>{label}</p></div>
}

export function ErrorState({ error }: { error: Error }) {
  return <div className="state-card error-state"><strong>无法读取数据</strong><p>{error.message}</p></div>
}

export function ScoreBadge({ score }: { score: number }) {
  const tone = score >= 80 ? 'score-high' : score >= 65 ? 'score-mid' : 'score-low'
  return <span className={`score-badge ${tone}`}>{score.toFixed(0)}</span>
}
