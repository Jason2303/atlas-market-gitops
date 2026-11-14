# Screenshots (capstone submission)

| Screenshot | What it shows |
|---|---|
| [02-argocd-applications.png](<02-argocd-applications.png>) | ArgoCD applications managed from the config repo (staging auto-sync, production manual) |
| [04-alert-tests-ci.png](<04-alert-tests-ci.png>) | CI: promtool alert unit tests SUCCESS + Alertmanager routing per severity/environment |
| [01-ci-pipeline.jpeg](<01-ci-pipeline.jpeg>) | Successful CI run on main: lint + test x3, build + scan + push x4, deploy to staging |
| [01b-config-commit.jpeg](<01b-config-commit.jpeg>) | Config repo commit by atlas-ci-bot: CI updated the staging image tag (GitOps hand-off) |
| [01c-trivy-blocked.jpeg](<01c-trivy-blocked.jpeg>) | Trivy security gate blocking an image with a fixable CRITICAL CVE (fixed with apk upgrade) |

Live Grafana/Prometheus screenshots were limited by the 7 GB test laptop; see the main README section 10 for how alerting, routing and dashboards are verified in CI.
