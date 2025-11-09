# Scalability Solution - Multi-Team Concurrent Deployments

## Problem Statement

### The Challenge

With a single config management repository:

**Problems**:
1. ❌ **Pipeline Bottleneck**: 100+ developers trying to deploy simultaneously
2. ❌ **Merge Conflicts**: Multiple teams editing `services.yaml` at once
3. ❌ **Deployment Queue**: Waiting for other deployments to finish
4. ❌ **Environment Contention**: Can't deploy to int-stable while someone else is deploying
5. ❌ **Approval Delays**: PRs pile up waiting for platform team review
6. ❌ **Failed Deployments**: One team's bad config blocks everyone
7. ❌ **No Isolation**: Can't test changes without affecting others

### What Doesn't Scale

```
┌──────────────────────────────────────────────────────┐
│ Single Pipeline (BAD)                                │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Developer A adds service → Creates PR → Waits      │
│  Developer B adds service → Creates PR → BLOCKED    │
│  Developer C updates config → Creates PR → BLOCKED  │
│  Developer D deploys to int → Waits for pipeline   │
│                                                      │
│  Pipeline: [════════] Running (30 min)              │
│  Queue: 15 deployments waiting...                   │
└──────────────────────────────────────────────────────┘
```

---

## Solution Architecture

### Multi-Dimensional Approach

We need **4 strategies combined**:

1. **Pipeline Parallelization** - Multiple pipelines running simultaneously
2. **Per-Service Isolation** - Each service deploys independently
3. **GitOps Pattern** - Declarative, self-healing, no manual apply
4. **Automated Approvals** - Reduce human bottlenecks

---

## Strategy 1: Pipeline Parallelization

### Problem

Current: Single pipeline processes all changes sequentially

### Solution: Per-Service Pipelines

**Architecture**:
```
┌───────────────────────────────────────────────────────────┐
│ Multi-Pipeline Architecture                               │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Developer A: account-service                             │
│    → Pipeline 1: [███░░] (5 min) ✓                       │
│                                                           │
│  Developer B: payment-service                             │
│    → Pipeline 2: [██░░░] (5 min) ✓ (parallel!)           │
│                                                           │
│  Developer C: user-service                                │
│    → Pipeline 3: [████░] (5 min) ✓ (parallel!)           │
│                                                           │
│  15 services deploying in parallel!                       │
└───────────────────────────────────────────────────────────┘
```

### Implementation: GitHub Actions Matrix

```yaml
# .github/workflows/deploy.yml
name: Parallel Service Deployment

on:
  push:
    paths:
      - 'kustomize/catalog/services.yaml'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.changed-services.outputs.services }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 2
      
      - name: Detect Changed Services
        id: changed-services
        run: |
          # Compare current with previous commit
          CHANGED=$(./scripts/detect-changed-services.sh)
          echo "services=$CHANGED" >> $GITHUB_OUTPUT
          # Output: ["account-service", "payment-service"]
  
  deploy-service:
    needs: detect-changes
    if: needs.detect-changes.outputs.services != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
      max-parallel: 20  # Deploy up to 20 services concurrently
      fail-fast: false  # Continue even if one fails
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Manifests for ${{ matrix.service }}
        run: |
          ./scripts/generate-kz-v3.sh ${{ matrix.service }} int-stable euw1
      
      - name: Validate Manifests
        run: |
          kustomize build tmp/${{ matrix.service }}/int-stable/euw1 | \
            kubeconform --strict -
      
      - name: Deploy to Int-Stable
        run: |
          kubectl apply -k tmp/${{ matrix.service }}/int-stable/euw1
      
      - name: Wait for Rollout
        run: |
          kubectl rollout status deploy/${{ matrix.service }} \
            -n int-stable-${{ matrix.service }}-euw1 \
            --timeout=5m
      
      - name: Health Check
        run: |
          ./scripts/health-check.sh ${{ matrix.service }} int-stable euw1
```

