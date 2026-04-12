# Student Outlines & AI Study Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing outlines feature with 3-tier visibility (private/unlisted/public), text extraction for AI, forking, and conversational AI study tools (multiple choice quizzes and practice essays).

**Architecture:** Build on the existing `outlines` table, CRUD endpoints, and frontend browse page. Add a new migration for schema changes, new backend endpoints for forking and AI study sessions, a new `/outline/[id]` detail page with chat-based study interface, and an Outlines tab in the Library page.

**Tech Stack:** FastAPI + asyncpg (backend), Next.js 16 + React 19 + Tailwind CSS 4 (frontend), Claude API via httpx (AI), pdfplumber + python-docx (text extraction — already installed), Supabase Storage (file hosting — already configured).

---

## Existing Infrastructure

These already exist and will be modified:

| What | Where | Notes |
|------|-------|-------|
| `outlines` table | `migrations/009_outlines.sql` | Has is_public BOOLEAN, no content/visibility/fork columns |
| Outline CRUD endpoints | `backend/main.py:3359-3562` | list, subjects, mine, create, get, delete |
| `OutlineCreate` Pydantic model | `backend/main.py:251-262` | JSON body, no file upload |
| `Outline` TypeScript interface | `frontend/types/index.ts:44-61` | Matches current schema |
| Outlines browse page | `frontend/app/outlines/page.tsx` | Upload modal, browse grid, subject filter |
| Text extraction functions | `backend/main.py:2011-2029` | `extract_text_from_pdf()`, `extract_text_from_docx()` |
| Study chat pattern | `backend/main.py:3883-4049` | BYOK/pool check, tier limits, streaming, conversation history |
| `conversations` + `messages` tables | `migrations/010_study_assistant.sql` | Separate tables for chat messages |

---

### Task 1: Database Migration — Schema Changes

**Files:**
- Create: `migrations/027_outline_study.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- migrations/027_outline_study.sql
-- Extend outlines with visibility, text content, forking; add outline study conversations

-- Replace is_public boolean with visibility text field
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'private';

-- Migrate existing data: is_public=true -> 'public', is_public=false -> 'private'
UPDATE outlines SET visibility = CASE WHEN is_public = TRUE THEN 'public' ELSE 'private' END;

-- Add extracted text content for AI features
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS content TEXT;

-- Add forking support
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS forked_from INTEGER REFERENCES outlines(id) ON DELETE SET NULL;
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS fork_count INTEGER NOT NULL DEFAULT 0;

-- Add year column for course year metadata
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS year INTEGER;

-- Update indexes for visibility-based queries
DROP INDEX IF EXISTS idx_outlines_public;
CREATE INDEX IF NOT EXISTS idx_outlines_visibility_subject ON outlines(visibility, subject);
CREATE INDEX IF NOT EXISTS idx_outlines_forked_from ON outlines(forked_from) WHERE forked_from IS NOT NULL;

-- Outline study conversations (separate from general study_notes conversations)
CREATE TABLE IF NOT EXISTS outline_conversations (
    id SERIAL PRIMARY KEY,
    outline_id INTEGER NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    mode TEXT NOT NULL,  -- 'multiple_choice' or 'practice_essay'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_outline_conv_outline_user ON outline_conversations(outline_id, user_id);

-- Messages for outline study conversations
CREATE TABLE IF NOT EXISTS outline_conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES outline_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_outline_msgs_conv ON outline_conversation_messages(conversation_id);
```

- [ ] **Step 2: Apply migration locally**

Run: `psql $DATABASE_URL -f migrations/027_outline_study.sql`
Expected: All ALTER TABLE and CREATE TABLE commands succeed. If outlines table already has some columns, `IF NOT EXISTS` prevents errors.

- [ ] **Step 3: Verify schema**

Run: `psql $DATABASE_URL -c "\d outlines" && psql $DATABASE_URL -c "\d outline_conversations" && psql $DATABASE_URL -c "\d outline_conversation_messages"`
Expected: outlines table shows visibility, content, forked_from, fork_count, year columns. Both new tables exist with correct columns and indexes.

- [ ] **Step 4: Commit**

```bash
git add migrations/027_outline_study.sql
git commit -m "feat: add migration for outline visibility, forking, and AI study conversations"
```

---

### Task 2: Backend — Update Outline CRUD for Visibility + Text Extraction

**Files:**
- Modify: `backend/main.py:251-262` (OutlineCreate model)
- Modify: `backend/main.py:3359-3562` (outline endpoints)

- [ ] **Step 1: Update OutlineCreate model to include visibility**

In `backend/main.py`, replace the `OutlineCreate` class at line 251:

```python
class OutlineCreate(BaseModel):
    title: str
    subject: str
    professor: Optional[str] = None
    law_school: Optional[str] = None
    semester: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    filename: str
    file_url: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    visibility: str = "private"  # private, unlisted, public
```

- [ ] **Step 2: Add OutlineUpdate model after OutlineCreate**

```python
class OutlineUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    professor: Optional[str] = None
    law_school: Optional[str] = None
    semester: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    visibility: Optional[str] = None  # private, unlisted, public
```

- [ ] **Step 3: Update create_outline to store visibility and extract text**

Replace the `create_outline` function at line 3467:

```python
@app.post("/api/v1/outlines")
async def create_outline(outline: OutlineCreate, user: dict = Depends(require_auth)):
    """Create a new outline, extract text from file for AI features"""
    # Validate visibility
    if outline.visibility not in ("private", "unlisted", "public"):
        raise HTTPException(status_code=400, detail="visibility must be private, unlisted, or public")

    # Extract text from file for AI features
    extracted_text = None
    if outline.file_url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(outline.file_url, timeout=30.0)
                if resp.status_code == 200:
                    file_bytes = resp.content
                    if outline.file_type == "pdf":
                        extracted_text = extract_text_from_pdf(file_bytes)
                    elif outline.file_type == "docx":
                        extracted_text = extract_text_from_docx(file_bytes)
                    else:
                        extracted_text = file_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"Text extraction failed for outline: {e}")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO outlines (user_id, title, subject, professor, law_school, semester,
                                  year, description, filename, file_url, file_size, file_type,
                                  visibility, is_public, content)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING id, title, subject, professor, law_school, semester, year, description,
                      filename, file_url, file_size, file_type, visibility, download_count, created_at
        """, user["id"], outline.title, outline.subject, outline.professor, outline.law_school,
            outline.semester, outline.year, outline.description, outline.filename, outline.file_url,
            outline.file_size, outline.file_type, outline.visibility,
            outline.visibility == "public", extracted_text)

    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "professor": row["professor"],
        "law_school": row["law_school"],
        "semester": row["semester"],
        "year": row["year"],
        "description": row["description"],
        "filename": row["filename"],
        "file_url": row["file_url"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "visibility": row["visibility"],
        "download_count": row["download_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
```

