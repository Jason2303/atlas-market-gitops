# Screenshots (capstone submission)

| # | File | What it shows |
|---|---|---|
| 1 | `01-ci-pipeline.png` | App repo → Actions: a green `ci` run on `main` (lint-test ×3, build ×4, update-config) with its duration |
| 1b | `01b-config-commit.png` | This repo: commit `deploy(staging): atlas-market sha-xxxxxxx` by atlas-ci-bot |
| 2 | `02-argocd-applications.png` | ArgoCD: root, kube-prometheus-stack, loki, alloy, monitoring-config, atlas-staging, atlas-production all **Synced / Healthy** |
| 2b | `02b-production-manual.png` | atlas-production OutOfSync after a promotion PR, before the manual Sync |
| 2c | `02c-self-heal.png` | `./scripts/chaos.sh drift` output (3 → 1) |
| 3 | `03-grafana-service-overview.png` | Atlas / Service overview on atlas-staging with live traffic |
| 3b | `03b-grafana-trace.png` | Atlas / Logs with a trace_id pasted: the same request in gateway, order-service, product-service |
| 3c | `03c-prometheus-targets.png` | Prometheus → Status → Targets: all UP |
| 4 | `04-alert-firing.png` | Prometheus → Alerts: DatabaseDown / HighErrorRate firing after `./scripts/chaos.sh outage` |
| 4b | `04b-notification.png` | Alertmanager UI and the alert-sink / Slack notification |
