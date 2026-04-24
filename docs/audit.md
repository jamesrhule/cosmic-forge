# Tool-call audit — export & review runbook

The assistant tool-call audit trail lives in the `tool_call_audit` table
(Lovable Cloud / Postgres). Per the Tier-D decision we ship the table only —
no admin UI in the app. Reviews happen via `psql` or CSV export.

## Roles & admin bootstrap

The `app_role` enum has three tiers:

- `viewer` — granted automatically to every newly-confirmed user (via the
  `on_auth_user_created` trigger). Default for the public catalog and chat.
- `researcher` — reserved for future write-tier defaults (currently unused).
- `admin` — required to read other users' audit rows and to approve
  destructive assistant tools.

**Bootstrapping the first admin.** After the first user signs in:

1. Open `/login` while signed in.
2. Expand "First-user admin claim".
3. Type the same email you signed in with and press **Claim**.

Internally this calls the SECURITY DEFINER function `public.claim_admin(_email)`
which checks `auth.jwt() ->> 'email'` and inserts an `admin` row in
`user_roles`. It is idempotent — safe to call repeatedly.

To grant `admin` to other users later, run as an existing admin:

```sql
insert into public.user_roles (user_id, role, granted_by)
select u.id, 'admin'::app_role, auth.uid()
from auth.users u where u.email = 'someone@example.com'
on conflict (user_id, role) do nothing;
```



## Schema

```
tool_call_audit (
  id                uuid PRIMARY KEY,
  user_id           uuid       -- author; NULL for signed-out / system calls
  conversation_id   text       -- chat conversation id
  tool_name         text       -- e.g. start_run, suggest_parameters
  tier              tool_tier  -- read | write | destructive
  args_redacted     jsonb      -- args with sensitive keys masked
  status            tool_status -- ok | error | denied | pending_approval
  result_summary    text       -- truncated result/reason (≤ 1000 chars)
  latency_ms        integer
  approval_token_id text       -- when destructive tool used a signed token
  created_at        timestamptz
)
```

Row-level security:
- Users can read their own rows.
- Members of `app_role = admin` can read everything (via `has_role()`).
- Inserts only from the row owner (`user_id = auth.uid()`).

## Common queries

Connect with the Cloud database connection string, then run:

### Recent calls across all users (admin only)

```sql
select created_at, user_id, tool_name, tier, status, latency_ms
from tool_call_audit
order by created_at desc
limit 200;
```

### Denied or errored calls in the last 24h

```sql
select created_at, user_id, tool_name, tier, status, result_summary
from tool_call_audit
where status in ('denied', 'error')
  and created_at > now() - interval '24 hours'
order by created_at desc;
```

### Per-tool failure rate (last 7 days)

```sql
select tool_name,
       count(*) filter (where status = 'ok')      as ok,
       count(*) filter (where status = 'error')   as errors,
       count(*) filter (where status = 'denied')  as denied,
       round(100.0 * count(*) filter (where status <> 'ok') / count(*), 1) as fail_pct
from tool_call_audit
where created_at > now() - interval '7 days'
group by tool_name
order by fail_pct desc nulls last;
```

### Slow calls

```sql
select created_at, tool_name, latency_ms, result_summary
from tool_call_audit
where latency_ms is not null
order by latency_ms desc
limit 50;
```

### A single user's history

```sql
select created_at, tool_name, tier, status, result_summary
from tool_call_audit
where user_id = '<UUID>'
order by created_at desc;
```

## CSV export

Streaming export — does not buffer in psql:

```bash
psql "$LOVABLE_CLOUD_DB_URL" \
  -c "COPY (
        select created_at, user_id, conversation_id, tool_name, tier,
               status, latency_ms, approval_token_id, result_summary, args_redacted
        from tool_call_audit
        where created_at > now() - interval '30 days'
        order by created_at desc
      ) TO STDOUT WITH CSV HEADER" \
  > audit_$(date +%Y%m%d).csv
```

For a tool-scoped export:

