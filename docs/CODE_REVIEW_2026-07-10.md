# Code Review - 2026-07-10

## Prioritized Findings

1. Secure the Ko-fi and CourtListener webhooks. Ko-fi donations can be forged and replayed, and CourtListener webhooks currently permit unauthorized database writes.
2. Sanitize all backend-controlled HTML before rendering it with `dangerouslySetInnerHTML`.
3. Prevent SSRF and resource exhaustion in outline downloads and document uploads.
4. Put every paid AI call behind centralized authentication, quota reservation, and accounting.
5. Repair password recovery and validate all post-authentication redirects.
6. Fix the profile update model/handler mismatch.
7. Add browser security headers and focused integration tests.

## Additional Findings

- Community-pool debits do not prevent overdrafts.
- The public textbook Q&A endpoint can be used to exhaust paid API credits.
- Search failures display fabricated legal authorities instead of an error.
- JWT validation does not require a valid subject and treats many invalid supplied tokens as anonymous.
- File parsers lack sufficient expanded-size and execution limits.
- The frontend has no lint, type-check, or automated test scripts.
- Backend tests do not cover authentication, ownership, webhooks, uploads, AI accounting, or concurrency.

## Verification Notes

- Backend Python compilation passed with `python3 -m compileall -q .`.
- The frontend build was blocked because the local Node.js version was 18.19.1; Next.js requires 20.9 or newer.
- Backend tests were blocked because pytest was not installed in the active environment.

## Remediation Status

- [x] Secure and make webhooks idempotent.
- [x] Sanitize rendered HTML.
- [ ] Harden remote downloads and uploads.
- [ ] Centralize paid AI authorization and accounting.
- [ ] Repair authentication recovery and redirects.
- [ ] Fix profile updates.
- [ ] Add security headers and automated coverage.
