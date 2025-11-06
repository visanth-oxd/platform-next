#!/usr/bin/env bash
set -euo pipefail

# Resolve latest image tag from GAR
# Usage: gar.sh resolve --image <IMAGE> --strategy <STRATEGY> [--branch <BRANCH>]

IMAGE=""
STRATEGY=""
BRANCH="main"

while [[ $# -gt 0 ]]; do
  case $1 in
    --image)
      IMAGE="$2"
      shift 2
      ;;
    --strategy)
      STRATEGY="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    resolve)
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$IMAGE" || -z "$STRATEGY" ]]; then
  echo "Usage: $0 resolve --image <IMAGE> --strategy <STRATEGY> [--branch <BRANCH>]"
  exit 1
fi

case "$STRATEGY" in
  gar-latest)
    # Get latest tag by timestamp
    gcloud artifacts docker images list "$IMAGE" \
      --include-tags \
      --format="value(tags)" \
      --sort-by="~create_time" \
      --limit=1 | head -n1 | cut -d',' -f1
    ;;
  gar-latest-by-branch)
    # Get latest tag that contains branch name
    gcloud artifacts docker images list "$IMAGE" \
      --include-tags \
      --format="json" | \
      jq -r ".[] | select(.tags[]? | contains(\"$BRANCH\")) | .tags[] | select(contains(\"$BRANCH\"))" | \
      sort -Vr | head -n1
    ;;
  git-sha)
    # Get tag matching git SHA pattern
    gcloud artifacts docker images list "$IMAGE" \
      --include-tags \
      --format="value(tags)" | \
      grep -E '^[a-f0-9]{7,40}$' | \
      sort -Vr | head -n1
    ;;
  pinned)
    # Return the pinned tag (would need to be passed as --tag)
    echo "pinned-tag"
    ;;
  *)
    echo "Unknown strategy: $STRATEGY"
    exit 1
    ;;
esac

