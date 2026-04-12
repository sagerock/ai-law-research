# Student Outlines & AI Study Tools

**Date:** 2026-04-12
**Status:** Draft
**Feature:** Upload, share, and study from law school outlines with AI-powered quizzes and practice essays

## Overview

Students upload their course outlines (DOCX, PDF, or plain text) and use AI-powered study tools to quiz themselves with multiple choice questions and practice issue-spotter essays. After each exercise, the AI gives feedback and the student can ask follow-up questions in a conversational interface. Outlines can be shared using a YouTube-style visibility model (private, unlisted, public) and forked by other students.

## Motivation

Law Study Group already provides AI case briefs and a personal library. Outlines are the missing piece — they're how students actually synthesize a course. Combined with AI study tools, this makes the platform a complete study companion rather than just a case lookup tool. The sharing model creates a community resource: students benefit from outlines shared by others, filtered by course subject, school, and professor.

## Data Model

### `outlines` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | |
| user_id | UUID | NOT NULL, FK to profiles | Owner |
| title | TEXT | NOT NULL | e.g., "Torts Fall 2025" |
| subject | TEXT | NOT NULL | Dropdown value (Torts, Contracts, etc.) |
| content | TEXT | | Extracted plain text for AI consumption |
| original_filename | TEXT | | Name of uploaded file |
| original_file | BYTEA | | Raw uploaded file for download |
| original_content_type | TEXT | | MIME type of uploaded file |
| visibility | TEXT | NOT NULL, DEFAULT 'private' | private, unlisted, public |
| school | TEXT | | Optional — law school name |
| professor | TEXT | | Optional — professor name |
| year | INTEGER | | Optional — year the course was taken |
| semester | TEXT | | Optional — Fall, Spring, Summer |
| description | TEXT | | Optional — short blurb about the outline |
| forked_from | INTEGER | FK to outlines | Tracks lineage for forked outlines |
| fork_count | INTEGER | NOT NULL, DEFAULT 0 | Denormalized count of forks |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes:**
- `idx_outlines_user_id` on (user_id)
- `idx_outlines_visibility_subject` on (visibility, subject) — for public browse/filter
- `idx_outlines_forked_from` on (forked_from)

### `outline_conversations` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | |
| outline_id | INTEGER | NOT NULL, FK to outlines | |
| user_id | UUID | NOT NULL, FK to profiles | |
| mode | TEXT | NOT NULL | multiple_choice, practice_essay |
| messages | JSONB | NOT NULL, DEFAULT '[]' | Full conversation history |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes:**
- `idx_outline_conversations_outline_user` on (outline_id, user_id)

### Subject dropdown values

Standard law school curriculum:
- Civil Procedure
- Constitutional Law
- Contracts
- Criminal Law
- Criminal Procedure
- Evidence
- Property
- Torts
- Administrative Law
- Business Organizations
- Family Law
- Federal Courts
- Legal Writing
- Professional Responsibility
- Tax
- Trusts & Estates
- Other

## API Endpoints

### Outline CRUD

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/outlines | Required | Upload outline (multipart form: file + metadata). Extracts text from DOCX/PDF, stores file and content. |
| GET | /api/v1/outlines/{id} | Conditional | Get outline details + content. Public/unlisted = anyone. Private = owner only. |
| PUT | /api/v1/outlines/{id} | Required (owner) | Update metadata (title, visibility, school, etc.) |
| DELETE | /api/v1/outlines/{id} | Required (owner) | Delete outline and all its conversations |
| GET | /api/v1/outlines/{id}/download | Conditional | Download original file. Same visibility rules as viewing. |
| GET | /api/v1/outlines/mine | Required | List current user's outlines (owned + forked) |

### Discovery

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/outlines/public | None | Browse public outlines. Query params: subject, school, search (title keyword), page, limit. |

### Forking

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/outlines/{id}/fork | Required | Copy outline to current user's library. Sets forked_from, increments fork_count on original. New outline starts as private. Copies content, file, and metadata. |

### AI Study Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/outlines/{id}/study | Required | Start a study session. Body: `{ mode: "multiple_choice" \| "practice_essay" }`. AI generates first exercise. Returns conversation with initial messages. |
| POST | /api/v1/outlines/{id}/conversations/{conv_id}/message | Required | Send a message in an existing conversation. Body: `{ content: "..." }`. Returns AI response. User must own the conversation. |
| GET | /api/v1/outlines/{id}/conversations | Required | List current user's study sessions for this outline (only their own). |

