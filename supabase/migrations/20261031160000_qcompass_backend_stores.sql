-- P3-01: Postgres for the compute API's own stores (replaces the SQLite
-- files under UCGLE_F1_STATE_DIR). Additive and idempotent (R13); the
-- inverse is down/20261031160000_qcompass_backend_stores.down.sql.
--
-- Tenancy reuses public.tenants / public.tenant_members (20260427001133).
-- The API connects with a privileged role; RLS protects direct access
-- through the Supabase client (anon/authenticated).

-- ── API keys (hashed; plaintext shown once at issue) ────────────────────
create table if not exists public.api_keys (
  key_hash    text primary key,
  key_prefix  text not null,
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  scopes      text[] not null default '{}',
  label       text not null default '',
  issued_at   timestamptz not null default now(),
  expires_at  timestamptz,
  revoked_at  timestamptz,
  created_by  uuid references auth.users(id) on delete set null
);
create index if not exists api_keys_tenant_idx on public.api_keys(tenant_id);
alter table public.api_keys enable row level security;
drop policy if exists "tenant admins read api keys" on public.api_keys;
create policy "tenant admins read api keys" on public.api_keys
  for select to authenticated
  using (public.tenant_role(tenant_id, auth.uid()) in ('owner', 'admin'));

-- ── Tenant budgets and spend ────────────────────────────────────────────
create table if not exists public.tenant_budgets (
  tenant_id           uuid primary key references public.tenants(id) on delete cascade,
  monthly_budget_usd  numeric(14, 6) not null check (monthly_budget_usd >= 0),
  spent_usd           numeric(14, 6) not null default 0 check (spent_usd >= 0),
  period_start        timestamptz not null,
  notes               text not null default ''
);
alter table public.tenant_budgets enable row level security;
drop policy if exists "tenant members read budget" on public.tenant_budgets;
create policy "tenant members read budget" on public.tenant_budgets
  for select to authenticated
  using (public.is_tenant_member(tenant_id, auth.uid()));

-- ── Parameter scans ─────────────────────────────────────────────────────
create table if not exists public.scans (
  scan_id     text primary key,
  tenant_id   uuid not null references public.tenants(id) on delete cascade,
  domain      text not null,
  kind        text not null,
  axes        jsonb not null default '{}'::jsonb,
  payload     jsonb not null default '{}'::jsonb,
  provenance  jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists scans_tenant_created_idx on public.scans(tenant_id, created_at desc);
alter table public.scans enable row level security;
drop policy if exists "tenant members read scans" on public.scans;
create policy "tenant members read scans" on public.scans
  for select to authenticated
  using (public.is_tenant_member(tenant_id, auth.uid()));
drop policy if exists "tenant members create scans" on public.scans;
create policy "tenant members create scans" on public.scans
  for insert to authenticated
  with check (public.tenant_role(tenant_id, auth.uid()) in ('owner', 'admin', 'member'));

-- ── Agent memory (service-only: RLS on, no client policies) ─────────────
create table if not exists public.agent_hypotheses (
  "hypothesisId"   text primary key,
  "conversationId" text not null,
  text             text not null,
  "createdAt"      timestamptz not null default now()
);
create index if not exists agent_hypotheses_conv_idx on public.agent_hypotheses("conversationId");

create table if not exists public.agent_plans (
  "planId"         text primary key,
  "conversationId" text not null,
  path             text not null,
  payload          text not null,
  "createdAt"      timestamptz not null default now()
);
create index if not exists agent_plans_conv_idx on public.agent_plans("conversationId");

create table if not exists public.agent_approval_tokens (
  "tokenId"   text primary key,
  scopes      text not null,
  "issuedAt"  timestamptz not null default now(),
  "expiresAt" timestamptz,
  consumed    boolean not null default false
);

create table if not exists public.agent_run_links (
  "runId"          text primary key,
  "conversationId" text not null,
  "hypothesisId"   text not null,
  "createdAt"      timestamptz not null default now()
);
create index if not exists agent_run_links_conv_idx on public.agent_run_links("conversationId");

create table if not exists public.agent_tool_calls (
  id               bigserial primary key,
  "conversationId" text not null,
  tool             text not null,
  "requestJson"    text not null,
  "responseJson"   text not null,
  ok               boolean not null,
  "createdAt"      timestamptz not null default now()
);
create index if not exists agent_tool_calls_conv_idx on public.agent_tool_calls("conversationId");

create table if not exists public.agent_patches (
  "patchId"        text primary key,
  "conversationId" text not null,
  "targetPath"     text not null,
  rationale        text not null,
  "unifiedDiff"    text not null,
  "reviewStatus"   text not null default 'draft',
  "createdAt"      timestamptz not null default now()
);
create index if not exists agent_patches_conv_idx on public.agent_patches("conversationId");

alter table public.agent_hypotheses enable row level security;
alter table public.agent_plans enable row level security;
alter table public.agent_approval_tokens enable row level security;
alter table public.agent_run_links enable row level security;
alter table public.agent_tool_calls enable row level security;
alter table public.agent_patches enable row level security;
