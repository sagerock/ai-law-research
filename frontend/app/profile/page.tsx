'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import {
  Scale,
  User,
  Settings,
  MessageSquare,
  Save,
  Loader2,
  Eye,
  EyeOff,
  Lock,
  GraduationCap,
  Building,
  FileText,
  ChevronRight,
  AlertCircle,
  Check,
  FolderOpen,
  Heart
} from 'lucide-react'
import { UserMenu } from '@/components/auth/UserMenu'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UserComment {
  id: number
  case_id: string
  case_title: string
  case_cite: string | null
  content: string
  is_edited: boolean
  created_at: string
}

export default function ProfilePage() {
  const { user, session, profile, isLoading: authLoading, isConfigured, updateProfile, changePassword, refreshProfile } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = useState(false)

  // Profile form state
  const [fullName, setFullName] = useState('')
  const [username, setUsername] = useState('')
  const [bio, setBio] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [lawSchool, setLawSchool] = useState('')
  const [graduationYear, setGraduationYear] = useState<number | ''>('')
  const [isPublic, setIsPublic] = useState(false)

  // Password change state
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswordForm, setShowPasswordForm] = useState(false)

  // Comments state
  const [comments, setComments] = useState<UserComment[]>([])
  const [isLoadingComments, setIsLoadingComments] = useState(false)

  // UI state
  const [isSaving, setIsSaving] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Load profile data into form
  useEffect(() => {
    if (profile) {
      setFullName(profile.full_name || profile.display_name || '')
      setUsername(profile.username || '')
      setBio(profile.bio || '')
      setAvatarUrl(profile.avatar_url || '')
      setLawSchool(profile.law_school || '')
      setGraduationYear(profile.graduation_year || '')
      setIsPublic(profile.is_public || false)
    }
  }, [profile])

  // Fetch user's comments
  useEffect(() => {
    const fetchComments = async () => {
      if (!session?.access_token) return

      setIsLoadingComments(true)
      try {
        const response = await fetch(`${API_URL}/api/v1/profile/comments`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          setComments(data.comments)
        }
      } catch (error) {
        console.error('Failed to fetch comments:', error)
      } finally {
        setIsLoadingComments(false)
      }
    }

    if (session?.access_token) {
      fetchComments()
    }
  }, [session])

  // Handle profile save
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setIsSaving(true)

    const updateData: Record<string, unknown> = {}
    if (fullName !== (profile?.full_name || profile?.display_name || '')) {
      updateData.full_name = fullName
    }
    if (username !== (profile?.username || '')) {
      updateData.username = username
    }
    if (bio !== (profile?.bio || '')) {
      updateData.bio = bio
    }
    if (avatarUrl !== (profile?.avatar_url || '')) {
      updateData.avatar_url = avatarUrl
    }
    if (lawSchool !== (profile?.law_school || '')) {
      updateData.law_school = lawSchool
    }
    if (graduationYear !== (profile?.graduation_year || '')) {
      updateData.graduation_year = graduationYear || null
    }
    if (isPublic !== (profile?.is_public || false)) {
      updateData.is_public = isPublic
    }

    if (Object.keys(updateData).length === 0) {
      setError('No changes to save')
      setIsSaving(false)
      return
    }

    const { error: updateError } = await updateProfile(updateData as Parameters<typeof updateProfile>[0])

    if (updateError) {
      setError(updateError.message)
    } else {
      setSuccess('Profile updated successfully!')
      setTimeout(() => setSuccess(null), 3000)
    }

    setIsSaving(false)
  }

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(null)

    if (newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters')
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }

    setIsChangingPassword(true)

    const { error: passwordErr } = await changePassword(newPassword)

    if (passwordErr) {
      setPasswordError(passwordErr.message)
    } else {
      setPasswordSuccess('Password changed successfully!')
      setNewPassword('')
      setConfirmPassword('')
      setShowPasswordForm(false)
      setTimeout(() => setPasswordSuccess(null), 3000)
    }

    setIsChangingPassword(false)
  }

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

    if (diffInDays === 0) return 'Today'
    if (diffInDays === 1) return 'Yesterday'
    if (diffInDays < 7) return `${diffInDays} days ago`
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`
    return date.toLocaleDateString()
  }

  // Show login prompt if not authenticated
  if (!mounted || authLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!isConfigured || !user) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <header className="border-b bg-white">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <Scale className="h-6 w-6 text-blue-600" />
              <span className="text-xl font-semibold">Sage&apos;s Study Group</span>
            </Link>
          </div>
        </header>
        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <User className="h-16 w-16 text-neutral-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">Sign in to view your profile</h1>
          <p className="text-neutral-600 mb-6">You need to be signed in to manage your profile settings.</p>
          <Link
            href="/login"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Sign In
          </Link>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2">
                <Scale className="h-6 w-6 text-blue-600" />
                <span className="text-xl font-semibold">Sage&apos;s Study Group</span>
              </Link>
              <nav className="hidden md:flex items-center gap-4">
                <Link
                  href="/briefcheck"
                  className="flex items-center gap-1 text-sm text-neutral-600 hover:text-blue-600"
                >
                  <FileText className="h-4 w-4" />
                  Brief Check
                </Link>
                <Link
                  href="/library"
                  className="flex items-center gap-1 text-sm text-neutral-600 hover:text-blue-600"
                >
                  <FolderOpen className="h-4 w-4" />
                  My Library
                </Link>
                <Link
                  href="/transparency"
                  className="flex items-center gap-1 text-sm text-neutral-600 hover:text-blue-600"
                >
                  <Heart className="h-4 w-4" />
                  Transparency
                </Link>
              </nav>
            </div>
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-neutral-900 mb-8 flex items-center gap-2">
          <User className="h-6 w-6" />
          My Profile
        </h1>

        <div className="grid gap-6">
          {/* Profile Information */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Profile Information
            </h2>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}

            {success && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
                <Check className="h-4 w-4" />
                {success}
              </div>
            )}

            <form onSubmit={handleSaveProfile} className="space-y-4">
              {/* Avatar Preview */}
              <div className="flex items-center gap-4">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt="Avatar"
                    className="h-16 w-16 rounded-full object-cover border"
                  />
                ) : (
                  <div className="h-16 w-16 rounded-full bg-blue-600 text-white flex items-center justify-center text-xl font-medium">
                    {(fullName || username || user.email || 'U')[0].toUpperCase()}
                  </div>
                )}
                <div className="flex-1">
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Avatar URL
                  </label>
                  <input
                    type="url"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://example.com/avatar.jpg"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Name and Username */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="John Doe"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                    placeholder="johndoe"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <p className="text-xs text-neutral-500 mt-1">Lowercase letters, numbers, and underscores only</p>
                </div>
              </div>

              {/* Bio */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Bio
                </label>
                <textarea
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  placeholder="Tell others about yourself..."
                  rows={3}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
              </div>

              {/* Education */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1 flex items-center gap-1">
                    <Building className="h-4 w-4" />
                    Law School
                  </label>
                  <input
                    type="text"
                    value={lawSchool}
                    onChange={(e) => setLawSchool(e.target.value)}
                    placeholder="Harvard Law School"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1 flex items-center gap-1">
                    <GraduationCap className="h-4 w-4" />
                    Graduation Year
                  </label>
                  <input
                    type="number"
                    value={graduationYear}
                    onChange={(e) => setGraduationYear(e.target.value ? parseInt(e.target.value) : '')}
                    placeholder="2025"
                    min="1900"
                    max="2100"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Public Profile Toggle */}
              <div className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg">
                <div className="flex items-center gap-3">
                  {isPublic ? (
                    <Eye className="h-5 w-5 text-green-600" />
                  ) : (
                    <EyeOff className="h-5 w-5 text-neutral-400" />
                  )}
                  <div>
                    <p className="font-medium text-neutral-900">Public Profile</p>
                    <p className="text-sm text-neutral-500">
                      {isPublic
                        ? 'Others can see your profile and comments'
                        : 'Your profile is private'}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsPublic(!isPublic)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    isPublic ? 'bg-green-600' : 'bg-neutral-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      isPublic ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save Changes
                </button>
              </div>
            </form>
          </div>

          {/* Password Change */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Security
            </h2>

            {passwordError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                <AlertCircle className="h-4 w-4" />
                {passwordError}
              </div>
            )}

            {passwordSuccess && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
                <Check className="h-4 w-4" />
                {passwordSuccess}
              </div>
            )}

            {!showPasswordForm ? (
              <button
                onClick={() => setShowPasswordForm(true)}
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                Change Password
              </button>
            ) : (
              <form onSubmit={handleChangePassword} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter new password"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={isChangingPassword}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isChangingPassword ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Lock className="h-4 w-4" />
                    )}
                    Update Password
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowPasswordForm(false)
                      setNewPassword('')
                      setConfirmPassword('')
                      setPasswordError(null)
                    }}
                    className="px-4 py-2 text-neutral-600 hover:text-neutral-900"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* My Comments */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              My Comments ({comments.length})
            </h2>

            {isLoadingComments ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
              </div>
            ) : comments.length === 0 ? (
              <p className="text-neutral-500 text-center py-8">
                You haven&apos;t made any comments yet.
              </p>
            ) : (
              <div className="space-y-3">
                {comments.map((comment) => (
                  <Link
                    key={comment.id}
                    href={`/case/${comment.case_id}`}
                    className="block p-4 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-neutral-900 truncate">
                          {comment.case_title}
                        </p>
                        {comment.case_cite && (
                          <p className="text-sm text-neutral-500">{comment.case_cite}</p>
                        )}
                        <p className="text-sm text-neutral-700 mt-1 line-clamp-2">
                          {comment.content}
                        </p>
                        <p className="text-xs text-neutral-400 mt-1">
                          {formatRelativeTime(comment.created_at)}
                          {comment.is_edited && ' (edited)'}
                        </p>
                      </div>
                      <ChevronRight className="h-5 w-5 text-neutral-400 flex-shrink-0" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
