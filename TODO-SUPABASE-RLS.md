# TODO — Supabase RLS disabled on 11 tables (flagged 2026-07-06)

**Status:** open · found by Supabase advisor while working in another session; parking it
here to fix in a dev session for this project.

## The problem

The **legal-researcher** Supabase project (ref `exgpmdwlxizxzlhzqkfk` — the one this
app uses for auth + user features) has **Row Level Security disabled** on 11 public
tables. Since Supabase's `anon` and `authenticated` client roles bypass nothing
without RLS, **anyone holding the public anon key (it ships in the frontend bundle)
can read or modify every row** in:

- `mindmaps`, `mindmap_nodes`
- `study_sessions`, `node_progress`
- `pool_ledger`
- `site_config`
- `msj_projects`, `msj_documents`, `msj_conversations`, `msj_messages`, `msj_library`

(The older tables — `profiles`, `comments`, `bookmarks`, `collections`,
`collection_cases`, etc. — already have RLS enabled.)

## Why not just run the fix

Enabling RLS with **no policies blocks ALL access** through the anon/authenticated
roles — it would break whatever frontend features read these tables the moment it's
applied. So the real work is:

1. Map how each table is actually accessed:
   - via the **FastAPI backend** (service-role / direct Postgres → unaffected by RLS), or
   - via the **Next.js frontend Supabase client** (anon key → needs policies).
2. For frontend-accessed tables, write policies (typical shape:
   `user_id = auth.uid()` for per-user rows; public read + no write for `site_config`
   if the frontend only reads it).
3. Then enable RLS table-by-table and click through the affected features
   (mindmapper, study sessions, MSJ builder).

## Advisor's remediation SQL (do NOT run as-is — see above)

```sql
ALTER TABLE public.mindmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mindmap_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.node_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pool_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_library ENABLE ROW LEVEL SECURITY;
```

Ref: https://supabase.com/docs/guides/database/postgres/row-level-security
