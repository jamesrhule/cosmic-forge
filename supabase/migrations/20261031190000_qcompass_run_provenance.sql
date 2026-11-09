-- P3-03: provenance records become rows (plus an object in the
-- run-artifacts bucket). Additive and idempotent (R13); the inverse is
-- down/20261031190000_qcompass_run_provenance.down.sql.

create table if not exists public.run_provenance (
  run_id                    text primary key references public.runs(id) on delete cascade,
  tenant_id                 uuid not null references public.tenants(id) on delete cascade,
  classical_reference_hash  text not null default '',
  calibration_hash          text,
  error_mitigation          jsonb,
  record                    jsonb not null default '{}'::jsonb,
  artifact_path             text,
  artifact_status           text not null default 'pending',
  created_at                timestamptz not null default now()
);
create index if not exists run_provenance_tenant_idx on public.run_provenance(tenant_id);
alter table public.run_provenance enable row level security;
drop policy if exists "tenant members read run provenance" on public.run_provenance;
create policy "tenant members read run provenance" on public.run_provenance
  for select to authenticated
  using (public.is_tenant_member(tenant_id, auth.uid()));

-- Worker-written artefacts of tenant runs (object name '<run_id>/<file>',
-- main's convention) are readable by that tenant's members.
drop policy if exists "tenant members read run-artifacts" on storage.objects;
create policy "tenant members read run-artifacts" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'run-artifacts'
    and exists (
      select 1 from public.runs r
      where r.id = split_part(name, '/', 1)
        and r.tenant_id is not null
        and public.is_tenant_member(r.tenant_id, auth.uid())
    )
  );