- [ ] **Step 4: Update list_outlines to use visibility instead of is_public**

Replace the `list_outlines` function at line 3359:

```python
@app.get("/api/v1/outlines")
async def list_outlines(subject: Optional[str] = None, search: Optional[str] = None, limit: int = 50, offset: int = 0):
    """Browse public outlines, optionally filtered by subject or search query"""
    async with db_pool.acquire() as conn:
        params: list = []
        conditions = ["o.visibility = 'public'"]
        param_idx = 1

        if subject:
            conditions.append(f"o.subject = ${param_idx}")
            params.append(subject)
            param_idx += 1

        if search:
            conditions.append(f"(o.title ILIKE ${param_idx} OR o.description ILIKE ${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        where_clause = " AND ".join(conditions)
        params.extend([limit, offset])

        rows = await conn.fetch(f"""
            SELECT o.id, o.user_id, o.title, o.subject, o.professor, o.law_school,
                   o.semester, o.year, o.description, o.filename, o.file_url, o.file_size,
                   o.file_type, o.download_count, o.fork_count, o.created_at,
                   p.username, p.full_name
            FROM outlines o
            LEFT JOIN profiles p ON o.user_id = p.id
            WHERE {where_clause}
            ORDER BY o.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """, *params)

    return {
        "outlines": [
            {
                "id": row["id"],
                "title": row["title"],
                "subject": row["subject"],
                "professor": row["professor"],
                "law_school": row["law_school"],
                "semester": row["semester"],
                "year": row["year"],
                "description": row["description"],
                "filename": row["filename"],
                "file_url": row["file_url"],
                "file_size": row["file_size"],
                "file_type": row["file_type"],
                "download_count": row["download_count"],
                "fork_count": row["fork_count"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "username": row["username"],
                "full_name": row["full_name"],
            }
            for row in rows
        ]
    }
```

- [ ] **Step 5: Update list_outline_subjects to use visibility**

Replace the query in `list_outline_subjects` at line 3412:

```python
@app.get("/api/v1/outlines/subjects")
async def list_outline_subjects():
    """List subjects with outline counts"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT subject, COUNT(*) as count
            FROM outlines
            WHERE visibility = 'public'
            GROUP BY subject
            ORDER BY count DESC
        """)

    return {
        "subjects": [
            {"subject": row["subject"], "count": row["count"]}
            for row in rows
        ]
    }
```

- [ ] **Step 6: Update list_my_outlines to include new columns**

Replace the `list_my_outlines` function at line 3432:

```python
@app.get("/api/v1/outlines/mine")
async def list_my_outlines(user: dict = Depends(require_auth)):
    """List current user's outlines"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, subject, professor, law_school, semester, year, description,
                   filename, file_url, file_size, file_type, visibility, download_count,
                   fork_count, forked_from, created_at,
                   content IS NOT NULL as has_content
            FROM outlines
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user["id"])

    return {
        "outlines": [
            {
                "id": row["id"],
                "title": row["title"],
                "subject": row["subject"],
                "professor": row["professor"],
                "law_school": row["law_school"],
                "semester": row["semester"],
                "year": row["year"],
                "description": row["description"],
                "filename": row["filename"],
                "file_url": row["file_url"],
                "file_size": row["file_size"],
                "file_type": row["file_type"],
                "visibility": row["visibility"],
                "download_count": row["download_count"],
                "fork_count": row["fork_count"],
                "forked_from": row["forked_from"],
                "has_content": row["has_content"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    }
```

- [ ] **Step 7: Update get_outline to use visibility logic**

Replace the `get_outline` function at line 3499:

```python
@app.get("/api/v1/outlines/{outline_id}")
async def get_outline(outline_id: int, user: Optional[dict] = Depends(get_current_user)):
    """Get a single outline with visibility checks"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT o.id, o.user_id, o.title, o.subject, o.professor, o.law_school,
                   o.semester, o.year, o.description, o.filename, o.file_url, o.file_size,
                   o.file_type, o.visibility, o.download_count, o.fork_count,
                   o.forked_from, o.content, o.created_at,
                   p.username, p.full_name, p.law_school as author_school
            FROM outlines o
            LEFT JOIN profiles p ON o.user_id = p.id
            WHERE o.id = $1
        """, outline_id)

        if not row:
            raise HTTPException(status_code=404, detail="Outline not found")

        # Visibility check
        visibility = row["visibility"]
        is_owner = user and user["id"] == row["user_id"]

        if visibility == "private" and not is_owner:
            raise HTTPException(status_code=404, detail="Outline not found")
        # unlisted and public: accessible to anyone with the link

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "subject": row["subject"],
        "professor": row["professor"],
        "law_school": row["law_school"],
        "semester": row["semester"],
        "year": row["year"],
        "description": row["description"],
        "filename": row["filename"],
        "file_url": row["file_url"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "visibility": row["visibility"],
        "download_count": row["download_count"],
        "fork_count": row["fork_count"],
        "forked_from": row["forked_from"],
        "content": row["content"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "username": row["username"],
        "full_name": row["full_name"],
        "author_school": row["author_school"],
        "is_owner": is_owner,
    }
```

- [ ] **Step 8: Add update_outline endpoint after delete_outline (line ~3562)**

```python
@app.put("/api/v1/outlines/{outline_id}")
async def update_outline(outline_id: int, update: OutlineUpdate, user: dict = Depends(require_auth)):
    """Update outline metadata (owner only)"""
    if update.visibility is not None and update.visibility not in ("private", "unlisted", "public"):
        raise HTTPException(status_code=400, detail="visibility must be private, unlisted, or public")

    async with db_pool.acquire() as conn:
        # Verify ownership
        existing = await conn.fetchrow(
            "SELECT user_id FROM outlines WHERE id = $1", outline_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Outline not found")
        if existing["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only update your own outlines")

        # Build dynamic update
        updates = []
        params = [outline_id]
        param_idx = 2

        for field in ["title", "subject", "professor", "law_school", "semester", "year", "description", "visibility"]:
            value = getattr(update, field)
            if value is not None:
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Keep is_public in sync with visibility
        if update.visibility is not None:
            updates.append(f"is_public = ${param_idx}")
            params.append(update.visibility == "public")
            param_idx += 1

        updates.append("updated_at = NOW()")

        row = await conn.fetchrow(f"""
            UPDATE outlines SET {', '.join(updates)}
            WHERE id = $1
            RETURNING id, title, subject, professor, law_school, semester, year,
                      description, visibility, updated_at
        """, *params)

    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "professor": row["professor"],
        "law_school": row["law_school"],
        "semester": row["semester"],
        "year": row["year"],
        "description": row["description"],
        "visibility": row["visibility"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }
```

