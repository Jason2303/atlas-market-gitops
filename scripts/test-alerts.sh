#!/usr/bin/env bash
# Validate + unit-test the alert rules and Alertmanager routing. No cluster needed.
# Needs: promtool, amtool (Prometheus / Alertmanager release tarballs) and mikefarah yq.
set -euo pipefail
cd "$(dirname "$0")/.."
yq '.spec' platform/monitoring-config/alert-rules.yaml > tests/rules.generated.yaml
promtool check rules tests/rules.generated.yaml
promtool test rules tests/alerts.test.yaml

yq '.alertmanager.config' platform/monitoring/kube-prometheus-stack.yaml > tests/alertmanager.generated.yaml
amtool check-config tests/alertmanager.generated.yaml
echo "Routing:"
for labels in \
  "alertname=HighErrorRate severity=critical namespace=atlas-production" \
  "alertname=HighErrorRate severity=critical namespace=atlas-staging" \
  "alertname=DiskSpaceLow severity=warning" \
  "alertname=LowStock severity=info namespace=atlas-production"; do
  printf "  %-72s -> %s\n" "$labels" "$(amtool config routes test --config.file=tests/alertmanager.generated.yaml $labels | tr '\n' ' ')"
done
