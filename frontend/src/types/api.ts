/** Typed interfaces matching the Phase 5 API schemas. */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type Severity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH'
export type ContractStatus = 'UPLOADED' | 'PARSING' | 'READY' | 'ANALYZING' | 'COMPLETED' | 'FAILED'

export interface ModelHealth {
  available: boolean
  state: 'fine_tuned' | 'baseline_on_demand' | string
  device: string
  final_model_present: boolean
  baseline_model_id: string | null
  model_version: string | null
}

export interface Health {
  status: string
  app: string
  version: string
  database: string
  model: ModelHealth
}

export interface AnalysisSummary {
  id: number
  status: string
  overall_risk_score: number | null
  overall_risk_level: RiskLevel | null
  model_state: string | null
  model_version: string | null
  processing_ms: number | null
  completed_at: string | null
  error_message: string | null
}

export interface Contract {
  id: string
  filename: string
  file_type: 'pdf' | 'docx' | 'txt' | string
  status: ContractStatus
  character_count: number | null
  page_count: number | null
  parser_warnings: string[]
  duplicate_of_id: string | null
  created_at: string | null
  latest_analysis: AnalysisSummary | null
}

export interface ContractListResponse {
  total: number
  page: number
  page_size: number
  items: Contract[]
}

export interface RawText {
  id: string
  filename: string
  character_count: number
  text: string
}

export interface Entities {
  parties: string | null
  agreement_date: string | null
  effective_date: string | null
  expiration_date: string | null
  governing_law: string | null
  document_name: string | null
}

export interface ClauseResult {
  clause_type: string
  found: boolean
  confidence: number | null
  text: string
  start_char: number | null
  end_char: number | null
  risk_level: Severity | null
  risk_reason: string | null
  uncertain: boolean
}

export interface RiskFinding {
  rule_id: string
  clause_type: string | null
  severity: Severity | null
  weight: number | null
  reason: string | null
  evidence: string | null
  confidence: number | null
  uncertain: boolean
}

export interface Analysis {
  analysis_id: number
  contract_id: string
  status: string
  model: { name: string | null; version: string | null; state: string | null; device: string | null }
  overall_risk: { score: number | null; level: RiskLevel | null }
  entities: Entities
  clauses: ClauseResult[]
  risk_findings: RiskFinding[]
  processing_ms: number | null
  disclaimer: string | null
  created_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface Stats {
  contracts_total: number
  completed_analyses: number
  failed_analyses: number
  risk_distribution: { LOW: number; MEDIUM: number; HIGH: number }
  avg_processing_ms: number | null
  clauses_detected_total: number
}

/** Structured API error envelope from the backend. */
export interface ApiErrorEnvelope {
  error: string
  message: string
  request_id?: string
  detail?: unknown
}
