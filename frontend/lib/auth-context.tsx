'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { User, Session } from '@supabase/supabase-js'
import { createClient, Profile, isSupabaseConfigured } from './supabase'

interface ProfileUpdateData {
  full_name?: string
  username?: string
  bio?: string
  avatar_url?: string
  law_school?: string
  graduation_year?: number
  is_public?: boolean
}

interface AuthContextType {
  user: User | null
  profile: Profile | null
  session: Session | null
  isLoading: boolean
  isConfigured: boolean
  signInWithEmail: (email: string, password: string) => Promise<{ error: Error | null }>
  signUpWithEmail: (email: string, password: string, username?: string) => Promise<{ error: Error | null }>
  signInWithOAuth: (provider: 'google' | 'github') => Promise<{ error: Error | null }>
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
  updateProfile: (data: ProfileUpdateData) => Promise<{ error: Error | null }>
  changePassword: (newPassword: string) => Promise<{ error: Error | null }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const supabase = createClient()

  // If Supabase is not configured, provide a minimal context
  if (!isSupabaseConfigured || !supabase) {
    return (
      <AuthContext.Provider
        value={{
          user: null,
          profile: null,
          session: null,
          isLoading: false,
          isConfigured: false,
          signInWithEmail: async () => ({ error: new Error('Supabase not configured') }),
          signUpWithEmail: async () => ({ error: new Error('Supabase not configured') }),
          signInWithOAuth: async () => ({ error: new Error('Supabase not configured') }),
          signOut: async () => {},
          refreshProfile: async () => {},
          updateProfile: async () => ({ error: new Error('Supabase not configured') }),
          changePassword: async () => ({ error: new Error('Supabase not configured') }),
        }}
      >
        {children}
      </AuthContext.Provider>
    )
  }

  // Fetch profile for a user
  const fetchProfile = async (userId: string) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .single()

    if (error) {
      console.error('Error fetching profile:', error)
      return null
    }
    return data as Profile
  }

  // Refresh profile data
  const refreshProfile = async () => {
    if (user) {
      const profileData = await fetchProfile(user.id)
      setProfile(profileData)
    }
  }

  // Initialize auth state
  useEffect(() => {
    let mounted = true
    let timeoutId: NodeJS.Timeout

    const initAuth = async () => {
      try {
        // Get initial session
        const { data: { session: initialSession }, error } = await supabase.auth.getSession()

        if (error) {
          console.error('Error getting session:', error)
          // Clear any stale state
          if (mounted) {
            setSession(null)
            setUser(null)
            setProfile(null)
          }
          return
        }

        if (initialSession?.user && mounted) {
          setSession(initialSession)
          setUser(initialSession.user)
          const profileData = await fetchProfile(initialSession.user.id)
          if (mounted) setProfile(profileData)
        } else if (mounted) {
          // Explicitly clear state if no valid session
          setSession(null)
          setUser(null)
          setProfile(null)
        }
      } catch (error) {
        console.error('Error initializing auth:', error)
        // Clear state on error
        if (mounted) {
          setSession(null)
          setUser(null)
          setProfile(null)
        }
      } finally {
        if (mounted) {
          clearTimeout(timeoutId)
          setIsLoading(false)
        }
      }
    }

    // Failsafe: if auth takes longer than 5 seconds, stop loading anyway
    timeoutId = setTimeout(() => {
      if (mounted) {
        console.warn('Auth initialization timed out')
        setIsLoading(false)
      }
    }, 5000)

    initAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        if (!mounted) return

        // Handle token refresh failure - clear state
        if (event === 'TOKEN_REFRESHED' && !newSession) {
          setSession(null)
          setUser(null)
          setProfile(null)
          setIsLoading(false)
          return
        }

        // Handle sign out
        if (event === 'SIGNED_OUT') {
          setSession(null)
          setUser(null)
          setProfile(null)
          setIsLoading(false)
          return
        }

        setSession(newSession)
        setUser(newSession?.user ?? null)

        if (newSession?.user) {
          const profileData = await fetchProfile(newSession.user.id)
          if (mounted) setProfile(profileData)
        } else {
          setProfile(null)
        }

        setIsLoading(false)
      }
    )

    return () => {
      mounted = false
      clearTimeout(timeoutId)
      subscription.unsubscribe()
    }
  }, [])

  // Sign in with email/password
  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return { error: error as Error | null }
  }

  // Sign up with email/password
  const signUpWithEmail = async (email: string, password: string, username?: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })

    if (error) {
      return { error: error as Error | null }
    }

    // Create profile after successful signup
    if (data.user) {
      const { error: profileError } = await supabase
        .from('profiles')
        .insert({
          id: data.user.id,
          username: username || email.split('@')[0],
          display_name: email.split('@')[0],
        })

      if (profileError) {
        console.error('Error creating profile:', profileError)
        // Don't return error - user is created, profile can be created later
      }
    }

    return { error: null }
  }

  // Sign in with OAuth provider
  const signInWithOAuth = async (provider: 'google' | 'github') => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    return { error: error as Error | null }
  }

  // Sign out
  const signOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
    setSession(null)
  }

  // Update profile via backend API
  const updateProfile = async (data: ProfileUpdateData) => {
    if (!session?.access_token) {
      return { error: new Error('Not authenticated') }
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/api/v1/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const errorData = await response.json()
        return { error: new Error(errorData.detail || 'Failed to update profile') }
      }

      // Use the returned profile data directly instead of refreshing from Supabase
      const updatedProfile = await response.json()
      setProfile({
        id: updatedProfile.id,
        username: updatedProfile.username,
        display_name: updatedProfile.full_name,
        full_name: updatedProfile.full_name,
        avatar_url: updatedProfile.avatar_url,
        bio: updatedProfile.bio,
        reputation: updatedProfile.reputation || 0,
        law_school: updatedProfile.law_school,
        graduation_year: updatedProfile.graduation_year,
        practice_areas: null,
        is_public: updatedProfile.is_public || false,
        created_at: updatedProfile.created_at,
        updated_at: updatedProfile.updated_at,
      })
      return { error: null }
    } catch (error) {
      return { error: error as Error }
    }
  }

  // Change password via Supabase
  const changePassword = async (newPassword: string) => {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    })
    return { error: error as Error | null }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        session,
        isLoading,
        isConfigured: true,
        signInWithEmail,
        signUpWithEmail,
        signInWithOAuth,
        signOut,
        refreshProfile,
        updateProfile,
        changePassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
