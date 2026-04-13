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

export interface Outline {
  id: number
  user_id?: string
  title: string
  subject: string
  professor: string | null
  law_school: string | null
  semester: string | null
  year: number | null
  description: string | null
  filename: string
  file_url: string
  file_size: number | null
  file_type: string | null
  visibility: 'private' | 'unlisted' | 'public'
  download_count: number
  fork_count: number
  forked_from: number | null
  has_content?: boolean
  content?: string
  created_at: string
  username?: string
  full_name?: string
  author_school?: string
  is_owner?: boolean
}

export interface OutlineConversation {
  id: number
  mode: 'multiple_choice' | 'short_answer' | 'practice_essay' | 'ask'
  message_count: number
  created_at: string
  updated_at: string
}

export interface OutlineMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  model?: string
  created_at?: string
}

export interface StudyNote {
  id: number
  title: string
  tags: string[] | null
  filename: string
  file_size: number | null
  file_type: string | null
  char_count: number
  created_at: string
}

export interface TagCount {
  tag: string
  count: number
}

export interface Conversation {
  id: number
  title: string | null
  note_ids: number[]
  case_id?: string | null
  message_count?: number
  created_at: string
  updated_at: string
}

export interface ChatMessageType {
  id: number
  role: 'user' | 'assistant'
  content: string
  model: string | null
  created_at: string
}

export interface UsageInfo {
  tier: 'free' | 'pro'
  messages_today: number
  daily_limit: number | null
  messages_remaining: number | null
  model: string
  is_byok?: boolean
}

export interface AdminUser {
  id: string
  email: string | null
  username: string | null
  full_name: string | null
  tier: 'free' | 'pro'
  messages_today: number
  daily_limit: number | null
  custom_daily_limit: number | null
  model_override: string | null
  effective_model: string
  last_message_date: string | null
  profile_created_at: string | null
  last_active: string | null
}

// Study Session Engine types
export interface Mindmap {
  id: number
  name: string
  node_count: number
  max_depth: number
  nodes_mastered: number
  is_public?: boolean
  subject?: string | null
  created_at: string
}

export interface CommunityMindmap {
  id: number
  name: string
  node_count: number
  max_depth: number
  subject: string | null
  author: string
  created_at: string
}

export interface MindmapNode {
  node_id: string
  parent_node_id: string | null
  depth: number
  text: string
  is_leaf: boolean
  case_refs: NodeRef[]
  rule_refs: NodeRef[]
  sort_order: number
  mastery: 'unseen' | 'learning' | 'mastered'
  correct_streak: number
  total_attempts: number
}

export interface NodeRef {
  name?: string
  case_id?: string | null
  ref?: string
  item_id?: number | null
  slug?: string | null
}

export interface StudySession {
  session_id: number
  resumed?: boolean
  completed?: boolean
  current_node_id: string
  question: string
  breadcrumb: string[]
  mode: string
  streak: number
  max_streak: number
  nodes_visited: number
  nodes_mastered: number
  total_correct: number
  total_incorrect: number
  total_nodes: number
  node_text: string
  case_refs: NodeRef[]
  rule_refs: NodeRef[]
  message?: string
}

export interface NodeProgress {
  node_id: string
  text: string
  depth: number
  is_leaf: boolean
  mastery: 'unseen' | 'learning' | 'mastered'
  correct_streak: number
  total_attempts: number
}

export interface AICategoryBreakdown {
  label: string
  calls: number
  cost: number
}

export interface TransparencyStats {
  month_name: string
  month_summaries: number
  month_ai_cost: number
  month_hosting_cost: number
  month_total_cost: number
  month_breakdown: AICategoryBreakdown[]
  monthly_donations: number
  monthly_donations_count: number
  total_donations: number
  total_summaries: number
  total_ai_cost: number
  alltime_breakdown: AICategoryBreakdown[]
  monthly_goal: number
  goal_percent: number
  kofi_url: string
  charity_name: string
  charity_description: string
  charity_url: string
  community_pool_balance: number
  community_pool_healthy: boolean
  community_pool_low: boolean
}

// MSJ Builder types
export interface MSJProject {
  id: number
  title: string
  status: 'draft' | 'generating' | 'complete'
  case_info: MSJCaseInfo
  material_facts: MSJFact[]
  legal_arguments: MSJArgument[]
  documents: MSJDocument[]
  generated_motion: string | null
  motion_metadata: Record<string, any>
  created_at: string
  updated_at: string
  doc_count?: number
}

export interface MSJCaseInfo {
  plaintiff?: string
  defendant?: string
  court?: string
  jurisdiction?: string
  case_number?: string
  representing_side?: string
  judge?: string
  county?: string
}

export interface MSJFact {
  fact_number: number
  text: string
  source_doc_ids: number[]
  source_excerpt: string | null
  // backward compat
  source_doc_id?: number | null
}

export interface MSJArgument {
  issue: string
  standard: string
  argument_text: string
  supporting_case_ids: string[]
  supporting_rule_ids: string[]
}

export interface MSJDocument {
  id: number
  doc_type: string
  title: string
  filename: string
  file_size: number
  file_type: string
  char_count: number
  step: number
  sort_order: number
  created_at: string
}

// Generic Legal Tool types
export interface ToolProject {
  id: number
  tool_type: string
  title: string
  status: 'draft' | 'generating' | 'complete'
  case_info: MSJCaseInfo  // reuse same shape
  form_data: Record<string, any>
  documents: ToolDocument[]
  generated_document: string | null
  document_metadata: Record<string, any>
  created_at: string
  updated_at: string
  doc_count?: number
}

export interface ToolDocument {
  id: number
  doc_type: string
  title: string
  filename: string
  file_size: number
  file_type: string
  char_count: number
  category: string
  sort_order: number
  created_at: string
}

// Affidavit-specific form_data shapes
export interface AffiantInfo {
  name?: string
  title?: string
  relationship_to_case?: string
  employer?: string
  has_personal_knowledge?: boolean
  knowledge_basis?: string
}

export interface AffidavitFact {
  fact_number: number
  text: string
  source_doc_ids: number[]
  knowledge_basis: string
  knowledge_basis_detail?: string
}

export interface AffidavitFormData {
  affiant_info: AffiantInfo
  attestable_facts: AffidavitFact[]
}