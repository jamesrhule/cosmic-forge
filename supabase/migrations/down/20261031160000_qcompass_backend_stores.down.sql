-- Inverse of 20261031160000_qcompass_backend_stores.sql.
-- R13: tables that may hold user data are never dropped. They are renamed
-- out of the way (deprecated), so a rollback loses nothing; re-applying
-- the up migration creates fresh tables.
do $$
declare
  t text;
  i record;
  suffix constant text := '_20261031160000';
begin
  foreach t in array array[
    'api_keys', 'tenant_budgets', 'scans',
    'agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
    'agent_run_links', 'agent_tool_calls', 'agent_patches'
  ] loop
    if to_regclass('public.' || t) is not null then
      -- Rename the table's indexes too, so re-applying the up migration
      -- recreates them (its `create index if not exists` matches by name).
      for i in select indexname from pg_indexes where schemaname = 'public' and tablename = t loop
        execute format('alter index public.%I rename to %I', i.indexname, left('_dep_' || i.indexname || suffix, 63));
      end loop;
      execute format('alter table public.%I rename to %I', t, '_deprecated_' || t || suffix);
    end if;
  end loop;
end $$;
