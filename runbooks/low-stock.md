# Runbook: LowStock (info)

| | |
|---|---|
| **Severity** | info → `#alerts-info` (no page; staging → `#alerts-staging`) |
| **Fires when** | A product has fewer than 5 units for 10 minutes (`product_stock_units`, read from Postgres at scrape time) |
| **Impact** | None yet. Orders for that SKU will soon be rejected with 409 `insufficient_stock`. |

## Steps
1. **Atlas / Service overview → Stock levels**: which SKUs, and how fast are they falling?
2. Notify merchandising/operations to restock.
3. In staging, the synthetic load generator buys continuously, so stock runs down over hours by design. Reset it by recreating the staging database (staging data is disposable):
   ```bash
   kubectl -n atlas-staging delete statefulset postgres && kubectl -n atlas-staging delete pvc data-postgres-0
   ```
   ArgoCD recreates Postgres and product-service reseeds the catalogue on its next start (`kubectl -n atlas-staging rollout restart deploy/product-service`).
