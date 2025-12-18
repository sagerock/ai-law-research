'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  Scale,
  User,
  MessageSquare,
  Loader2,
  Lock,
  GraduationCap,
  Building,
  FileText,
  ChevronRight,
  FolderOpen,
  Heart
} from 'lucide-react'
import { UserMenu } from '@/components/auth/UserMenu'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PublicProfile {
  id?: string
  username: string
  full_name?: string
  avatar_url?: string
  bio?: string
  reputation?: number
  law_school?: string
  graduation_year?: number
  is_public: boolean
  message?: string
  created_at?: string
}

interface UserComment {
  id: number
  case_id: string
  case_title: string
  case_cite: string | null
  content: string
  is_edited: boolean
  created_at: string
}

export default function PublicProfilePage() {
  const params = useParams()
  const username = params.username as string

  const [profile, setProfile] = useState<PublicProfile | null>(null)
  const [comments, setComments] = useState<UserComment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingComments, setIsLoadingComments] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch profile
  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(`${API_URL}/api/v1/users/${username}`)

        if (response.status === 404) {
          setError('User not found')
          return
        }

        if (!response.ok) {
          throw new Error('Failed to fetch profile')
        }

        const data = await response.json()
        setProfile(data)

        // If profile is public, fetch comments
        if (data.is_public) {
          fetchComments()
        }
      } catch (err) {
        setError('Failed to load profile')
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }

    if (username) {
      fetchProfile()
    }
  }, [username])

  // Fetch user comments
  const fetchComments = async () => {
    setIsLoadingComments(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/users/${username}/comments`)
      if (response.ok) {
        const data = await response.json()
        setComments(data.comments)
      }
    } catch (err) {
      console.error('Failed to fetch comments:', err)
    } finally {
      setIsLoadingComments(false)
    }
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

  // Get initials for avatar
  const getInitials = (name: string) => {
    return name.slice(0, 2).toUpperCase()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <header className="border-b bg-white">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <Scale className="h-6 w-6 text-blue-600" />
              <span className="text-xl font-semibold">Sage&apos;s Study Group</span>
            </Link>
            <UserMenu />
          </div>
        </header>
        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <User className="h-16 w-16 text-neutral-300 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">{error || 'User not found'}</h1>
          <p className="text-neutral-600 mb-6">The profile you&apos;re looking for doesn&apos;t exist.</p>
          <Link
            href="/"
            className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Go Home
          </Link>
        </main>
      </div>
    )
  }

  // Private profile
  if (!profile.is_public) {
    return (
      <div className="min-h-screen bg-neutral-50">
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

        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <div className="flex justify-center mb-4">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.username}
                className="h-24 w-24 rounded-full object-cover border-4 border-white shadow"
              />
            ) : (
              <div className="h-24 w-24 rounded-full bg-blue-600 text-white flex items-center justify-center text-2xl font-medium border-4 border-white shadow">
                {getInitials(profile.username)}
              </div>
            )}
          </div>
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">@{profile.username}</h1>
          <div className="flex items-center justify-center gap-2 text-neutral-500 mb-6">
            <Lock className="h-5 w-5" />
            <span>This profile is private</span>
          </div>
        </main>
      </div>
    )
  }

  // Public profile
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
        {/* Profile Header */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-start gap-6">
            {/* Avatar */}
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.full_name || profile.username}
                className="h-24 w-24 rounded-full object-cover border-4 border-white shadow"
              />
            ) : (
              <div className="h-24 w-24 rounded-full bg-blue-600 text-white flex items-center justify-center text-2xl font-medium border-4 border-white shadow flex-shrink-0">
                {getInitials(profile.full_name || profile.username)}
              </div>
            )}

            {/* Info */}
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-neutral-900">
                {profile.full_name || profile.username}
              </h1>
              <p className="text-neutral-500">@{profile.username}</p>

              {profile.bio && (
                <p className="text-neutral-700 mt-3">{profile.bio}</p>
              )}

              <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-neutral-500">
                {profile.law_school && (
                  <div className="flex items-center gap-1">
                    <Building className="h-4 w-4" />
                    {profile.law_school}
                  </div>
                )}
                {profile.graduation_year && (
                  <div className="flex items-center gap-1">
                    <GraduationCap className="h-4 w-4" />
                    Class of {profile.graduation_year}
                  </div>
                )}
                {profile.reputation !== undefined && profile.reputation > 0 && (
                  <div className="flex items-center gap-1 text-amber-600">
                    <span className="font-medium">{profile.reputation}</span> reputation
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Comments */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Comments ({comments.length})
          </h2>

          {isLoadingComments ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : comments.length === 0 ? (
            <p className="text-neutral-500 text-center py-8">
              No comments yet.
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
                        &ldquo;{comment.content}&rdquo;
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
      </main>
    </div>
  )
}
