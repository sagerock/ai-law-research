import { database, defineRailway, github, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  // Pinned to the live image: plain postgres() would plan postgres:18, a major-version switch on live data.
  const Postgres = database("Postgres", "postgres", { image: "ghcr.io/railwayapp-templates/postgres-ssl:17", region: "us-east4-eqdc4a" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-east4-eqdc4a", sizeMB: 5000 });
  const aiLawResearch = service("ai-law-research", {
    source: github("sagerock/ai-law-research", { checkSuites: false, rootDirectory: "/frontend" }),
    // Was frontend/railway.toml (Config as Code, hard cutoff 2026-12-01); item #2097.
    build: { builder: "NIXPACKS", buildCommand: "npm install && npm run build" },
    deploy: { startCommand: "npm run start", healthcheckPath: "/", healthcheckTimeout: 100 },
    replicas: { "us-east4-eqdc4a": 1 },
    domains: ["lawstudygroup.com", "tortwell.com", "www.tortwell.com"],
    env: { NIXPACKS_NODE_VERSION: "20", ENCRYPTION_KEY: preserve(), NEXT_PUBLIC_API_URL: preserve(), NEXT_PUBLIC_GA_ID: preserve(), NEXT_PUBLIC_SITE_URL: preserve(), NEXT_PUBLIC_SUPABASE_ANON_KEY: preserve(), NEXT_PUBLIC_SUPABASE_URL: preserve(), NODE_OPTIONS: preserve() },
  });
  const Backend = service("Backend", {
    source: github("sagerock/ai-law-research", { checkSuites: false, rootDirectory: "/backend" }),
    // Was backend/railway.toml; restart ON_FAILURE x10 is Railway's default (stored null), so not set.
    // backend/Dockerfile is picked up automatically (builder DOCKERFILE does not persist; Railway keeps null).
    deploy: { healthcheckPath: "/health", healthcheckTimeout: 300 },
    replicas: { "us-east4-eqdc4a": 1 },
    networking: { privateNetworkEndpoint: "backend" },
    env: { ANTHROPIC_API_KEY: preserve(), AWS_ACCESS_KEY_ID: preserve(), AWS_DEFAULT_REGION: preserve(), AWS_SECRET_ACCESS_KEY: preserve(), COURTLISTENER_API_KEY: preserve(), COURTLISTENER_TOKEN: preserve(), DATABASE_URL: preserve(), KOFI_VERIFICATION_TOKEN: preserve(), MALLOC_ARENA_MAX: preserve(), OPENAI_API_KEY: preserve(), OPINIONS_BUCKET: preserve(), OUTLINE_STORAGE_HOSTS: preserve(), QDRANT_API_KEY: preserve(), QDRANT_URL: preserve(), SITE_URL: preserve(), SUPABASE_JWT_SECRET: preserve(), WEBHOOK_SECRET: preserve() },
  });

  return project("Legal Research AI", {
    resources: [aiLawResearch, Backend, Postgres, postgresVolume],
  });
});
