# Runbook: HighLatencyP99

| | |
|---|---|
| **Severity** | warning → `#alerts-warning` (staging: `#alerts-staging`) |
| **Fires when** | p99 latency of a service > 1 s for 5 minutes |
| **Impact** | Slow pages and checkouts for the slowest 1%. Often comes before timeouts (gateway 504 after 10 s). |

## Steps
1. **Atlas / Service overview → Duration** for each service. Latency adds up the chain: gateway includes order-service, which includes product-service and Postgres.
2. **Cache:** a low *Catalogue cache hit ratio* means every read hits Postgres. Is Redis down? See [redis-down](redis-down.md).
3. **CPU throttling** (limits are 300 m by default):
   ```promql
   sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="atlas-production"}[5m]))
   / sum by (pod) (rate(container_cpu_cfs_periods_total{namespace="atlas-production"}[5m]))
   ```
4. **Event loop:** `nodejs_eventloop_lag_p99_seconds` per pod (default Node.js metrics).
5. **Slow requests in logs:** every request line has `ms`:
   ```logql
   {namespace="atlas-production"} | json | ms > 1000
   ```
   Then follow one `trace_id` on **Atlas / Logs**.
6. **Mitigate:** more replicas or higher CPU limits **via a PR** to `envs/<env>/values.yaml`; roll back a slow release with `git revert`.
7. **Verify:** p99 < 500 ms for 10 minutes and the alert resolves.
