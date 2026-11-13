# Runbook: DiskSpaceLow / DiskSpaceCritical

| | |
|---|---|
| **Severity** | DiskSpaceLow: warning (< 10% free) → `#alerts-warning`. DiskSpaceCritical: critical (< 5% free) → `#alerts-critical` |
| **Fires when** | Free space on a writable, non-tmpfs filesystem is below the threshold for 5 minutes |
| **Impact** | When full: pods evicted (DiskPressure), databases and Prometheus/Loki stop writing, logs lost |
| **Dashboards** | Atlas / Infrastructure + GitOps → *Disk used by mountpoint* |

## 1. Confirm
```promql
1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}
```
How fast is it filling?
```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*3600) < 0
```

## 2. Find what is using space (on the node)
```bash
df -h
sudo du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -20
sudo crictl images | sort -k4 -h | tail      # container images
sudo journalctl --disk-usage
```
Common culprits: unused container images, container logs, journald, PVCs of Prometheus/Loki.

## 3. Mitigate (safest first)
1. `sudo crictl rmi --prune`: remove unused images.
2. `sudo journalctl --vacuum-size=500M`
3. Large app logs: fix log level / rotation rather than deleting open files.
4. Observability storage: lower retention (`retention` in helm values) or expand the PVC.
5. Long term: expand the volume, or add an alert on `predict_linear` so this is caught days earlier.

## 4. Verify
Free space > 20% and the alert resolves. No pods are in `Evicted` state (`kubectl get pods -A | grep Evicted`).
