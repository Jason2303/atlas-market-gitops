# Runbook: StagingOutOfSync / ArgoAppDegraded

| Alert | Fires when | Severity |
|---|---|---|
| StagingOutOfSync | `atlas-staging` is not Synced for 15 minutes (it auto-syncs, so this means syncs are failing) | warning |
| ArgoAppDegraded | Any ArgoCD application has been Degraded for 10 minutes | warning |

`atlas-production` being **OutOfSync is normal** after a promotion PR is merged: it waits for a release manager to sync. That's why it is excluded from StagingOutOfSync.

## Steps
1. ArgoCD UI → the app → **Sync status** / **Last sync result** (or `kubectl -n argocd get application <app> -o yaml | yq .status.operationState`).
2. Common causes:
   | Message | Fix |
   |---|---|
   | `ComparisonError` / chart render error | The last commit broke the chart or values. `git revert` it (the `validate` workflow should have caught it, so check why it didn't) |
   | `one or more objects failed to apply` | Read the object error, e.g. a forbidden kind for the `atlas` AppProject, or an immutable field change |
   | `ImagePullBackOff` (Degraded) | The tag in `envs/<env>/values.yaml` doesn't exist in the registry: CI didn't push, or there's a typo. Revert, or push the image |
   | Self-heal loop | Something outside Git keeps changing a field (an operator, an HPA). Add `ignoreDifferences` for that field in Git |
3. Retry: **Sync** in the UI (staging) once Git is fixed.
4. Verify: Synced/Healthy and the alert resolves.
