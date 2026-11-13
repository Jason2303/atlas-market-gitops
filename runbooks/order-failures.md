# Runbook: OrderFailuresHigh (business)

| | |
|---|---|
| **Severity** | warning |
| **Fires when** | > 5% of checkouts fail **on our side** (`shop_orders_total{result="failed"}`) over 10 minutes. Out-of-stock rejections and invalid input are excluded: those are not failures of the system. |
| **Impact** | Direct revenue loss, even when HTTP error rates look small (checkout is a small share of traffic). |

## Steps
1. **Atlas / Service overview → Order outcomes**: is `failed` rising while `placed` drops?
2. Why orders fail (order-service logs):
   ```logql
   {namespace="atlas-production", service="order-service", level="error"}
   ```
   | Message | Cause |
   |---|---|
   | `product-service unreachable` | product-service down or slow (5 s timeout) |
   | `stock reservation failed` | product-service returned 5xx |
   | `unhandled error` after reservation | Postgres write failed; stock was **released** by the compensating call |
   | `stock release failed` | The compensation also failed: **stock is now under-counted**. Fix the stock levels by hand and record what you did. |
3. Follow one failed checkout's `trace_id` on **Atlas / Logs**.
4. Usually a symptom of [database-down](database-down.md), [service-down](service-down.md) or [high-error-rate](high-error-rate.md). Mitigate there.