- [ ] **Step 9: Test endpoints locally**

Run: `cd backend && python simple_api.py` (or `uvicorn main:app --reload`)

Test with curl:
```bash
# List public outlines
curl http://localhost:8000/api/v1/outlines

# List subjects
curl http://localhost:8000/api/v1/outlines/subjects
```

Expected: Endpoints return data using visibility field. Existing outlines with is_public=true show as visibility='public'.

- [ ] **Step 10: Commit**

```bash
git add backend/main.py
git commit -m "feat: update outline endpoints for visibility, text extraction, and update support"
```

---

### Task 3: Backend — Fork Endpoint

**Files:**
- Modify: `backend/main.py` (add after update_outline endpoint)

- [ ] **Step 1: Add fork endpoint**

Add after the `update_outline` endpoint:

```python
@app.post("/api/v1/outlines/{outline_id}/fork")
async def fork_outline(outline_id: int, user: dict = Depends(require_auth)):
    """Fork an outline to the current user's library"""
    async with db_pool.acquire() as conn:
        # Get source outline
        source = await conn.fetchrow("""
            SELECT id, title, subject, professor, law_school, semester, year,
                   description, filename, file_url, file_size, file_type, content
            FROM outlines WHERE id = $1
        """, outline_id)

        if not source:
            raise HTTPException(status_code=404, detail="Outline not found")

        # Check visibility — can't fork private outlines you don't own
        vis_row = await conn.fetchrow(
            "SELECT visibility, user_id FROM outlines WHERE id = $1", outline_id
        )
        if vis_row["visibility"] == "private" and vis_row["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Outline not found")

        # Can't fork your own outline
        if vis_row["user_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="Cannot fork your own outline")

        # Create the fork (starts as private)
        row = await conn.fetchrow("""
            INSERT INTO outlines (user_id, title, subject, professor, law_school, semester,
                                  year, description, filename, file_url, file_size, file_type,
                                  visibility, is_public, content, forked_from)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'private', FALSE, $13, $14)
            RETURNING id, title, subject, visibility, created_at
        """, user["id"], source["title"], source["subject"], source["professor"],
            source["law_school"], source["semester"], source["year"], source["description"],
            source["filename"], source["file_url"], source["file_size"], source["file_type"],
            source["content"], outline_id)

        # Increment fork count on original
        await conn.execute(
            "UPDATE outlines SET fork_count = fork_count + 1 WHERE id = $1",
            outline_id
        )

    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "visibility": row["visibility"],
        "forked_from": outline_id,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: add outline fork endpoint"
```

---

### Task 4: Backend — AI Study Session Endpoints

**Files:**
- Modify: `backend/main.py` (add after fork endpoint)

- [ ] **Step 1: Add Pydantic models for study sessions**

Add near the other Pydantic models (after `OutlineUpdate`):

```python
class OutlineStudyStart(BaseModel):
    mode: str  # "multiple_choice" or "practice_essay"

class OutlineStudyMessage(BaseModel):
    content: str
```

- [ ] **Step 2: Add the start study session endpoint**

```python
@app.post("/api/v1/outlines/{outline_id}/study")
async def start_outline_study(outline_id: int, body: OutlineStudyStart, user: dict = Depends(require_auth)):
    """Start a new AI study session on an outline"""
    if body.mode not in ("multiple_choice", "practice_essay"):
        raise HTTPException(status_code=400, detail="mode must be multiple_choice or practice_essay")

    user_id = user["id"]

    # Check BYOK
    user_api_key = await get_user_api_key(user_id)
    is_byok = user_api_key is not None
    api_key = user_api_key or ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Check pool for non-BYOK
    if not is_byok:
        if not await check_pool_available(user_id):
            raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    async with db_pool.acquire() as conn:
        # Get outline with visibility check
        outline = await conn.fetchrow("""
            SELECT id, user_id, title, subject, content, visibility
            FROM outlines WHERE id = $1
        """, outline_id)

        if not outline:
            raise HTTPException(status_code=404, detail="Outline not found")

        if outline["visibility"] == "private" and outline["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Outline not found")

        if not outline["content"]:
            raise HTTPException(status_code=400, detail="This outline has no extracted text. AI study requires text content.")

        # Check daily limits (reuse existing tier logic)
        tier_row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit FROM user_tiers WHERE user_id = $1",
            user_id,
        )
        if tier_row:
            messages_today = tier_row["messages_today"]
            if tier_row["last_message_date"] != date.today():
                messages_today = 0
            effective_limit = None if is_byok else (tier_row["daily_limit"] or (None if tier_row["tier"] == "pro" else 15))
            if effective_limit is not None and messages_today >= effective_limit:
                raise HTTPException(status_code=429, detail="Daily message limit reached.")

        # Create conversation
        conv = await conn.fetchrow("""
            INSERT INTO outline_conversations (outline_id, user_id, mode)
            VALUES ($1, $2, $3)
            RETURNING id, created_at
        """, outline_id, user_id, body.mode)

        # Build system prompt
        outline_text = outline["content"]
        if len(outline_text) > 60000:
            outline_text = outline_text[:60000] + "\n...[outline truncated]"

        if body.mode == "multiple_choice":
            system_prompt = f"""You are a law school study assistant helping a student prepare for their {outline["subject"]} exam using their own course outline.

STUDENT'S OUTLINE:
{outline_text}

YOUR TASK: Generate multiple choice questions that test the student's understanding of concepts from their outline. Follow these rules:
- Generate ONE question at a time with 4 answer options labeled A, B, C, D
- Questions should test conceptual understanding, not rote memorization of exact wording
- Only ask about topics covered in the outline — never introduce topics not in their notes
- After the student answers, explain why the correct answer is right and why wrong answers are wrong
- Reference specific parts of their outline in your explanations
- You may use your broader legal knowledge to give richer explanations, but questions must come from outline topics
- After explaining, ask if they want another question or have follow-up questions
- Keep a conversational, encouraging tone

Start by generating the first multiple choice question now."""

        else:  # practice_essay
            system_prompt = f"""You are a law school study assistant helping a student practice issue-spotter essays for their {outline["subject"]} exam using their own course outline.

STUDENT'S OUTLINE:
{outline_text}

YOUR TASK: Generate practice essay prompts (issue spotters) and provide feedback on student responses. Follow these rules:
- Create a fact pattern that implicates issues covered in the student's outline
- Only use topics from the outline — never test on material they haven't studied
- When the student submits their analysis, provide detailed feedback:
  * Which issues they correctly identified
  * Which issues they missed
  * How their rule statements could be stronger
  * How their application/analysis could improve
  * Encourage IRAC format (Issue, Rule, Application, Conclusion)
- Reference specific parts of their outline in your feedback
- You may use your broader legal knowledge to deepen explanations
- After feedback, the student can ask follow-up questions about any issue
- Keep a supportive, educational tone

Start by generating the first fact pattern now."""

        # Call Claude API
        model = "claude-sonnet-4-6" if is_byok else ("claude-sonnet-4-6" if (tier_row and tier_row["tier"] == "pro") else "claude-haiku-4-5-20251001")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 2000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": f"Start a {body.mode.replace('_', ' ')} session."}],
                },
                timeout=60.0,
            )

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service error")

        result = resp.json()
        ai_text = result["content"][0]["text"]
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        # Save messages
        await conn.execute("""
            INSERT INTO outline_conversation_messages (conversation_id, role, content, model, input_tokens, output_tokens, cost)
            VALUES ($1, 'assistant', $2, $3, $4, $5, $6)
        """, conv["id"], ai_text, model, input_tokens, output_tokens, cost)

        # Log usage
        await log_api_usage("outline_study", input_tokens, output_tokens, cost, "byok" if is_byok else "site")

        # Update daily usage
        await conn.execute("""
            INSERT INTO user_tiers (user_id, messages_today, last_message_date)
            VALUES ($1, 1, CURRENT_DATE)
            ON CONFLICT (user_id) DO UPDATE SET
                messages_today = CASE
                    WHEN user_tiers.last_message_date = CURRENT_DATE
                    THEN user_tiers.messages_today + 1
                    ELSE 1
                END,
                last_message_date = CURRENT_DATE,
                updated_at = NOW()
        """, user_id)

    return {
        "conversation_id": conv["id"],
        "mode": body.mode,
        "messages": [
            {
                "role": "assistant",
                "content": ai_text,
                "created_at": conv["created_at"].isoformat() if conv["created_at"] else None,
            }
        ],
    }
```

