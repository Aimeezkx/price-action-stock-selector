export interface IBKRStatus {
  connected: boolean
  host: string
  port: number
  client_id: number
  readonly: boolean
  market_data_type: number
  message: string
}

export interface SymbolItem {
  id: number
  symbol: string
  name: string
  sector: string | null
  exchange: string
  currency: string
  enabled: boolean
  last_synced_at: string | null
}

export interface Rule {
  id: string
  name: string
  category: string
  description: string
  direction: string
  parameters: Record<string, number>
  source_references: SourceReference[]
  enabled: boolean
}

export interface SourceReference {
  source_id: string
  document: string
  pages: number[]
  page_basis: 'pdf' | 'printed'
  section: string
  concept: string
}

export interface KnowledgeSource {
  id: string
  title: string
  filename: string
  category: string
  pages: number
  size_bytes: number
  sha256: string
  extraction_status: 'rules_indexed'
  encryption: string
  available: boolean
  local_path: string
  redistributed: boolean
  indexed_rules: string[]
  evidence_pages: number[]
}

export interface Annotation {
  type: 'line' | 'zone'
  price?: number
  low?: number
  high?: number
  label: string
}

export interface ScanResult {
  id: number
  scan_job_id: number
  symbol: string
  signal_date: string
  rule_id: string
  rule_name: string
  score: number
  direction: string
  entry: number
  stop: number
  target: number
  risk_reward: number
  explanation: string[]
  annotations: Annotation[]
  created_at: string
  market_cap_rank: number | null
  index_weight: number | null
}

export interface DailyBar {
  bar_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  source: string
}

export interface DashboardData {
  symbol_count: number
  active_rule_count: number
  signal_count: number
  high_score_count: number
  latest_job: { id: number; status: string; completed_at: string | null } | null
  top_results: ScanResult[]
  ibkr: IBKRStatus
  sync: SyncStatus
  digest: DigestStatus
}

export interface DigestStatus {
  enabled: boolean
  configured: boolean
  running: boolean
  timezone: string
  daily_time: string
  recipient: string
  next_run_at: string | null
  last_started_at: string | null
  last_finished_at: string | null
  last_error: string | null
  last_job_id: number | null
  last_candidate_count: number
}

export interface SyncStatus {
  enabled: boolean
  running: boolean
  timezone: string
  daily_time: string
  weekdays_only: boolean
  retention_trading_days: number
  next_run_at: string | null
  last_started_at: string | null
  last_finished_at: string | null
  last_error: string | null
  processed: number
  total: number
  succeeded: number
  failed: number
}

export interface BacktestRun {
  id: number
  rule_id: string
  symbols: string[]
  config: { holding_days: number; entry_expiry_days: number; target_r: number }
  metrics: {
    sample_size: number
    win_rate: number
    average_r: number
    profit_factor: number
    max_drawdown_r: number
    expectancy_r: number
    sharpe_like: number
  }
  trades: Array<{ symbol: string; signal_date: string; entry_date: string; exit_date: string; entry: number; exit: number; score: number; r: number; market_cap_rank: number | null; index_weight: number | null }>
}
