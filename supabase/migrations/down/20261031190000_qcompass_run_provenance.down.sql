-- Inverse of 20261031190000_qcompass_run_provenance.sql.
-- R13: run_provenance is renamed (deprecated), never dropped; the storage
-- policy holds no data and is dropped.
do $$
declare
  i record;
  suffix constant text := '_20261031190000';
begin
  if to_regclass('public.run_provenance') is not null then
    for i in select indexname from pg_indexes where schemaname = 'public' and tablename = 'run_provenance' loop
      execute format('alter index public.%I rename to %I', i.indexname, left('_dep_' || i.indexname || suffix, 63));
    end loop;
    alter table public.run_provenance rename to _deprecated_run_provenance_20261031190000;
  end if;
end $$;

drop policy if exists "tenant members read run-artifacts" on storage.objects;
