# GPU Scaling — Architecture Note (Tier 5)

Status: **Scaffold**. Workers are not yet running. This document defines the contract that future workers will implement, plus the decisions taken in the database scaffold.

## Why a separate compute fabric

The TanStack Worker SSR runtime is fine for app logic but is fundamentally wrong for:
- long-running CPU work (>30 s)
- any GPU workload (no native compute, no CUDA, no PyTorch)
- workloads needing local scratch disk >256 MB

Therefore heavy work runs in **out-of-process workers** that pull from the Postgres job queue.

## Job queue contract

Source of truth: `public.jobs` (see migration `tier5_multitenant_jobs`).

- Workers authenticate as `service_role`.
- Workers call `claim_next_job(worker_id, classes[], lease_seconds)` — the function uses `FOR UPDATE SKIP LOCKED` so multiple workers safely poll in parallel.
- Workers must call `complete_job(job_id, result, error)` before the lease expires, or the row stays in `running` and a janitor (TODO) requeues it.

## Compute classes

| `compute_class` | Backed by                   | When to pick                           |
|-----------------|-----------------------------|----------------------------------------|
| `cpu`           | shared CPU pool             | sims < 5 min, audits, viz baking       |
| `gpu_small`     | 1× T4 / L4 worker           | medium grids, single-GPU               |
| `gpu_large`     | 1× A100 / H100 worker       | full-resolution sweeps, multi-GPU      |

Workers advertise the classes they can serve when calling `claim_next_job`. A `cpu` worker will never pick up a `gpu_large` job and vice versa.

## Scaling triggers

Until a real autoscaler is wired, the operator scales manually. Future autoscaling signals:

1. `queued` jobs older than `2× P50_runtime(class)` → scale up that class.
2. Workers idle (no `claim_next_job` row > 5 min) → scale down.
3. `attempts >= max_attempts` → page on-call (alert via `system_incidents`).

## Deployment shape (pending)

Recommended initial topology:
- **CPU pool**: 2× small instances on Cloud Run (auto-scale 0→10).
- **GPU pool**: 1× reserved L4 instance on Modal/RunPod, hand-scaled.
- All workers ship the same OCI image; entrypoint takes `--classes cpu,gpu_small` etc.

## Open questions

- [ ] How does a worker stream progress back? **Decided:** Supabase Realtime broadcast on `run:<runId>` (see `src/lib/runProgressChannel.ts`).
- [ ] Where does scratch storage live? Likely a per-job tmp dir + S3 for large artifacts.
- [ ] Per-tenant quotas — enforce in `enqueueJob` (TODO) using `PLAN_LIMITS`.
