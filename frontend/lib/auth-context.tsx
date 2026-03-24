'use client'

import { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react'
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
  resetPassword: (email: string) => Promise<{ error: Error | null }>
  refreshProfile: () => Promise<void>
  updateProfile: (data: ProfileUpdateData) => Promise<{ error: Error | null }>
  changePassword: (newPassword: string) => Promise<{ error: Error | null }>
  getAccessToken: () => Promise<string | null>
  getAuthHeaders: () => Promise<Record<string, string>>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Monotonic counter to prevent stale async operations from clobbering fresh state
  const authVersionRef = useRef(0)

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
          resetPassword: async () => ({ error: new Error('Supabase not configured') }),
          refreshProfile: async () => {},
          updateProfile: async () => ({ error: new Error('Supabase not configured') }),
          changePassword: async () => ({ error: new Error('Supabase not configured') }),
          getAccessToken: async () => null,
          getAuthHeaders: async () => ({}),
        }}
      >
        {children}
      </AuthContext.Provider>
    )
  }

  // Fetch profile for a user
  const fetchProfile = async (userId: string, email?: string) => {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .maybeSingle()

    if (error) {
      console.error('Error fetching profile:', error)
      return null
    }

    // Auto-create profile if it doesn't exist (e.g. OAuth sign-in)
    if (!data) {
      const username = email?.split('@')[0] || 'user'
      const { data: newProfile, error: insertError } = await supabase
        .from('profiles')
        .insert({ id: userId, username, display_name: username })
        .select()
        .single()

      if (insertError) {
        console.error('Error creating profile:', insertError)
        return null
      }
      return newProfile as Profile
    }

    return data as Profile
  }

  // Refresh profile data
  const refreshProfile = async () => {
    if (user) {
      const profileData = await fetchProfile(user.id, user.email)
      setProfile(profileData)
    }
  }

  // Initialize auth state
  useEffect(() => {
    let mounted = true
    let timeoutId: NodeJS.Timeout

    // Helper to apply session state with version check
    const applySession = async (newSession: Session | null, version: number) => {
      if (!mounted || version < authVersionRef.current) return

      setSession(newSession)
      setUser(newSession?.user ?? null)

      if (newSession?.user) {
        // Set loading false immediately — don't block on profile fetch
        setIsLoading(false)
        const profileData = await fetchProfile(newSession.user.id, newSession.user.email)
        // Check version again after async fetch — a newer event may have arrived
        if (mounted && version >= authVersionRef.current) {
          setProfile(profileData)
        }
      } else {
        setProfile(null)
        setIsLoading(false)
      }
    }

    const initAuth = async () => {
      const version = ++authVersionRef.current

      try {
        // Get initial session — timeout after 5s in case token refresh hangs
        const getSessionWithTimeout = Promise.race([
          supabase.auth.getSession(),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('getSession timed out')), 5000)
          ),
        ])

        const { data: { session: initialSession }, error } = await getSessionWithTimeout

        if (error) {
          console.error('Error getting session:', error)
        }

        await applySession(
          error ? null : (initialSession ?? null),
          version
        )
      } catch (error: any) {
        if (error?.message === 'getSession timed out') {
          // Token refresh is hanging — just proceed as unauthenticated
          // Don't clear tokens, they may still be valid for other tabs
          console.warn('Auth init timed out, proceeding as unauthenticated')
        } else {
          console.error('Error initializing auth:', error)
        }
        await applySession(null, version)
      } finally {
        if (mounted) {
          clearTimeout(timeoutId)
          setIsLoading(false)
        }
      }
    }

    // Failsafe: if auth takes longer than 8 seconds, stop loading anyway
    timeoutId = setTimeout(() => {
      if (mounted) {
        setIsLoading(false)
      }
    }, 8000)

    initAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        if (!mounted) return

        // Bump version — this ensures any in-flight initAuth or older
        // event handler won't overwrite this newer state
        const version = ++authVersionRef.current

        // Handle sign out
        if (event === 'SIGNED_OUT') {
          await applySession(null, version)
          return
        }

        // Handle token refresh failure — only clear if no fresh sign-in
        // arrived in the meantime
        if (event === 'TOKEN_REFRESHED' && !newSession) {
          await applySession(null, version)
          return
        }

        await applySession(newSession, version)
      }
    )

    // @supabase/ssr stores sessions in document.cookie, not localStorage,
    // so StorageEvent never fires. Instead, re-sync from cookies when the
    // tab becomes visible — another tab may have refreshed or signed out.
    const handleVisibilityChange = () => {
      if (document.visibilityState !== 'visible' || !mounted) return

      supabase.auth.getSession().then(({ data: { session: freshSession } }) => {
        if (!mounted) return
        const version = ++authVersionRef.current

        // Compare with current state to avoid unnecessary re-renders
        const currentToken = session?.access_token
        const freshToken = freshSession?.access_token

        if (currentToken !== freshToken) {
          applySession(freshSession, version)
        }
      })
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      mounted = false
      clearTimeout(timeoutId)
      subscription.unsubscribe()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  // Helper: race a promise against a timeout
  const withTimeout = <T,>(promise: Promise<T>, ms: number): Promise<T> => {
    return Promise.race([
      promise,
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Request timed out. Please try again.')), ms)
      ),
    ])
  }

  // Sign in with email/password
  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await withTimeout(
      supabase.auth.signInWithPassword({ email, password }),
      15000
    )
    return { error: error as Error | null }
  }

  // Sign up with email/password
  const signUpWithEmail = async (email: string, password: string, username?: string) => {
    const { data, error } = await withTimeout(
      supabase.auth.signUp({ email, password }),
      15000
    )

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

  // Sign out — call Supabase signOut (invalidates server session + notifies other tabs)
  // with a timeout fallback in case the Supabase client hangs
  const signOut = async () => {
    // Clear local state immediately so UI updates
    setUser(null)
    setProfile(null)
    setSession(null)

    try {
      // Give Supabase 3 seconds to sign out properly (invalidates refresh token server-side)
      await withTimeout(supabase.auth.signOut(), 3000)
    } catch {
      // Fallback: manually clear localStorage if signOut hangs or fails
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('sb-')) localStorage.removeItem(key)
      })
    }

    window.location.href = '/'
  }

  // Reset password — redirects to /login?reset=true for new password form
  const resetPassword = async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/login?reset=true`,
      })
      return { error: error as Error | null }
    } catch (err) {
      return { error: err as Error }
    }
  }

  // Update profile via backend API
  const updateProfile = async (data: ProfileUpdateData) => {
    const token = await getAccessToken()
    if (!token) {
      return { error: new Error('Not authenticated') }
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/api/v1/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
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

  // Token refresh is handled by Supabase SDK's autoRefreshToken: true.
  // Do NOT add a manual refresh timer here — it races with the SDK's
  // built-in refresh and with other tabs, causing refresh token rotation
  // conflicts that log users out.

  // Get a fresh access token — delegates refresh to SDK (autoRefreshToken).
  // Avoids calling refreshSession() directly to prevent multi-tab race conditions.
  const getAccessToken = async (): Promise<string | null> => {
    try {
      const { data: { session: currentSession } } = await supabase.auth.getSession()
      if (!currentSession) return null

      // If token is expired or about to expire, let getUser() trigger the
      // SDK's internal refresh (which uses navigator.locks for tab safety)
      const expiresAt = currentSession.expires_at
      if (expiresAt && expiresAt * 1000 < Date.now() + 60000) {
        const { data: { user: refreshedUser }, error } = await Promise.race([
          supabase.auth.getUser(),
          new Promise<{ data: { user: null }, error: Error }>((resolve) =>
            setTimeout(() => resolve({ data: { user: null }, error: new Error('timed out') }), 5000)
          ),
        ])
        if (error || !refreshedUser) {
          console.warn('Auth token near expiry, refresh pending')
          // Return the current token anyway — it may still be valid for a few more seconds
          return currentSession.access_token
        }
        // After getUser, re-read the session which the SDK may have refreshed
        const { data: { session: freshSession } } = await supabase.auth.getSession()
        if (freshSession) {
          setSession(freshSession)
          setUser(freshSession.user)
          return freshSession.access_token
        }
      }

      return currentSession.access_token
    } catch (e) {
      console.error('getAccessToken error:', e)
      return null
    }
  }

  // Get auth headers with a fresh token — use this for API calls
  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    const token = await getAccessToken()
    if (!token) return {}
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
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
        resetPassword,
        refreshProfile,
        updateProfile,
        changePassword,
        getAccessToken,
        getAuthHeaders,
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
