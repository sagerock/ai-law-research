import { createBrowserClient } from '@supabase/ssr'
import { SupabaseClient } from '@supabase/supabase-js'

// Check if Supabase is configured
export const isSupabaseConfigured = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL &&
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

let supabaseInstance: SupabaseClient | null = null

export function createClient(): SupabaseClient | null {
  if (!isSupabaseConfigured) {
    return null
  }

  if (!supabaseInstance) {
    supabaseInstance = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
  }

  return supabaseInstance
}

// Type definitions for our database tables
export interface Profile {
  id: string
  username: string | null
  display_name: string | null
  full_name: string | null
  avatar_url: string | null
  bio: string | null
  reputation: number
  law_school: string | null
  graduation_year: number | null
  practice_areas: string[] | null
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface Comment {
  id: string
  case_id: string
  user_id: string
  parent_id: string | null
  content: string
  is_edited: boolean
  created_at: string
  updated_at: string
  // Joined fields from get_comments_for_case function
  username?: string
  display_name?: string
  avatar_url?: string
  user_reputation?: number
  vote_count?: number
  user_vote?: number | null
}

export interface CommentVote {
  id: string
  comment_id: string
  user_id: string
  vote_type: -1 | 1
  created_at: string
}

export interface Bookmark {
  id: string
  user_id: string
  case_id: string
  folder: string
  notes: string | null
  created_at: string
}

export interface Collection {
  id: string
  user_id: string
  name: string
  description: string | null
  is_public: boolean
  subject: string | null
  created_at: string
  updated_at: string
}