- [ ] **Step 3: Add the send message endpoint**

```python
@app.post("/api/v1/outlines/{outline_id}/conversations/{conv_id}/message")
async def outline_study_message(outline_id: int, conv_id: int, body: OutlineStudyMessage, user: dict = Depends(require_auth)):
    """Send a message in an outline study conversation"""
    user_id = user["id"]

    # Check BYOK
    user_api_key = await get_user_api_key(user_id)
    is_byok = user_api_key is not None
    api_key = user_api_key or ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    if not is_byok:
        if not await check_pool_available(user_id):
            raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    async with db_pool.acquire() as conn:
        # Verify conversation ownership and get outline
        conv = await conn.fetchrow("""
            SELECT oc.id, oc.mode, oc.user_id, oc.outline_id,
                   o.content, o.subject
            FROM outline_conversations oc
            JOIN outlines o ON oc.outline_id = o.id
            WHERE oc.id = $1 AND oc.outline_id = $2
        """, conv_id, outline_id)

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not your conversation")

        # Check daily limits
        tier_row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit FROM user_tiers WHERE user_id = $1",
            user_id,
        )
        if tier_row:
            messages_today = tier_row["messages_today"]
            if tier_row["last_message_date"] != date.today():
                messages_today = 0
            effective_limit = None if is_byok else (tier_row["daily_limit"] or (None if tier_row["tier"] == "pro" else 15))
            if effective_limit is not None and messages_today >= effective_limit:
                raise HTTPException(status_code=429, detail="Daily message limit reached.")

        # Save user message
        await conn.execute("""
            INSERT INTO outline_conversation_messages (conversation_id, role, content)
            VALUES ($1, 'user', $2)
        """, conv_id, body.content)

        # Get conversation history
        history = await conn.fetch("""
            SELECT role, content FROM outline_conversation_messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
        """, conv_id)

        # Build system prompt (same as start, but we rebuild it)
        outline_text = conv["content"] or ""
        if len(outline_text) > 60000:
            outline_text = outline_text[:60000] + "\n...[outline truncated]"

        if conv["mode"] == "multiple_choice":
            system_prompt = f"""You are a law school study assistant helping a student prepare for their {conv["subject"]} exam using their own course outline.

STUDENT'S OUTLINE:
{outline_text}

You are in a multiple choice quiz session. Continue generating questions, explaining answers, and responding to follow-up questions. Only test on topics from the outline. Reference the outline in explanations. Use broader legal knowledge for richer explanations only."""
        else:
            system_prompt = f"""You are a law school study assistant helping a student practice issue-spotter essays for their {conv["subject"]} exam using their own course outline.

STUDENT'S OUTLINE:
{outline_text}

You are in a practice essay session. Provide feedback on student essays, explain missed issues, and respond to follow-up questions. Only test on topics from the outline. Reference the outline in feedback. Use broader legal knowledge for richer explanations only."""

        # Build API messages from history
        api_messages = [{"role": h["role"], "content": h["content"]} for h in history]

        # Select model
        model = "claude-sonnet-4-6" if is_byok else ("claude-sonnet-4-6" if (tier_row and tier_row["tier"] == "pro") else "claude-haiku-4-5-20251001")

        # Call Claude
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 2000,
                    "system": system_prompt,
                    "messages": api_messages,
                },
                timeout=60.0,
            )

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service error")

        result = resp.json()
        ai_text = result["content"][0]["text"]
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        # Save AI response
        await conn.execute("""
            INSERT INTO outline_conversation_messages (conversation_id, role, content, model, input_tokens, output_tokens, cost)
            VALUES ($1, 'assistant', $2, $3, $4, $5, $6)
        """, conv_id, ai_text, model, input_tokens, output_tokens, cost)

        # Update conversation timestamp
        await conn.execute(
            "UPDATE outline_conversations SET updated_at = NOW() WHERE id = $1", conv_id
        )

        # Log usage and update daily count
        await log_api_usage("outline_study", input_tokens, output_tokens, cost, "byok" if is_byok else "site")

        await conn.execute("""
            INSERT INTO user_tiers (user_id, messages_today, last_message_date)
            VALUES ($1, 1, CURRENT_DATE)
            ON CONFLICT (user_id) DO UPDATE SET
                messages_today = CASE
                    WHEN user_tiers.last_message_date = CURRENT_DATE
                    THEN user_tiers.messages_today + 1
                    ELSE 1
                END,
                last_message_date = CURRENT_DATE,
                updated_at = NOW()
        """, user_id)

    return {
        "role": "assistant",
        "content": ai_text,
        "model": model,
        "tokens": {"input": input_tokens, "output": output_tokens},
    }
```

