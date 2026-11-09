-- Gate 1 round 2 (security lane DB): a client-chosen runId is a per-tenant
-- alias, never the primary key. Additive and idempotent (R13); the inverse
-- is down/20261102100300_qcompass_run_client_alias.down.sql.
--
-- public.runs.id is one global namespace. POST
-- /api/qcompass/domains/{d}/runs used the body's runId as that key, so a
-- tenant (or any signed-up user, through a PostgREST insert of a personal
-- run) could take an id another tenant would submit and make that submit
-- fail with 409, and a 409 answered "this id is taken somewhere" (SEC-L2,
-- round-2 c4). The API now always generates the primary key itself and
-- keeps the client's runId in client_run_id, unique per tenant among the
-- runs the API created (author_user_id is null; client-written runs always
-- carry their author). A runId is then only ever compared with the caller's
-- own tenant's runs.

do $$
begin
  -- A rollback renames the column; bring it (and its data) back.
  if exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = '_deprecated_client_run_id_20261102100300')
     and not exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = 'client_run_id') then
    alter table public.runs rename column _deprecated_client_run_id_20261102100300 to client_run_id;
  end if;
end $$;

alter table public.runs add column if not exists client_run_id text;

create unique index if not exists runs_tenant_client_run_id_key
  on public.runs (tenant_id, client_run_id)
  where client_run_id is not null and author_user_id is null;