### AI cost tracking

AI study interactions follow the existing pattern:
- Check for BYOK Anthropic API key first
- Fall back to community pool with daily usage cap
- Log each AI call to `api_usage_log` for the transparency dashboard

## Frontend Pages

### `/outlines` — Browse & Discover

- Subject dropdown filter for the standard law school subjects
- Search bar for title/keyword
- Grid of public outline cards: title, subject badge, school, professor, year, author name, fork count
- "Upload Outline" button (visible when logged in)
- No auth required to browse

### `/outline/[id]` — Outline Detail Page

**Header:** title, subject badge, metadata (school, professor, year, semester), author display name, visibility badge, fork count

**Owner controls:** edit metadata, change visibility dropdown, delete

**Visitor controls:** "Fork to My Library" button, "Download" button

**Content section:** rendered outline text

**Study section:** two buttons — "Multiple Choice Quiz" and "Practice Essay"
- Clicking either opens a chat-style interface on the page
- AI generates the first exercise
- Student responds in a text input
- AI gives feedback, conversation continues naturally
- Previous study sessions accessible via dropdown/sidebar

SSR with `generateMetadata()` for SEO on public outlines (title, subject, school in meta tags).

### `/library` page updates

New "Outlines" tab alongside existing Collections and Bookmarks tabs. Lists user's owned and forked outlines with subject badges and visibility indicators.

### Upload flow

Modal or dedicated section with:
- File dropzone (accepts .pdf, .docx, .txt)
- Title field (required)
- Subject dropdown (required)
- Visibility selector: Private / Unlisted / Public (default: Private)
- Optional fields: school, professor, year, semester, description

## AI Prompt Design

### Multiple Choice Quiz

**System prompt context:** outline text, student's subject area

**Behavior:**
- Generate one question at a time with 4-5 answer options
- Questions test understanding of concepts from the outline, not rote memorization of exact wording
- After the student answers: reveal correct answer, explain why it's right, explain why the student's pick was wrong (if applicable), reference the relevant part of their outline
- Student can ask follow-up questions conversationally before moving to the next question
- AI's broader legal knowledge used for richer explanations but never for generating questions on topics not in the outline

### Practice Essay (Issue Spotter)

**System prompt context:** outline text, student's subject area

**Behavior:**
- Generate a fact pattern that implicates issues covered in the outline
- Student writes their analysis (IRAC format encouraged)
- AI gives feedback: which issues spotted, which missed, how rule statements and application could improve
- Opens into conversation — student can ask about specific issues, get clarification, understand what they missed
- AI uses broader legal knowledge to deepen explanations but fact patterns only draw from outline topics

### Conversation storage

- Outline text included once in the system prompt (not repeated per message)
- Full message history stored in `messages` JSONB column
- Each message: `{ role: "user" | "assistant", content: "...", timestamp: "..." }`
- History sent with each API call for conversation continuity

## Visibility & Sharing Model

### Three visibility levels

| Level | Browse/search | Direct link access | AI features | Download |
|-------|--------------|-------------------|-------------|----------|
| Private | Hidden | Owner only | Owner only | Owner only |
| Unlisted | Hidden | Anyone with link | Logged-in users | Anyone with link |
| Public | Visible | Anyone | Logged-in users | Anyone |

### Forking

- Creates a full copy: text content, original file, and metadata
- `forked_from` field tracks lineage; original outline shows fork count
- Forked outline starts as private — new owner decides visibility
- Edits to a fork do not affect the original (no sync)

### Author attribution

- Public and unlisted outlines show uploader's display name from profiles table
- If the profile has `law_school` set, that displays alongside the name
- Students can keep their profile minimal if they prefer

## File Processing

### Upload pipeline

1. Accept multipart form upload (max file size: 10MB)
2. Validate file type: .pdf, .docx, .txt
3. Extract plain text:
   - **PDF**: Use `PyPDF2` or `pdfplumber` for text extraction
   - **DOCX**: Use `python-docx` to extract text from paragraphs
   - **TXT**: Read directly
4. Store extracted text in `content` column
5. Store original file bytes in `original_file` column
6. Store MIME type in `original_content_type` column

### Download

Serve the `original_file` bytes with `Content-Disposition: attachment; filename="{original_filename}"` and the stored content type.

## Text-only upload

For students who want to paste text directly:
- Skip file upload, write text directly to `content`
- `original_file`, `original_filename`, `original_content_type` remain NULL
- Download button hidden when no original file exists
