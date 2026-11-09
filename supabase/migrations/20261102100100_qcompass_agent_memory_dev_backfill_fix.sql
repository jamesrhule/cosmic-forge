-- Gate 1 round 2 (security lane DB): undo the SF4 backfill into a
-- user-owned 'dev' tenant. Additive and idempotent (R13); the inverse is
-- down/20261102100100_qcompass_agent_memory_dev_backfill_fix.down.sql.
--
-- 20261031200400 set tenant_id on every tenant-less agent_* row to the
-- tenant whose slug is 'dev', whoever owns it. Those rows came from every
-- tenant's /v1/chat and /mcp calls, not only from the dev path, and the
-- member read policies of 20261031200400 then show them to that tenant's
-- members. A 'dev' tenant that a user created or joined (main had no slug
-- guard, and 20261031200000 leaves such a row in place with its constraint
-- NOT VALID) therefore received every customer's legacy conversations,
-- tool calls and patches (round-2 c1/c2/c4).
--
-- The service's own development tenant is the one AuthStore.ensure_tenant
-- creates: created_by is null and it has no members. Any other 'dev' tenant
-- is user-owned: created_by is not null, or some user is a member. Agent
-- rows assigned to a user-owned 'dev' tenant are set back to tenant_id null
-- (a null row belongs to no tenant and is invisible to every caller and to
-- ConversationStore). Their real tenant is unknown, so null is the only
-- safe owner. Nothing is deleted. The row count is reported with a NOTICE.
--
-- 20261031200400 is not edited (decision 14). No environment has applied it
-- (DATABASE_URL is BLOCKED-ON-JAMES), so the first deploy applies both
-- files in one run and the backfill is undone before any request is served.

do $$
declare
  t text;
  n bigint;
  total bigint := 0;
begin
  foreach t in array array['agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
                           'agent_run_links', 'agent_tool_calls', 'agent_patches'] loop
    if exists (select 1 from information_schema.columns where table_schema = 'public'
                and table_name = t and column_name = 'tenant_id') then
      execute format(
        'update public.%I a set tenant_id = null from public.tenants d '
        'where a.tenant_id = d.id and d.slug = ''dev'' '
        'and (d.created_by is not null '
        '     or exists (select 1 from public.tenant_members m where m.tenant_id = d.id))', t);
      get diagnostics n = row_count;
      total := total + n;
    end if;
  end loop;
  if total > 0 then
    raise notice 'agent memory: % row(s) assigned to a user-owned ''dev'' tenant set back to tenant_id null', total;
  end if;
end $$;