```bash
psql "$LOVABLE_CLOUD_DB_URL" \
  -c "COPY (
        select * from tool_call_audit
        where tool_name = 'start_run' and created_at > now() - interval '90 days'
      ) TO STDOUT WITH CSV HEADER" \
  > start_run_audit.csv
```

## Tier policy reference

The frontend resolves the tier from `src/lib/toolRegistry.ts`:

| Tier         | Examples                                | Default policy                                                |
| ------------ | --------------------------------------- | ------------------------------------------------------------- |
| `read`       | `load_run`, `compare_runs`, `cite_paper`| Auto-allow.                                                   |
| `write`      | `start_run`, `suggest_parameters`       | Confirm in UI; allowed for `researcher` + `admin`.            |
| `destructive`| `delete_run`, `cancel_run` (future)     | Block unless `admin` AND signed approval token from backend.  |

When extending the tool surface, add the new tool to `TOOL_TIERS` (or
`DESTRUCTIVE_TOOLS`) — unknown tools fail closed and get audited as
`denied`.

## Argument redaction

Args are stored in `args_redacted` after passing through `redactArgs()`
(`src/lib/audit.ts`). Sensitive keys (`password`, `token`, `api_key`,
`authorization`, `approval_token`, …) are masked as `"[redacted]"` and
strings over 2000 chars are truncated. Extend `SENSITIVE_KEYS` when new
tools accept new secret-like inputs.

## Retention

There is no automated retention policy yet. To truncate:

```sql
delete from tool_call_audit where created_at < now() - interval '180 days';
```

Wire this into a scheduled job once the consortium picks a retention
window.

---

## QCompass shell — isolation contract (Phase 1)

The QCompass shell adds a typed plugin seam (`src/lib/domains/`) and
five stub modules (`src/lib/qcompass/{hamiltonianRegistry,
resourceEstimator, classicalReference, backendRouter, benchmarkSuite}`)
so additional physics domains can be added later without touching the
audited UCGLE-F1 cosmology core.

### Invariants

1. **One-way coupling.** Nothing under `src/services/` may import from
   `src/lib/domains/` or `src/lib/qcompass/`. The cosmology adapter
   wraps `services/simulator.ts`; services do not know the registry
   exists. CI may grep for violations.
2. **S1–S15 reads cosmology outputs only.** The audit pipeline
   continues to consume `RunResult` produced by the cosmology code
   path. No quantum-derived claim is admitted to S1–S15. Phase 2+
   quantum experiments will run a parallel S-Q audit suite per domain.
3. **`RunResult.provenance` is reserved.** The new optional
   `RunProvenance` field stays `null` / omitted for cosmology runs and
   never participates in η_B validation. It exists only so Phase 2+
   quantum results can attach their classical reference, resource
   estimate, device calibration hash, and error mitigation config
   without a database migration.
4. **`FEATURES.domainsRegistry` defaults off.** With the flag off the
   UI is byte-identical to the UCGLE-F1-only build. Cosmology runs are
   byte-identical with the flag on or off.
5. **No vendor estimates without cross-check.** Phase 2 quantum
   resource numbers MUST be cross-validated by at least two of Azure
   QRE / QREChem / TFermion before any claim ships, per the architect
   assessment Section 7.
6. **No "wormhole in a lab" framing.** The eventual `gravity.syk`
   plugin must flag learned Hamiltonians in provenance and never
   present them as empirical quantum-gravity measurements.

### Phase boundaries

- **Phase 1 (now):** shell only — domain registry + stubs + cosmology
  adapter + UI selector. No new science, no new backends.
- **Phase 2:** first non-cosmology plugin (chemistry: H₂ / LiH / N₂
  via Qiskit SQD with classical DMRG reference). Adds its own S-chem
  audit suite in a separate package. Cosmology core unchanged.
- **Phase 3:** early-FT readiness (QIR, surface-code-aware compilation,
  FeMoco/P450 templates). Decision point: if no domain has delivered a
  reproducible, classically unreachable, scientifically relevant
  observable by end of Phase 3, descope quantum to research-only.
