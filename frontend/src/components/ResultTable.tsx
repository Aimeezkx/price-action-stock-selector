import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ScanResult } from '../types'
import { ScoreBadge } from './StateViews'

export function ResultTable({ results }: { results: ScanResult[] }) {
  if (!results.length) return <div className="empty-panel"><strong>暂无命中信号</strong><p>降低评分阈值或先同步更多日线数据。</p></div>
  return <div className="table-scroll"><table>
    <thead><tr><th>Ticker</th><th>市值排名</th><th>规则</th><th>Score</th><th>方向</th><th>Entry</th><th>Stop</th><th>Target</th><th>R/R</th><th /></tr></thead>
    <tbody>{results.map((item) => <tr key={item.id}>
      <td><Link className="ticker ticker-link" to={`/chart/${item.symbol}?result=${item.id}`}>{item.symbol}</Link><span className="subcell">{item.signal_date}</span></td>
      <td>{item.market_cap_rank ? `#${item.market_cap_rank}` : '—'}<span className="subcell">{item.index_weight != null ? `${item.index_weight.toFixed(3)}%` : '非 Top 300'}</span></td>
      <td>{item.rule_name}</td><td><ScoreBadge score={item.score} /></td>
      <td><span className={`direction ${item.direction}`}>{item.direction.toUpperCase()}</span></td>
      <td>{item.entry.toFixed(2)}</td><td>{item.stop.toFixed(2)}</td><td>{item.target ? item.target.toFixed(2) : '—'}</td><td>{item.risk_reward ? `${item.risk_reward.toFixed(2)}R` : '—'}</td>
      <td><Link className="row-action" to={`/chart/${item.symbol}?result=${item.id}`} aria-label={`查看 ${item.symbol}`}><ArrowUpRight size={16} /></Link></td>
    </tr>)}</tbody>
  </table></div>
}
