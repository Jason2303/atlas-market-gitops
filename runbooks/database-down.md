# Runbook: DatabaseDown

| | |
|---|---|
| **Severity** | critical. Production pages via `#alerts-critical`. It inhibits HighErrorRate / ServiceDown / OrderFailuresHigh in the same namespace, because they are symptoms of this. |
| **Fires when** | The `postgres` StatefulSet has had 0 ready replicas for 2 minutes |
| **Impact** | Catalogue (cache misses), every order, and product-/order-service readiness all fail. Pods go NotReady; the gateway returns 502. |

## 1. Look
```bash
NS=atlas-production
kubectl -n $NS get statefulset postgres
kubectl -n $NS get pods -l app=postgres
kubectl -n $NS describe pod postgres-0 | tail -20
kubectl -n $NS logs postgres-0 --tail=50
kubectl -n $NS get pvc
```

## 2. Common causes
| Symptom | Cause | Fix |
|---|---|---|
| `READY 0/0`, replicas: 0 | Someone scaled it down by hand (drift). ArgoCD shows atlas-production **OutOfSync**. | Sync atlas-production in ArgoCD (release manager): Git says replicas: 1 |
| `Pending`, PVC `Pending` | No volume. On EKS: EBS CSI or AZ mismatch | `kubectl describe pvc`; check the StorageClass |
| `CrashLoopBackOff`, `could not write ... No space left` | Volume full | Expand the PVC (`allowVolumeExpansion: true`) via `postgres.storage` in Git |
| `CreateContainerConfigError` | `atlas-db` Secret missing | Recreate it (see scripts/bootstrap.sh); the password must match the existing data |
| Probe failures, OOMKilled | Too little memory | Raise `postgres.resources` in Git |

## 3. After recovery
- product-service and order-service become Ready on their own: `readyz` checks the DB and the pods are never restarted for it, by design.
- Watch **Atlas / Service overview**: errors drop to 0, and orders/min recovers.
- Orders attempted during the outage were rejected (503/502), never half-written: stock reservation is all-or-nothing with a compensating release.
- If the volume was lost: restore from backup. On EKS, use EBS snapshots; RDS with PITR is the recommended production upgrade.
