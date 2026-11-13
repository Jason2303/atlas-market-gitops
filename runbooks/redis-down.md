# Runbook: RedisDown

| | |
|---|---|
| **Severity** | warning (the shop keeps working) |
| **Fires when** | The `redis` Deployment has had 0 available replicas for 5 minutes |
| **Impact** | By design both uses fail **open**: the catalogue is read from Postgres on every request (slower, more DB load), and the gateway **stops rate limiting**. |

## Steps
1. `kubectl -n <ns> get pods -l app=redis` and `kubectl -n <ns> logs deploy/redis --tail=30`.
2. Confirm the effect: **Atlas / Service overview → Catalogue cache hit ratio** drops to 0%. Logs show `redis unavailable, serving without cache` / `rate limiting disabled`.
3. Redis holds nothing durable (no disk, by design), so restarting it is always safe: `kubectl -n <ns> rollout restart deploy/redis`. Note that in staging, ArgoCD self-heal recreates a deleted Redis by itself.
4. If it keeps dying: OOMKilled? Raise `redis.resources` via a PR.
5. Watch Postgres and latency until the cache is warm again (TTL 30 to 60 s).
