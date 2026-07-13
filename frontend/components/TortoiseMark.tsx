// Tortwell brand marks, from the "Tortwell Brand" Claude Design project.
// TortoiseMark is the primary mascot ("Tort"-oise); TortwellRoundel is the
// compact emblem (a well seen from above / tortoise-shell scutes) used where
// the full mascot can't follow — favicons, tiles, tight corners.

interface MarkProps {
  className?: string
  /** Renders in light-on-dark colors for dark surfaces like the footer */
  onDark?: boolean
}

export function TortoiseMark({ className, onDark = false }: MarkProps) {
  const shell = onDark ? '#9aa78a' : '#8c9981'
  const outline = onDark ? '#22201c' : '#45503d'
  const scute = onDark ? '#c3cbb7' : '#a7b399'
  return (
    <svg viewBox="0 0 72 52" fill="none" className={className} aria-hidden="true">
      <rect x="15" y="34" width="6.5" height="11" rx="3.2" fill={onDark ? '#3f4a35' : '#58654d'} />
      <rect x="40" y="34" width="6.5" height="11" rx="3.2" fill={onDark ? '#3f4a35' : '#58654d'} />
      <path d="M55 24c8-1.6 13 1 13 6.4 0 5-5 6.8-11.5 5.6" fill="#6f7d63" stroke={onDark ? undefined : '#45503d'} strokeWidth={onDark ? undefined : 1.4} />
      <circle cx="63.5" cy="29.2" r="1.7" fill={onDark ? '#22201c' : '#2b2a26'} />
      <path d="M8 37C8 20 17.5 11 31.5 11S55 20 55 37Z" fill={shell} stroke={onDark ? undefined : '#45503d'} strokeWidth={onDark ? undefined : 1.6} strokeLinejoin="round" />
      <path d="M6.5 37h50" stroke={outline} strokeWidth="2.4" strokeLinecap="round" />
      <path d="M31.5 15l7 6-2.7 8.4h-8.6L24.5 21z" fill={scute} stroke={onDark ? undefined : '#45503d'} strokeWidth={onDark ? undefined : 1.3} strokeLinejoin="round" />
      <path d="M24.5 21l-9 3M38.5 21l9 3M27.2 29.4L22 36M35.8 29.4L41 36" stroke={outline} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

export function TortwellRoundel({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} aria-hidden="true">
      <circle cx="32" cy="32" r="30" fill="#58654d" />
      <circle cx="32" cy="32" r="22" fill="#8c9981" />
      <path d="M32 20l10 6v12l-10 6-10-6V26z" fill="#f3efe6" />
    </svg>
  )
}
