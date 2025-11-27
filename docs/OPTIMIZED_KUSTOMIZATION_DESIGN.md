# Optimized Kustomization Design: Shared Checkout Location

## Executive Summary

This document proposes a **better approach** than copying resources to each service folder or using remote Git refs. Instead, we use a **shared checkout location** where each unique Git ref is checked out once, and all services using that ref reference the shared location.

---

## Table of Contents

1. [Problem with Current Approaches](#1-problem-with-current-approaches)
2. [Proposed Solution: Shared Checkout Location](#2-proposed-solution-shared-checkout-location)
3. [How It Works](#3-how-it-works)
4. [Complete Examples](#4-complete-examples)
5. [Benefits](#5-benefits)
6. [Implementation Details](#6-implementation-details)
7. [Alternative: Kustomize Remote Bases with Local Git](#7-alternative-kustomize-remote-bases-with-local-git)

---

## 1. Problem with Current Approaches

### **Approach 1: Copy Resources to Each Service Folder**

**Structure**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml
├── kustomize/  # Copied from refs/tags/config-2025.11.06
├── patches/
└── monitoring/

generated/account-service/int-stable/euw1/
├── kustomization.yaml
├── kustomize/  # Copied from refs/tags/config-2025.11.06 (DUPLICATE!)
├── patches/
└── monitoring/
```

**Problems**:
- ❌ **Duplication**: Same `kustomize/` folder copied for each service
- ❌ **Large Git Repository**: Many copies of same resources
- ❌ **Wasteful**: 100 services × 3 envs × 2 regions = 600 copies of same resources

### **Approach 2: Remote Git Refs**

**Structure**:
```yaml
resources:
  - git::https://github.com/org/platform-next.git//kustomize/cb-base?ref=refs/tags/config-2025.11.06
```

**Problems**:
- ❌ **Git Access Required**: Needs Git access during `kustomize build`
- ❌ **Network Dependency**: Requires network connectivity
- ❌ **Slower Builds**: Network calls during build
- ❌ **Air-Gapped Issues**: Doesn't work in air-gapped environments

---

## 2. Proposed Solution: Shared Checkout Location

### **Concept**

Instead of copying resources to each service folder, we:
1. **Checkout each unique Git ref once** to a shared location
2. **Reference the shared location** from service kustomization.yaml files
3. **Generate only service-specific resources** (patches, monitoring) in service folders

### **Structure**

```
platform-next/
├── _checkouts/                    # Shared checkout location (gitignored)
│   ├── config-2025.11.06/        # Checkout of refs/tags/config-2025.11.06
│   │   └── kustomize/
│   │       ├── cb-base/
│   │       ├── archetype/
│   │       ├── envs/
│   │       ├── regions/
│   │       └── components/
│   ├── config-2025.11.07/        # Checkout of refs/tags/config-2025.11.07
│   │   └── kustomize/
│   └── config-2025.10.28/        # Checkout of refs/tags/config-2025.10.28
│       └── kustomize/
│
└── generated/                     # Service-specific folders
    ├── payment-processor/
    │   └── int-stable/
    │       └── euw1/
    │           ├── kustomization.yaml  # References shared checkout
    │           ├── patches/             # Service-specific
    │           └── monitoring/          # Service-specific
    └── account-service/
        └── int-stable/
            └── euw1/
                ├── kustomization.yaml  # References shared checkout
                ├── patches/            # Service-specific
                └── monitoring/         # Service-specific
```

### **Key Points**

- ✅ **Single Checkout**: Each Git ref checked out once to `_checkouts/<TAG>/`
- ✅ **Shared Reference**: All services using same ref reference same checkout
- ✅ **No Duplication**: Resources stored once, referenced many times
- ✅ **Local Paths**: All references are local (relative or absolute)
- ✅ **No Git Access**: During build, all resources are local

---

## 3. How It Works

### **3.1 Generation Process**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Resolve Channel/Env Pin → Git Ref                  │
├─────────────────────────────────────────────────────────────┤
│ Service: payment-processor                                   │
│ Channel: stable → refs/tags/config-2025.11.06              │
│ CONFIG_REF = refs/tags/config-2025.11.06                    │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Check if Shared Checkout Exists                     │
├─────────────────────────────────────────────────────────────┤
│ Check: _checkouts/config-2025.11.06/ exists?                │
│                                                              │
│ IF exists:                                                   │
│   → Use existing checkout (no need to checkout again)       │
│                                                              │
│ IF not exists:                                               │
│   → Clone repository                                         │
│   → Checkout at refs/tags/config-2025.11.06                │
│   → Copy to _checkouts/config-2025.11.06/                   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Create Service Folder                                │
├─────────────────────────────────────────────────────────────┤
│ Create: generated/payment-processor/int-stable/euw1/        │
│ Create: patches/, monitoring/ directories                   │
│                                                              │
│ NO kustomize/ directory in service folder                   │
│ (Resources are in shared checkout)                          │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Generate Service-Specific Resources                │
├─────────────────────────────────────────────────────────────┤
│ • patches/resources-patch.yaml (from size)                  │
│ • patches/hpa-patch.yaml (from size)                        │
│ • monitoring/*.yaml (from monitoring profile)               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Generate kustomization.yaml                         │
├─────────────────────────────────────────────────────────────┤
│ References shared checkout using relative or absolute paths: │
│                                                              │
│ resources:                                                   │
│   - ../../../../_checkouts/config-2025.11.06/kustomize/cb-base │
│   - ../../../../_checkouts/config-2025.11.06/kustomize/archetype/api │
│   - patches/resources-patch.yaml                            │
│   - monitoring/servicemonitor.yaml                          │
└─────────────────────────────────────────────────────────────┘
```

### **3.2 kustomization.yaml Structure**

```yaml
# generated/payment-processor/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Resources from shared checkout (relative path from service folder)
resources:
  - ../../../../_checkouts/config-2025.11.06/kustomize/cb-base
  - ../../../../_checkouts/config-2025.11.06/kustomize/archetype/api
  - ../../../../_checkouts/config-2025.11.06/kustomize/envs/int-stable
  - ../../../../_checkouts/config-2025.11.06/kustomize/regions/euw1
  # Service-specific resources (local)
  - patches/resources-patch.yaml
  - patches/hpa-patch.yaml
  - monitoring/servicemonitor.yaml
  - monitoring/prometheusrule-recording.yaml
  - monitoring/prometheusrule-alerts.yaml
  - monitoring/dynatrace-config.yaml

# Components from shared checkout
components:
  - ../../../../_checkouts/config-2025.11.06/kustomize/components/ingress
  - ../../../../_checkouts/config-2025.11.06/kustomize/components/hpa
  - ../../../../_checkouts/config-2025.11.06/kustomize/components/pdb

namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1
  cost.costCenter: "COR-B"
  cost.businessUnit: "core-banking"
  cost.owner: "owner@company.com"

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
```

### **3.3 Path Calculation**

**Service Folder**: `generated/payment-processor/int-stable/euw1/`
**Shared Checkout**: `_checkouts/config-2025.11.06/`

**Relative Path**:
```
From: generated/payment-processor/int-stable/euw1/
To:   _checkouts/config-2025.11.06/kustomize/cb-base

Path: ../../../../_checkouts/config-2025.11.06/kustomize/cb-base
      ↑      ↑      ↑
      euw1/  int-stable/  payment-processor/
```

**Or Use Absolute Path** (if supported):
```
/workspace/_checkouts/config-2025.11.06/kustomize/cb-base
```

---

## 4. Complete Examples

### **Example 1: Multiple Services Using Same Git Ref**

**Setup**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06

# services.yaml
services:
  - name: payment-processor
    channel: stable
  - name: account-service
    channel: stable
  - name: user-service
    channel: stable
```

**What Happens**:

**First Service (payment-processor)**:
1. Channel: `stable` → `refs/tags/config-2025.11.06`
2. Check if `_checkouts/config-2025.11.06/` exists → No
3. Clone repository, checkout at `config-2025.11.06`
4. Copy to `_checkouts/config-2025.11.06/`
5. Generate service folder: `generated/payment-processor/int-stable/euw1/`
6. kustomization.yaml references: `../../../../_checkouts/config-2025.11.06/kustomize/...`

**Second Service (account-service)**:
1. Channel: `stable` → `refs/tags/config-2025.11.06`
2. Check if `_checkouts/config-2025.11.06/` exists → **Yes!**
3. **Skip checkout** (use existing)
4. Generate service folder: `generated/account-service/int-stable/euw1/`
5. kustomization.yaml references: `../../../../_checkouts/config-2025.11.06/kustomize/...`

**Result**:
- ✅ **Single checkout**: `_checkouts/config-2025.11.06/` created once
- ✅ **Shared reference**: All services reference same checkout
- ✅ **No duplication**: Resources stored once
- ✅ **Faster generation**: Subsequent services skip checkout

---

### **Example 2: Services Using Different Git Refs**

**Setup**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1

# services.yaml
services:
  - name: payment-processor
    channel: stable  # Uses config-2025.11.06
  - name: test-service
    channel: next    # Uses config-2025.11.07-rc1
```

**What Happens**:

**For payment-processor**:
1. Channel: `stable` → `refs/tags/config-2025.11.06`
2. Checkout to: `_checkouts/config-2025.11.06/`
3. kustomization.yaml references: `../../../../_checkouts/config-2025.11.06/kustomize/...`

**For test-service**:
1. Channel: `next` → `refs/tags/config-2025.11.07-rc1`
2. Checkout to: `_checkouts/config-2025.11.07-rc1/` (different checkout)
3. kustomization.yaml references: `../../../../_checkouts/config-2025.11.07-rc1/kustomize/...`

**Result**:
- ✅ **Multiple checkouts**: One per unique Git ref
- ✅ **No duplication**: Each ref checked out once
- ✅ **Services reference correct checkout**: Based on their channel/env pin

---

### **Example 3: Environment Pins**

**Setup**:
```yaml
# env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28

# services.yaml
services:
  - name: payment-processor
    # channel: (not specified)
    # In prod environment
```

**What Happens**:
1. No channel → Use envPins: `prod` → `refs/tags/config-2025.10.28`
2. Checkout to: `_checkouts/config-2025.10.28/`
3. kustomization.yaml references: `../../../../_checkouts/config-2025.10.28/kustomize/...`

**Result**:
- ✅ Environment pin determines which checkout to use
- ✅ All services in prod reference same checkout
- ✅ Consistent configuration across environment

---

## 5. Benefits

### **5.1 No Duplication**

**Before (Copy to Each Service)**:
```
generated/payment-processor/int-stable/euw1/kustomize/  # 50MB
generated/account-service/int-stable/euw1/kustomize/    # 50MB (duplicate)
generated/user-service/int-stable/euw1/kustomize/       # 50MB (duplicate)
Total: 150MB for 3 services
```

**After (Shared Checkout)**:
```
_checkouts/config-2025.11.06/kustomize/  # 50MB (shared)
generated/payment-processor/int-stable/euw1/  # 5KB (kustomization.yaml + patches)
generated/account-service/int-stable/euw1/    # 5KB
generated/user-service/int-stable/euw1/      # 5KB
Total: 50MB + 15KB for 3 services
```

**Savings**: 100MB for 3 services, scales linearly with more services

### **5.2 Faster Generation**

**Before**: Checkout and copy for each service (even if same ref)
**After**: Checkout once per unique ref, subsequent services skip checkout

**Time Savings**:
- First service: ~10 seconds (checkout + copy)
- Subsequent services (same ref): ~1 second (skip checkout)

### **5.3 Smaller Git Repository**

**Before**: Each service folder contains full `kustomize/` directory
**After**: Only service-specific files in `generated/`, shared checkouts in `_checkouts/` (gitignored)

**Git Repository Size**:
- Before: 100 services × 50MB = 5GB
- After: 100 services × 5KB = 500KB (99.99% reduction)

### **5.4 All Resources Still Local**

- ✅ No Git access needed during `kustomize build`
- ✅ All resources are local paths
- ✅ Works in air-gapped environments
- ✅ Fast builds (no network calls)

---

## 6. Implementation Details

### **6.1 Generator Script Logic**

```bash
#!/usr/bin/env bash
# generate-kz.sh - Optimized with shared checkouts

SERVICE=$1
ENV=$2
REGION=$3

# ... resolve CONFIG_REF (channel/env pin) ...

# Extract tag name from Git ref
# refs/tags/config-2025.11.06 → config-2025.11.06
CHECKOUT_NAME=$(echo "$CONFIG_REF" | sed 's|refs/tags/||' | sed 's|refs/heads/||' | tr '/' '-')
CHECKOUT_DIR="_checkouts/$CHECKOUT_NAME"

# Step 1: Check if shared checkout exists
if [[ ! -d "$CHECKOUT_DIR" ]]; then
  echo "Creating shared checkout: $CHECKOUT_DIR"
  
  # Clone repository
  TEMP_REPO_DIR=$(mktemp -d)
  git clone "$REPO_URL" "$TEMP_REPO_DIR"
  
  # Checkout at CONFIG_REF
  cd "$TEMP_REPO_DIR"
  git checkout "$CONFIG_REF"
  
  # Copy to shared checkout location
  mkdir -p "$CHECKOUT_DIR"
  cp -r kustomize "$CHECKOUT_DIR/"
  
  # Cleanup
  cd -
  rm -rf "$TEMP_REPO_DIR"
  
  echo "✅ Shared checkout created: $CHECKOUT_DIR"
else
  echo "✅ Using existing shared checkout: $CHECKOUT_DIR"
fi

# Step 2: Create service folder (no kustomize/ directory)
OUTPUT_DIR="generated/$SERVICE/$ENV/$REGION"
mkdir -p "$OUTPUT_DIR/patches"
mkdir -p "$OUTPUT_DIR/monitoring"

# Step 3: Generate service-specific resources
# ... (patches, monitoring from profile expansion) ...

# Step 4: Calculate relative path from service folder to shared checkout
# From: generated/payment-processor/int-stable/euw1/
# To:   _checkouts/config-2025.11.06/kustomize/cb-base
RELATIVE_PATH="../../../../$CHECKOUT_DIR/kustomize"

# Step 5: Generate kustomization.yaml
cat > "$OUTPUT_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Resources from shared checkout
resources:
  - ${RELATIVE_PATH}/cb-base
  - ${RELATIVE_PATH}/archetype/${ARCHETYPE}
  - ${RELATIVE_PATH}/envs/${ENV}
  - ${RELATIVE_PATH}/regions/${REGION}
  # Service-specific resources
  - patches/resources-patch.yaml
  - patches/hpa-patch.yaml
  - monitoring/servicemonitor.yaml
  - monitoring/prometheusrule-recording.yaml
  - monitoring/prometheusrule-alerts.yaml
  - monitoring/dynatrace-config.yaml

# Components from shared checkout
components:
$(for COMP in $COMPONENTS; do
  echo "  - ${RELATIVE_PATH}/components/${COMP}"
done)

namespace: ${ENV}-${SERVICE}-${REGION}-stable

commonLabels:
  app: ${SERVICE}
  env: ${ENV}
  region: ${REGION}
  # Cost labels (from profile expansion)
$(echo "$COST_LABELS" | sed 's/^/  /')

images:
  - name: placeholder
    newName: ${IMAGE}
    newTag: PLACEHOLDER_TAG

patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
EOF

echo "✅ Generated service folder at: $OUTPUT_DIR"
echo "   References shared checkout: $CHECKOUT_DIR"
```

### **6.2 .gitignore Configuration**

```gitignore
# Shared checkouts (not committed to Git)
_checkouts/

# Temporary files
tmp/
*.tmp
```

**Why**: Shared checkouts are generated artifacts, not source code. They can be regenerated from Git refs.

### **6.3 CI/CD Pipeline**

```yaml
# .github/workflows/generate-kustomizations.yml
name: Generate Kustomizations

on:
  push:
    branches: [main]
    paths:
      - 'kustomize/catalog/**'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Service Folders
        run: |
          # Detect changed services
          ./scripts/detect-changed-services.sh | while read SERVICE; do
            for ENV in int-stable pre-stable prod; do
              for REGION in euw1 euw2; do
                ./scripts/generate-kz.sh "$SERVICE" "$ENV" "$REGION"
              done
            done
          done
      
      - name: Commit Generated Folders
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add generated/
          # Note: _checkouts/ is gitignored, not committed
          git commit -m "🤖 Generated kustomization.yaml files" || exit 0
          git push
```

**Note**: `_checkouts/` is not committed to Git. It's generated locally in CI/CD and deployment environments.

---

## 7. Alternative: Kustomize Remote Bases with Local Git

### **7.1 Using file:// Protocol**

If Kustomize supports `file://` protocol for remote bases, we can use:

```yaml
# kustomization.yaml
resources:
  - file:///workspace/_checkouts/config-2025.11.06/kustomize/cb-base
  - file:///workspace/_checkouts/config-2025.11.06/kustomize/archetype/api
```

**Benefits**:
- ✅ Explicit file protocol
- ✅ Absolute paths
- ✅ Clear that resources are local

**Limitations**:
- ⚠️ Requires absolute paths (less portable)
- ⚠️ May not be supported by all Kustomize versions

### **7.2 Using Relative Paths (Recommended)**

```yaml
# kustomization.yaml
resources:
  - ../../../../_checkouts/config-2025.11.06/kustomize/cb-base
  - ../../../../_checkouts/config-2025.11.06/kustomize/archetype/api
```

**Benefits**:
- ✅ Works with all Kustomize versions
- ✅ Portable (relative to kustomization.yaml)
- ✅ No special protocol needed

---

## 8. Deployment Considerations

### **8.1 Harness Deployment**

**Option 1: Include Shared Checkouts in Git** (if small enough):
- Commit `_checkouts/` to Git
- Harness fetches everything
- All resources local

**Option 2: Generate Shared Checkouts in Harness**:
- Harness checks out platform-next repo
- Generates shared checkouts during deployment
- Then runs `kustomize build`

**Option 3: Pre-Generate in CI, Include in Artifact**:
- CI generates shared checkouts
- Packages as artifact
- Harness downloads artifact
- All resources local

### **8.2 Recommended Approach**

**For CI/CD Generation**:
- Generate shared checkouts locally
- Commit only `generated/` folders (with references to `_checkouts/`)
- `_checkouts/` is gitignored

**For Deployment**:
- Harness fetches `generated/` folders
- Harness also checks out platform-next repo
- Harness generates `_checkouts/` from Git refs (same logic as CI)
- Then runs `kustomize build` (all resources local)

**Script for Harness**:
```bash
# In Harness deployment step
# 1. Fetch generated service folder
git clone https://github.com/org/platform-next.git
cd platform-next

# 2. Extract required Git refs from kustomization.yaml
REFS=$(grep -o '_checkouts/[^/]*' generated/payment-processor/int-stable/euw1/kustomization.yaml | \
  sed 's|_checkouts/||' | sort -u)

# 3. Generate shared checkouts for required refs
for REF in $REFS; do
  if [[ ! -d "_checkouts/$REF" ]]; then
    git checkout "refs/tags/$REF" || git checkout "refs/heads/$REF"
    mkdir -p "_checkouts/$REF"
    cp -r kustomize "_checkouts/$REF/"
  fi
done

# 4. Build manifests
cd generated/payment-processor/int-stable/euw1
kustomize build . > manifests.yaml
```

---

## 9. Comparison of Approaches

| Aspect | Copy to Each Service | Remote Git Refs | **Shared Checkout** |
|--------|---------------------|-----------------|---------------------|
| **Duplication** | ❌ High (each service) | ✅ None | ✅ **None (shared)** |
| **Git Access During Build** | ✅ Not needed | ❌ Required | ✅ **Not needed** |
| **Git Repository Size** | ❌ Large | ✅ Small | ✅ **Small** |
| **Generation Speed** | ⚠️ Slow (copy each time) | ✅ Fast | ✅ **Fast (checkout once)** |
| **Air-Gapped** | ✅ Works | ❌ Doesn't work | ✅ **Works** |
| **Complexity** | ⚠️ Medium | ⚠️ Medium | ✅ **Low** |

**Winner**: **Shared Checkout** approach provides the best balance.

---

## 10. Summary

### **Recommended Approach: Shared Checkout Location**

**Structure**:
```
_checkouts/                    # Shared (gitignored)
  ├── config-2025.11.06/       # Checkout once, used by many services
  └── config-2025.11.07/       # Different checkout for different ref

generated/                     # Service-specific (committed)
  └── payment-processor/
      └── int-stable/
          └── euw1/
              ├── kustomization.yaml  # References shared checkout
              ├── patches/            # Service-specific
              └── monitoring/         # Service-specific
```

**Key Benefits**:
- ✅ **No Duplication**: Each Git ref checked out once
- ✅ **All Resources Local**: No Git access during build
- ✅ **Small Git Repository**: Only service-specific files committed
- ✅ **Fast Generation**: Checkout once per unique ref
- ✅ **Flexible**: Services can use different refs

**How It Works**:
1. Resolve channel/env pin → Git ref
2. Check if shared checkout exists for that ref
3. If not, checkout and copy to `_checkouts/<TAG>/`
4. Generate service folder with kustomization.yaml
5. kustomization.yaml references shared checkout using relative paths
6. All resources local, no duplication, fast builds

This approach provides the **best of all worlds**: no duplication, local resources, small Git repository, and fast generation.

