export interface Case {
  id: string
  case_name?: string
  title?: string
  court_id?: string
  court_name?: string
  date_filed?: string
  decision_date?: string
  citation_count?: number
  url?: string
  content?: string
  snippet?: string
  similarity?: number
  score?: number
  citator_badge?: 'green' | 'yellow' | 'red'
  citations?: string[]
  metadata?: any
}

export interface SearchRequest {
  query: string
  search_type: 'keyword' | 'semantic' | 'hybrid'
  jurisdiction?: string
  date_from?: string
  date_to?: string
  limit?: number
}

export interface SearchResponse {
  results: Case[]
  count: number
  query: string
  search_type: string
}

export interface CitatorResult {
  case_id: string
  badge: 'green' | 'yellow' | 'red'
  citing_cases: Case[]
  negative_treatments: Case[]
  positive_treatments: Case[]
}

export interface TransparencyStats {
  month_name: string
  month_summaries: number
  month_ai_cost: number
  month_hosting_cost: number
  month_total_cost: number
  monthly_donations: number
  total_summaries: number
  total_ai_cost: number
  monthly_goal: number
  goal_percent: number
  kofi_url: string
  charity_name: string
  charity_description: string
  charity_url: string
}