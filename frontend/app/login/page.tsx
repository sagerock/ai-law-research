'use client'

import { useState, useEffect, Suspense } from 'react'
import { Mail, Loader2, Lock } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Header from '@/components/Header'

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  )
}

function LoginPageContent() {
  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot' | 'newpassword'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [username, setUsername] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null)

  const { user, isLoading: authLoading, signInWithEmail, signUpWithEmail, signInWithOAuth, resetPassword, isConfigured } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get('returnTo') || '/'

  // Redirect if already authenticated (unless doing password recovery)
  useEffect(() => {
    if (!authLoading && user && mode !== 'newpassword') {
      router.replace(returnTo)
    }
  }, [authLoading, user, mode, router])

  // Detect password recovery from Supabase redirect
  // Capture access_token immediately before the Supabase client consumes the hash
  useEffect(() => {
    const hash = window.location.hash
    if (hash.includes('type=recovery')) {
      const hashParams = new URLSearchParams(hash.substring(1))
      setRecoveryToken(hashParams.get('access_token'))
      setMode('newpassword')
      setError(null)
      setMessage(null)
    }
  }, [])

  const handleOAuth = async (provider: 'google' | 'github') => {
    setError(null)
    setMessage(null)
    // Redirects the browser to the provider; returnTo is preserved through the
    // /auth/callback route. On failure we stay on the page and surface the error.
    const { error } = await signInWithOAuth(provider, returnTo)
    if (error) {
      setError(error.message)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setIsLoading(true)

    try {
      if (mode === 'newpassword') {
        if (password !== confirmPassword) {
          setError('Passwords do not match')
          setIsLoading(false)
          return
        }
        // Call Supabase API directly — the Supabase client hangs during recovery
        if (!recoveryToken) {
          setError('Recovery session expired. Please request a new reset link.')
          setIsLoading(false)
          return
        }
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
        const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
        const res = await fetch(`${supabaseUrl}/auth/v1/user`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${recoveryToken}`,
            'Content-Type': 'application/json',
            'apikey': supabaseKey || '',
          },
          body: JSON.stringify({ password }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          setError(data.msg || data.message || 'Failed to update password')
        } else {
          setMessage('Password updated successfully! Sign in with your new password.')
          setRecoveryToken(null)
          setTimeout(() => {
            setMode('signin')
            setPassword('')
            setConfirmPassword('')
          }, 1500)
        }
      } else if (mode === 'forgot') {
        const { error } = await resetPassword(email)
        if (error) {
          setError(error.message)
        } else {
          setMessage('Check your email for a password reset link!')
        }
      } else if (mode === 'signin') {
        const { error } = await signInWithEmail(email, password)
        if (error) {
          setError(error.message)
        } else {
          router.push(returnTo)
        }
      } else {
        const { error } = await signUpWithEmail(email, password, username)
        if (error) {
          setError(error.message)
        } else {
          setMessage('Check your email for a confirmation link!')
        }
      }
    } catch (err: any) {
      console.error('Auth error:', err)
      setError(err?.message || 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isConfigured) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-stone-600">Authentication is not configured.</p>
          <Link href="/" className="text-sage-600 hover:text-sage-700 mt-4 inline-block font-medium">
            Return home
          </Link>
        </div>
      </div>
    )
  }

  const heading = mode === 'newpassword'
    ? 'Set new password'
    : mode === 'forgot'
    ? 'Reset password'
    : mode === 'signin'
    ? 'Welcome back'
    : 'Create an account'

  const subtitle = mode === 'newpassword'
    ? 'Enter your new password below.'
    : mode === 'forgot'
    ? 'We\'ll send you a link to reset it.'
    : mode === 'signin'
    ? 'Sign in to access your bookmarks and collections.'
    : 'Join to save cases and participate in discussions.'

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Login Form */}
      <main className="flex items-center justify-center py-16 sm:py-24 px-4">
        <div className="w-full max-w-md animate-fade-in-up">
          {/* Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-stone-200 p-8 sm:p-10">
            {/* Heading */}
            <div className="mb-8">
              <h2 className="font-display text-3xl text-stone-900 mb-2">
                {heading}
              </h2>
              <p className="text-stone-500 text-[15px] leading-relaxed">
                {subtitle}
              </p>
            </div>

            {/* Google sign-in — only for sign in / sign up, not password flows */}
            {(mode === 'signin' || mode === 'signup') && (
              <div className="mb-6">
                <button
                  type="button"
                  onClick={() => handleOAuth('google')}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-stone-200
                             rounded-xl text-stone-700 font-medium hover:bg-stone-50
                             transition-colors cursor-pointer"
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                  <span>Continue with Google</span>
                </button>

                {/* Divider */}
                <div className="relative mt-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-stone-200" />
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-white px-3 text-sm text-stone-400">or</span>
                  </div>
                </div>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {mode === 'signup' && (
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-stone-700 mb-1.5">
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full px-4 py-3 border border-stone-200 rounded-xl text-stone-900
                               placeholder:text-stone-400 focus:outline-none focus:ring-2
                               focus:ring-sage-200 focus:border-sage-400 transition-all"
                    placeholder="johndoe"
                  />
                </div>
              )}

              {mode !== 'newpassword' && (
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-stone-700 mb-1.5">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-stone-200 rounded-xl text-stone-900
                               placeholder:text-stone-400 focus:outline-none focus:ring-2
                               focus:ring-sage-200 focus:border-sage-400 transition-all"
                    placeholder="you@example.com"
                  />
                </div>
              )}

              {mode !== 'forgot' && (
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-stone-700 mb-1.5">
                    {mode === 'newpassword' ? 'New password' : 'Password'}
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    className="w-full px-4 py-3 border border-stone-200 rounded-xl text-stone-900
                               placeholder:text-stone-400 focus:outline-none focus:ring-2
                               focus:ring-sage-200 focus:border-sage-400 transition-all"
                    placeholder="••••••••"
                  />
                  {mode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode('forgot')
                        setError(null)
                        setMessage(null)
                      }}
                      className="text-sm text-sage-600 hover:text-sage-700 mt-2 font-medium transition-colors"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
              )}

              {mode === 'newpassword' && (
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-stone-700 mb-1.5">
                    Confirm new password
                  </label>
                  <input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    className="w-full px-4 py-3 border border-stone-200 rounded-xl text-stone-900
                               placeholder:text-stone-400 focus:outline-none focus:ring-2
                               focus:ring-sage-200 focus:border-sage-400 transition-all"
                    placeholder="••••••••"
                  />
                </div>
              )}

              {error && (
                <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                  {error}
                </div>
              )}

              {message && (
                <div className="p-3.5 bg-sage-50 border border-sage-200 rounded-xl text-sage-800 text-sm">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-sage-700
                           text-white font-medium rounded-xl hover:bg-sage-600
                           disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors shadow-sm cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>
                      {mode === 'newpassword' ? 'Updating...' : mode === 'forgot' ? 'Sending...' : mode === 'signin' ? 'Signing in...' : 'Creating account...'}
                    </span>
                  </>
                ) : (
                  <>
                    {mode === 'newpassword' ? <Lock className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
                    <span>
                      {mode === 'newpassword' ? 'Update password' : mode === 'forgot' ? 'Send reset link' : mode === 'signin' ? 'Sign in' : 'Create account'}
                    </span>
                  </>
                )}
              </button>
            </form>

            {/* Toggle mode */}
            {mode !== 'newpassword' && (
              <p className="mt-8 text-center text-sm text-stone-500">
                {mode === 'signin' ? (
                  <>
                    Don&apos;t have an account?{' '}
                    <button
                      onClick={() => {
                        setMode('signup')
                        setError(null)
                        setMessage(null)
                      }}
                      className="text-sage-600 hover:text-sage-700 font-medium transition-colors"
                    >
                      Sign up
                    </button>
                  </>
                ) : (
                  <>
                    {mode === 'forgot' ? 'Remember your password?' : 'Already have an account?'}{' '}
                    <button
                      onClick={() => {
                        setMode('signin')
                        setError(null)
                        setMessage(null)
                      }}
                      className="text-sage-600 hover:text-sage-700 font-medium transition-colors"
                    >
                      Sign in
                    </button>
                  </>
                )}
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
