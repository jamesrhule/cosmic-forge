-- Gate 1 code review SF4: agent memory is tenant-scoped. Additive and
-- idempotent (R13); the inverse is
-- down/20261031200400_qcompass_agent_memory_tenancy.down.sql.
--
-- The six agent_* tables (20261031160000) had no tenant, so /v1/chat and
-- /mcp shared conversations, tool calls, patches and approval tokens across
-- tenants. Each gets a nullable tenant_id. Existing rows are backfilled to
-- the dev tenant where one exists (they were written by the dev/in-process
-- path), otherwise left null; a null row belongs to no tenant and is
-- invisible to every caller. ConversationStore filters every read and
-- write on it. Members read their tenant's rows; approval tokens stay
-- service-only (a token id is a bearer secret).

do $$
declare
  t text;
  dev uuid;
begin
  select id into dev from public.tenants where slug = 'dev';
  foreach t in array array['agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
                           'agent_run_links', 'agent_tool_calls', 'agent_patches'] loop
    -- A rollback renames the column; bring it (and its data) back.
    if exists (select 1 from information_schema.columns where table_schema = 'public'
                and table_name = t and column_name = '_deprecated_tenant_id_20261031200400')
       and not exists (select 1 from information_schema.columns where table_schema = 'public'
                and table_name = t and column_name = 'tenant_id') then
      execute format('alter table public.%I rename column _deprecated_tenant_id_20261031200400 to tenant_id', t);
    end if;
    execute format(
      'alter table public.%I add column if not exists tenant_id uuid references public.tenants(id) on delete cascade', t);
    execute format('create index if not exists %I on public.%I(tenant_id)', t || '_tenant_idx', t);
    if dev is not null then
      execute format('update public.%I set tenant_id = $1 where tenant_id is null', t) using dev;
    end if;
  end loop;
end $$;

drop policy if exists "tenant members read agent hypotheses" on public.agent_hypotheses;
create policy "tenant members read agent hypotheses" on public.agent_hypotheses
  for select to authenticated using (public.is_tenant_member(tenant_id, auth.uid()));
drop policy if exists "tenant members read agent plans" on public.agent_plans;
create policy "tenant members read agent plans" on public.agent_plans
  for select to authenticated using (public.is_tenant_member(tenant_id, auth.uid()));
drop policy if exists "tenant members read agent run links" on public.agent_run_links;
create policy "tenant members read agent run links" on public.agent_run_links
  for select to authenticated using (public.is_tenant_member(tenant_id, auth.uid()));
drop policy if exists "tenant members read agent tool calls" on public.agent_tool_calls;
create policy "tenant members read agent tool calls" on public.agent_tool_calls
  for select to authenticated using (public.is_tenant_member(tenant_id, auth.uid()));
drop policy if exists "tenant members read agent patches" on public.agent_patches;
create policy "tenant members read agent patches" on public.agent_patches
  for select to authenticated using (public.is_tenant_member(tenant_id, auth.uid()));
