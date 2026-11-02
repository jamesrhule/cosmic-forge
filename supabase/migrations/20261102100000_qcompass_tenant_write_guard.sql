-- Gate 1 round 2 (security lane DB): column rules on public.tenants for
-- client writers. Additive and idempotent (R13); the inverse is
-- down/20261102100000_qcompass_tenant_write_guard.down.sql, which drops only
-- what this file adds (no data is touched in either direction).
--
-- Main's "owners update tenants" policy (20260427001133) lets a tenant's
-- owner or admin update every column, and every user owns their personal
-- tenant (ensure_personal_tenant). So any user could:
--   * set subscription_tier = 'enterprise', which plans.enforce_at_enqueue
--     trusts for every plan limit (round-2 c2 HIGH);
--   * set created_by = null and slug = 'dev' in one UPDATE, which passes
--     tenants_slug_reserved_check (20261031200000) because that check keys
--     the reservation on created_by (round-2 c1/c2 MEDIUM).
--
-- A BEFORE INSERT OR UPDATE trigger now applies these rules to every caller
-- that is neither service_role nor the table owner (PostgREST's
-- authenticated/anon users; the API, the worker, security-definer functions
-- such as ensure_personal_tenant and migrations run as the owner):
--   * INSERT: subscription_tier is forced to 'free'.
--   * UPDATE: subscription_tier and created_by are immutable.
--   * INSERT/UPDATE: the slug may not become 'dev' (any case, any
--     surrounding blanks): only the service creates its development tenant.
--
-- The UUID-shaped-slug part of tenants_slug_reserved_check is a regex that
-- misses forms Postgres casts to uuid (a hyphen after any group of four hex
-- digits, e.g. 'a0ee-bc99-9c0b-4ef8-bb6d-6bb9-bd38-0a11'; round-2 c1 NIT).
-- tenants_slug_not_uuid_check refuses any slug that casts to uuid, for every
-- writer. It is added NOT VALID and validated only when no existing row
-- violates it; a violating row is reported with a NOTICE for James to rename.

create or replace function public.qcompass_text_is_uuid(_value text)
returns boolean
language plpgsql
immutable
set search_path = public
as $$
begin
  perform _value::uuid;
  return true;
exception when invalid_text_representation then
  return false;
end;
$$;

-- True for the roles that may write any column: the table's owner (and
-- superusers) and service_role. Security invoker on purpose: it judges the
-- role that runs the statement.
create or replace function public.qcompass_privileged_writer(_rel regclass)
returns boolean
language sql
stable
set search_path = public
as $$
  select pg_has_role(current_user, (select relowner from pg_class where oid = _rel), 'MEMBER')
      or pg_has_role(current_user, 'service_role', 'MEMBER')
$$;

create or replace function public.qcompass_tenants_guard()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if public.qcompass_privileged_writer(tg_relid::regclass) then
    return new;
  end if;
  if (tg_op = 'INSERT' or new.slug is distinct from old.slug)
     and lower(btrim(new.slug)) = 'dev' then
    raise exception 'tenant slug % is reserved', quote_literal(new.slug)
      using errcode = 'check_violation';
  end if;
  if tg_op = 'INSERT' then
    new.subscription_tier := 'free';
    return new;
  end if;
  if new.subscription_tier is distinct from old.subscription_tier then
    raise exception 'subscription_tier is changed by billing only'
      using errcode = 'insufficient_privilege';
  end if;
  if new.created_by is distinct from old.created_by then
    raise exception 'created_by is immutable'
      using errcode = 'insufficient_privilege';
  end if;
  return new;
end;
$$;

drop trigger if exists tenants_write_guard on public.tenants;
create trigger tenants_write_guard
  before insert or update on public.tenants
  for each row execute function public.qcompass_tenants_guard();

do $$
declare
  bad int;
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'tenants_slug_not_uuid_check' and conrelid = 'public.tenants'::regclass
  ) then
    alter table public.tenants
      add constraint tenants_slug_not_uuid_check check (not public.qcompass_text_is_uuid(slug)) not valid;
  end if;

  select count(*) into bad from public.tenants where public.qcompass_text_is_uuid(slug);
  if bad = 0 then
    alter table public.tenants validate constraint tenants_slug_not_uuid_check;
  else
    raise notice 'tenants_slug_not_uuid_check left NOT VALID: % existing tenant(s) use a slug that casts to uuid', bad;
  end if;
end $$;
