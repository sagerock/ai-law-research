'use client'

import { useState, useRef, useEffect } from 'react'
import { User, LogOut, Settings, Bookmark, FolderOpen, ChevronDown } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { LoginModal } from './LoginModal'

export function UserMenu() {
  const { user, profile, isLoading, isConfigured, signOut } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

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

  // Don't show anything if Supabase is not configured
  if (!isConfigured) {
    return null
  }

  if (isLoading) {
    return (
      <div className="h-8 w-8 rounded-full bg-neutral-200 animate-pulse" />
    )
  }

  if (!user) {
    return (
      <>
        <button
          onClick={() => setShowLoginModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <User className="h-4 w-4" />
          <span>Sign In</span>
        </button>
        <LoginModal
          isOpen={showLoginModal}
          onClose={() => setShowLoginModal(false)}
        />
      </>
    )
  }

  const displayName = profile?.display_name || profile?.username || user.email?.split('@')[0] || 'User'
  const initials = displayName.slice(0, 2).toUpperCase()

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-neutral-100 transition-colors"
      >
        {profile?.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={displayName}
            className="h-8 w-8 rounded-full object-cover"
          />
        ) : (
          <div className="h-8 w-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium">
            {initials}
          </div>
        )}
        <span className="text-sm font-medium text-neutral-700 hidden sm:block">
          {displayName}
        </span>
        <ChevronDown className="h-4 w-4 text-neutral-500" />
      </button>

      {showDropdown && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-neutral-200 py-1 z-50">
          {/* User info */}
          <div className="px-4 py-3 border-b border-neutral-100">
            <p className="text-sm font-medium text-neutral-900">{displayName}</p>
            <p className="text-xs text-neutral-500 truncate">{user.email}</p>
            {profile?.reputation !== undefined && profile.reputation > 0 && (
              <p className="text-xs text-amber-600 mt-1">
                {profile.reputation} reputation
              </p>
            )}
          </div>

          {/* Menu items */}
          <div className="py-1">
            <button
              onClick={() => {
                setShowDropdown(false)
                // TODO: Navigate to bookmarks page
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
            >
              <Bookmark className="h-4 w-4" />
              <span>Bookmarks</span>
            </button>

            <button
              onClick={() => {
                setShowDropdown(false)
                // TODO: Navigate to collections page
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
            >
              <FolderOpen className="h-4 w-4" />
              <span>Collections</span>
            </button>

            <button
              onClick={() => {
                setShowDropdown(false)
                // TODO: Navigate to settings page
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </button>
          </div>

          {/* Sign out */}
          <div className="border-t border-neutral-100 py-1">
            <button
              onClick={() => {
                signOut()
                setShowDropdown(false)
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
  )
}
