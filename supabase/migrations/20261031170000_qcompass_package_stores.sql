-- P3-01 (part 2): Postgres for the library-package stores that used SQLite
-- files or the local filesystem:
--   qcompass-router  calibration history  (~/.cache/qcompass/calibration.sqlite)
--   qcompass-router  pricing cache        (~/.cache/qcompass/pricing/<provider>.json)
--   qcompass-router  free-tier ledger     (in memory)
--   qcompass-bench   leaderboard          (~/.qcompass/bench/leaderboard.sqlite)
-- Additive and idempotent (R13); the inverse is
-- down/20261031170000_qcompass_package_stores.down.sql.
--
-- Calibration history, the pricing cache and the bench leaderboard are
-- platform data (not tenant-owned): RLS is on, clients may read, only the
-- service role writes. Free-tier ledger rows of a tenant's own provider
-- account are tenant-owned: members read their tenant's rows; the house
-- account (tenant_id null) is service-only.

-- ── Router calibration: v1 per-day snapshots ────────────────────────────
create table if not exists public.router_calibration_daily (
  provider         text not null,
  backend          text not null,
  day              date not null,
  two_qubit_error  double precision not null,
  readout_error    double precision not null,
  t1_t2_us         double precision not null,
  recorded_at      timestamptz not null default now(),
  primary key (provider, backend, day)
);
alter table public.router_calibration_daily enable row level security;
drop policy if exists "clients read calibration history" on public.router_calibration_daily;
create policy "clients read calibration history" on public.router_calibration_daily
  for select to authenticated using (true);

-- ── Router calibration: v2 device snapshots (FoMaC) ─────────────────────
create table if not exists public.router_calibration_devices (
  provider       text not null,
  backend        text not null,
  recorded_at    timestamptz not null,
  two_q_error    double precision not null,
  readout_error  double precision not null,
  t1_us          double precision not null,
  t2_us          double precision not null,
  primary key (provider, backend, recorded_at)
);
alter table public.router_calibration_devices enable row level security;
drop policy if exists "clients read device calibration" on public.router_calibration_devices;
create policy "clients read device calibration" on public.router_calibration_devices
  for select to authenticated using (true);

-- ── Router pricing cache (one row per provider) ─────────────────────────
create table if not exists public.router_pricing_cache (
  provider     text primary key,
  recorded_at  timestamptz not null default now(),
  origin       text not null default 'seed' check (origin in ('seed', 'live')),
  entries      jsonb not null default '{}'::jsonb
);
alter table public.router_pricing_cache enable row level security;
drop policy if exists "clients read pricing cache" on public.router_pricing_cache;
create policy "clients read pricing cache" on public.router_pricing_cache
  for select to authenticated using (true);

-- ── Router free-tier ledger (per provider account and tier) ─────────────
-- account: 'house' for PHC's own provider accounts, or 'tenant:<uuid>' for
-- a tenant's own (bring-your-own-key) account; tenant_id is set for the
-- latter and drives RLS.
create table if not exists public.router_free_tier_ledger (
  account              text not null,
  tier_name            text not null,
  tenant_id            uuid references public.tenants(id) on delete cascade,
  units                double precision not null check (units >= 0),
  unit_kind            text not null default 'minutes'
                         check (unit_kind in ('minutes', 'credits', 'usd', 'hours')),
  applicable_backends  text[] not null default '{}',
  updated_at           timestamptz not null default now(),
  primary key (account, tier_name)
);
create index if not exists router_free_tier_ledger_tenant_idx
  on public.router_free_tier_ledger(tenant_id);
alter table public.router_free_tier_ledger enable row level security;
drop policy if exists "tenant members read free-tier ledger" on public.router_free_tier_ledger;
create policy "tenant members read free-tier ledger" on public.router_free_tier_ledger
  for select to authenticated
  using (tenant_id is not null and public.is_tenant_member(tenant_id, auth.uid()));

-- ── Bench leaderboard (append-only) ─────────────────────────────────────
create table if not exists public.bench_runs (
  id                bigserial primary key,
  domain            text not null,
  fixture           text not null,
  package_version   text not null,
  started_at        timestamptz not null,
  wall_seconds      double precision not null,
  classical_energy  double precision,
  quantum_energy    double precision,
  provenance_hash   text not null,
  ok                boolean not null,
  notes             text not null default ''
);
create index if not exists bench_runs_started_idx on public.bench_runs(started_at desc);
alter table public.bench_runs enable row level security;
-- The leaderboard is public (P2-14 publishes it on a public page).
drop policy if exists "anyone reads the bench leaderboard" on public.bench_runs;
create policy "anyone reads the bench leaderboard" on public.bench_runs
  for select to anon, authenticated using (true);
