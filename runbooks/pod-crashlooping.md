# Runbook: PodCrashLooping

| | |
|---|---|
| **Severity** | warning → `#alerts-warning` (critical if it also triggers ServiceDown/HighErrorRate) |
| **Fires when** | A container restarted more than 3 times in the last hour |
| **Impact** | Reduced capacity; if all replicas crash, the service is down |
| **Dashboards** | Atlas / Infrastructure + GitOps → *Containers restarting* |

## 1. Identify
```bash
kubectl get pods -A --field-selector=status.phase!=Succeeded | grep -Ei 'crash|error|backoff'
kubectl -n <ns> describe pod <pod>         # Last State: reason + exit code
```
| Exit code / reason | Usually means |
|---|---|
| `OOMKilled` (137) | Memory limit too low or a memory leak |
| 1 / 2 | Application error on start (bad config, missing env/secret) |
| 137 without OOM | Liveness probe failing, so kubelet kills it |
| `CreateContainerConfigError` | Missing ConfigMap/Secret |

## 2. Read the logs of the crashed attempt
```bash
kubectl -n <ns> logs <pod> --previous
```
Or in Loki: `{namespace="<ns>", pod="<pod>"}` (Alloy keeps logs from earlier attempts).

## 3. Mitigate
| Cause | Action |
|---|---|
| Bad release | Roll back **in Git**: `git revert` the commit that changed `image.tag` in `envs/<env>/values.yaml` (a `kubectl rollout undo` is reverted by self-heal in staging) |
| `startup failed: postgres not reachable after 30 attempts` | The DB is down; see [database-down](database-down.md). Pods recover by themselves once Postgres is back |
| OOMKilled | Raise `resources.limits.memory`; investigate a leak with the memory panels |
| Liveness too strict | Increase `initialDelaySeconds` / `failureThreshold` |
| Missing config | Restore the ConfigMap/Secret (via Git) |

## 4. Verify
`kubectl -n <ns> get pods -w` shows Running and Ready with restarts no longer increasing. The alert auto-resolves once the 1-hour window no longer contains more than 3 restarts.
