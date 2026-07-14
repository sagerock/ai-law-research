-- These tables are accessed through FastAPI, not directly through PostgREST.
-- Keep the Supabase anon and authenticated roles default-denied.
ALTER TABLE public.mindmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mindmap_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.node_progress ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.msj_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.msj_library ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.pool_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    api_role TEXT;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE %s FROM %I',
                'public.mindmaps, public.mindmap_nodes, public.study_sessions, public.node_progress, '
                'public.msj_projects, public.msj_documents, public.msj_conversations, '
                'public.msj_messages, public.msj_library, public.pool_ledger, public.site_config',
                api_role
            );
        END IF;
    END LOOP;
END
$$;
