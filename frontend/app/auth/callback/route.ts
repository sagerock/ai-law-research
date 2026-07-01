import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  let next = searchParams.get('next') ?? '/'
  // Only allow same-site relative redirects
  if (!next.startsWith('/') || next.startsWith('//')) {
    next = '/'
  }

  // Behind Railway's proxy, request.url is the internal host (localhost:8080),
  // so redirect from the forwarded host — falling back to the configured site
  // URL. In local dev, origin is already correct (and http).
  const forwardedHost = request.headers.get('x-forwarded-host')
  const baseUrl =
    process.env.NODE_ENV === 'development'
      ? origin
      : forwardedHost
        ? `https://${forwardedHost}`
        : process.env.NEXT_PUBLIC_SITE_URL || origin

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (code && supabaseUrl && supabaseKey) {
    // Create the redirect response up front so the session cookies from the
    // code exchange get attached to it
    const response = NextResponse.redirect(`${baseUrl}${next}`)

    const supabase = createServerClient(supabaseUrl, supabaseKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    })

    try {
      const { error } = await supabase.auth.exchangeCodeForSession(code)

      if (!error) {
        return response
      }
      console.error('OAuth code exchange failed:', error.message)
    } catch (err) {
      console.error('OAuth code exchange threw:', err)
    }
  }

  // Return to home page with error indicator
  return NextResponse.redirect(`${baseUrl}/?auth_error=true`)
}
