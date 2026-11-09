-- Inverse of 20261031200000_qcompass_tenant_slug_guard.sql.
-- Drops only the constraint; no data is touched (R13).
alter table public.tenants drop constraint if exists tenants_slug_reserved_check;
