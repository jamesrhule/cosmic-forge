-- Auto-grant 'viewer' role on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_roles (user_id, role)
  values (new.id, 'viewer'::app_role)
  on conflict (user_id, role) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- One-shot admin claim. Caller must be signed in AND the email argument
-- must match auth.jwt() ->> 'email'. Returns true on success.
create or replace function public.claim_admin(_email text)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  caller_email text;
  caller_id uuid;
begin
  caller_id := auth.uid();
  if caller_id is null then
    return false;
  end if;

  caller_email := lower(coalesce(auth.jwt() ->> 'email', ''));
  if caller_email = '' or caller_email <> lower(_email) then
    return false;
  end if;

  insert into public.user_roles (user_id, role, granted_by)
  values (caller_id, 'admin'::app_role, caller_id)
  on conflict (user_id, role) do nothing;

  return true;
end;
$$;