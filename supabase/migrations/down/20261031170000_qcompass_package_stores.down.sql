-- Inverse of 20261031170000_qcompass_package_stores.sql.
-- R13: tables that may hold data are never dropped. They are renamed out of
-- the way (deprecated), so a rollback loses nothing; re-applying the up
-- migration creates fresh tables.
do $$
declare
  t text;
  i record;
  suffix constant text := '_20261031170000';
begin
  foreach t in array array[
    'router_calibration_daily', 'router_calibration_devices',
    'router_pricing_cache', 'router_free_tier_ledger', 'bench_runs'
  ] loop
    if to_regclass('public.' || t) is not null then
      for i in select indexname from pg_indexes where schemaname = 'public' and tablename = t loop
        execute format('alter index public.%I rename to %I', i.indexname, left('_dep_' || i.indexname || suffix, 63));
      end loop;
      execute format('alter table public.%I rename to %I', t, '_deprecated_' || t || suffix);
    end if;
  end loop;
end $$;
