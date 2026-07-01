import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request })

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey) {
    return response
  }

  // Skip entirely for anonymous visitors — no auth cookies means nothing to refresh
  const hasAuthCookie = request.cookies
    .getAll()
    .some((c) => c.name.startsWith('sb-'))
  if (!hasAuthCookie) {
    return response
  }

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        )
        response = NextResponse.next({ request })
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        )
      },
    },
  })

  // getSession() refreshes the access token if expired and writes fresh
  // cookies via setAll above. We use it (not getUser()) because nothing
  // server-side makes authorization decisions from this session — SSR pages
  // are public and the FastAPI backend validates JWTs itself — so paying a
  // Supabase network round-trip on every request isn't worth it.
  try {
    await supabase.auth.getSession()
  } catch {
    // A malformed/corrupt auth cookie must never take down the page —
    // serve it without a session and let the client sort the cookie out
  }

  return response
}

export const config = {
  // Skip static assets; run on pages and API routes
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|txt|xml)$).*)',
  ],
}
