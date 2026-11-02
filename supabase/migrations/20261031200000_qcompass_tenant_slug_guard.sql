-- SEC-H1 (Gate 1 security review): reserve the tenant slug 'dev' and forbid
-- UUID-shaped slugs. Additive and idempotent (R13); the inverse is
-- down/20261031200000_qcompass_tenant_slug_guard.down.sql.
--
--   * 'dev' is the API's development tenant (QCOMPASS_ENV=dev only). Only
--     the service itself may create it (created_by is null); a user who
--     creates or renames a tenant to 'dev' is refused.
--   * A slug shaped like a UUID (any form Postgres casts to uuid) could
--     shadow another tenant's id wherever a tenant is named by slug or id
--     (AuthStore.resolve_tenant), so it is refused.
--
-- Existing rows are never rewritten. The constraint is added NOT VALID, so
-- it binds every insert and update from now on, and is validated only when
-- no existing row violates it. A violating row is reported with a NOTICE
-- for James to rename (docs/build/lanes/W1-platform.md, SEC-H1).

do $$
declare
  bad int;
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'tenants_slug_reserved_check' and conrelid = 'public.tenants'::regclass
  ) then
    alter table public.tenants
      add constraint tenants_slug_reserved_check check (
        (slug <> 'dev' or created_by is null)
        and slug !~* '^\{?[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\}?$'
      ) not valid;
  end if;

  select count(*) into bad from public.tenants
   where not ((slug <> 'dev' or created_by is null)
              and slug !~* '^\{?[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\}?$');
  if bad = 0 then
    alter table public.tenants validate constraint tenants_slug_reserved_check;
  else
    raise notice 'tenants_slug_reserved_check left NOT VALID: % existing tenant(s) use a reserved slug', bad;
  end if;
end $$;
