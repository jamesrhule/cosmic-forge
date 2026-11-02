-- Inverse of 20261102100000_qcompass_tenant_write_guard.sql. Drops the
-- trigger, the slug constraint and the helper functions; no data is touched
-- (R13). Main's "owners update tenants" policy is unchanged by either file.
drop trigger if exists tenants_write_guard on public.tenants;
drop function if exists public.qcompass_tenants_guard();
alter table public.tenants drop constraint if exists tenants_slug_not_uuid_check;
drop function if exists public.qcompass_privileged_writer(regclass);
drop function if exists public.qcompass_text_is_uuid(text);
