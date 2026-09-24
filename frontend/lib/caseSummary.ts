export interface BriefCachePayload {
  summary?: string | null
  structured_candidates?: unknown[] | null
}

/** A reviewed structured candidate is displayable without a legacy summary. */
export function hasDisplayableBrief(payload: BriefCachePayload): boolean {
  return Boolean(payload.summary) || (payload.structured_candidates?.length ?? 0) > 0
}
