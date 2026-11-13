# Runbook: NodeNotReady

| | |
|---|---|
| **Severity** | critical → `#alerts-critical` (pages on-call) |
| **Fires when** | `kube_node_status_condition{condition="Ready",status="true"} == 0` for 5 minutes |
| **Impact** | Pods on the node are unreachable. After about 5 minutes Kubernetes evicts them to other nodes, if there is capacity. |
| **Dashboards** | Atlas / Infrastructure + GitOps → *Nodes Ready* |

## 1. Confirm
```bash
kubectl get nodes -o wide
kubectl describe node <node>      # Conditions: MemoryPressure / DiskPressure / PIDPressure / KubeletReady
kubectl get pods -A -o wide --field-selector spec.nodeName=<node>
```

## 2. Diagnose
| Condition / symptom | Likely cause |
|---|---|
| `DiskPressure=True` | Disk full: see [disk-space-low](disk-space-low.md) |
| `MemoryPressure=True` | Node out of memory |
| Status `Unknown`, no heartbeat | Kubelet stopped, or the node is powered off / network partitioned |
| Cloud VM | Check the provider console for instance health / scheduled maintenance |

On the node (SSH, or `docker exec -it <node> bash` for kind):
```bash
systemctl status kubelet
journalctl -u kubelet --since "15 min ago" | tail -50
df -h ; free -m
```

## 3. Mitigate
1. Protect workloads: `kubectl cordon <node>` and `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` (if reachable).
2. Fix the cause (free disk, restart kubelet: `systemctl restart kubelet`).
3. Unrecoverable: replace the node (cloud: terminate it and let the node group recreate it; kind: `docker restart argo-lab-control-plane`).
4. `kubectl uncordon <node>` when Ready.

## 4. Verify
Node `Ready` and the alert resolves. Pods are rescheduled and the Atlas dashboards are green.

**Escalation:** if more than one node is affected, treat it as a cluster incident and involve the platform lead.
