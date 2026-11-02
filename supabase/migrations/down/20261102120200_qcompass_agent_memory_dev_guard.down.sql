-- Inverse of 20261102120200_qcompass_agent_memory_dev_guard.sql: the six
-- triggers and the two functions. They hold no data (R13).
do $$
declare
  t text;
begin
  foreach t in array array['agent_hypotheses', 'agent_plans', 'agent_approval_tokens',
                           'agent_run_links', 'agent_tool_calls', 'agent_patches'] loop
    execute format('drop trigger if exists %I on public.%I', t || '_dev_guard', t);
  end loop;
end $$;
drop function if exists public.qcompass_agent_memory_dev_guard();
drop function if exists public.qcompass_user_owned_dev(uuid);
