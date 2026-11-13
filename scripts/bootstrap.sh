#!/usr/bin/env bash
# One-time bootstrap. After this, ArgoCD deploys EVERYTHING from Git:
# the monitoring stack, the monitoring config, and the app in staging + production.
#
#   ./scripts/bootstrap.sh                                   # current kubectl context
#   SLACK_WEBHOOK_URL=https://hooks.slack.com/... ./scripts/bootstrap.sh
#
# Creates only what must NOT live in Git: secrets. Everything else is a Git commit away.
set -euo pipefail
cd "$(dirname "$0")/.."
step() { echo; echo "==> $*"; }

echo "Cluster: $(kubectl config current-context)"

step "ArgoCD (installed only if missing)"
if ! kubectl get namespace argocd >/dev/null 2>&1; then
  kubectl create namespace argocd
  kubectl apply -n argocd --server-side --force-conflicts \
    -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
fi
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=300s
kubectl -n argocd rollout status deploy/argocd-applicationset-controller --timeout=300s

step "ArgoCD RBAC + demo accounts (dev-alice = developer, release-bob = release manager)"
kubectl -n argocd patch configmap argocd-cm --type merge \
  -p '{"data":{"accounts.dev-alice":"login","accounts.release-bob":"login"}}'
kubectl apply -f argocd/rbac.yaml

step "Namespaces"
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
for env in staging production; do
  kubectl create namespace "atlas-$env" --dry-run=client -o yaml | kubectl apply -f -
  kubectl label namespace "atlas-$env" pod-security.kubernetes.io/enforce=restricted environment="$env" --overwrite
done

step "Secrets (generated here, never committed)"
rand() { openssl rand -base64 32 | tr -d '/+=' | cut -c1-24; }
for env in staging production; do
  kubectl -n "atlas-$env" get secret atlas-db >/dev/null 2>&1 || \
    kubectl -n "atlas-$env" create secret generic atlas-db --from-literal=password="$(rand)"
done
kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1 || \
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=admin-user=admin --from-literal=admin-password="$(rand)"
kubectl -n monitoring create secret generic alertmanager-slack \
  --from-literal=webhook-url="${SLACK_WEBHOOK_URL:-https://hooks.slack.com/services/NOT/CONFIGURED/YET}" \
  --dry-run=client -o yaml | kubectl apply -f -

step "AppProjects + root app (app-of-apps)"
kubectl apply -f argocd/projects.yaml
kubectl apply -f argocd/root-app.yaml

cat <<'EOF'

==================================================================================
 Bootstrapped. ArgoCD now creates, in order (watch: kubectl -n argocd get applications -w):
   wave 0  kube-prometheus-stack     (Prometheus, Alertmanager, Grafana)    ~3-5 min
   wave 1  loki, alloy, monitoring-config (rules, dashboards, alert-sink)
   wave 2  atlas-staging  (auto-sync)   atlas-production (waits for manual Sync)

 ArgoCD UI     kubectl -n argocd port-forward svc/argocd-server 8080:443
               admin password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
 Grafana       kubectl -n monitoring port-forward svc/kps-grafana 3000:80
               admin password: kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
 Prometheus    kubectl -n monitoring port-forward svc/kps-prometheus 9090
 Alertmanager  kubectl -n monitoring port-forward svc/kps-alertmanager 9093
 Shop UI       kubectl -n atlas-staging port-forward svc/frontend 8081:8080   -> http://localhost:8081
==================================================================================
EOF
