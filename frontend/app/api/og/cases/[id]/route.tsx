import { ImageResponse } from 'next/og'
import { readFile } from 'node:fs/promises'
import { BRAND_NAME, SITE_TAGLINE } from '@/lib/site'
import { caseYear, getCase } from '@/lib/case-data'

const size = { width: 1200, height: 630 }

const sourceSerifRegular = readFile(
  new URL('../../../../fonts/SourceSerif4-Regular.ttf', import.meta.url),
).then((font) => font.buffer.slice(font.byteOffset, font.byteOffset + font.byteLength) as ArrayBuffer)
const sourceSerifSemibold = readFile(
  new URL('../../../../fonts/SourceSerif4-Semibold.ttf', import.meta.url),
).then((font) => font.buffer.slice(font.byteOffset, font.byteOffset + font.byteLength) as ArrayBuffer)

interface RouteProps {
  params: Promise<{ id: string }>
}

function displayTitle(title: string): string {
  const normalized = title.replace(/\s+/g, ' ').trim()
  if (normalized.length <= 150) return normalized

  const breakAt = normalized.lastIndexOf(' ', 146)
  return `${normalized.slice(0, breakAt > 110 ? breakAt : 146).trimEnd()}...`
}

function titleSize(title: string): number {
  if (title.length > 125) return 46
  if (title.length > 85) return 54
  if (title.length > 52) return 64
  return 74
}

function Tortoise() {
  return (
    <svg width="280" height="202" viewBox="0 0 72 52" fill="none">
      <rect x="15" y="34" width="6.5" height="11" rx="3.2" fill="#58654d" />
      <rect x="40" y="34" width="6.5" height="11" rx="3.2" fill="#58654d" />
      <path d="M55 24c8-1.6 13 1 13 6.4 0 5-5 6.8-11.5 5.6" fill="#6f7d63" stroke="#45503d" strokeWidth="1.4" />
      <circle cx="63.5" cy="29.2" r="1.7" fill="#2b2a26" />
      <path d="M8 37C8 20 17.5 11 31.5 11S55 20 55 37Z" fill="#8c9981" stroke="#45503d" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M6.5 37h50" stroke="#45503d" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M31.5 15l7 6-2.7 8.4h-8.6L24.5 21z" fill="#a7b399" stroke="#45503d" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M24.5 21l-9 3M38.5 21l9 3M27.2 29.4L22 36M35.8 29.4L41 36" stroke="#45503d" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export async function GET(_request: Request, { params }: RouteProps) {
  const { id } = await params
  const caseData = await getCase(id)
  const title = displayTitle(caseData?.title || caseData?.case_name || 'Free case briefs for law students')
  const court = caseData?.court_name || caseData?.court_id || ''
  const year = caseYear(caseData?.decision_date || caseData?.date_filed)
  const detail = [court, year].filter(Boolean).join(' | ')

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          backgroundColor: '#faf8f3',
          color: '#2b2a26',
          padding: '64px 76px 50px',
          border: '10px solid #f3efe6',
          fontFamily: 'Source Serif 4',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
          <div style={{ display: 'flex', flexDirection: 'column', width: '790px' }}>
            <div
              style={{
                display: 'flex',
                alignSelf: 'flex-start',
                padding: '10px 20px',
                borderRadius: '999px',
                backgroundColor: '#e7ebe0',
                color: '#58654d',
                fontFamily: 'Arial',
                fontSize: '20px',
                fontWeight: 700,
                letterSpacing: '1.5px',
              }}
            >
              FREE CASE BRIEF
            </div>
            <div
              style={{
                display: 'flex',
                marginTop: '32px',
                fontSize: `${titleSize(title)}px`,
                fontWeight: 600,
                lineHeight: 1.03,
                letterSpacing: '-1.5px',
                maxHeight: '236px',
                overflow: 'hidden',
              }}
            >
              {title}
            </div>
            {detail && (
              <div
                style={{
                  display: 'flex',
                  marginTop: '23px',
                  color: '#6f7d63',
                  fontFamily: 'Arial',
                  fontSize: '25px',
                  lineHeight: 1.2,
                }}
              >
                {detail}
              </div>
            )}
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '270px',
              height: '340px',
              marginTop: '14px',
              borderRadius: '135px 135px 48px 48px',
              backgroundColor: '#f1f4ec',
            }}
          >
            <Tortoise />
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            width: '100%',
            paddingTop: '24px',
            borderTop: '2px solid #ccd4c1',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'baseline' }}>
            <div style={{ display: 'flex', fontSize: '43px', lineHeight: 1 }}>Tortwell</div>
            <div
              style={{
                display: 'flex',
                marginLeft: '23px',
                color: '#58654d',
                fontFamily: 'Arial',
                fontSize: '19px',
              }}
            >
              {SITE_TAGLINE}
            </div>
          </div>
          <div style={{ display: 'flex', color: '#58654d', fontFamily: 'Arial', fontSize: '20px' }}>
            tortwell.com
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      headers: {
        'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400',
      },
      fonts: [
        { name: 'Source Serif 4', data: await sourceSerifRegular, weight: 400 },
        { name: 'Source Serif 4', data: await sourceSerifSemibold, weight: 600 },
      ],
    },
  )
}