**Benefits**:
- ✅ **20 services deploy in parallel** (vs 1 at a time)
- ✅ **5 minute per-service deployment** (vs 30+ min sequential)
- ✅ **Independent failures** (one bad deploy doesn't block others)
- ✅ **Automatic retry** on transient failures

---

## Strategy 2: Per-Service Isolation

### Problem

All services share same catalog file → merge conflicts

### Solution: Service-Specific Files

**Before (Single File)**:
```yaml
# kustomize/catalog/services.yaml (everyone edits this)
services:
  - name: account-service
    ...
  - name: payment-service
    ...
  - name: user-service
    ...
  # 100+ services in one file = merge hell
```

**After (Per-Service Files)**:
```
kustomize/catalog/
├── services/
│   ├── account-service.yaml      # Team A owns this
│   ├── payment-service.yaml      # Team B owns this
│   ├── user-service.yaml         # Team C owns this
│   └── ...                        # 100+ files, no conflicts!
│
├── profiles.yaml                  # Shared (rarely changes)
├── sizes.yaml                     # Shared (rarely changes)
└── environments.yaml              # Shared (rarely changes)
```

**Per-Service File**:
```yaml
# kustomize/catalog/services/account-service.yaml
name: account-service
profile: public-api
size: medium
environments: [int, pre, prod]

# Optional overrides
resources:
  overrides:
    prod:
      size: large

# Ownership
owners:
  team: platform-team-a
  slack: "#team-platform-a"
  oncall: pagerduty-team-a
```

### Benefits

✅ **No merge conflicts** - Each team edits their own file
✅ **Clear ownership** - File = service = team
✅ **CODEOWNERS** - Auto-assign reviews
✅ **Parallel PRs** - 10 teams can create PRs simultaneously

### CODEOWNERS File

```
# .github/CODEOWNERS

# Platform team owns profiles and sizes
/kustomize/catalog/profiles.yaml @platform-team
/kustomize/catalog/sizes.yaml @platform-team

# Teams own their services
/kustomize/catalog/services/account-service.yaml @team-platform-a
/kustomize/catalog/services/payment-service.yaml @team-payments
/kustomize/catalog/services/user-service.yaml @team-identity
```

---

## Strategy 3: GitOps Pattern (ArgoCD/Flux)

### Problem

Manual `kubectl apply` → only one person can deploy at a time

### Solution: Declarative GitOps

**GitOps Principles**:
1. Git is the source of truth
2. Changes are pull requests
3. CD system auto-syncs from Git
4. No manual `kubectl apply`

### Architecture: ArgoCD ApplicationSets

```
┌─────────────────────────────────────────────────────────┐
│ GitOps Flow                                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Developer commits to Git                               │
│         ↓                                               │
│  ArgoCD detects change (every 3 min)                    │
│         ↓                                               │
│  ArgoCD syncs to cluster                                │
│         ↓                                               │
│  Multiple services deploy in parallel automatically     │
│                                                         │
│  No manual kubectl apply!                               │
│  No deployment queue!                                   │
└─────────────────────────────────────────────────────────┘
```

### ArgoCD ApplicationSet

```yaml
# argocd/applicationset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: services
spec:
  generators:
    # Generate one Application per service
    - git:
        repoURL: https://github.com/company/platform-next
        revision: main
        files:
          - path: "kustomize/catalog/services/*.yaml"
    
    # Cross-product with environments
    - list:
        elements:
          - env: int-stable
            cluster: https://int-stable.k8s.company.com
          - env: pre-stable
            cluster: https://pre-stable.k8s.company.com
          - env: prod
            cluster: https://prod.k8s.company.com
  
  template:
    metadata:
      name: '{{name}}-{{env}}'
      labels:
        service: '{{name}}'
        env: '{{env}}'
    spec:
      project: default
      
      source:
        repoURL: https://github.com/company/platform-next
        targetRevision: main
        path: 'generated/{{name}}/{{env}}/euw1'  # Generated by CI
      
      destination:
        server: '{{cluster}}'
        namespace: '{{env}}-{{name}}-euw1'
      
      syncPolicy:
        automated:
          prune: true      # Delete removed resources
          selfHeal: true   # Auto-fix drift
        syncOptions:
          - CreateNamespace=true
        
        # Sync waves for ordering
        syncWave:
          - namespace: 0
          - rbac: 1
          - deployment: 2
          - service: 3
```

### How It Works

**1. Developer Creates PR**
```bash
# Edit service file
vim kustomize/catalog/services/my-service.yaml

# Commit and push
git add kustomize/catalog/services/my-service.yaml
git commit -m "Add my-service"
git push origin add-my-service
```

**2. CI Pipeline Generates Manifests**
```yaml
# .github/workflows/generate-manifests.yml
on:
  pull_request:
    paths:
      - 'kustomize/catalog/services/*.yaml'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - name: Generate Manifests for Changed Services
        run: |
          for service in $(./scripts/detect-changed-services.sh); do
            for env in int-stable pre-stable prod; do
              for region in euw1 euw2; do
                ./scripts/generate-kz-v3.sh $service $env $region
                
                # Output to generated/ directory
                mkdir -p generated/$service/$env/$region
                kustomize build tmp/$service/$env/$region > \
                  generated/$service/$env/$region/manifests.yaml
              done
            done
          done
      
      - name: Commit Generated Manifests
        run: |
          git add generated/
          git commit -m "Generated manifests for PR #${{ github.event.number }}"
          git push
```

**3. ArgoCD Auto-Syncs**
```
PR Merged → main branch updated
           ↓
ArgoCD detects change (3 min polling)
           ↓
ArgoCD syncs all affected services in parallel
           ↓
Done! (no manual intervention)
```

### Benefits

✅ **No deployment queue** - Git commits deploy automatically
✅ **Parallel deployments** - ArgoCD syncs multiple apps concurrently
✅ **Self-healing** - ArgoCD reverts manual changes
✅ **Rollback** - Git revert = instant rollback
✅ **Audit trail** - Git history = deployment history
✅ **Preview environments** - Feature branches = ephemeral envs

---

## Strategy 4: Automated Approvals

### Problem

Platform team becomes bottleneck reviewing every PR

### Solution: Tiered Approval System

#### Level 1: Auto-Approve (No Human Review)

**Criteria**:
- ✅ All validation passes
- ✅ Only int-stable environment
- ✅ Service size ≤ medium
- ✅ No new components enabled
- ✅ Team owns service (CODEOWNERS)

**Implementation**:
```yaml
# .github/workflows/auto-approve.yml
name: Auto-Approve Low-Risk Changes

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  auto-approve:
    runs-on: ubuntu-latest
    steps:
      - name: Check Approval Criteria
        id: check
        run: |
          # Check if only int-stable changed
          INT_ONLY=$(./scripts/check-int-only.sh)
          
          # Check if validation passed
          VALID=$(./scripts/check-validation-passed.sh)
          
          # Check service size
          SIZE=$(./scripts/get-service-size.sh)
          
          if [[ "$INT_ONLY" == "true" && "$VALID" == "true" && "$SIZE" =~ ^(small|medium)$ ]]; then
            echo "auto_approve=true" >> $GITHUB_OUTPUT
          fi
      
      - name: Auto-Approve and Merge
        if: steps.check.outputs.auto_approve == 'true'
        uses: hmarr/auto-approve-action@v3
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Auto-Merge
        if: steps.check.outputs.auto_approve == 'true'
        run: gh pr merge --auto --squash
```

#### Level 2: Automated Review (Fast Lane)

**Criteria**:
- Changes to pre-stable environment
- Service size = large
- Standard components only

**Action**: Auto-assign + auto-approve after 1 hour if no objections

#### Level 3: Manual Review (Slow Lane)

**Criteria**:
- Production environment
- Service size = xlarge
- New components
- Infrastructure changes

**Action**: Require platform team approval

### Approval Matrix

| Change | Environment | Size | Auto-Approve | Review Time |
|--------|-------------|------|--------------|-------------|
| New service | int-stable | small/medium | ✅ Yes | Instant |
| Update config | int-stable | any | ✅ Yes | Instant |
| New service | pre-stable | small/medium | ⚠️ Auto (1hr) | 1 hour |
| Update config | pre-stable | large | ⚠️ Auto (1hr) | 1 hour |
| Any change | prod | small/medium | ❌ Manual | 1-4 hours |
| Any change | prod | large/xlarge | ❌ Manual | 2-8 hours |
| New component | any | any | ❌ Manual | Platform team |
| Archetype change | any | any | ❌ Manual | Platform team |

---

## Strategy 5: Branch-Based Deployments

### Problem

Multiple teams want to deploy to int-stable simultaneously

### Solution: Dynamic Environments

**Concept**: Each feature branch gets its own environment

```
main branch           → prod + pre-stable
staging branch        → int-stable (shared)
feature/add-service-a → int-stable-feature-add-service-a (isolated)
feature/add-service-b → int-stable-feature-add-service-b (isolated)
```

### Implementation

```yaml
# .github/workflows/feature-branch-deploy.yml
name: Feature Branch Deployment

on:
  push:
    branches:
      - 'feature/**'

jobs:
  deploy-feature-env:
    runs-on: ubuntu-latest
    steps:
      - name: Generate Environment Name
        id: env
        run: |
          BRANCH=${GITHUB_REF#refs/heads/}
          ENV_NAME=$(echo "$BRANCH" | sed 's/[^a-z0-9-]/-/g' | cut -c1-63)
          echo "env_name=$ENV_NAME" >> $GITHUB_OUTPUT
      
      - name: Deploy to Feature Environment
        run: |
          NAMESPACE="${{ steps.env.outputs.env_name }}"
          
          # Generate manifests
          ./scripts/generate-kz-v3.sh my-service int-stable euw1
          
          # Override namespace
          cd tmp/my-service/int-stable/euw1
          kustomize edit set namespace $NAMESPACE
          
          # Deploy
          kustomize build . | kubectl apply -f -
      
      - name: Comment PR with URL
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🚀 Deployed to feature environment!\n\nURL: https://${{ steps.env.outputs.env_name }}.int-stable.company.com`
            })