- [ ] **Step 4: Add list conversations endpoint**

```python
@app.get("/api/v1/outlines/{outline_id}/conversations")
async def list_outline_conversations(outline_id: int, user: dict = Depends(require_auth)):
    """List user's study sessions for an outline"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT oc.id, oc.mode, oc.created_at, oc.updated_at,
                   COUNT(ocm.id) as message_count
            FROM outline_conversations oc
            LEFT JOIN outline_conversation_messages ocm ON ocm.conversation_id = oc.id
            WHERE oc.outline_id = $1 AND oc.user_id = $2
            GROUP BY oc.id
            ORDER BY oc.updated_at DESC
        """, outline_id, user["id"])

    return [
        {
            "id": row["id"],
            "mode": row["mode"],
            "message_count": row["message_count"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


@app.get("/api/v1/outlines/{outline_id}/conversations/{conv_id}")
async def get_outline_conversation(outline_id: int, conv_id: int, user: dict = Depends(require_auth)):
    """Get a study conversation with all messages"""
    async with db_pool.acquire() as conn:
        conv = await conn.fetchrow("""
            SELECT id, user_id, mode, outline_id, created_at
            FROM outline_conversations WHERE id = $1 AND outline_id = $2
        """, conv_id, outline_id)

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your conversation")

        msgs = await conn.fetch("""
            SELECT id, role, content, model, created_at
            FROM outline_conversation_messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
        """, conv_id)

    return {
        "id": conv["id"],
        "mode": conv["mode"],
        "created_at": conv["created_at"].isoformat() if conv["created_at"] else None,
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "model": m["model"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            }
            for m in msgs
        ],
    }
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat: add outline AI study session endpoints (quiz, essay, conversation)"
```

---

### Task 5: Frontend — Update TypeScript Types

**Files:**
- Modify: `frontend/types/index.ts:44-61`

- [ ] **Step 1: Update the Outline interface**

Replace the `Outline` interface at line 44:

```typescript
export interface Outline {
  id: number
  user_id?: string
  title: string
  subject: string
  professor: string | null
  law_school: string | null
  semester: string | null
  year: number | null
  description: string | null
  filename: string
  file_url: string
  file_size: number | null
  file_type: string | null
  visibility: 'private' | 'unlisted' | 'public'
  download_count: number
  fork_count: number
  forked_from: number | null
  has_content?: boolean
  content?: string
  created_at: string
  username?: string
  full_name?: string
  author_school?: string
  is_owner?: boolean
}

export interface OutlineConversation {
  id: number
  mode: 'multiple_choice' | 'practice_essay'
  message_count: number
  created_at: string
  updated_at: string
}

export interface OutlineMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  model?: string
  created_at?: string
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/types/index.ts
git commit -m "feat: update Outline types for visibility, forking, and study conversations"
```

---

### Task 6: Frontend — Update Outlines Browse Page for Visibility

**Files:**
- Modify: `frontend/app/outlines/page.tsx`

- [ ] **Step 1: Update upload modal to use 3-tier visibility**

In `frontend/app/outlines/page.tsx`, replace the `uploadPublic` state (line 71) and the public toggle checkbox (lines 604-616):

Replace state declaration:
```typescript
const [uploadVisibility, setUploadVisibility] = useState<'private' | 'unlisted' | 'public'>('private')
```

Replace the checkbox in the upload modal (the `{/* Public Toggle */}` section around line 604) with:
```tsx
{/* Visibility */}
<div>
  <label className="block text-sm font-medium text-stone-700 mb-1">Visibility</label>
  <select
    value={uploadVisibility}
    onChange={(e) => setUploadVisibility(e.target.value as 'private' | 'unlisted' | 'public')}
    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none bg-white"
  >
    <option value="private">Private — only you can see it</option>
    <option value="unlisted">Unlisted — anyone with the link</option>
    <option value="public">Public — visible to everyone</option>
  </select>
</div>
```

- [ ] **Step 2: Update handleUpload to send visibility instead of is_public**

In the `handleUpload` function, replace `is_public: uploadPublic` with `visibility: uploadVisibility` in the request body.

- [ ] **Step 3: Update resetUploadForm**

Replace `setUploadPublic(true)` with `setUploadVisibility('private')`.

- [ ] **Step 4: Update outline cards to show fork_count and link to detail page**

Replace the outline card's download link (around line 419) with a link to the detail page:

```tsx
<Link
  href={`/outline/${outline.id}`}
  className="mt-3 w-full inline-flex items-center justify-center px-4 py-2 bg-sage-50 text-sage-700 rounded-lg text-sm font-medium hover:bg-sage-100 transition"
>
  View Outline
</Link>
```

Add fork count to the card footer (around line 412):
```tsx
{outline.fork_count > 0 && (
  <span className="flex items-center">
    <GitFork className="h-3 w-3 mr-1" />
    {outline.fork_count}
  </span>
)}
```

Import `GitFork` from lucide-react at the top of the file, and import `Link` from `next/link`.

- [ ] **Step 5: Update "My Outlines" to show visibility badges**

Replace the Private badge logic (around line 448-450) with:

```tsx
{outline.visibility === 'private' && (
  <span className="px-2 py-0.5 bg-stone-100 text-stone-600 text-xs rounded-full">Private</span>
)}
{outline.visibility === 'unlisted' && (
  <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded-full">Unlisted</span>
)}
{outline.visibility === 'public' && (
  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">Public</span>
)}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/app/outlines/page.tsx
git commit -m "feat: update outlines page for 3-tier visibility and detail page links"
```

---

### Task 7: Frontend — Outline Detail Page with AI Study Tools

**Files:**
- Create: `frontend/app/outline/[id]/page.tsx`

This is the largest frontend task — the individual outline page with metadata, content view, owner controls, fork/download, and AI study chat interface.

- [ ] **Step 1: Create the outline detail page**

Create `frontend/app/outline/[id]/page.tsx`:

```tsx
import OutlineDetail from './OutlineDetail'

export const dynamic = 'force-dynamic'

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const res = await fetch(`${API_URL}/api/v1/outlines/${id}`, { next: { revalidate: 60 } })
    if (!res.ok) return { title: 'Outline | Law Study Group' }
    const outline = await res.json()
    const parts = [outline.title]
    if (outline.subject) parts.push(outline.subject)
    return {
      title: `${parts.join(' — ')} | Law Study Group`,
      description: outline.description || `${outline.subject} outline${outline.law_school ? ` from ${outline.law_school}` : ''}`,
    }
  } catch {
    return { title: 'Outline | Law Study Group' }
  }
}

export default async function OutlinePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <OutlineDetail outlineId={id} />
}
```

