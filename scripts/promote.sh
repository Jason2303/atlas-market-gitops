#!/usr/bin/env bash
# Manual promotion (same result as the "Promote to production" workflow, for when Actions
# is unavailable): copies the staging image tag into production on a branch and pushes it.
# You then open + merge the PR on GitHub, and a release manager Syncs atlas-production in ArgoCD.
#   ./scripts/promote.sh            # promote whatever staging runs now
#   ./scripts/promote.sh sha-1a2b3c4
set -euo pipefail
cd "$(dirname "$0")/.."
git checkout main && git pull --ff-only
TAG="${1:-$(yq '.image.tag' envs/staging/values.yaml)}"
[[ "$TAG" =~ ^(sha-[0-9a-f]{7}|v[0-9]+\.[0-9]+\.[0-9]+)$ ]] || { echo "refusing non-immutable tag '$TAG'"; exit 1; }
BRANCH="promote/production-$TAG"
git checkout -b "$BRANCH"
yq -i ".image.tag = \"$TAG\"" envs/production/values.yaml
git commit -am "promote(production): atlas-market $TAG"
git push -u origin "$BRANCH"
git checkout main
echo
echo "Next: open the PR for $BRANCH on GitHub, get it approved and merge it."
echo "Then ArgoCD shows atlas-production OutOfSync -> log in as release-bob -> App Diff -> Sync."
