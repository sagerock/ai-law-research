export interface Case {
  id: string
  case_name: string
  court_id?: string
  court_name?: string
  date_filed: string
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