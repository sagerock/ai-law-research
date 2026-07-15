// Custom featured artwork for specific cases. When a case has an entry here,
// its social/OG image uses this art (served from /public/case-art/) instead of
// the generated /api/og/cases/[id] card. Images are sized 1200x627 (LinkedIn's
// recommended featured-image size; within OG/Twitter specs).
export interface CaseArt {
  file: string
  width: number
  height: number
  alt: string
}

const CASE_ART: Record<string, CaseArt> = {
  // Palsgraf v. Long Island Railroad Co. (N.Y. 1928)
  '3602780': {
    file: '/case-art/palsgraf-v-long-island-railroad.jpg',
    width: 1200,
    height: 627,
    alt: 'Palsgraf v. Long Island Railroad — guards pull a running passenger aboard a departing train as his package explodes on the tracks, toppling a platform scale onto Mrs. Palsgraf about 25 to 30 feet away.',
  },
}

export function getCaseArt(caseId: string): CaseArt | null {
  return CASE_ART[caseId] ?? null
}
