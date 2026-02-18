'use client'

import { useState, useEffect } from 'react'
import { Mail, Loader2, Scale, ArrowLeft, MessageCircle, GraduationCap, Lock } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function LoginPage() {
  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot' | 'newpassword'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [username, setUsername] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [recoveryToken, setRecoveryToken] = useState<string | null>(null)

  const { signInWithEmail, signUpWithEmail, resetPassword, isConfigured } = useAuth()
  const router = useRouter()

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
          // Clear recovery session and redirect
          Object.keys(localStorage).forEach(key => {
            if (key.startsWith('sb-')) localStorage.removeItem(key)
          })
          setMessage('Password updated successfully! Redirecting...')
          setTimeout(() => { window.location.href = '/login' }, 1500)
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
          router.push('/')
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
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-neutral-600">Authentication is not configured.</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
            Return home
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Law Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/study"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <GraduationCap className="h-5 w-5" />
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <MessageCircle className="h-5 w-5" />
              </a>
              <Link
                href="/"
                className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 transition"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Back to Search</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Login Form */}
      <main className="flex items-center justify-center py-16 px-4">
        <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-8">
          {/* Header */}
          <h2 className="text-2xl font-bold text-neutral-900 mb-2">
            {mode === 'newpassword' ? 'Set new password' : mode === 'forgot' ? 'Reset your password' : mode === 'signin' ? 'Welcome back' : 'Create an account'}
          </h2>
          <p className="text-neutral-600 mb-6">
            {mode === 'newpassword'
              ? 'Enter your new password below'
              : mode === 'forgot'
              ? 'Enter your email and we\'ll send you a reset link'
              : mode === 'signin'
              ? 'Sign in to access your bookmarks and annotations'
              : 'Join to save cases and participate in discussions'}
          </p>

          {/* Email form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-neutral-700 mb-1">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="johndoe"
                />
              </div>
            )}

            {mode !== 'newpassword' && (
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-neutral-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="you@example.com"
                />
              </div>
            )}

            {mode !== 'forgot' && (
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-neutral-700 mb-1">
                  {mode === 'newpassword' ? 'New password' : 'Password'}
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                    className="text-sm text-blue-600 hover:text-blue-700 mt-1"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
            )}

            {mode === 'newpassword' && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-neutral-700 mb-1">
                  Confirm new password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="••••••••"
                />
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            {message && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
          {mode !== 'newpassword' && <p className="mt-6 text-center text-sm text-neutral-600">
            {mode === 'signin' ? (
              <>
                Don&apos;t have an account?{' '}
                <button
                  onClick={() => {
                    setMode('signup')
                    setError(null)
                    setMessage(null)
                  }}
                  className="text-blue-600 hover:text-blue-700 font-medium"
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
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  Sign in
                </button>
              </>
            )}
          </p>}
        </div>
      </main>
    </div>
  )
}
