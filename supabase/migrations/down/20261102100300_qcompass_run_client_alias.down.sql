-- Inverse of 20261102100300_qcompass_run_client_alias.sql. The index is
-- dropped; R13: client_run_id holds data, so it is renamed
-- _deprecated_client_run_id_20261102100300, never dropped (re-applying the
-- up migration renames it back).
drop index if exists public.runs_tenant_client_run_id_key;
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema = 'public'
              and table_name = 'runs' and column_name = 'client_run_id') then
    alter table public.runs rename column client_run_id to _deprecated_client_run_id_20261102100300;
  end if;
end $$;
