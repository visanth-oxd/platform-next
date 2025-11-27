# Complete Design: Service Folder Structure with Local Checkout

## Executive Summary

This document provides a **complete, detailed design** of the updated Kustomize-based configuration management system. It details all areas where changes have been made and explains how the entire system works end-to-end with the new approach of generating service folder structures with local resource checkout.

---

## Table of Contents

1. [What Changed?](#1-what-changed)
2. [Complete System Architecture](#2-complete-system-architecture)
3. [Detailed Workflow](#3-detailed-workflow)
4. [Changed Areas in Detail](#4-changed-areas-in-detail)
5. [How Channels/Env Pins Work Now](#5-how-channelsenv-pins-work-now)
6. [Complete Example: End-to-End](#6-complete-example-end-to-end)
7. [Generation Process Deep Dive](#7-generation-process-deep-dive)
8. [Deployment Process Deep Dive](#8-deployment-process-deep-dive)
9. [File Structure Details](#9-file-structure-details)
10. [Benefits and Trade-offs](#10-benefits-and-trade-offs)

---

## 1. What Changed?

### **1.1 Original Design (Pre-Built Manifests)**

**Approach**:
- Generate final Kubernetes manifests (YAML files)
- Store in `generated/<SERVICE>/<ENV>/<REGION>/manifests.yaml`
- Harness fetches and applies manifests directly

**Problems**:
- Large generated files in Git
- Manifests "baked" at generation time
- Channel/env pin changes require regeneration
- Less flexible

### **1.2 New Design (Service Folder Structure)**

**Approach**:
- Generate service folder structure with `kustomization.yaml`
- Checkout repository at Git ref (from channel/env pin)
- Copy resources locally to service folder
- Generate service-specific resources from profile expansion
- Store in `generated/<SERVICE>/<ENV>/<REGION>/` with folder structure
- Harness fetches folder, runs `kustomize build`, applies manifests

**Benefits**:
- Smaller files in Git
- All resources local (no Git access needed during build)
- Channel/env pin determines which version to checkout
- More flexible and GitOps-friendly

---

## 2. Complete System Architecture

### **2.1 High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Service Catalog                                    │
├─────────────────────────────────────────────────────────────┤
│ • services.yaml (service definitions)                       │
│ • profiles.yaml (behavior profiles)                         │
│ • sizes.yaml (resource sizing)                              │
│ • channels.yaml (channel → Git ref mapping)                 │
│ • env-pins.yaml (environment → Git ref pinning)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: CI/CD Pipeline (Generation Phase)                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Detect service changes                                   │
│ 2. For each service/environment/region:                      │
│    a. Resolve channel/env pin → Git ref                     │
│    b. Checkout repository at Git ref                         │
│    c. Copy resources to service folder                     │
│    d. Expand profiles → Generate local resources            │
│    e. Create kustomization.yaml                             │
│ 3. Commit to generated/ directory                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Generated Service Folders                         │
├─────────────────────────────────────────────────────────────┤
│ generated/<SERVICE>/<ENV>/<REGION>/                         │
│ ├── kustomization.yaml (local path references)              │
│ ├── kustomize/ (copied from Git ref)                       │
│ ├── patches/ (generated from size)                          │
│ └── monitoring/ (generated from profiles)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Deployment Tool (Harness)                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Fetch service folder from Git                            │
│ 2. Replace image tag placeholder                            │
│ 3. Run: kustomize build (all resources local)               │
│ 4. Apply generated manifests to cluster                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Workflow

### **3.1 Complete Flow: Service Addition to Deployment**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Service Added to Catalog                           │
├─────────────────────────────────────────────────────────────┤
│ Developer adds service to services.yaml:                     │
│                                                              │
│ services:                                                    │
│   - name: payment-processor                                  │
│     archetype: api                                           │
│     profile: public-api                                      │
│     size: large                                              │
│     channel: stable  # Optional                              │
│     costProfile: standard-api-cost                           │
│     monitoringProfile: domain-api                           │
│     regions: [euw1]                                          │
│     enabledIn: [int-stable]                                  │
│                                                              │
│ Commits to Git                                               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: CI/CD Pipeline Triggered                            │
├─────────────────────────────────────────────────────────────┤
│ GitHub Actions detects change in services.yaml               │
│ Runs: generate-kz.sh for each service/environment/region    │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Channel/Env Pin Resolution                          │
├─────────────────────────────────────────────────────────────┤
│ Resolution Logic:                                            │
│                                                              │
│ 1. Check service.channel:                                    │
│    - If exists → Lookup in channels.yaml                    │
│    - Example: stable → refs/tags/config-2025.11.06          │
│                                                              │
│ 2. If no channel → Check region pins:                       │
│    - regionPins.euw1.int-stable → Git ref                   │
│                                                              │
│ 3. If no region pin → Check env pins:                       │
│    - Check defaultChannel.int-stable → channel → Git ref    │
│    - Or use envPins.int-stable → Git ref                    │
│                                                              │
│ Result: CONFIG_REF = refs/tags/config-2025.11.06            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Repository Checkout                                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Clone platform-next repository (if not already)         │
│ 2. Checkout at CONFIG_REF:                                  │
│    git checkout refs/tags/config-2025.11.06                 │
│ 3. Repository now at specific version                       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Copy Resources to Service Folder                    │
├─────────────────────────────────────────────────────────────┤
│ Create: generated/payment-processor/int-stable/euw1/         │
│                                                              │
│ Copy from checked-out repo:                                  │
│ • kustomize/cb-base → kustomize/cb-base/                    │
│ • kustomize/archetype/api → kustomize/archetype/api/        │
│ • kustomize/envs/int-stable → kustomize/envs/int-stable/    │
│ • kustomize/regions/euw1 → kustomize/regions/euw1/          │
│ • kustomize/components/ingress → kustomize/components/ingress/ │
│ • kustomize/components/hpa → kustomize/components/hpa/      │
│ • kustomize/components/pdb → kustomize/components/pdb/       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Profile Expansion                                    │
├─────────────────────────────────────────────────────────────┤
│ Expand cost profile:                                         │
│ • Calculate budgets: base × size-multiplier                 │
│ • Substitute variables: {service}, {costOwner}              │
│ • Apply overrides                                           │
│ • Generate cost labels                                      │
│                                                              │
│ Expand monitoring profile:                                   │
│ • Calculate thresholds: base × size-multiplier              │
│ • Substitute variables: {SERVICE}, {TEAM}                   │
│ • Apply environment overrides                               │
│ • Generate monitoring resources                             │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Generate Local Resources                            │
├─────────────────────────────────────────────────────────────┤
│ From Size (sizes.yaml):                                      │
│ • patches/resources-patch.yaml (CPU/memory)                 │
│ • patches/hpa-patch.yaml (min/max replicas)                 │
│                                                              │
│ From Monitoring Profile:                                     │
│ • monitoring/servicemonitor.yaml                            │
│ • monitoring/prometheusrule-recording.yaml                   │
│ • monitoring/prometheusrule-alerts.yaml                      │
│ • monitoring/dynatrace-config.yaml                           │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Generate kustomization.yaml                         │
├─────────────────────────────────────────────────────────────┤
│ Create kustomization.yaml with:                              │
│ • Local resource references (kustomize/...)                  │
│ • Local component references (kustomize/components/...)     │
│ • Local patch references (patches/...)                      │
│ • Local monitoring references (monitoring/...)              │
│ • Cost labels in commonLabels                               │
│ • Service-specific config (namespace, images, etc.)         │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 9: Commit to Git                                       │
├─────────────────────────────────────────────────────────────┤
│ Commit entire service folder structure to:                   │
│ generated/payment-processor/int-stable/euw1/                │
│                                                              │
│ Includes:                                                    │
│ • kustomization.yaml                                        │
│ • kustomize/ (entire directory tree)                        │
│ • patches/ (YAML files)                                     │
│ • monitoring/ (YAML files)                                  │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 10: Deployment Triggered                                │
├─────────────────────────────────────────────────────────────┤
│ Developer triggers Harness pipeline with:                    │
│ • Service: payment-processor                                 │
│ • Environment: int-stable                                   │
│ • Region: euw1                                               │
│ • Image tag: v1.2.3                                         │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 11: Harness Fetches Service Folder                      │
├─────────────────────────────────────────────────────────────┤
│ Fetches from Git:                                            │
│ generated/payment-processor/int-stable/euw1/                │
│                                                              │
│ Entire folder structure:                                     │
│ • kustomization.yaml                                        │
│ • kustomize/ directory                                       │
│ • patches/ directory                                         │
│ • monitoring/ directory                                      │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 12: Replace Image Tag                                  │
├─────────────────────────────────────────────────────────────┤
│ Replace PLACEHOLDER_TAG with actual image tag:              │
│ sed -i "s/PLACEHOLDER_TAG/v1.2.3/g" kustomization.yaml     │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 13: Run kustomize build                                 │
├─────────────────────────────────────────────────────────────┤
│ Command: kustomize build .                                   │
│                                                              │
│ Process:                                                     │
│ 1. Reads kustomization.yaml                                 │
│ 2. Loads all local resources:                                │
│    - kustomize/cb-base (from checked-out ref)               │
│    - kustomize/archetype/api (from checked-out ref)         │
│    - kustomize/envs/int-stable (from checked-out ref)       │
│    - kustomize/regions/euw1 (from checked-out ref)          │
│    - kustomize/components/* (from checked-out ref)          │
│    - patches/* (generated from size)                        │
│    - monitoring/* (generated from profiles)                 │
│ 3. Applies patches, labels, images                          │
│ 4. Generates final Kubernetes manifests                     │
│                                                              │
│ Result: Complete Kubernetes manifests (YAML)                 │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 14: Apply to Cluster                                   │
├─────────────────────────────────────────────────────────────┤
│ kubectl apply -f manifests.yaml                              │
│                                                              │
│ Resources created:                                           │
│ • Namespace                                                  │
│ • Deployment (with resources from size)                      │
│ • Service                                                    │
│ • Ingress                                                    │
│ • HPA (with min/max from size)                              │
│ • PDB                                                        │
│ • ServiceMonitor (from monitoring profile)                  │
│ • PrometheusRule (from monitoring profile)                  │
│ • Dynatrace ConfigMap (from monitoring profile)             │
│ • All with cost labels (from cost profile)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Changed Areas in Detail

### **4.1 Area 1: Generation Output**

**Before**:
```
generated/payment-processor/int-stable/euw1/
└── manifests.yaml  (500+ lines, final Kubernetes resources)
```

**After**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml  (50-100 lines, references local paths)
├── kustomize/  (copied from checked-out Git ref)
│   ├── cb-base/
│   ├── archetype/api/
│   ├── envs/int-stable/
│   ├── regions/euw1/
│   └── components/
│       ├── ingress/
│       ├── hpa/
│       └── pdb/
├── patches/  (generated from size)
│   ├── resources-patch.yaml
│   └── hpa-patch.yaml
└── monitoring/  (generated from monitoring profile)
    ├── servicemonitor.yaml
    ├── prometheusrule-recording.yaml
    ├── prometheusrule-alerts.yaml
    └── dynatrace-config.yaml
```

**Change**: Instead of single manifest file, now we have a folder structure with kustomization.yaml and all resources.

---

### **4.2 Area 2: Channel/Env Pin Usage**

**Before**:
- Channels/env pins were used to determine Git refs
- Git refs were embedded in remote resource references
- Example: `git::https://...//kustomize/archetype/api?ref=refs/tags/config-2025.11.06`

**After**:
- Channels/env pins still determine Git refs
- Repository is checked out at that Git ref
- Resources are copied locally
- kustomization.yaml references local paths only
- Example: `kustomize/archetype/api` (local path)

**Change**: Git refs are used to checkout and copy resources, not embedded in kustomization.yaml.

---

### **4.3 Area 3: Resource References**

**Before**:
```yaml
resources:
  - git::https://github.com/org/platform-next.git//kustomize/cb-base?ref=refs/tags/config-2025.11.06
  - git::https://github.com/org/platform-next.git//kustomize/archetype/api?ref=refs/tags/config-2025.11.06
```

**After**:
```yaml
resources:
  - kustomize/cb-base
  - kustomize/archetype/api
  - patches/resources-patch.yaml
  - monitoring/servicemonitor.yaml
```

**Change**: All references are local paths. No remote Git URLs.

---

### **4.4 Area 4: Profile Expansion Output**

**Before**:
- Profile expansion generated values
- Values injected into kustomization.yaml
- Monitoring resources might be inline or separate

**After**:
- Profile expansion generates actual resource files
- Files stored in `patches/` and `monitoring/` directories
- kustomization.yaml references these files as resources

**Change**: Profile expansion now generates actual YAML files, not just values.

---

### **4.5 Area 5: Deployment Process**

**Before**:
```
Harness → Fetch manifests.yaml → Apply directly
```

**After**:
```
Harness → Fetch service folder → Replace image tag → kustomize build → Apply
```

**Change**: Deployment now includes a `kustomize build` step.

---

### **4.6 Area 6: CI/CD Pipeline**

**Before**:
```yaml
- name: Generate Manifests
  run: |
    ./scripts/generate-kz.sh payment-processor int-stable euw1
    kustomize build tmp/... > generated/.../manifests.yaml
```

**After**:
```yaml
- name: Generate Service Folders
  run: |
    ./scripts/generate-kz.sh payment-processor int-stable euw1
    # Generates folder structure (no kustomize build needed)
    # kustomize build happens at deployment time
```

**Change**: CI/CD generates folder structure, not final manifests.

---

## 5. How Channels/Env Pins Work Now

### **5.1 Resolution Process**

```
┌─────────────────────────────────────────────────────────────┐
│ Input: Service Definition                                   │
├─────────────────────────────────────────────────────────────┤
│ services:                                                    │
│   - name: payment-processor                                  │
│     channel: stable  # Optional                              │
│     # OR no channel specified                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Resolution Logic                                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Check service.channel                                     │
│    IF channel exists:                                        │
│      → Lookup channels.yaml                                  │
│      → channels.stable → refs/tags/config-2025.11.06        │
│      → CONFIG_REF = refs/tags/config-2025.11.06             │
│                                                              │
│    IF no channel:                                            │
│      → Check regionPins.$REGION.$ENV                         │
│      IF region pin exists:                                   │
│        → CONFIG_REF = region pin value                       │
│      ELSE:                                                   │
│        → Check defaultChannel.$ENV                           │
│        IF defaultChannel exists:                             │
│          → Lookup channels.yaml for defaultChannel          │
│          → CONFIG_REF = channel Git ref                      │
│        ELSE:                                                 │
│          → Use envPins.$ENV                                  │
│          → CONFIG_REF = env pin value                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Result: CONFIG_REF                                          │
├─────────────────────────────────────────────────────────────┤
│ Example: refs/tags/config-2025.11.06                        │
│                                                              │
│ This Git ref determines which version of resources to use    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Repository Checkout                                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Clone platform-next repository                          │
│ 2. Checkout at CONFIG_REF:                                  │
│    git checkout refs/tags/config-2025.11.06                │
│ 3. Repository now contains resources from that version      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Copy Resources                                               │
├─────────────────────────────────────────────────────────────┤
│ Copy from checked-out repository to service folder:          │
│ • kustomize/cb-base → service folder                        │
│ • kustomize/archetype/api → service folder                  │
│ • kustomize/envs/int-stable → service folder                │
│ • kustomize/regions/euw1 → service folder                   │
│ • kustomize/components/* → service folder                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ kustomization.yaml References                                │
├─────────────────────────────────────────────────────────────┤
│ All references are local paths:                             │
│ • kustomize/cb-base (local)                                 │
│ • kustomize/archetype/api (local)                           │
│ • patches/resources-patch.yaml (local)                      │
│ • monitoring/servicemonitor.yaml (local)                    │
└─────────────────────────────────────────────────────────────┘
```

### **5.2 Channel Promotion Example**

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
├── kustomization.yaml  (references kustomize/cb-base, etc.)
├── kustomize/  # Copied from refs/tags/config-2025.11.06
│   ├── cb-base/
│   ├── archetype/api/
│   └── ...
├── patches/
└── monitoring/
```

**After Channel Promotion**:
```yaml
# channels.yaml (updated)
channels:
  stable: refs/tags/config-2025.11.07  # Promoted
  next: refs/tags/config-2025.11.08-rc1
```

**What Happens**:
- **Option 1: Don't regenerate** → Service folder keeps old `kustomize/` (stability)
- **Option 2: Regenerate** → Checkout new ref, copy new `kustomize/`, update service folder

**If Regenerated**:
```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml  # Same (still references kustomize/cb-base)
├── kustomize/  # NEW - Copied from refs/tags/config-2025.11.07
│   ├── cb-base/  # New version
│   ├── archetype/api/  # New version
│   └── ...
├── patches/  # Same (from size)
└── monitoring/  # Same (from profiles)
```

**Key Point**: The kustomization.yaml file structure doesn't change, but the `kustomize/` folder contents change when regenerated with a new ref.

---

## 6. Complete Example: End-to-End

### **6.1 Service Definition**

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    channel: stable
    costProfile: standard-api-cost
    monitoringProfile: domain-api
    cost:
      costCenter: "COR-B"
      businessUnit: "core-banking"
      costOwner: "owner@company.com"
    regions: [euw1]
    enabledIn: [int-stable]
```

### **6.2 Channel Resolution**

```yaml
# kustomize/catalog/channels.yaml
channels:
  stable: refs/tags/config-2025.11.06
```

**Resolution**:
- Service channel: `stable`
- Lookup: `channels.stable` → `refs/tags/config-2025.11.06`
- CONFIG_REF: `refs/tags/config-2025.11.06`

### **6.3 Repository Checkout**

```bash
# Clone repository
git clone https://github.com/org/platform-next.git /tmp/platform-next-checkout

# Checkout at resolved Git ref
cd /tmp/platform-next-checkout
git checkout refs/tags/config-2025.11.06

# Repository now at config-2025.11.06 version
```

### **6.4 Copy Resources**

```bash
# Create service folder
OUTPUT_DIR="generated/payment-processor/int-stable/euw1"
mkdir -p "$OUTPUT_DIR"

# Copy resources from checked-out repo
cp -r /tmp/platform-next-checkout/kustomize/cb-base "$OUTPUT_DIR/kustomize/"
cp -r /tmp/platform-next-checkout/kustomize/archetype/api "$OUTPUT_DIR/kustomize/archetype/"
cp -r /tmp/platform-next-checkout/kustomize/envs/int-stable "$OUTPUT_DIR/kustomize/envs/"
cp -r /tmp/platform-next-checkout/kustomize/regions/euw1 "$OUTPUT_DIR/kustomize/regions/"
cp -r /tmp/platform-next-checkout/kustomize/components/ingress "$OUTPUT_DIR/kustomize/components/"
cp -r /tmp/platform-next-checkout/kustomize/components/hpa "$OUTPUT_DIR/kustomize/components/"
cp -r /tmp/platform-next-checkout/kustomize/components/pdb "$OUTPUT_DIR/kustomize/components/"
```

### **6.5 Profile Expansion**

**Cost Profile Expansion**:
```python
# expand-profiles.py
cost_config = {
    "labels": {
        "cost.costCenter": "COR-B",
        "cost.businessUnit": "core-banking",
        "cost.owner": "owner@company.com"
    },
    "budgets": {
        "int-stable": {
            "monthly": 1000,  # base × size-multiplier
            "alerts": [...]
        }
    }
}
```

**Monitoring Profile Expansion**:
```python
monitoring_config = {
    "servicemonitor": {...},
    "prometheusrule": {...},
    "dynatrace": {
        "application": {
            "name": "payment-processor",
            "customMetrics": []
        }
    }
}
```

### **6.6 Generate Local Resources**

**patches/resources-patch.yaml**:
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
              cpu: "500m"  # From size: large
              memory: "1Gi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
```

**patches/hpa-patch.yaml**:
```yaml
# generated/payment-processor/int-stable/euw1/patches/hpa-patch.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app
spec:
  minReplicas: 3  # From size: large
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**monitoring/dynatrace-config.yaml**:
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
      "alertRules": [...],
      "customMetrics": []
    }
```

### **6.7 Generate kustomization.yaml**

```yaml
# generated/payment-processor/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Local resources (copied from checked-out Git ref: refs/tags/config-2025.11.06)
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

### **6.8 Deployment Process**

**Step 1: Fetch Service Folder**
```bash
git clone https://github.com/org/platform-next.git
cd platform-next
# Service folder at: generated/payment-processor/int-stable/euw1/
```

**Step 2: Replace Image Tag**
```bash
cd generated/payment-processor/int-stable/euw1
sed -i "s/PLACEHOLDER_TAG/v1.2.3/g" kustomization.yaml
```

**Step 3: Build Manifests**
```bash
kustomize build . > manifests.yaml
```

**What kustomize build does**:
1. Reads `kustomization.yaml`
2. Loads `kustomize/cb-base` (from checked-out ref)
3. Loads `kustomize/archetype/api` (from checked-out ref)
4. Loads `kustomize/envs/int-stable` (from checked-out ref)
5. Loads `kustomize/regions/euw1` (from checked-out ref)
6. Loads `kustomize/components/*` (from checked-out ref)
7. Loads `patches/*` (generated from size)
8. Loads `monitoring/*` (generated from profiles)
9. Applies patches, labels, images
10. Generates final manifests

**Step 4: Apply to Cluster**
```bash
kubectl apply -f manifests.yaml
```

---

## 7. Generation Process Deep Dive

### **7.1 Complete Generator Script Logic**

```bash
#!/usr/bin/env bash
# generate-kz.sh - Complete implementation

SERVICE=$1
ENV=$2
REGION=$3

# ================================================
# Step 1: Load Service Data
# ================================================
SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" \
  kustomize/catalog/services.yaml)

ARCHETYPE=$(echo "$SERVICE_DATA" | yq eval '.archetype' -)
PROFILE=$(echo "$SERVICE_DATA" | yq eval '.profile' -)
SIZE=$(echo "$SERVICE_DATA" | yq eval '.size' -)
COST_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.costProfile' -)
MONITORING_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.monitoringProfile' -)

# Load profile to get components
PROFILE_DATA=$(yq eval ".profiles.$PROFILE" kustomize/catalog/profiles.yaml)
COMPONENTS=$(echo "$PROFILE_DATA" | yq eval '.components[]' -)

# Load size to get resources
SIZE_DATA=$(yq eval ".sizes.$SIZE" kustomize/catalog/sizes.yaml)
CPU=$(echo "$SIZE_DATA" | yq eval '.cpu' -)
MEMORY=$(echo "$SIZE_DATA" | yq eval '.memory' -)
MIN_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.min' -)
MAX_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.max' -)
CPU_TARGET=$(echo "$SIZE_DATA" | yq eval '.scaling.cpuTarget' -)

# ================================================
# Step 2: Resolve Channel/Env Pin → Git Ref
# ================================================
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)

if [[ -n "$CHANNEL" ]]; then
  # Service specifies channel
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" kustomize/catalog/channels.yaml)
else
  # Check region pins
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" \
    kustomize/catalog/region-pins.yaml)
  
  if [[ -n "$REGION_PIN" ]]; then
    CONFIG_REF="$REGION_PIN"
  else
    # Check defaultChannel
    DEFAULT_CHANNEL=$(yq eval ".defaultChannel.$ENV // \"\"" \
      kustomize/catalog/env-pins.yaml)
    
    if [[ -n "$DEFAULT_CHANNEL" ]]; then
      CONFIG_REF=$(yq eval ".channels.$DEFAULT_CHANNEL" \
        kustomize/catalog/channels.yaml)
    else
      # Use envPins directly
      CONFIG_REF=$(yq eval ".envPins.$ENV" \
        kustomize/catalog/env-pins.yaml)
    fi
  fi
fi

echo "Resolved CONFIG_REF: $CONFIG_REF"

# ================================================
# Step 3: Checkout Repository at Git Ref
# ================================================
REPO_URL="${PLATFORM_NEXT_REPO_URL:-https://github.com/org/platform-next.git}"
TEMP_REPO_DIR=$(mktemp -d)

echo "Cloning repository..."
git clone "$REPO_URL" "$TEMP_REPO_DIR"

echo "Checking out $CONFIG_REF..."
cd "$TEMP_REPO_DIR"
git checkout "$CONFIG_REF"

# ================================================
# Step 4: Create Service Folder Structure
# ================================================
OUTPUT_DIR="generated/$SERVICE/$ENV/$REGION"
mkdir -p "$OUTPUT_DIR/patches"
mkdir -p "$OUTPUT_DIR/monitoring"
mkdir -p "$OUTPUT_DIR/cost"
mkdir -p "$OUTPUT_DIR/kustomize"

# ================================================
# Step 5: Copy Resources from Checked-Out Ref
# ================================================
echo "Copying resources from checked-out ref..."

# Copy base
cp -r "$TEMP_REPO_DIR/kustomize/cb-base" "$OUTPUT_DIR/kustomize/"

# Copy archetype
mkdir -p "$OUTPUT_DIR/kustomize/archetype"
cp -r "$TEMP_REPO_DIR/kustomize/archetype/$ARCHETYPE" \
  "$OUTPUT_DIR/kustomize/archetype/"

# Copy environment overlay
mkdir -p "$OUTPUT_DIR/kustomize/envs"
cp -r "$TEMP_REPO_DIR/kustomize/envs/$ENV" \
  "$OUTPUT_DIR/kustomize/envs/"

# Copy region overlay
mkdir -p "$OUTPUT_DIR/kustomize/regions"
cp -r "$TEMP_REPO_DIR/kustomize/regions/$REGION" \
  "$OUTPUT_DIR/kustomize/regions/"

# Copy components
mkdir -p "$OUTPUT_DIR/kustomize/components"
for COMP in $COMPONENTS; do
  cp -r "$TEMP_REPO_DIR/kustomize/components/$COMP" \
    "$OUTPUT_DIR/kustomize/components/"
done

# Cleanup temp repo
cd -
rm -rf "$TEMP_REPO_DIR"

# ================================================
# Step 6: Expand Profiles
# ================================================
echo "Expanding profiles..."
python3 scripts/expand-profiles.py \
  --service "$SERVICE" \
  --environment "$ENV" \
  --output /tmp/expanded-${SERVICE}-${ENV}.json

# Extract cost labels
COST_LABELS=$(jq -r '.cost.labels | to_entries | map("\(.key): \(.value)") | join("\n  ")' \
  /tmp/expanded-${SERVICE}-${ENV}.json)

# ================================================
# Step 7: Generate Local Resources from Size
# ================================================
echo "Generating patches from size..."

# Resources patch
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
              cpu: "$(echo "$SIZE_DATA" | yq eval '.limits.cpu' -)"
              memory: "$(echo "$SIZE_DATA" | yq eval '.limits.memory' -)"
EOF

# HPA patch
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

# ================================================
# Step 8: Generate Monitoring Resources
# ================================================
if [[ -n "$MONITORING_PROFILE" ]]; then
  echo "Generating monitoring resources..."
  
  python3 scripts/generate-monitoring-resources.py \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type servicemonitor
  
  python3 scripts/generate-monitoring-resources.py \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type prometheusrule-recording
  
  python3 scripts/generate-monitoring-resources.py \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type prometheusrule-alerts
  
  python3 scripts/generate-monitoring-resources.py \
    --service "$SERVICE" \
    --environment "$ENV" \
    --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
    --output-dir "$OUTPUT_DIR/monitoring" \
    --resource-type dynatrace-config
fi

# ================================================
# Step 9: Generate kustomization.yaml
# ================================================
echo "Generating kustomization.yaml..."

cat > "$OUTPUT_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Local resources (copied from checked-out Git ref: ${CONFIG_REF})
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
    newName: gcr.io/project/${SERVICE}
    newTag: PLACEHOLDER_TAG

# Patches (reference local patch files)
patches:
  - path: patches/resources-patch.yaml
  - path: patches/hpa-patch.yaml
EOF

echo "✅ Generated service folder structure at: $OUTPUT_DIR"
echo "   Config ref: $CONFIG_REF"
echo "   Resources from: $CONFIG_REF"
```

---

## 8. Deployment Process Deep Dive

### **8.1 Harness Pipeline Configuration**

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
              
              # Custom kustomize build
              pluginPath: kustomize
```

### **8.2 Deployment Steps**

**Step 1: Fetch Service Folder**
```bash
# Harness fetches from Git
git clone https://github.com/org/platform-next.git
cd platform-next

# Service folder structure:
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml
├── kustomize/
├── patches/
└── monitoring/
```

**Step 2: Replace Image Tag**
```bash
cd generated/payment-processor/int-stable/euw1

# Replace placeholder with actual image tag
sed -i "s/PLACEHOLDER_TAG/v1.2.3/g" kustomization.yaml

# kustomization.yaml now has:
images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: v1.2.3  # ← Replaced
```

**Step 3: Run kustomize build**
```bash
# All resources are local, no Git access needed
kustomize build . > manifests.yaml
```

**What happens during build**:
1. Kustomize reads `kustomization.yaml`
2. Loads `kustomize/cb-base/` (local, from checked-out ref)
3. Loads `kustomize/archetype/api/` (local, from checked-out ref)
4. Loads `kustomize/envs/int-stable/` (local, from checked-out ref)
5. Loads `kustomize/regions/euw1/` (local, from checked-out ref)
6. Loads `kustomize/components/*` (local, from checked-out ref)
7. Loads `patches/resources-patch.yaml` (local, generated)
8. Loads `patches/hpa-patch.yaml` (local, generated)
9. Loads `monitoring/*` (local, generated)
10. Applies patches (resources, HPA)
11. Applies commonLabels (including cost labels)
12. Replaces image (placeholder → v1.2.3)
13. Generates final manifests

**Step 4: Apply to Cluster**
```bash
kubectl apply -f manifests.yaml
```

**Result**: All resources deployed with correct configuration from checked-out Git ref and profile expansion.

---

## 9. File Structure Details

### **9.1 Complete Service Folder Structure**

```
generated/payment-processor/int-stable/euw1/
├── kustomization.yaml                    # Main kustomization file
│
├── kustomize/                            # Copied from checked-out Git ref
│   ├── cb-base/                          # Base configuration
│   │   ├── kustomization.yaml
│   │   ├── labels-annotations.yaml
│   │   ├── base-netpol.yaml
│   │   └── serviceaccount-defaults.yaml
│   │
│   ├── archetype/
│   │   └── api/                          # API archetype
│   │       ├── kustomization.yaml
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── rbac.yaml
│   │       └── probes.yaml
│   │
│   ├── envs/
│   │   └── int-stable/                   # Environment overlay
│   │       ├── kustomization.yaml
│   │       ├── limitrange.yaml
│   │       ├── resourcequota.yaml
│   │       ├── dns-config-patch.yaml
│   │       └── certificate-issuer-patch.yaml
│   │
│   ├── regions/
│   │   └── euw1/                         # Region overlay
│   │       ├── kustomization.yaml
│   │       ├── region-labels-patch.yaml
│   │       ├── gateway-class-patch.yaml
│   │       └── topology-spread-patch.yaml
│   │
│   └── components/                       # Components
│       ├── ingress/
│       │   ├── kustomization.yaml
│       │   └── ingress.yaml
│       ├── hpa/
│       │   ├── kustomization.yaml
│       │   └── hpa.yaml
│       └── pdb/
│           ├── kustomization.yaml
│           └── pdb.yaml
│
├── patches/                              # Generated from size
│   ├── resources-patch.yaml              # CPU/memory patches
│   └── hpa-patch.yaml                    # HPA min/max replicas
│
└── monitoring/                            # Generated from monitoring profile
    ├── servicemonitor.yaml               # Prometheus ServiceMonitor
    ├── prometheusrule-recording.yaml     # Recording rules
    ├── prometheusrule-alerts.yaml        # Alert rules
    └── dynatrace-config.yaml             # Dynatrace ConfigMap
```

### **9.2 File Sizes**

**Before (Pre-Built Manifests)**:
- `manifests.yaml`: ~500-1000 lines per service/environment/region
- Total: Large files in Git

**After (Service Folder)**:
- `kustomization.yaml`: ~50-100 lines
- `kustomize/`: Copied from repo (shared across services using same ref)
- `patches/`: ~20-30 lines per file
- `monitoring/`: ~50-200 lines per file
- Total: Smaller, more organized

---

## 10. Benefits and Trade-offs

### **10.1 Benefits**

1. **All Resources Local**:
   - ✅ No Git access needed during `kustomize build`
   - ✅ Faster builds (no network calls)
   - ✅ Works in air-gapped environments

2. **Channel/Env Pin Control**:
   - ✅ Determines which Git ref to checkout
   - ✅ Easy to see which version is used (checkout happens at generation)
   - ✅ Can regenerate to get new version

3. **Clear Separation**:
   - ✅ Shared config (from Git ref) in `kustomize/`
   - ✅ Service-specific config (from profiles) in `patches/`, `monitoring/`
   - ✅ Easy to understand what comes from where

4. **GitOps-Friendly**:
   - ✅ Folder structure easy to review
   - ✅ Can see all resources in one place
   - ✅ Easy to debug (all files visible)

5. **Flexibility**:
   - ✅ Can regenerate to update to new Git ref
   - ✅ Can keep existing folder (explicit pinning)
   - ✅ Profile expansion generates actual files

### **10.2 Trade-offs**

1. **Larger Git Repository**:
   - ⚠️ `kustomize/` folder copied for each service/environment/region
   - ⚠️ More files in Git than single manifest file
   - ✅ But: More organized and reviewable

2. **Generation Time**:
   - ⚠️ Need to checkout repository for each service
   - ⚠️ Copy resources takes time
   - ✅ But: Happens in CI/CD, not at deployment time

3. **Storage**:
   - ⚠️ More disk space needed (copied resources)
   - ✅ But: Can be optimized (shared refs, compression)

### **10.3 Comparison Summary**

| Aspect | Old (Pre-Built Manifests) | New (Service Folder) |
|--------|---------------------------|----------------------|
| **Git Access During Build** | ❌ Not needed | ❌ Not needed |
| **File Size** | Large (500-1000 lines) | Smaller (organized) |
| **Channel/Env Pin Usage** | Embedded in refs | Used for checkout |
| **Profile Expansion** | Values injected | Files generated |
| **Reviewability** | Hard (large files) | Easy (folder structure) |
| **Flexibility** | Lower | Higher |
| **Git Repository Size** | Smaller | Larger (but organized) |

---

## Summary

### **Key Changes**

1. **Generation Output**: Service folder structure instead of single manifest file
2. **Channel/Env Pin Usage**: Used to checkout and copy resources, not embedded in refs
3. **Resource References**: All local paths, no remote Git URLs
4. **Profile Expansion**: Generates actual YAML files, not just values
5. **Deployment Process**: Includes `kustomize build` step
6. **CI/CD Pipeline**: Generates folder structure, not final manifests

### **How It Works**

1. **Service added to catalog** → CI/CD triggered
2. **Resolve channel/env pin** → Git ref (e.g., `refs/tags/config-2025.11.06`)
3. **Checkout repository** at that Git ref
4. **Copy resources** to service folder (`kustomize/` directory)
5. **Expand profiles** → Generate local resources (`patches/`, `monitoring/`)
6. **Generate kustomization.yaml** with local path references
7. **Commit to Git** → Service folder in `generated/`
8. **Deployment** → Fetch folder, replace image tag, `kustomize build`, apply

### **Key Benefits**

- ✅ All resources local (no Git access during build)
- ✅ Channel/env pin determines which version to use
- ✅ Clear separation: shared config vs service-specific
- ✅ GitOps-friendly structure
- ✅ Flexible: regenerate or keep existing

This design provides a **complete, self-contained service folder structure** that is easy to review, manage, and deploy, with **channel/env pins controlling which version of shared configuration is used**.

