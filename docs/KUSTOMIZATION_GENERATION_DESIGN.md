# Kustomization Generation Design: Service Folder Structure with Local Resources

## Executive Summary

This document describes the **updated design** where we generate **service-specific folder structures** containing:
1. A `kustomization.yaml` file that references local resources (both from checked-out Git ref and profile expansion)
2. Local resource files from the checked-out Git ref (base, archetype, env, region, components)
3. Local resource files generated from profile expansion (patches, monitoring resources, etc.)

The channel/env pin determines which Git ref to checkout, then all resources are copied locally and referenced as local paths in kustomization.yaml.

---

## Table of Contents

1. [Design Change Overview](#1-design-change-overview)
2. [New Architecture](#2-new-architecture)
3. [Kustomization File Structure](#3-kustomization-file-structure)
4. [Channel and Environment Pin Resolution](#4-channel-and-environment-pin-resolution)
5. [Git Ref Embedding](#5-git-ref-embedding)
6. [Complete Examples](#6-complete-examples)
7. [Deployment Flow](#7-deployment-flow)
8. [Benefits of This Approach](#8-benefits-of-this-approach)
9. [Migration Considerations](#9-migration-considerations)

---

## 1. Design Change Overview

### **Old Design (Pre-Built Manifests)**

```
Service Added to Catalog
    ↓
CI/CD Generates Final Manifests (YAML)
    ↓
Manifests Stored in generated/ directory
    ↓
Harness Fetches Manifests and Applies
```

**Problems**:
- Manifests are "baked" at generation time
- Channel/env pin changes require regeneration
- Large generated files in Git
- Less flexible

### **New Design (Service Folder Structure with Local Checkout)**

```
Service Added to Catalog
    ↓
CI/CD Generates Service Folder Structure:
  1. Resolve channel/env pin → Git ref
  2. Checkout platform-next repo at that Git ref
  3. Copy needed resources (base, archetype, env, region, components) to service folder
  4. Generate service-specific resources (patches, monitoring) from profile expansion
  5. Create kustomization.yaml with local path references
    ↓
Service Folder Stored in generated/<SERVICE>/<ENV>/<REGION>/
  - kustomization.yaml (references local paths)
  - kustomize/ (copied from checked-out Git ref)
  - patches/ (generated from size)
  - monitoring/ (generated from profiles)
    ↓
Harness Fetches Entire Service Folder
    ↓
Harness Runs: kustomize build (all resources are local)
    ↓
Harness Applies Generated Manifests
```

**Benefits**:
- All resources are local (no Git access needed during build)
- Channel/env pin determines which version to checkout
- Service-specific resources generated from profile expansion
- Clear separation: shared config (from Git ref) vs service-specific (from profiles)
- GitOps-friendly structure
- No remote Git dependencies during deployment

---

## 2. New Architecture

### **Component Flow**

```
┌─────────────────────────────────────────────────────────────┐
│ Service Catalog (services.yaml)                             │
│ • Service definition                                         │
│ • channel: stable (optional)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Channel/Env Pin Resolution                                  │
│ • Resolve channel → Git ref                                 │
│ • Or use env pin → Git ref                                 │
│ • Result: CONFIG_REF (e.g., refs/tags/config-2025.11.06)  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Repository Checkout                                         │
│ • Clone/checkout platform-next repo                         │
│ • Checkout at CONFIG_REF (refs/tags/config-2025.11.06)     │
│ • Copy needed resources to service folder                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Kustomization Generator (generate-kz.sh)                   │
│ • Copy base, archetype, env, region, components locally     │
│ • Generate service-specific resources from profiles         │
│ • Create kustomization.yaml with local path references      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Generated Service Folder                                    │
│ • kustomization.yaml (references local paths)               │
│ • kustomize/ (copied from checked-out ref)                 │
│ • patches/ (generated from size)                            │
│ • monitoring/ (generated from profiles)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Deployment Tool (Harness)                                   │
│ • Fetches entire service folder from Git                    │
│ • Runs: kustomize build (all resources are local)           │
│ • Generates final manifests                                 │
│ • Applies to cluster                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Service Folder Structure

### **Directory Layout**

```
generated/
  payment-processor/
    int-stable/
      euw1/
        kustomization.yaml          # Main kustomization file (local path references)
        kustomize/                  # Copied from checked-out Git ref
          cb-base/                  # Base configuration
          archetype/
            api/                    # API archetype
          envs/
            int-stable/             # Environment overlay
          regions/
            euw1/                   # Region overlay
          components/
            ingress/                # Ingress component
            hpa/                    # HPA component
            pdb/                    # PDB component
        patches/                    # Generated from size/profile expansion
          resources-patch.yaml     # CPU/memory patches from size
          hpa-patch.yaml            # HPA min/max replicas from size
        monitoring/                 # Generated from monitoring profile
          servicemonitor.yaml       # Prometheus ServiceMonitor
          prometheusrule-recording.yaml  # Recording rules
          prometheusrule-alerts.yaml     # Alert rules
          dynatrace-config.yaml     # Dynatrace ConfigMap
        cost/                       # Any cost-specific resources
          (if needed)
```

### **Kustomization File Structure**

The `kustomization.yaml` references **all resources as local paths**:
1. **Local resources from checked-out Git ref** (base, archetype, env, region, components) - copied from repo at channel/env pin ref
2. **Local resources from profile expansion** (patches, monitoring, cost) - generated from profiles

**Example Structure**:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Local resources (copied from checked-out Git ref - channels/env pins determine which ref)
resources:
  - kustomize/cb-base
  - kustomize/archetype/api
  - kustomize/envs/int-stable
  - kustomize/regions/euw1
  # Local resources (generated from profile expansion)
  - patches/resources-patch.yaml
  - patches/hpa-patch.yaml
  - monitoring/servicemonitor.yaml
  - monitoring/prometheusrule-recording.yaml
  - monitoring/prometheusrule-alerts.yaml
  - monitoring/dynatrace-config.yaml

# Local components (copied from checked-out Git ref)
components:
  - kustomize/components/ingress
  - kustomize/components/hpa
  - kustomize/components/pdb

# Service-specific configuration
namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1
  # Cost labels (from profile expansion)
  cost.costCenter: "COR-B"
  cost.businessUnit: "core-banking"
  cost.owner: "owner@company.com"

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

# Patches (reference local patch files)
patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
```

**Key Point**: All resources are local paths. The channel/env pin determines which Git ref to checkout and copy, but the kustomization.yaml itself only references local paths.

---

## 4. Generation Process

### **Step-by-Step Generation**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Resolve Channel/Env Pin                             │
├─────────────────────────────────────────────────────────────┤
│ • Service specifies channel OR uses env pin                  │
│ • Resolve to Git ref: CONFIG_REF                            │
│ • Example: refs/tags/config-2025.11.06                      │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Checkout Repository at Git Ref                      │
├─────────────────────────────────────────────────────────────┤
│ • Clone platform-next repository (if not already cloned)    │
│ • Checkout at CONFIG_REF (refs/tags/config-2025.11.06)     │
│ • Copy needed resources to service folder:                  │
│   - kustomize/cb-base                                       │
│   - kustomize/archetype/<ARCHETYPE>                         │
│   - kustomize/envs/<ENV>                                    │
│   - kustomize/regions/<REGION>                              │
│   - kustomize/components/<COMPONENT> (for each component)   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Profile Expansion                                   │
├─────────────────────────────────────────────────────────────┤
│ • Expand cost profile → Generate cost labels                │
│ • Expand monitoring profile → Generate monitoring resources │
│ • Calculate budgets, thresholds, etc.                       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Create Service Folder Structure                     │
├─────────────────────────────────────────────────────────────┤
│ • Create: generated/<SERVICE>/<ENV>/<REGION>/               │
│ • Create subdirectories: patches/, monitoring/, cost/       │
│ • kustomize/ already copied from checked-out ref            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Generate Local Resources from Profiles             │
├─────────────────────────────────────────────────────────────┤
│ • patches/resources-patch.yaml (from size)                  │
│ • patches/hpa-patch.yaml (from size)                        │
│ • monitoring/servicemonitor.yaml (from monitoring profile) │
│ • monitoring/prometheusrule-*.yaml (from monitoring profile) │
│ • monitoring/dynatrace-config.yaml (from monitoring profile)│
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Generate kustomization.yaml                         │
├─────────────────────────────────────────────────────────────┤
│ • Reference local paths (kustomize/...)                     │
│ • Reference local resources (patches, monitoring)           │
│ • Include cost labels in commonLabels                       │
│ • Include service-specific config                           │
└─────────────────────────────────────────────────────────────┘
```

### **What Gets Copied from Checked-Out Git Ref**

**From Repository at CONFIG_REF**:
- `kustomize/cb-base/` - Base configuration
- `kustomize/archetype/<ARCHETYPE>/` - Workload archetype
- `kustomize/envs/<ENV>/` - Environment overlay
- `kustomize/regions/<REGION>/` - Region overlay
- `kustomize/components/<COMPONENT>/` - Each enabled component

**Note**: These are copied from the repository at the Git ref determined by channel/env pin.

### **What Gets Generated Locally from Profile Expansion**

**From Size (sizes.yaml)**:
- `patches/resources-patch.yaml` - CPU/memory requests/limits
- `patches/hpa-patch.yaml` - Min/max replicas, CPU target

**From Monitoring Profile**:
- `monitoring/servicemonitor.yaml` - Prometheus ServiceMonitor
- `monitoring/prometheusrule-recording.yaml` - Recording rules
- `monitoring/prometheusrule-alerts.yaml` - Alert rules
- `monitoring/dynatrace-config.yaml` - Dynatrace ConfigMap

**From Cost Profile**:
- Cost labels (injected into `commonLabels` in kustomization.yaml)
- Any cost-specific resources (if needed)

---

## 5. Channel and Environment Pin Resolution

### **Resolution Logic**

The generator script resolves channels/env pins to Git refs and embeds them in the kustomization.yaml.

**Resolution Algorithm**:
```bash
# 1. Check if service specifies channel
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)

if [[ -n "$CHANNEL" ]]; then
  # 2a. Service has channel → lookup in channels.yaml
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
else
  # 2b. Check region pins
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" "$CATALOG_DIR/region-pins.yaml")
  
  if [[ -n "$REGION_PIN" ]]; then
    CONFIG_REF="$REGION_PIN"
  else
    # 2c. Use environment pin
    # First check defaultChannel
    DEFAULT_CHANNEL=$(yq eval ".defaultChannel.$ENV // \"\"" "$CATALOG_DIR/env-pins.yaml")
    
    if [[ -n "$DEFAULT_CHANNEL" ]]; then
      # Resolve defaultChannel to Git ref
      CONFIG_REF=$(yq eval ".channels.$DEFAULT_CHANNEL" "$CATALOG_DIR/channels.yaml")
    else
      # Use envPins directly
      CONFIG_REF=$(yq eval ".envPins.$ENV" "$CATALOG_DIR/env-pins.yaml")
    fi
  fi
fi

# CONFIG_REF now contains the Git ref to use (e.g., refs/tags/config-2025.11.06)
```

### **Git Repository URL**

The Git repository URL is determined from:
- Environment variable: `PLATFORM_NEXT_REPO_URL`
- Or default: `https://github.com/org/platform-next.git`

---

## 6. Git Ref Embedding

### **How Git Refs Are Embedded**

All resource and component references in the kustomization.yaml use the resolved `CONFIG_REF`.

**Template**:
```yaml
resources:
  - git::${REPO_URL}//kustomize/cb-base?ref=${CONFIG_REF}
  - git::${REPO_URL}//kustomize/archetype/${ARCHETYPE}?ref=${CONFIG_REF}
  - git::${REPO_URL}//kustomize/envs/${ENV}?ref=${CONFIG_REF}
  - git::${REPO_URL}//kustomize/regions/${REGION}?ref=${CONFIG_REF}

components:
  - git::${REPO_URL}//kustomize/components/${COMPONENT}?ref=${CONFIG_REF}
```

**Example with Values**:
```yaml
resources:
  - git::https://github.com/org/platform-next.git//kustomize/cb-base?ref=refs/tags/config-2025.11.06
  - git::https://github.com/org/platform-next.git//kustomize/archetype/api?ref=refs/tags/config-2025.11.06
  - git::https://github.com/org/platform-next.git//kustomize/envs/int-stable?ref=refs/tags/config-2025.11.06
  - git::https://github.com/org/platform-next.git//kustomize/regions/euw1?ref=refs/tags/config-2025.11.06
```

---

## 7. Complete Examples

### **Example 1: Service with Channel**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    channel: stable  # ← Explicit channel
    regions: [euw1]
    enabledIn: [int-stable]
```

**Channel Mapping**:
```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Resolution**:
- Service channel: `stable`
- Lookup: `channels.stable` → `refs/tags/config-2025.11.06`
- CONFIG_REF: `refs/tags/config-2025.11.06`

**Generated Service Folder Structure**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml
├── patches/
│   ├── resources-patch.yaml
│   └── hpa-patch.yaml
└── monitoring/
    ├── servicemonitor.yaml
    ├── prometheusrule-recording.yaml
    ├── prometheusrule-alerts.yaml
    └── dynatrace-config.yaml
```

**kustomization.yaml**:
```yaml
# generated/payment-processor/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Local resources (copied from checked-out Git ref - channel/env pin determined which ref)
resources:
  - kustomize/cb-base
  - kustomize/archetype/api
  - kustomize/envs/int-stable
  - kustomize/regions/euw1
  # Local resources (generated from profile expansion)
  - patches/resources-patch.yaml
  - patches/hpa-patch.yaml
  - monitoring/servicemonitor.yaml
  - monitoring/prometheusrule-recording.yaml
  - monitoring/prometheusrule-alerts.yaml
  - monitoring/dynatrace-config.yaml

# Local components (copied from checked-out Git ref)
components:
  - kustomize/components/ingress
  - kustomize/components/hpa
  - kustomize/components/pdb

namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1
  # Cost labels (from profile expansion)
  cost.costCenter: "COR-B"
  cost.businessUnit: "core-banking"
  cost.owner: "owner@company.com"

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

# Patches (reference local patch files)
patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
```

**patches/resources-patch.yaml** (generated from size):
```yaml
# generated/payment-processor/int-stable/euw1/patches/resources-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
```

**patches/hpa-patch.yaml** (generated from size):
```yaml
# generated/payment-processor/int-stable/euw1/patches/hpa-patch.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**monitoring/dynatrace-config.yaml** (generated from monitoring profile):
```yaml
# generated/payment-processor/int-stable/euw1/monitoring/dynatrace-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dynatrace-app-config
  labels:
    app: payment-processor
    monitoring.profile: domain-api
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "int-stable",
        "team": "core-banking",
        "costCenter": "COR-B"
      },
      "monitoring": {
        "technologies": ["java", "http", "databases"],
        "requestNaming": "{RequestPath} [{RequestMethod}]"
      },
      "alertRules": [
        {
          "name": "ErrorRateAnomaly",
          "enabled": true,
          "condition": "Anomaly(ErrorRate)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
        }
      ],
      "customMetrics": []
    }
```

**Key Points**:
- ✅ All resources are local paths (no remote Git refs in kustomization.yaml)
- ✅ Channel/env pin determines which Git ref to checkout and copy
- ✅ `kustomize/` folder contains resources from checked-out Git ref
- ✅ Local resources generated from profile expansion (patches, monitoring)
- ✅ Clear separation: shared config (from Git ref) vs service-specific (from profiles)
- ✅ Ready for `kustomize build` at deployment time (all resources local)

---

### **Example 2: Service without Channel (Uses Environment Pin)**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: account-service
    archetype: api
    profile: public-api
    size: medium
    # channel: (not specified)  # ← No channel
    regions: [euw1]
    enabledIn: [prod]
```

**Environment Pins**:
```yaml
# kustomize/catalog/env-pins.yaml
envPins:
  prod: refs/tags/config-2025.10.28  # ← Direct Git ref

defaultChannel:
  prod: stable  # ← But envPins takes priority
```

**Resolution**:
- Service has no channel
- No region pin for `euw1+prod`
- Use `envPins.prod` → `refs/tags/config-2025.10.28`
- CONFIG_REF: `refs/tags/config-2025.10.28`

**Generated kustomization.yaml**:
```yaml
# generated/account-service/prod/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - git::https://github.com/org/platform-next.git//kustomize/cb-base?ref=refs/tags/config-2025.10.28
  - git::https://github.com/org/platform-next.git//kustomize/archetype/api?ref=refs/tags/config-2025.10.28
  - git::https://github.com/org/platform-next.git//kustomize/envs/prod?ref=refs/tags/config-2025.10.28
  - git::https://github.com/org/platform-next.git//kustomize/regions/euw1?ref=refs/tags/config-2025.10.28

components:
  - git::https://github.com/org/platform-next.git//kustomize/components/ingress?ref=refs/tags/config-2025.10.28
  - git::https://github.com/org/platform-next.git//kustomize/components/hpa?ref=refs/tags/config-2025.10.28
  - git::https://github.com/org/platform-next.git//kustomize/components/pdb?ref=refs/tags/config-2025.10.28

namespace: prod-account-service-euw1-stable

commonLabels:
  app: account-service
  env: prod
  region: euw1

images:
  - name: placeholder
    newName: gcr.io/project/account-service
    newTag: PLACEHOLDER_TAG

patches:
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "250m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "512Mi"
  
  - target:
      kind: HorizontalPodAutoscaler
      name: app
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 2
      - op: replace
        path: /spec/maxReplicas
        value: 6
```

**Key Points**:
- ✅ Uses environment pin: `refs/tags/config-2025.10.28` (older, stable version)
- ✅ Repository checked out at that ref, resources copied locally
- ✅ All resources are local paths (no remote Git refs)
- ✅ Production pinned to proven version

---

### **Example 3: Service with defaultChannel**

**Service Definition**:
```yaml
# kustomize/catalog/services.yaml
services:
  - name: test-service
    archetype: api
    profile: public-api
    size: small
    # channel: (not specified)
    regions: [euw1]
    enabledIn: [int-stable]
```

**Environment Pins**:
```yaml
# kustomize/catalog/env-pins.yaml
envPins:
  int-stable: refs/tags/config-2025.11.06

defaultChannel:
  int-stable: next  # ← Default channel for int-stable
```

**Channel Mapping**:
```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Resolution**:
- Service has no channel
- No region pin
- Check `defaultChannel.int-stable` → `next`
- Lookup `channels.next` → `refs/tags/config-2025.11.07-rc1`
- CONFIG_REF: `refs/tags/config-2025.11.07-rc1`

**Generated kustomization.yaml**:
```yaml
# generated/test-service/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - git::https://github.com/org/platform-next.git//kustomize/cb-base?ref=refs/tags/config-2025.11.07-rc1
  - git::https://github.com/org/platform-next.git//kustomize/archetype/api?ref=refs/tags/config-2025.11.07-rc1
  - git::https://github.com/org/platform-next.git//kustomize/envs/int-stable?ref=refs/tags/config-2025.11.07-rc1
  - git::https://github.com/org/platform-next.git//kustomize/regions/euw1?ref=refs/tags/config-2025.11.07-rc1

components:
  - git::https://github.com/org/platform-next.git//kustomize/components/ingress?ref=refs/tags/config-2025.11.07-rc1
  - git::https://github.com/org/platform-next.git//kustomize/components/hpa?ref=refs/tags/config-2025.11.07-rc1
  - git::https://github.com/org/platform-next.git//kustomize/components/pdb?ref=refs/tags/config-2025.11.07-rc1

namespace: int-stable-test-service-euw1-stable

commonLabels:
  app: test-service
  env: int-stable
  region: euw1

images:
  - name: placeholder
    newName: gcr.io/project/test-service
    newTag: PLACEHOLDER_TAG

patches:
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "100m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "256Mi"
```

**Key Points**:
- ✅ Uses `defaultChannel` → resolves to `next` channel → `refs/tags/config-2025.11.07-rc1`
- ✅ Repository checked out at that ref, resources copied locally
- ✅ Test service gets latest RC version (for testing)
- ✅ Two-step resolution: defaultChannel → channel → Git ref → checkout

---

### **Example 4: Channel Promotion Scenario**

**Initial State**:
```yaml
# channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.07-rc1
```

**Service Folder (before promotion)**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml
├── kustomize/  # Copied from refs/tags/config-2025.11.06
├── patches/
└── monitoring/
```

**After Channel Promotion**:
```yaml
# channels.yaml (updated)
channels:
  stable: refs/tags/config-2025.11.07  # ← Promoted
  next: refs/tags/config-2025.11.08-rc1
```

**What Happens**:
- ✅ **Option 1: No regeneration** - Service folder still has `kustomize/` from old ref (stability)
- ✅ **Option 2: Regenerate** - Checkout new ref, copy new `kustomize/` folder, update service folder
- ✅ **Choice**: Keep old ref (stability) or regenerate (get new config)

**If Regenerated**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml  # Same local path references
├── kustomize/  # Now copied from refs/tags/config-2025.11.07 (new version)
├── patches/    # Same (from size)
└── monitoring/ # Same (from profiles)
```

**Note**: The kustomization.yaml file itself doesn't change (still references `kustomize/cb-base`, etc.), but the `kustomize/` folder contents change when regenerated with new ref.

**Key Insight**: 
- **Option 1**: Don't regenerate → Service stays on old ref (explicit pinning)
- **Option 2**: Regenerate → Service gets new ref (follows channel)

---

## 8. Deployment Flow

### **Complete Deployment Process**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Service Added to Catalog                            │
├─────────────────────────────────────────────────────────────┤
│ • Developer adds service to services.yaml                   │
│ • Specifies: archetype, profile, size, channel (optional)   │
│ • Commits to Git                                            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: CI/CD Detects Change                                │
├─────────────────────────────────────────────────────────────┤
│ • CI pipeline triggered                                     │
│ • Detects new/updated service                               │
│ • Runs: generate-kz.sh <SERVICE> <ENV> <REGION>            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Generate kustomization.yaml                        │
├─────────────────────────────────────────────────────────────┤
│ • Resolves channel/env pin → Git ref                        │
│ • Generates kustomization.yaml with Git refs embedded      │
│ • Commits to: generated/<SERVICE>/<ENV>/<REGION>/           │
│   kustomization.yaml                                        │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Deployment Triggered                                │
├─────────────────────────────────────────────────────────────┤
│ • Developer triggers deployment (Harness pipeline)          │
│ • Provides: image tag, environment, region                  │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Harness Fetches Service Folder                      │
├─────────────────────────────────────────────────────────────┤
│ • Fetches entire folder from Git:                           │
│   generated/<SERVICE>/<ENV>/<REGION>/                       │
│ • Includes:                                                 │
│   - kustomization.yaml                                      │
│   - patches/ (resources-patch.yaml, hpa-patch.yaml)        │
│   - monitoring/ (servicemonitor.yaml, prometheusrule-*.yaml) │
│ • Replaces PLACEHOLDER_TAG with actual image tag            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Harness Runs kustomize build                        │
├─────────────────────────────────────────────────────────────┤
│ • Command: kustomize build generated/.../<SERVICE>/<ENV>/<REGION>/ │
│ • Kustomize resolves all Git refs (remote resources)       │
│ • Fetches remote resources from Git at specified refs       │
│ • Includes local resources (patches, monitoring)            │
│ • Applies patches, labels, images                           │
│ • Generates final Kubernetes manifests                      │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Harness Applies Manifests                           │
├─────────────────────────────────────────────────────────────┤
│ • Applies generated manifests to cluster                    │
│ • Service deployed with correct configuration               │
└─────────────────────────────────────────────────────────────┘
```

### **Harness Pipeline Configuration**

```yaml
# Harness Service Definition
service:
  serviceDefinition:
    type: Kubernetes
    spec:
      manifests:
        - manifest:
            identifier: kustomization
            type: K8sManifest
            spec:
              store:
                type: Github
                spec:
                  connectorRef: github_platform_next
                  gitFetchType: Branch
                  branch: main
                  paths:
                    # Fetch entire service folder
                    - generated/{{SERVICE_NAME}}/{{ENV}}/{{REGION}}/
              
              # Kustomize build step
              skipResourceVersioning: false
              enableDeclarativeRollback: true
              
              # Kustomize-specific settings
              pluginPath: kustomize
              commandFlags:
                - commandType: Build
                  flag: --load-restrictor=LoadRestrictionsNone
```

**Note**: Harness needs to support Kustomize build. If not available, use a custom step:

```yaml
# Custom Kustomize Build Step
- step:
    type: ShellScript
    name: Build Kustomize
    spec:
      shell: Bash
      onDelegate: true
      source:
        type: Inline
        script: |
          # Fetch service folder (already contains all resources)
          git clone https://github.com/org/platform-next.git
          cd platform-next
          
          # Replace image tag placeholder in kustomization.yaml
          sed -i "s/PLACEHOLDER_TAG/${IMAGE_TAG}/g" \
            generated/${SERVICE_NAME}/${ENV}/${REGION}/kustomization.yaml
          
          # Build manifests (all resources are local, no Git access needed)
          cd generated/${SERVICE_NAME}/${ENV}/${REGION}
          kustomize build . > manifests.yaml
          
          # Output manifests for next step
          echo "manifests.yaml" > /harness/manifests-path
          
          # Output manifests for next step
          echo "manifests.yaml" > /harness/manifests-path
      
      environmentVariables:
        - name: SERVICE_NAME
          value: payment-processor
        - name: ENV
          value: int-stable
        - name: REGION
          value: euw1
        - name: IMAGE_TAG
          value: <+pipeline.variables.imageTag>
```

---

## 9. Benefits of This Approach

### **1. GitOps-Friendly**

**Before**: Pre-built manifests in Git
- Large files
- Hard to review changes
- Less transparent

**After**: Kustomization files with Git refs
- Small files (just references)
- Easy to review (see which refs are used)
- More transparent (Git refs visible)

### **2. Flexibility**

**Before**: Manifests "baked" at generation time
- Channel changes require regeneration
- Less flexible

**After**: Git refs resolved at deployment time
- Can change channel/env pin without regeneration
- More flexible (can regenerate or keep old refs)

### **3. Version Control**

**Before**: Generated manifests show final state
- Hard to see which config version was used
- Less traceable

**After**: Git refs embedded in kustomization.yaml
- Clear which config version is used
- Easy to trace (Git ref → specific commit/tag)
- Better audit trail

### **4. Rollback**

**Before**: Need to regenerate with old config
- Time-consuming
- Risk of errors

**After**: Can regenerate with old ref or keep existing
- Quick rollback (regenerate with old ref)
- Or keep existing kustomization.yaml (explicit pinning)

### **5. Smaller Git Repository**

**Before**: Large manifest files
- `generated/payment-processor/int-stable/euw1/manifests.yaml` (500+ lines)

**After**: Small kustomization files
- `generated/payment-processor/int-stable/euw1/kustomization.yaml` (50-100 lines)
- Much smaller, easier to manage

---

## 10. Migration Considerations

### **What Changes**

1. **Generator Script**: Update to generate kustomization.yaml with Git refs
2. **CI/CD Pipeline**: Generate kustomization.yaml instead of manifests
3. **Deployment Tool**: Run `kustomize build` at deployment time
4. **Repository Structure**: Store kustomization.yaml instead of manifests.yaml

### **Updated Generator Script**

```bash
#!/usr/bin/env bash
# generate-kz.sh - Generate service folder structure with local resources

SERVICE=$1
ENV=$2
REGION=$3

# ... existing setup (load service, profile, size) ...

# Resolve config ref (channel/env pin)
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)

if [[ -n "$CHANNEL" ]]; then
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
else
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" "$CATALOG_DIR/region-pins.yaml")
  
  if [[ -n "$REGION_PIN" ]]; then
    CONFIG_REF="$REGION_PIN"
  else
    DEFAULT_CHANNEL=$(yq eval ".defaultChannel.$ENV // \"\"" "$CATALOG_DIR/env-pins.yaml")
    
    if [[ -n "$DEFAULT_CHANNEL" ]]; then
      CONFIG_REF=$(yq eval ".channels.$DEFAULT_CHANNEL" "$CATALOG_DIR/channels.yaml")
    else
      CONFIG_REF=$(yq eval ".envPins.$ENV" "$CATALOG_DIR/env-pins.yaml")
    fi
  fi
fi

# Get repository URL
REPO_URL="${PLATFORM_NEXT_REPO_URL:-https://github.com/org/platform-next.git}"

# Step 1: Checkout repository at CONFIG_REF
TEMP_REPO_DIR=$(mktemp -d)
git clone "$REPO_URL" "$TEMP_REPO_DIR"
cd "$TEMP_REPO_DIR"
git checkout "$CONFIG_REF"

# Create service folder structure
OUTPUT_DIR="generated/$SERVICE/$ENV/$REGION"
mkdir -p "$OUTPUT_DIR/patches"
mkdir -p "$OUTPUT_DIR/monitoring"
mkdir -p "$OUTPUT_DIR/cost"
mkdir -p "$OUTPUT_DIR/kustomize"

# Step 2: Copy needed resources from checked-out ref
cp -r "$TEMP_REPO_DIR/kustomize/cb-base" "$OUTPUT_DIR/kustomize/"
cp -r "$TEMP_REPO_DIR/kustomize/archetype/$ARCHETYPE" "$OUTPUT_DIR/kustomize/archetype/"
cp -r "$TEMP_REPO_DIR/kustomize/envs/$ENV" "$OUTPUT_DIR/kustomize/envs/"
cp -r "$TEMP_REPO_DIR/kustomize/regions/$REGION" "$OUTPUT_DIR/kustomize/regions/"

# Copy components
mkdir -p "$OUTPUT_DIR/kustomize/components"
for COMP in $COMPONENTS; do
  cp -r "$TEMP_REPO_DIR/kustomize/components/$COMP" "$OUTPUT_DIR/kustomize/components/"
done

# Cleanup temp repo
cd -
rm -rf "$TEMP_REPO_DIR"

# Step 1: Expand profiles (cost and monitoring)
python3 "$SCRIPT_DIR/expand-profiles.py" \
  --service "$SERVICE" \
  --environment "$ENV" \
  --output /tmp/expanded-${SERVICE}-${ENV}.json

# Step 2: Generate local resources from profile expansion

# 2a. Generate patches from size
cat > "$OUTPUT_DIR/patches/resources-patch.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "${CPU}"
              memory: "${MEMORY}"
            limits:
              cpu: "${CPU_LIMIT}"
              memory: "${MEMORY_LIMIT}"
EOF

cat > "$OUTPUT_DIR/patches/hpa-patch.yaml" <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app
spec:
  minReplicas: ${MIN_REPLICAS}
  maxReplicas: ${MAX_REPLICAS}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: ${CPU_TARGET}
EOF

# 2b. Generate monitoring resources from monitoring profile
if [[ -n "$MONITORING_PROFILE" ]]; then
  python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type servicemonitor
  
  python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type prometheusrule-recording
  
  python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type prometheusrule-alerts
  
  python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type dynatrace-config
fi

# Step 3: Extract cost labels from expanded config
COST_LABELS=$(jq -r '.cost.labels | to_entries | map("\(.key): \(.value)") | join("\n  ")' \
  /tmp/expanded-${SERVICE}-${ENV}.json)

# Step 4: Generate kustomization.yaml
cat > "$OUTPUT_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Local resources (copied from checked-out Git ref - channel/env pin: ${CONFIG_REF})
resources:
  - kustomize/cb-base
  - kustomize/archetype/${ARCHETYPE}
  - kustomize/envs/${ENV}
  - kustomize/regions/${REGION}
  # Local resources (generated from profile expansion)
  - patches/resources-patch.yaml
  - patches/hpa-patch.yaml
$(if [[ -n "$MONITORING_PROFILE" ]]; then
  echo "  - monitoring/servicemonitor.yaml"
  echo "  - monitoring/prometheusrule-recording.yaml"
  echo "  - monitoring/prometheusrule-alerts.yaml"
  echo "  - monitoring/dynatrace-config.yaml"
fi)

# Local components (copied from checked-out Git ref)
components:
$(for COMP in $COMPONENTS; do
  echo "  - kustomize/components/${COMP}"
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

# Patches (reference local patch files)
patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
EOF

echo "Generated service folder structure at: $OUTPUT_DIR"
echo "Config ref: $CONFIG_REF"
echo "Resources copied from: $CONFIG_REF"
echo ""
echo "Folder structure:"
echo "  - kustomize/ (from Git ref: $CONFIG_REF)"
echo "  - patches/ (generated from size)"
echo "  - monitoring/ (generated from profiles)"
```

### **Updated CI/CD Pipeline**

```yaml
# .github/workflows/generate-kustomizations.yml
name: Generate Kustomizations

on:
  push:
    branches: [main]
    paths:
      - 'kustomize/catalog/services.yaml'
      - 'kustomize/catalog/channels.yaml'
      - 'kustomize/catalog/env-pins.yaml'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Kustomizations
        run: |
          # Detect changed services
          ./scripts/detect-changed-services.sh | while read SERVICE; do
            for ENV in int-stable pre-stable prod; do
              for REGION in euw1 euw2; do
                ./scripts/generate-kz.sh "$SERVICE" "$ENV" "$REGION"
              done
            done
          done
      
      - name: Commit Generated Kustomizations
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add generated/
          git commit -m "🤖 Generated kustomization.yaml files" || exit 0
          git push
```

---

## Summary

### **New Design: Service Folder Structure with Local Checkout**

**Structure**:
```
generated/<SERVICE>/<ENV>/<REGION>/
├── kustomization.yaml          # References local paths only
├── kustomize/                  # Copied from checked-out Git ref
│   ├── cb-base/
│   ├── archetype/
│   ├── envs/
│   ├── regions/
│   └── components/
├── patches/                    # Generated from size
│   ├── resources-patch.yaml
│   └── hpa-patch.yaml
└── monitoring/                 # Generated from monitoring profile
    ├── servicemonitor.yaml
    ├── prometheusrule-recording.yaml
    ├── prometheusrule-alerts.yaml
    └── dynatrace-config.yaml
```

**Key Principles**:
1. **Channel/Env Pin Resolution**:
   - Resolve channel/env pin → Git ref (e.g., `refs/tags/config-2025.11.06`)
   - Checkout platform-next repository at that Git ref
   - Copy needed resources to service folder

2. **Local Resources from Checked-Out Ref**:
   - Base, archetype, environment, region overlays
   - Components (ingress, hpa, pdb, etc.)
   - Copied from repository at Git ref determined by channel/env pin
   - Referenced using local paths: `kustomize/cb-base`, `kustomize/archetype/api`, etc.

3. **Local Resources from Profile Expansion**:
   - Patches (resources, HPA) - from size
   - Monitoring resources - from monitoring profile
   - Cost labels - injected into commonLabels
   - Referenced using relative paths: `patches/resources-patch.yaml`

4. **Generation Process**:
   - Resolve channel/env pin → Git ref
   - Checkout repository at that Git ref
   - Copy resources to service folder
   - Expand profiles → Generate local resources
   - Create kustomization.yaml with local path references

5. **Deployment Process**:
   - Fetch entire service folder from Git (already contains all resources)
   - Run `kustomize build` (all resources are local, no Git access needed)
   - Apply generated manifests

**Key Benefits**:
- ✅ **All Resources Local**: No Git access needed during `kustomize build`
- ✅ **Channel/Env Pin Control**: Determines which Git ref to checkout and copy
- ✅ **Clear Separation**: Shared config (from Git ref) vs service-specific (from profiles)
- ✅ **Profile Expansion**: Resources generated from profiles stored locally
- ✅ **GitOps-Friendly**: Folder structure easy to review and manage
- ✅ **Flexible**: Can update channels/env pins and regenerate to get new ref
- ✅ **Self-Contained**: Service folder has everything needed for deployment

**How Channels/Env Pins Work**:
- Channels/env pins resolve to Git refs at generation time
- Repository checked out at that Git ref
- Resources copied to service folder (`kustomize/` directory)
- kustomization.yaml references local paths only
- All resources are local (no remote Git refs in kustomization.yaml)

This approach provides: **shared configuration via Git ref checkout** (channels/env pins determine which version) and **service-specific resources via profile expansion** (local files), with **all resources local** for deployment.

