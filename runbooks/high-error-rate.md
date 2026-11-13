# Runbook: HighErrorRate

| | |
|---|---|
| **Severity** | critical. Production → `#alerts-critical` (pages). Staging → `#alerts-staging` (no page) |
| **Fires when** | > 5% of a service's requests return 5xx for 5 minutes |
| **Impact** | Shoppers can't browse or check out. Revenue is lost while it lasts. |
| **Dashboards** | Atlas / Service overview, Atlas / Logs + trace lookup |

## 1. Confirm and locate (2 min)
1. **Atlas / Service overview**, choose the environment → *Errors: 5xx ratio by service*.
2. Errors flow **upstream**: `postgres → product-service → order-service → gateway`. The **deepest** red service is usually the cause; the gateway turns every failure behind it into a 502/504.
3. Check the data tier on **Atlas / Infrastructure**: *Postgres ready*, *Redis available*. If Postgres is 0, go to [database-down](database-down.md).

## 2. Find the cause (5 min)
- Error logs in the environment (Loki):
  ```logql
  {namespace="atlas-production", level="error"}
  ```
- Take one failing request's `trace_id` (in every log line, and in the `X-Trace-Id` response header). Paste it into **Atlas / Logs → trace_id** to see that request's path through gateway → order-service → product-service, with the error at the hop where it happened.
- Typical messages:
  | Log message | Meaning |
  |---|---|
  | `upstream error ... ECONNREFUSED` (gateway) | backend has no ready pods |
  | `upstream timeout` (gateway, 504) | backend too slow (see [high-latency](high-latency.md)) |
  | `product-service unreachable` (order-service, 503) | product-service down |
  | `unhandled error` / `postgres pool error` | database problem |
- What changed? Check ArgoCD → app → *History and rollback*, or `git log -5 envs/production/values.yaml`.

## 3. Mitigate
| Cause | Action |
|---|---|
| Bad release | **Roll back in Git:** `git revert <promotion commit>`, merge, then Sync `atlas-production` (staging auto-syncs) |
| Postgres down | [database-down](database-down.md) |
| Pods crash looping | [pod-crashlooping](pod-crashlooping.md) |
| Overload | Raise replicas in `envs/<env>/values.yaml` (PR), or enable the HPA on EKS |

Avoid `kubectl edit` in staging, because self-heal will undo it. In production, a manual change shows as OutOfSync; reconcile it in Git afterwards.

## 4. Verify and close
Error ratio < 1% for 10 minutes, the alert resolves (✅ in Slack and a `resolved` line in alert-sink), and the error-budget impact is checked on **Atlas / SLO**.
