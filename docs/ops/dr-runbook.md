# Disaster Recovery Runbook (Tier 5)

**Audience:** on-call engineer.
**Goal:** restore service to a known-good state with bounded data loss after any of the failure modes below.

## Service-level objectives

| Metric | Target | Notes |
|--------|--------|-------|
| RPO    | ≤ 24 h | Lovable Cloud takes daily Postgres + storage snapshots. |
| RTO    | ≤ 4 h  | Time from detection to last-known-good restore. |
| MTTR (incident comms) | ≤ 30 min | First entry in `system_incidents` within this window. |

## Failure modes & playbooks

### A. Database corruption / accidental drop

1. Page on-call, set status to **major** in `system_incidents`.
2. Stop all writes — set the project to read-only via Lovable Cloud → Pause writes.
3. Restore the most recent snapshot from Lovable Cloud → Backups.
   - Restore as a *new* project first; never restore in place until verified.
4. Verify row counts on `runs`, `tenants`, `tenant_members`, `jobs`.
5. Cut DNS (or update `VITE_SUPABASE_URL` build secret) once verified.
6. Resume writes; close incident.

### B. Storage bucket loss (`viz-timelines`, `run-artifacts`)

1. Snapshot timelines are large but regenerable from the source `run_results` payload.
2. Mark affected runs as `status = 'failed'` and re-enqueue `viz.bake` jobs:
   ```sql
   insert into public.jobs (tenant_id, kind, payload, run_id, created_by, compute_class)
   select r.tenant_id, 'viz.bake', '{}'::jsonb, r.id, r.author_user_id, 'cpu'
     from public.runs r
    where r.id in ( /* affected ids */ );
   ```
3. Communicate via `/status`.

### C. Secret leak (service-role key, JWT secret)

1. Rotate the leaked secret in Lovable Cloud → Settings → API keys.
2. Rotate `LOVABLE_API_KEY` via the dedicated rotate tool.
3. Invalidate all live sessions (Auth → "Sign out all users").
4. Audit `tool_call_audit` for the time window since suspected leak.
5. File a post-mortem.

### D. Region-wide outage

1. Lovable Cloud is single-region today — no warm DR exists.
2. Update `/status` with severity `critical`, link to upstream provider status page.
3. While waiting: set all routes that depend on Supabase to a maintenance shell (TODO: add a global `MAINTENANCE_MODE` env flag).
4. After restore, run smoke tests (`bun test:e2e`) and the audit gate (`bun audit:gate`).

## Drills

Run once per quarter:

- [ ] Restore last night's snapshot into a scratch project; diff `runs.id` set against production.
- [ ] Trigger a fake `system_incidents` row and verify `/status` reflects it within 60 s.
- [ ] Rotate `LOVABLE_API_KEY` in a test workspace; confirm chat still works after rotation.

## On-call comms template

```
Incident: <short title>
Severity: <minor | major | critical>
Started: <UTC timestamp>
Impact: <user-visible effect>
Status: investigating | identified | monitoring | resolved
Next update: <UTC timestamp>
```

Post the same payload to `system_incidents` so `/status` reflects it automatically.
