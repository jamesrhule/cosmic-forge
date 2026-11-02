-- Inverse of 20261031200400_qcompass_agent_memory_tenancy.sql. Policies and
-- indexes are dropped; R13: the tenant_id columns hold data, so they are
-- renamed _deprecated_tenant_id_20261031200400, never dropped (re-applying
-- the up migration renames them back).
do $$
declare
  t text;
begin
  foreach t in array array['agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
                           'agent_run_links', 'agent_tool_calls', 'agent_patches'] loop
    execute format('drop index if exists public.%I', t || '_tenant_idx');
    if exists (select 1 from information_schema.columns where table_schema = 'public'
                and table_name = t and column_name = 'tenant_id') then
      execute format('alter table public.%I rename column tenant_id to _deprecated_tenant_id_20261031200400', t);
    end if;
  end loop;
end $$;

drop policy if exists "tenant members read agent hypotheses" on public.agent_hypotheses;
drop policy if exists "tenant members read agent plans" on public.agent_plans;
drop policy if exists "tenant members read agent run links" on public.agent_run_links;
drop policy if exists "tenant members read agent tool calls" on public.agent_tool_calls;
drop policy if exists "tenant members read agent patches" on public.agent_patches;
