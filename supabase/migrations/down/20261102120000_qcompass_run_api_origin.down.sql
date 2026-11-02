-- Inverse of 20261102120000_qcompass_run_api_origin.sql. The guard trigger
-- and its function are dropped, and the alias index of
-- 20261102100300 (author_user_id is null) is restored. R13: origin holds
-- data, so it is renamed _deprecated_origin_20261102120000, never dropped
-- (re-applying the up migration renames it back).
drop trigger if exists runs_origin_guard on public.runs;
drop function if exists public.qcompass_runs_origin_guard();

drop index if exists public.runs_tenant_client_run_id_key;
do $$
begin
  create unique index runs_tenant_client_run_id_key
    on public.runs (tenant_id, client_run_id)
    where client_run_id is not null and author_user_id is null;
exception when unique_violation then
  -- Rows the newer rules allowed (an API alias reused by a run whose author
  -- was deleted) can't be held by 20261102100300's index; leave it absent and
  -- say so rather than fail the rollback.
  raise notice 'runs_tenant_client_run_id_key not restored: author-less runs share an alias within a tenant';
end $$;

alter table public.runs drop constraint if exists runs_origin_check;
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = 'origin') then
    alter table public.runs rename column origin to _deprecated_origin_20261102120000;
  end if;
end $$;
