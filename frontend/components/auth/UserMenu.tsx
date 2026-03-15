'use client'

import { useState, useRef, useEffect } from 'react'
import { User, LogOut, Settings, Bookmark, FolderOpen, ChevronDown, GraduationCap, Upload, Heart, Shield, Key } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import Link from 'next/link'

export function UserMenu() {
  const { user, profile, isLoading, isConfigured, signOut } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)
  const [mounted, setMounted] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Track client-side mount to avoid hydration issues
  useEffect(() => {
    setMounted(true)
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Don't render until mounted (prevents hydration mismatch)
  if (!mounted) {
    return (
      <div className="h-8 w-8 rounded-full bg-stone-200 animate-pulse" />
    )
  }

  // Don't show anything if Supabase is not configured
  if (!isConfigured) {
    return (
      <Link
        href="/login"
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-sage-700 rounded-lg hover:bg-sage-600 transition-colors"
      >
        <User className="h-4 w-4" />
        <span>Sign In</span>
      </Link>
    )
  }

  if (isLoading) {
    return (
      <div className="h-8 w-8 rounded-full bg-stone-200 animate-pulse" />
    )
  }

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-sage-700 rounded-lg hover:bg-sage-600 transition-colors"
      >
        <User className="h-4 w-4" />
        <span>Sign In</span>
      </Link>
    )
  }

  const displayName = profile?.display_name || profile?.username || user.email?.split('@')[0] || 'User'
  const initials = displayName.slice(0, 2).toUpperCase()
  const isAdmin = user.email === 'sage@sagerock.com'

  return (
    <>
    {isAdmin && (
      <Link
        href="/admin"
        className="text-amber-600 hover:text-amber-800 transition flex items-center"
        title="Admin"
      >
        <Shield className="h-5 w-5 sm:mr-2" />
        <span className="hidden sm:inline">Admin</span>
      </Link>
    )}
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
      >
        {profile?.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={displayName}
            className="h-8 w-8 rounded-full object-cover"
          />
        ) : (
          <div className="h-8 w-8 rounded-full bg-sage-700 text-white flex items-center justify-center text-sm font-medium">
            {initials}
          </div>
        )}
        <span className="text-sm font-medium text-stone-700 hidden sm:block">
          {displayName}
        </span>
        <ChevronDown className="h-4 w-4 text-stone-500" />
      </button>

      {showDropdown && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-stone-200 py-1 z-50">
          {/* User info */}
          <div className="px-4 py-3 border-b border-stone-100">
            <p className="text-sm font-medium text-stone-900">{displayName}</p>
            <p className="text-xs text-stone-500 truncate">{user.email}</p>
            {profile?.reputation !== undefined && profile.reputation > 0 && (
              <p className="text-xs text-amber-600 mt-1">
                {profile.reputation} reputation
              </p>
            )}
          </div>

          {/* Menu items */}
          <div className="py-1">
            {user.email === 'sage@sagerock.com' && (
              <Link
                href="/admin"
                onClick={() => setShowDropdown(false)}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-amber-700 hover:bg-amber-50"
              >
                <Shield className="h-4 w-4" />
                <span>Admin Panel</span>
              </Link>
            )}

            <Link
              href="/profile"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <Settings className="h-4 w-4" />
              <span>My Profile</span>
            </Link>

            <Link
              href="/library"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <Bookmark className="h-4 w-4" />
              <span>My Bookmarks</span>
            </Link>

            <Link
              href="/library"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <FolderOpen className="h-4 w-4" />
              <span>My Collections</span>
            </Link>

            <Link
              href="/study"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <GraduationCap className="h-4 w-4" />
              <span>Study Assistant</span>
            </Link>

            <Link
              href="/briefcheck"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <Upload className="h-4 w-4" />
              <span>Brief Check</span>
            </Link>

            <Link
              href="/byok"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <Key className="h-4 w-4" />
              <span>Unlimited AI</span>
            </Link>

            <Link
              href="/transparency"
              onClick={() => setShowDropdown(false)}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
            >
              <Heart className="h-4 w-4" />
              <span>Contribute</span>
            </Link>
          </div>

          {/* Sign out */}
          <div className="border-t border-stone-100 py-1">
            <button
              onClick={async () => {
                setShowDropdown(false)
                await signOut()
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      )}
    </div>
    </>
  )
}