- [ ] **Step 2: Create the OutlineDetail client component**

Create `frontend/app/outline/[id]/OutlineDetail.tsx`. This is a large component — the full code is below:

```tsx
'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { Outline, OutlineConversation, OutlineMessage } from '@/types'
import Header from '@/components/Header'
import {
  FileText, Download, GitFork, Edit3, Trash2, Loader2, Send,
  BookOpen, PenTool, ArrowLeft, MessageSquare, ChevronDown, X, Check,
} from 'lucide-react'

interface Props {
  outlineId: string
}

export default function OutlineDetail({ outlineId }: Props) {
  const { user, session } = useAuth()
  const router = useRouter()

  // Outline data
  const [outline, setOutline] = useState<Outline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editVisibility, setEditVisibility] = useState<'private' | 'unlisted' | 'public'>('private')
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  // Study session
  const [activeMode, setActiveMode] = useState<'multiple_choice' | 'practice_essay' | null>(null)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<OutlineMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [startingStudy, setStartingStudy] = useState(false)
  const [pastSessions, setPastSessions] = useState<OutlineConversation[]>([])
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Fork
  const [forking, setForking] = useState(false)

  const getHeaders = useCallback(() => {
    if (!session?.access_token) return {}
    return { 'Authorization': `Bearer ${session.access_token}`, 'Content-Type': 'application/json' }
  }, [session?.access_token])

  // Fetch outline
  useEffect(() => {
    const fetchOutline = async () => {
      try {
        const headers: Record<string, string> = {}
        if (session?.access_token) {
          headers['Authorization'] = `Bearer ${session.access_token}`
        }
        const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}`, { headers })
        if (!res.ok) {
          if (res.status === 404) setError('Outline not found')
          else setError('Failed to load outline')
          return
        }
        const data = await res.json()
        setOutline(data)
        setEditTitle(data.title)
        setEditVisibility(data.visibility)
        setEditDescription(data.description || '')
      } catch {
        setError('Failed to load outline')
      } finally {
        setLoading(false)
      }
    }
    fetchOutline()
  }, [outlineId, session?.access_token])

  // Fetch past sessions
  useEffect(() => {
    if (!session?.access_token || !outline) return
    const fetchSessions = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/conversations`, {
          headers: { 'Authorization': `Bearer ${session.access_token}` },
        })
        if (res.ok) {
          const data = await res.json()
          setPastSessions(data)
        }
      } catch { /* ignore */ }
    }
    fetchSessions()
  }, [outlineId, session?.access_token, outline])

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSaveEdit = async () => {
    if (!outline) return
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({
          title: editTitle,
          visibility: editVisibility,
          description: editDescription || null,
        }),
      })
      if (res.ok) {
        const updated = await res.json()
        setOutline({ ...outline, ...updated })
        setEditing(false)
      }
    } catch { /* ignore */ } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this outline? This cannot be undone.')) return
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (res.ok) router.push('/outlines')
    } catch { /* ignore */ }
  }

  const handleFork = async () => {
    if (!session?.access_token) return
    setForking(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/fork`, {
        method: 'POST',
        headers: getHeaders(),
      })
      if (res.ok) {
        const data = await res.json()
        router.push(`/outline/${data.id}`)
      }
    } catch { /* ignore */ } finally {
      setForking(false)
    }
  }

  const startStudy = async (mode: 'multiple_choice' | 'practice_essay') => {
    if (!session?.access_token) return
    setStartingStudy(true)
    setActiveMode(mode)
    setMessages([])
    setConversationId(null)

    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/study`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ mode }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setMessages([{ role: 'assistant', content: `Error: ${err.detail || 'Could not start study session'}` }])
        return
      }
      const data = await res.json()
      setConversationId(data.conversation_id)
      setMessages(data.messages)
    } catch {
      setMessages([{ role: 'assistant', content: 'Error: Failed to connect to AI service' }])
    } finally {
      setStartingStudy(false)
    }
  }

  const loadPastSession = async (convId: number) => {
    if (!session?.access_token) return
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/conversations/${convId}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setActiveMode(data.mode)
        setConversationId(data.id)
        setMessages(data.messages)
      }
    } catch { /* ignore */ }
  }

  const sendMessage = async () => {
    if (!input.trim() || !conversationId || !session?.access_token) return
    const userMsg: OutlineMessage = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const res = await fetch(
        `${API_URL}/api/v1/outlines/${outlineId}/conversations/${conversationId}/message`,
        {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ content: userMsg.content }),
        }
      )
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', content: data.content }])
      } else {
        const err = await res.json().catch(() => ({}))
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.detail || 'AI request failed'}` }])
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to send message' }])
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-stone-400" />
        </div>
      </div>
    )
  }

  if (error || !outline) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="container mx-auto px-4 py-16 max-w-4xl text-center">
          <FileText className="h-16 w-16 text-stone-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-stone-700 mb-2">{error || 'Outline not found'}</h2>
          <Link href="/outlines" className="text-sage-700 hover:underline">Back to outlines</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Back link */}
        <Link href="/outlines" className="inline-flex items-center text-sm text-stone-500 hover:text-stone-700 mb-6">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to outlines
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg border p-6 mb-6">
          {editing ? (
            <div className="space-y-4">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full text-2xl font-bold px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 outline-none"
              />
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Description..."
                rows={2}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 outline-none resize-none"
              />
              <select
                value={editVisibility}
                onChange={(e) => setEditVisibility(e.target.value as typeof editVisibility)}
                className="px-3 py-2 border rounded-lg bg-white"
              >
                <option value="private">Private</option>
                <option value="unlisted">Unlisted</option>
                <option value="public">Public</option>
              </select>
              <div className="flex gap-2">
                <button onClick={handleSaveEdit} disabled={saving} className="px-4 py-2 bg-sage-700 text-white rounded-lg text-sm hover:bg-sage-600 disabled:bg-stone-300">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Check className="h-4 w-4 inline mr-1" />Save</>}
                </button>
                <button onClick={() => setEditing(false)} className="px-4 py-2 border rounded-lg text-sm hover:bg-stone-50">
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h1 className="text-2xl font-bold text-stone-900 mb-2">{outline.title}</h1>
                  <div className="flex items-center gap-2 flex-wrap text-sm">
                    <span className="px-2.5 py-1 bg-sage-50 text-sage-700 font-medium rounded-full">{outline.subject}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      outline.visibility === 'public' ? 'bg-green-100 text-green-700' :
                      outline.visibility === 'unlisted' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-stone-100 text-stone-600'
                    }`}>
                      {outline.visibility}
                    </span>
                    {outline.fork_count > 0 && (
                      <span className="flex items-center text-stone-500">
                        <GitFork className="h-3.5 w-3.5 mr-1" />{outline.fork_count} forks
                      </span>
                    )}
                  </div>
                </div>
                {outline.is_owner && (
                  <div className="flex gap-2">
                    <button onClick={() => setEditing(true)} className="p-2 text-stone-500 hover:bg-stone-100 rounded-lg" title="Edit">
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button onClick={handleDelete} className="p-2 text-red-500 hover:bg-red-50 rounded-lg" title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              {outline.description && <p className="text-stone-600 mb-4">{outline.description}</p>}

              <div className="flex items-center gap-4 text-sm text-stone-500 flex-wrap">
                {outline.professor && <span>Prof. {outline.professor}</span>}
                {outline.law_school && <span>{outline.law_school}</span>}
                {outline.semester && <span>{outline.semester}</span>}
                {outline.year && <span>{outline.year}</span>}
                {!outline.is_owner && (outline.username || outline.full_name) && (
                  <span>by {outline.username || outline.full_name}{outline.author_school ? ` (${outline.author_school})` : ''}</span>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 mt-4 pt-4 border-t">
                {outline.file_url && (
                  <a
                    href={outline.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-4 py-2 bg-stone-100 text-stone-700 rounded-lg text-sm font-medium hover:bg-stone-200 transition"
                  >
                    <Download className="h-4 w-4 mr-2" />Download
                  </a>
                )}
                {!outline.is_owner && user && (
                  <button
                    onClick={handleFork}
                    disabled={forking}
                    className="inline-flex items-center px-4 py-2 bg-sage-50 text-sage-700 rounded-lg text-sm font-medium hover:bg-sage-100 transition disabled:opacity-50"
                  >
                    {forking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <GitFork className="h-4 w-4 mr-2" />}
                    Fork to My Library
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        {/* Content preview */}
        {outline.content && (
          <div className="bg-white rounded-lg border p-6 mb-6">
            <h2 className="text-lg font-semibold text-stone-900 mb-3">Outline Content</h2>
            <div className="prose prose-stone max-w-none text-sm whitespace-pre-wrap max-h-96 overflow-y-auto">
              {outline.content.length > 5000 ? outline.content.slice(0, 5000) + '\n\n...[content truncated — full text used for AI study]' : outline.content}
            </div>
          </div>
        )}

        {/* Study Tools */}
        {user && outline.content && (
          <div className="bg-white rounded-lg border p-6">
            <h2 className="text-lg font-semibold text-stone-900 mb-4">AI Study Tools</h2>

            {!activeMode ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button
                    onClick={() => startStudy('multiple_choice')}
                    disabled={startingStudy}
                    className="flex items-center p-4 border-2 border-sage-200 rounded-lg hover:bg-sage-50 transition text-left"
                  >
                    <BookOpen className="h-8 w-8 text-sage-600 mr-4 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-stone-900">Multiple Choice Quiz</div>
                      <div className="text-sm text-stone-500">Test your knowledge with AI-generated questions</div>
                    </div>
                  </button>
                  <button
                    onClick={() => startStudy('practice_essay')}
                    disabled={startingStudy}
                    className="flex items-center p-4 border-2 border-sage-200 rounded-lg hover:bg-sage-50 transition text-left"
                  >
                    <PenTool className="h-8 w-8 text-sage-600 mr-4 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-stone-900">Practice Essay</div>
                      <div className="text-sm text-stone-500">Practice issue spotters with AI feedback</div>
                    </div>
                  </button>
                </div>

                {startingStudy && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-sage-600 mr-3" />
                    <span className="text-stone-600">Generating your first question...</span>
                  </div>
                )}

                {/* Past sessions */}
                {pastSessions.length > 0 && (
                  <div className="mt-6 pt-4 border-t">
                    <h3 className="text-sm font-semibold text-stone-700 mb-2">Previous Sessions</h3>
                    <div className="space-y-2">
                      {pastSessions.map(s => (
                        <button
                          key={s.id}
                          onClick={() => loadPastSession(s.id)}
                          className="w-full flex items-center justify-between p-3 bg-stone-50 rounded-lg hover:bg-stone-100 transition text-sm"
                        >
                          <div className="flex items-center">
                            <MessageSquare className="h-4 w-4 text-stone-400 mr-2" />
                            <span className="font-medium text-stone-700">
                              {s.mode === 'multiple_choice' ? 'Quiz' : 'Essay'} — {s.message_count} messages
                            </span>
                          </div>
                          <span className="text-stone-400">
                            {new Date(s.updated_at).toLocaleDateString()}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div>
                {/* Active study session header */}
                <div className="flex items-center justify-between mb-4 pb-3 border-b">
                  <div className="flex items-center">
                    {activeMode === 'multiple_choice' ? (
                      <BookOpen className="h-5 w-5 text-sage-600 mr-2" />
                    ) : (
                      <PenTool className="h-5 w-5 text-sage-600 mr-2" />
                    )}
                    <span className="font-semibold text-stone-800">
                      {activeMode === 'multiple_choice' ? 'Multiple Choice Quiz' : 'Practice Essay'}
                    </span>
                  </div>
                  <button
                    onClick={() => { setActiveMode(null); setConversationId(null); setMessages([]) }}
                    className="text-sm text-stone-500 hover:text-stone-700 flex items-center"
                  >
                    <X className="h-4 w-4 mr-1" /> End Session
                  </button>
                </div>

                {/* Chat messages */}
                <div className="space-y-4 max-h-[500px] overflow-y-auto mb-4 px-1">
                  {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-lg p-4 text-sm whitespace-pre-wrap ${
                        msg.role === 'user'
                          ? 'bg-sage-700 text-white'
                          : 'bg-stone-100 text-stone-800'
                      }`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {sending && (
                    <div className="flex justify-start">
                      <div className="bg-stone-100 rounded-lg p-4">
                        <Loader2 className="h-5 w-5 animate-spin text-stone-400" />
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input */}
                {conversationId && (
                  <div className="flex gap-2">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          sendMessage()
                        }
                      }}
                      placeholder={activeMode === 'multiple_choice' ? 'Type your answer (e.g., B) or ask a question...' : 'Write your essay or ask a question...'}
                      rows={activeMode === 'practice_essay' ? 6 : 2}
                      className="flex-1 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none resize-none"
                    />
                    <button
                      onClick={sendMessage}
                      disabled={sending || !input.trim()}
                      className="px-4 py-3 bg-sage-700 text-white rounded-lg hover:bg-sage-600 disabled:bg-stone-300 disabled:cursor-not-allowed transition self-end"
                    >
                      <Send className="h-5 w-5" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* No content warning */}
        {!outline.content && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <FileText className="h-10 w-10 text-yellow-500 mx-auto mb-2" />
            <p className="text-yellow-800 font-medium">AI study tools are not available for this outline</p>
            <p className="text-yellow-600 text-sm mt-1">Text could not be extracted from the uploaded file.</p>
          </div>
        )}

        {/* Login prompt for AI tools */}
        {!user && outline.content && (
          <div className="bg-stone-50 border rounded-lg p-6 text-center">
            <BookOpen className="h-10 w-10 text-stone-400 mx-auto mb-2" />
            <p className="text-stone-700 font-medium">Sign in to use AI study tools</p>
            <p className="text-stone-500 text-sm mt-1">Quiz yourself and practice essays powered by AI</p>
            <Link
              href={`/login?returnTo=/outline/${outlineId}`}
              className="inline-block mt-3 px-5 py-2 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 transition"
            >
              Sign in
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Test the outline detail page**

Run: `cd frontend && npm run dev`

Navigate to `/outline/{id}` for an existing outline. Verify:
- Metadata displays correctly
- Content section shows extracted text
- Owner sees edit/delete controls
- Non-owner sees fork/download buttons
- AI study buttons appear when logged in and outline has content
- Starting a quiz generates the first question
- Answering and follow-up conversation works

- [ ] **Step 4: Commit**

```bash
git add frontend/app/outline/[id]/page.tsx frontend/app/outline/[id]/OutlineDetail.tsx
git commit -m "feat: add outline detail page with AI study tools (quiz, essay, chat)"
```

---

### Task 8: Frontend — Add Outlines Tab to Library Page

**Files:**
- Modify: `frontend/app/library/page.tsx`

- [ ] **Step 1: Add Outlines tab and data fetching**

In `frontend/app/library/page.tsx`, the page already has tab infrastructure. Add an 'outlines' tab alongside the existing tabs.

Add imports at the top:
```tsx
import { GitFork } from 'lucide-react'
import { Outline } from '@/types'
```

Add state for outlines:
```tsx
const [myOutlines, setMyOutlines] = useState<Outline[]>([])
```

Add fetch function (alongside existing fetchers):
```tsx
const fetchMyOutlines = useCallback(async () => {
  if (!session?.access_token) return
  try {
    const res = await fetch(`${API_URL}/api/v1/outlines/mine`, {
      headers: { 'Authorization': `Bearer ${session.access_token}` },
    })
    if (res.ok) {
      const data = await res.json()
      setMyOutlines(data.outlines || [])
    }
  } catch { /* ignore */ }
}, [session?.access_token])
```

Call it in the existing `loadData` function.

- [ ] **Step 2: Add the Outlines tab button to the tab bar**

Add alongside existing tab buttons:
```tsx
<button
  onClick={() => setActiveTab('outlines')}
  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
    activeTab === 'outlines'
      ? 'border-sage-600 text-sage-700'
      : 'border-transparent text-stone-500 hover:text-stone-700'
  }`}
>
  Outlines ({myOutlines.length})
</button>
```

- [ ] **Step 3: Add the Outlines tab content panel**

```tsx
{activeTab === 'outlines' && (
  <div className="space-y-3">
    {myOutlines.length === 0 ? (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-stone-300 mx-auto mb-3" />
        <p className="text-stone-600 font-medium">No outlines yet</p>
        <Link href="/outlines" className="text-sage-700 text-sm hover:underline mt-1 inline-block">
          Browse or upload outlines
        </Link>
      </div>
    ) : (
      myOutlines.map(outline => (
        <Link
          key={outline.id}
          href={`/outline/${outline.id}`}
          className="block bg-white rounded-lg border p-4 hover:shadow-md transition"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <FileText className="h-6 w-6 text-sage-500 flex-shrink-0" />
              <div className="min-w-0">
                <div className="font-medium text-stone-900 truncate">{outline.title}</div>
                <div className="text-sm text-stone-500 flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 bg-sage-50 text-sage-700 text-xs rounded-full">{outline.subject}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    outline.visibility === 'public' ? 'bg-green-100 text-green-700' :
                    outline.visibility === 'unlisted' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-stone-100 text-stone-600'
                  }`}>{outline.visibility}</span>
                  {outline.forked_from && (
                    <span className="flex items-center text-stone-400">
                      <GitFork className="h-3 w-3 mr-0.5" />forked
                    </span>
                  )}
                  {outline.has_content && (
                    <span className="text-green-600 text-xs">AI ready</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </Link>
      ))
    )}
  </div>
)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/library/page.tsx
git commit -m "feat: add Outlines tab to library page"
```

---

### Task 9: Apply Migration to Production

**Files:**
- Modify: none (database operation)

- [ ] **Step 1: Connect to Railway production database**

Run: `psql "postgresql://postgres:PASSWORD@switchyard.proxy.rlwy.net:22438/railway"`

(Use the actual credentials from Railway dashboard or environment variables.)

- [ ] **Step 2: Apply the migration**

Run: `psql $RAILWAY_DATABASE_URL -f migrations/027_outline_study.sql`

Expected: All ALTER TABLE and CREATE TABLE succeed. Existing outlines get visibility='public' (from is_public=true migration).

- [ ] **Step 3: Verify production schema**

Run: `psql $RAILWAY_DATABASE_URL -c "SELECT visibility, count(*) FROM outlines GROUP BY visibility"`

Expected: Shows count of outlines with visibility='public' matching the previous is_public=true count.

---

### Task 10: Deploy and Test End-to-End

- [ ] **Step 1: Push to main to trigger Railway deploy**

```bash
git push origin main
```

- [ ] **Step 2: Test on production**

Verify in browser at `lawstudygroup.com`:
1. `/outlines` — browse page shows outlines, subject filter works
2. Upload a new outline with "unlisted" visibility — verify it doesn't appear in browse
3. `/outline/{id}` — detail page loads with metadata, content preview, and study buttons
4. Start a Multiple Choice Quiz — verify AI generates a question
5. Answer a question — verify AI gives feedback and allows follow-ups
6. Start a Practice Essay — verify AI generates a fact pattern
7. Fork someone else's outline — verify it copies to your library as private
8. `/library` — verify Outlines tab shows your outlines

- [ ] **Step 3: Commit any production fixes**

If any issues arise during testing, fix and commit.
