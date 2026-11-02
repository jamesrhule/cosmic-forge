-- Inverse of 20261102100100_qcompass_agent_memory_dev_backfill_fix.sql.
--
-- Deliberately changes nothing. The up migration only set tenant_id back to
-- null on agent rows that 20261031200400 had handed to a user-owned 'dev'
-- tenant; restoring that assignment would hand other customers' legacy
-- agent memory back to that user. No column, policy or row is removed by
-- either direction (R13), so the previous schema is already in place.
select 1;
