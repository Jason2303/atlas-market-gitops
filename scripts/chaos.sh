#!/usr/bin/env bash
# Demonstrations for the capstone evidence.
#
#   ./scripts/chaos.sh drift      kubectl-scale the STAGING gateway to 3 -> ArgoCD self-heal puts it back to 1
#   ./scripts/chaos.sh outage     stop PRODUCTION postgres + send traffic -> DatabaseDown + HighErrorRate fire
#                                 (critical, production -> #alerts-critical + alert-sink). Takes ~3-6 min.
#   ./scripts/chaos.sh status     firing alerts (via Alertmanager API) and the last notifications delivered
#   ./scripts/chaos.sh reset      remove the test traffic; production is restored by a release-manager Sync
set -euo pipefail
PROD=atlas-production
STG=atlas-staging

case "${1:-help}" in
  drift)
    echo "Desired (Git): gateway replicas=1. Changing it by hand..."
    kubectl -n $STG scale deploy gateway --replicas=3
    for i in $(seq 1 12); do
      sleep 5
      printf "t+%2ss  spec.replicas=%s  argocd=%s\n" $((i*5)) \
        "$(kubectl -n $STG get deploy gateway -o jsonpath='{.spec.replicas}')" \
        "$(kubectl -n argocd get application atlas-staging -o jsonpath='{.status.sync.status}/{.status.health.status}')"
    done
    echo "Production has no self-heal: the same change there shows OutOfSync and waits for a human." ;;

  outage)
    echo "1) Stopping production Postgres (a manual change: production does not self-heal)"
    kubectl -n $PROD scale statefulset postgres --replicas=0
    echo "2) Sending checkout traffic to production for 15 minutes"
    kubectl -n $PROD apply -f - <<'EOF'
apiVersion: batch/v1
kind: Job
metadata:
  name: chaos-traffic
  labels: { app: chaos-traffic }
spec:
  activeDeadlineSeconds: 900
  backoffLimit: 0
  template:
    metadata:
      labels: { app: chaos-traffic }
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: traffic
          image: python:3.12-alpine
          command: ["python", "-c"]
          args:
            - |
              import json, time, urllib.request
              body = json.dumps({"customer_name": "Chaos", "customer_email": "chaos@example.com",
                                 "items": [{"product_id": 1, "quantity": 1}]}).encode()
              while True:
                  for url, data in (("http://gateway:3000/api/products", None), ("http://gateway:3000/api/orders", body)):
                      try:
                          req = urllib.request.Request(url, data=data, headers={"content-type": "application/json"})
                          urllib.request.urlopen(req, timeout=5).read()
                      except Exception:
                          pass
                  time.sleep(0.5)
          resources:
            requests: { cpu: 10m, memory: 32Mi }
            limits: { cpu: 100m, memory: 64Mi }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
EOF
    echo
    echo "Expected: DatabaseDown after ~2-3 min, HighErrorRate after ~5-6 min."
    echo "Watch: Prometheus -> Alerts | Alertmanager UI | ./scripts/chaos.sh status | Grafana 'Atlas / Logs'" ;;

  status)
    echo "== Firing alerts (Alertmanager)"
    kubectl -n monitoring exec statefulset/alertmanager-kps-alertmanager -c alertmanager -- \
      wget -qO- 'http://localhost:9093/api/v2/alerts?active=true&silenced=false&inhibited=false' 2>/dev/null \
      | python3 -c 'import sys,json; [print(f"  {a[\"labels\"].get(\"severity\",\"\"):8} {a[\"labels\"][\"alertname\"]:26} {a[\"labels\"].get(\"namespace\",\"\")}") for a in json.load(sys.stdin)]' \
      || echo "  (could not reach Alertmanager)"
    echo "== Last notifications delivered (alert-sink)"
    kubectl -n monitoring logs deploy/alert-sink --tail=10 ;;

  reset)
    kubectl -n $PROD delete job chaos-traffic --ignore-not-found
    echo "Production is now OutOfSync (postgres replicas 0 vs 1 in Git)."
    echo "Restore it the GitOps way: ArgoCD UI as release-bob -> atlas-production -> Sync"
    echo "  (or: kubectl -n argocd exec deploy/argocd-server -- argocd app sync atlas-production ... )" ;;

  *) sed -n '2,10p' "$0" ;;
esac
