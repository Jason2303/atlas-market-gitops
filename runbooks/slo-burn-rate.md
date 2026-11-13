# Runbook: SLOErrorBudgetBurnFast / SLOErrorBudgetBurnSlow

**SLO:** 99.5% of requests per service succeed (per environment) over 30 days, so the error budget is 0.5% (~3.6 h of total outage per month).

| Alert | Condition | Severity | Meaning |
|---|---|---|---|
| SLOErrorBudgetBurnFast | 1 h **and** 5 m error ratio > 14.4 × 0.5% | critical (page) | 2% of the monthly budget gone in 1 h; budget exhausted in about 2 days |
| SLOErrorBudgetBurnSlow | 6 h **and** 30 m error ratio > 6 × 0.5% | warning (ticket) | 5% of the budget gone in 6 h; budget exhausted in about 5 days |

The short window makes the alert resolve quickly once the problem is fixed; the long window prevents paging on short blips.

## Steps
1. Open **Atlas / SLO 99.5%**: which service, and how much budget is left?
2. The underlying cause is almost always the same as [high-error-rate](high-error-rate.md); follow that runbook to find and fix it.
3. Slow burn with no HighErrorRate: look for a steady low-level error source (one bad replica, a specific route, a flaky dependency):
   ```promql
   sum by (service, route, status) (rate(http_requests_total{namespace="atlas-production", status=~"5.."}[6h]))
   ```
4. **Budget policy:** if less than 25% of the budget remains, freeze risky releases for that service and prioritise reliability work until it recovers.
