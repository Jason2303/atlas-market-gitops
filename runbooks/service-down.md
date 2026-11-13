# Runbook: ServiceDown

| | |
|---|---|
| **Severity** | critical (production pages; staging goes to `#alerts-staging`) |
| **Fires when** | Prometheus cannot scrape a gateway / product-service / order-service pod (`up == 0`) for 2 minutes |
| **Impact** | That pod serves nothing. If every replica is down, the service is down. |

## Steps
1. `kubectl -n <ns> get pods -l app=<service> -o wide`: Running? Ready? Restarts? If it's crash looping, see [pod-crashlooping](pod-crashlooping.md).
2. Is the database the root cause? product- and order-service exit on start if Postgres stays unreachable. Check **Atlas / Infrastructure → Postgres ready**, then [database-down](database-down.md).
3. Pod running but not scrapeable:
   ```bash
   kubectl -n <ns> port-forward pod/<pod> 9999:<3000|3001|3002>
   curl -s localhost:9999/metrics | head
   ```
4. Prometheus side: Prometheus UI → *Status → Targets* → `serviceMonitor/<ns>/atlas-market` shows the scrape error.
5. NetworkPolicies on (EKS production)? The `allow-prometheus-scrape` policy must exist: `kubectl -n <ns> get networkpolicy`.
6. Mitigate: roll back the last change **in Git**, or Sync the app if ArgoCD shows drift.
7. Verify: `up{namespace="<ns>"} == 1` for every pod, and the alert resolves.