```

### Benefits

✅ **No contention** - Each team has isolated environment
✅ **Test safely** - Changes don't affect others
✅ **Preview** - Test before merging to main
✅ **Clean up** - Auto-delete on PR close

---

## Strategy 6: Smart Change Detection

### Problem

Pipeline runs for ALL services even if only one changed

### Solution: Detect Changed Services

```bash
#!/bin/bash
# scripts/detect-changed-services.sh

set -euo pipefail

# Get changed files between commits
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD)

CHANGED_SERVICES=()

# Check if service files changed
for file in $CHANGED_FILES; do
  if [[ $file == kustomize/catalog/services/*.yaml ]]; then
    SERVICE=$(basename "$file" .yaml)
    CHANGED_SERVICES+=("$SERVICE")
  fi
done

# Check if archetypes/components changed (affects all services using them)
if echo "$CHANGED_FILES" | grep -q "kustomize/archetype/api"; then
  # Get all services using 'api' archetype
  API_SERVICES=$(yq eval '.services[] | select(.profile == "public-api" or .archetype == "api") | .name' \
    kustomize/catalog/services/*.yaml)
  CHANGED_SERVICES+=($API_SERVICES)
fi

# Remove duplicates
CHANGED_SERVICES=($(echo "${CHANGED_SERVICES[@]}" | tr ' ' '\n' | sort -u))

# Output as JSON array
echo -n "["
printf '"%s",' "${CHANGED_SERVICES[@]}" | sed 's/,$//'
echo "]"
```

**Usage**:
```bash
# Only deploys changed services
SERVICES=$(./scripts/detect-changed-services.sh)
# Output: ["account-service", "payment-service"]

# Pipeline only runs for these 2 services (not all 100)
```

---

## Complete Architecture: All Strategies Combined

```
┌──────────────────────────────────────────────────────────────┐
│ Developer Workflow                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. Developer edits service file (no conflicts!)             │
│    vim kustomize/catalog/services/my-service.yaml           │
│                                                              │
│ 2. Create feature branch (isolated testing!)                │
│    git checkout -b feature/add-my-service                   │
│    git push                                                  │
│                                                              │
│ 3. CI auto-deploys to feature environment                   │
│    → https://feature-add-my-service.int.company.com         │
│    → Test in isolation (no contention!)                     │
│                                                              │
│ 4. Create PR                                                 │
│    → Auto-assigned via CODEOWNERS                           │
│    → Validation runs in parallel                            │
│    → Manifests generated                                    │
│                                                              │
│ 5. Approval (tiered)                                        │
│    Int-stable: Auto-approved ✅ (instant)                   │
│    Pre-stable: Auto-approved ⚠️ (1 hour)                    │
│    Prod: Manual review ❌ (2-8 hours)                       │
│                                                              │
│ 6. Merge to main                                            │
│    → ArgoCD detects change (3 min)                          │
│    → Syncs service (parallel with others!)                  │
│    → Done! (no manual kubectl)                              │
│                                                              │
│ Total time: 5-10 minutes (vs 30+ min before)                │
│ Bottlenecks: ZERO (parallel everything!)                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1-2)

1. **Split Catalog into Per-Service Files**
   ```bash
   ./scripts/split-catalog.sh
   # Creates services/account-service.yaml, services/payment-service.yaml, etc.
   ```

2. **Add CODEOWNERS**
   ```
   /kustomize/catalog/services/account-service.yaml @team-a
   /kustomize/catalog/services/payment-service.yaml @team-b
   ```

3. **Enable Parallel Pipelines**
   ```yaml
   strategy:
     matrix:
       service: ${{ fromJson(needs.detect-changes.outputs.services) }}
     max-parallel: 20
   ```

**Result**: ✅ No more merge conflicts, 10x faster pipelines

### Phase 2: GitOps (Week 3-4)

1. **Deploy ArgoCD**
   ```bash
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   ```

2. **Create ApplicationSet**
   ```bash
   kubectl apply -f argocd/applicationset.yaml
   ```

3. **Migrate 10 Pilot Services**
   - Manual deploys → ArgoCD auto-sync

**Result**: ✅ Automatic deployments, no manual kubectl

### Phase 3: Auto-Approvals (Week 5-6)

1. **Implement Approval Tiers**
   - Auto-approve int-stable
   - 1-hour delay for pre-stable
   - Manual for prod

2. **Add Validation Gates**
   - Schema validation
   - Policy checks (OPA)
   - Security scans

**Result**: ✅ 80% of PRs auto-approved

### Phase 4: Feature Environments (Week 7-8)

1. **Feature Branch Deployments**
   - Auto-create namespace per branch
   - Deploy to isolated environment
   - Auto-cleanup on PR close

2. **Preview URLs**
   - Comment on PR with preview link
   - E2E tests in preview env

**Result**: ✅ Zero contention, safe testing

---

## Metrics & KPIs

### Before (Single Pipeline)

| Metric | Value | Problem |
|--------|-------|---------|
| **Deployment Time** | 30+ min | Too slow |
| **Queue Wait** | 1-2 hours | Bottleneck |
| **Merge Conflicts** | 5-10/day | Frustrating |
| **Failed Deployments** | 20% | Blocks others |
| **PR Review Time** | 4-24 hours | Platform team overwhelmed |
| **Concurrent Deployments** | 1 | Serial only |

### After (Parallel + GitOps)

| Metric | Value | Improvement |
|--------|-------|-------------|
| **Deployment Time** | 5-10 min | ✅ 3-6x faster |
| **Queue Wait** | 0 min | ✅ No queue! |
| **Merge Conflicts** | 0/day | ✅ Per-service files |
| **Failed Deployments** | 5% | ✅ 4x better |
| **PR Review Time** | 0-1 hour | ✅ Auto-approve |
| **Concurrent Deployments** | 20+ | ✅ 20x parallelism |

---

## FAQ

### Q: What if two services share the same archetype and it breaks?

**A**: Change detection catches this:
```bash
# If archetype/api changes, detect all services using it
./scripts/detect-affected-services.sh archetype/api
# Output: [all-api-services]

# Deploy all affected services in parallel
```

### Q: What if someone deploys bad config to prod?

**A**: Multiple safeguards:
1. Validation in CI (schema, OPA policies)
2. Manual approval required for prod
3. GitOps rollback (git revert)
4. ArgoCD health checks (auto-rollback on failure)

### Q: How to prevent resource exhaustion (100 deployments at once)?

**A**: Rate limiting in pipeline:
```yaml
strategy:
  max-parallel: 20  # Max 20 concurrent deployments
  
concurrency:
  group: deploy-${{ matrix.service }}
  cancel-in-progress: false  # Don't cancel ongoing deploys
```

### Q: What about database migrations?

**A**: Separate pipeline for pre-deploy jobs:
```yaml
jobs:
  pre-deploy:
    steps:
      - name: Run Migrations
        run: kubectl apply -k kustomize/jobs/migration
      - name: Wait for Completion
        run: kubectl wait --for=condition=complete job/migration
  
  deploy:
    needs: pre-deploy  # Wait for migrations
    steps: ...
```

---

## Summary

### Solution Components

| Problem | Solution | Tool/Pattern |
|---------|----------|--------------|
| **Pipeline bottleneck** | Parallel pipelines | GitHub Actions matrix |
| **Merge conflicts** | Per-service files | Filesystem organization |
| **Deployment queue** | GitOps auto-sync | ArgoCD ApplicationSets |
| **Manual approvals** | Tiered auto-approve | GitHub Actions + policies |
| **Environment contention** | Feature environments | Dynamic namespaces |
| **Change detection** | Smart diff detection | Git + yq parsing |

### Key Principles

1. ✅ **Parallelism** - Everything runs in parallel
2. ✅ **Isolation** - Per-service files, per-branch environments
3. ✅ **Automation** - GitOps, auto-approve, auto-sync
4. ✅ **Safety** - Validation, approvals, rollback
5. ✅ **Scalability** - 100+ services, 100+ developers

### Expected Outcomes

**Before**: 1 deployment at a time, 30+ min, merge conflicts daily
**After**: 20+ parallel deployments, 5-10 min, zero conflicts

**Developer happiness**: ⭐⭐⭐⭐⭐ (no more waiting!)
