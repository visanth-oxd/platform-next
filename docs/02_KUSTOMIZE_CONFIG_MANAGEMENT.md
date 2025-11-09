# Kustomize Config Management - Detailed Design

## Executive Summary

This document describes the **Config Management Repository (platform-next)** - the heart of the Kubernetes configuration system using Kustomize.

**Key Points**:
- Kustomize-native (no Helm)
- Catalog-driven (single source of truth)
- Layered architecture (archetypes → components → overlays)
- GitOps-compliant (all config in Git)
- Manifest generation in CI (reproducible builds)

---

## 1. Why Kustomize?

### Rationale for Kustomize Over Alternatives

#### Comparison Matrix

| Aspect | Kustomize | Helm | Jsonnet | Custom |
|--------|-----------|------|---------|--------|
| **K8s Native** | ✅ Built into kubectl | ❌ External tool | ❌ External | ❌ Custom |
| **Templating** | ❌ No logic | ✅ Go templates | ✅ Full language | ✅ Any |
| **Complexity** | ⭐⭐ Low | ⭐⭐⭐⭐ High | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Very high |
| **Learning Curve** | ⭐⭐ Easy | ⭐⭐⭐⭐ Steep | ⭐⭐⭐⭐ Steep | ⭐⭐⭐⭐⭐ Very steep |
| **Debugging** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐ Hard | ⭐⭐ Hard | ⭐ Very hard |
| **GitOps** | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐ Requires prep | ⭐⭐⭐ Requires prep | ⭐⭐ Custom |
| **Composability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | ⭐⭐⭐ Good | ⭐⭐ Custom |

**Decision**: Kustomize wins for GitOps, simplicity, and K8s-native integration

### What Kustomize Enables

1. **Declarative Overlays**
   ```
   Base → Environment Overlay → Region Overlay
   No templating logic, pure YAML patching
   ```

2. **Components** (kind: Component)
   ```
   Optional features as composable units
   Enable/disable features without modifying base
   ```

3. **Strategic Merge Patches**
   ```
   Add or modify sections of YAML
   No need to duplicate entire manifests
   ```

4. **Built into kubectl**
   ```
   kubectl apply -k .
   No additional tools needed
   ```

---

## 2. Repository Structure

### Directory Layout

```
platform-next/
└── kustomize/
    ├── archetype/           # Layer 1: Workload Shapes
    │   ├── api/
    │   ├── listener/
    │   ├── streaming/
    │   ├── scheduler/
    │   └── job/
    │
    ├── components/          # Layer 2: Behavior Modifiers
    │   ├── ingress/
    │   ├── hpa/
    │   ├── pdb/
    │   ├── retry/
    │   ├── circuit-breaker/
    │   ├── mtls/
    │   ├── network-policy/
    │   ├── security-hardening/
    │   └── topology/
    │
    ├── cb-base/             # Layer 3: Organization Standards
    │   ├── labels-annotations.yaml
    │   ├── base-netpol.yaml
    │   ├── pdb-defaults.yaml
    │   └── serviceaccount-defaults.yaml
    │
    ├── envs/                # Layer 4: Environment Overlays
    │   ├── int-stable/
    │   ├── pre-stable/
    │   └── prod/
    │
    ├── regions/             # Layer 5: Region Overlays
    │   ├── euw1/
    │   └── euw2/
    │
    └── catalog/             # Layer 6: Metadata & Configuration
        ├── services.yaml        # Service definitions
        ├── profiles.yaml        # Behavior profiles
        ├── sizes.yaml          # T-shirt sizing
        ├── channels.yaml       # Release channels
        └── env-pins.yaml       # Environment versioning
```

---

## 3. Design Layers (Deep Dive)

### Layer 1: Archetypes (Workload Shapes)

**Purpose**: Define fundamental structure of each workload type

**Archetype = Answer these questions**:
- What K8s controller? (Deployment, CronJob, Job, StatefulSet)
- Does it need a Service?
- What health probes?
- What ports?
- What security context?

#### Archetype: `api`

**Files**:
```
archetype/api/
├── deployment.yaml       # Deployment with ports, security
├── service.yaml         # ClusterIP Service
├── rbac.yaml           # ServiceAccount + RoleBinding
├── probes.yaml         # HTTP health checks
└── kustomization.yaml
```

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    app.kubernetes.io/component: deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: app-sa
      
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      
      containers:
        - name: app
          image: placeholder:latest  # Replaced by Harness
          ports:
            - containerPort: 8080
              name: http
          
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          
          resources:
            requests:
              cpu: "250m"      # Replaced by size
              memory: "512Mi"  # Replaced by size
            limits:
              cpu: "250m"
              memory: "512Mi"
          
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities:
              drop: [ALL]
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - rbac.yaml

patchesStrategicMerge:
  - probes.yaml

commonLabels:
  workload.archetype: api
```

**Why This Structure?**
- ✅ Minimal (only core resources)
- ✅ Reusable (all API services use this)
- ✅ No environment logic (pure structure)
- ✅ Patchable (can be customized)

---

### Layer 2: Components (Optional Features)

**Purpose**: Add optional capabilities without modifying archetypes

**Component = Answer**: What extra feature does this enable?

#### Component: `ingress`

**Files**:
```
components/ingress/
├── ingress.yaml
└── kustomization.yaml
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component  # ← Important: kind=Component

resources:
  - ingress.yaml
```

**ingress.yaml**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  ingressClassName: nginx
  rules:
    - host: PLACEHOLDER_DOMAIN  # Replaced by generated patch
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 80
  tls:
    - hosts:
        - PLACEHOLDER_DOMAIN
      secretName: app-tls
```

**Why Component (not part of archetype)?**
- ✅ Not all APIs need external exposure
- ✅ Optional feature (enable per service)
- ✅ Composable (can combine with other components)

---

### Layer 3: Base Configuration (Organization Standards)

**Purpose**: Enforce company-wide policies on ALL services

**File**: `cb-base/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - labels-annotations.yaml
  - base-netpol.yaml
  - pdb-defaults.yaml
  - serviceaccount-defaults.yaml

commonLabels:
  platform: kubernetes
  managed-by: kustomize
  company: mycompany

commonAnnotations:
  platform.company.com/managed: "true"
```

**Why Separate Base?**
- ✅ Apply to ALL services (consistency)
- ✅ Change once, affects all
- ✅ Compliance (audit requirements)
- ✅ Security baseline

---

### Layer 4: Environment Overlays

**Purpose**: Environment-specific configuration (int, pre, prod)

**Example**: `envs/prod/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - limitrange.yaml          # Container limits
  - resourcequota.yaml       # Namespace quotas
  - networkpolicy-defaults.yaml

patches:
  - path: dns-config-patch.yaml        # Custom DNS
  - path: certificate-issuer-key.yaml  # Prod cert issuer
  - path: pdb-defaults.yaml            # Stricter PDB for prod
```

**Rationale**:
- Prod has tighter resource controls
- Different certificate issuers per environment
- DNS config varies by environment
- Policy toggles (enable/disable features per env)

---

### Layer 5: Region Overlays

**Purpose**: Regional infrastructure differences

**Example**: `regions/euw1/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

patches:
  - path: tolerations-taints.yaml      # euw1 node pools
  - path: topology-spread.yaml         # AZ spread for euw1
  - path: region-labels.yaml           # region=euw1 label
```

**Rationale**:
- Different node pools per region
- Different availability zones
- Regional certificate authorities
- Geography-specific settings

---

## 4. Catalog Design

### Single Catalog File Approach

**File**: `kustomize/catalog/services.yaml`

```yaml
# ================================================
# Service Catalog - Single Source of Truth
# ================================================
services:
  # Service 1: API
  - name: payment-service
    archetype: api
    profile: public-api
    size: medium
    environments: [int, pre, prod]
    regions: [euw1, euw2]
    team: payments-team
    slack: "#team-payments"
    
    # Optional overrides
    resources:
      overrides:
        prod:
          size: large
    
    # Harness metadata
    harness:
      pipelineId: payment-service-cd
      createdAt: "2025-11-09T10:00:00Z"
      createdBy: user@company.com
  
  # Service 2: Listener
  - name: events-listener
    archetype: listener
    profile: event-consumer
    size: small
    environments: [int, prod]
    regions: [euw1, euw2]
    team: events-team
    slack: "#team-events"
```

**Why Single File?**
- ✅ Backstage updates via API (atomic updates)
- ✅ Easy to search and query
- ✅ Simple to render in UI
- ✅ No merge conflicts (UI serializes)
- ✅ Clear ordering (easy to scan)

**When to Split?**
- If file grows > 10,000 lines (~500 services)
- If query performance degrades
- If Git operations slow down

---

### Supporting Catalog Files

#### profiles.yaml

**Purpose**: Define behavior presets

```yaml
profiles:
  public-api:
    archetype: api
    components:
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - hpa
      - pdb
      - security-hardening
    probes:
      readiness: /health/ready
      liveness: /health/live
  
  internal-api:
    archetype: api
    components:
      - mtls
      - hpa
      - pdb
    probes:
      readiness: /health/ready
      liveness: /health/live
  
  event-consumer:
    archetype: listener
    components:
      - pdb
      - security-hardening
    probes:
      liveness: /health/live
```

#### sizes.yaml

**Purpose**: T-shirt sizing for resources

```yaml
sizes:
  small:
    cpu: 100m
    memory: 256Mi
    limits:
      cpu: 200m
      memory: 512Mi
    scaling:
      min: 1
      max: 3
      cpuTarget: 80
  
  medium:
    cpu: 250m
    memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi
    scaling:
      min: 2
      max: 6
      cpuTarget: 75
  
  large:
    cpu: 500m
    memory: 1Gi
    limits:
      cpu: 1000m
      memory: 2Gi
    scaling:
      min: 3
      max: 10
      cpuTarget: 70
```

---

## 5. Manifest Generation Process

### The Generator Script

**File**: `scripts/generate-kz-v3.sh`

**Purpose**: Read catalog → Generate kustomization.yaml → Output to tmp/

**Logic Flow**:

```bash
#!/usr/bin/env bash
# Usage: generate-kz-v3.sh <SERVICE> <ENV> <REGION>

SERVICE=$1
ENV=$2
REGION=$3

# 1. Load service definition from catalog
SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" \
  kustomize/catalog/services.yaml)

# 2. Extract configuration
ARCHETYPE=$(echo "$SERVICE_DATA" | yq eval '.archetype' -)
PROFILE=$(echo "$SERVICE_DATA" | yq eval '.profile' -)
SIZE=$(echo "$SERVICE_DATA" | yq eval '.size' -)

# 3. Load profile (components to enable)
PROFILE_DATA=$(yq eval ".profiles.$PROFILE" kustomize/catalog/profiles.yaml)
COMPONENTS=$(echo "$PROFILE_DATA" | yq eval '.components[]' -)

# 4. Load size (resources)
SIZE_DATA=$(yq eval ".sizes.$SIZE" kustomize/catalog/sizes.yaml)
CPU=$(echo "$SIZE_DATA" | yq eval '.cpu' -)
MEMORY=$(echo "$SIZE_DATA" | yq eval '.memory' -)
MIN_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.min' -)
MAX_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.max' -)

# 5. Generate kustomization.yaml
TMP_DIR="tmp/$SERVICE/$ENV/$REGION"
mkdir -p "$TMP_DIR"

cat > "$TMP_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Base resources
resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/$ARCHETYPE
  - ../../../../kustomize/envs/$ENV
  - ../../../../kustomize/regions/$REGION

# Components from profile
components:
$(for COMP in $COMPONENTS; do
  echo "  - ../../../../kustomize/components/$COMP"
done)

namespace: $ENV-$SERVICE-$REGION

commonLabels:
  app: $SERVICE
  env: $ENV
  region: $REGION

images:
  - name: placeholder
    newName: gcr.io/project/$SERVICE
    newTag: PLACEHOLDER_TAG  # Replaced by Harness

# Patches from size
patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "$CPU"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "$MEMORY"

  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: $MIN_REPLICAS
      - op: replace
        path: /spec/maxReplicas
        value: $MAX_REPLICAS
EOF

# 6. Build manifests
kustomize build "$TMP_DIR" > "$TMP_DIR/manifests.yaml"
```

**Output**: `tmp/payment-service/prod/euw1/manifests.yaml`

---

### CI Workflow (GitHub Actions)

**File**: `.github/workflows/generate-manifests.yml`

```yaml
name: Generate K8s Manifests

on:
  push:
    branches: [main]
    paths:
      - 'kustomize/catalog/services.yaml'
      - 'kustomize/archetype/**'
      - 'kustomize/components/**'
      - 'kustomize/envs/**'
      - 'kustomize/regions/**'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      changed_services: ${{ steps.detect.outputs.services }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 2
      
      - name: Detect Changed Services
        id: detect
        run: |
          # Smart detection logic
          ./scripts/detect-changed-services.sh > services.json
          echo "services=$(cat services.json)" >> $GITHUB_OUTPUT
  
  generate:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.changed_services) }}
        environment: ['int-stable', 'pre-stable', 'prod']
        region: ['euw1', 'euw2']
      max-parallel: 20
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate Kustomization
        run: |
          ./scripts/generate-kz-v3.sh \
            ${{ matrix.service }} \
            ${{ matrix.environment }} \
            ${{ matrix.region }}
      
      - name: Build Manifests
        run: |
          OUTPUT_DIR="generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}"
          mkdir -p $OUTPUT_DIR
          
          cd tmp/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}
          kustomize build . > $GITHUB_WORKSPACE/$OUTPUT_DIR/manifests.yaml
      
      - name: Validate
        run: |
          kubeconform --strict \
            generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}/manifests.yaml
      
      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: manifests-${{ matrix.service }}-${{ matrix.environment }}-${{ matrix.region }}
          path: generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}/
  
  commit:
    needs: generate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/download-artifact@v3
        with:
          path: generated/
      
      - name: Commit Manifests
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          
          git add generated/
          git commit -m "🤖 Generated manifests
          
          Services: ${{ join(fromJson(needs.detect-changes.outputs.changed_services), ', ') }}"
          
          git push
```

**Result**: Manifests committed to `generated/` directory (GitOps source of truth)

---

## 6. Why This Design?

### Design Decision Rationale

#### Decision 1: Archetypes vs Templates

**Considered**:
- Option A: Many archetypes (10+) for every variation
- Option B: Few archetypes (5) + components
- Option C: No archetypes, only components

**Chose**: Option B (5 archetypes + components)

**Rationale**:
- ✅ Clear patterns (api, listener, job, scheduler, streaming)
- ✅ Components for variations (DRY principle)
- ✅ Easy to understand (5 is memorable)
- ✅ Flexible (components enable customization)

#### Decision 2: Components as `kind: Component`

**Considered**:
- Option A: Components as Kustomization bases
- Option B: Components as `kind: Component`
- Option C: No components (everything in archetypes)

**Chose**: Option B (Component kind)

**Rationale**:
- ✅ Kustomize native feature
- ✅ Composable (enable multiple)
- ✅ Optional (can be omitted)
- ✅ Clear semantics (Component = optional)

#### Decision 3: Single Catalog File

**Considered**:
- Option A: Per-service files (100+ files)
- Option B: Single catalog file
- Option C: Per-archetype catalogs

**Chose**: Option B (single file)

**Rationale**:
- ✅ Backstage updates atomically (no merge conflicts)
- ✅ Easy to search/query
- ✅ Simple for UI rendering
- ✅ Matches current pattern

#### Decision 4: Manifests in Git (generated/)

**Considered**:
- Option A: Generate manifests in Harness (runtime)
- Option B: Generate in CI, commit to Git
- Option C: Don't commit generated files

**Chose**: Option B (commit to Git)

**Rationale**:
- ✅ GitOps-compliant (Git = source of truth)
- ✅ Harness can't run scripts (security policy)
- ✅ Reproducible builds
- ✅ Audit trail (see exactly what deployed)
- ✅ Rollback via Git history

---

## 7. Benefits & Trade-offs

### Benefits

| Benefit | How Kustomize Delivers |
|---------|------------------------|
| **No Templating** | Pure YAML, no logic, easy to debug |
| **Composable** | Archetypes + Components = flexible |
| **GitOps Native** | All config in Git, declarative |
| **K8s Native** | Built into kubectl, no external tools |
| **Layered** | Clear separation (archetype/component/overlay) |
| **DRY** | Reuse archetypes, no duplication |

### Trade-offs

| Trade-off | Why Acceptable |
|-----------|----------------|
| **Generated files in Git** | Audit trail worth the repo size |
| **CI dependency** | Fast CI (5-10 min), acceptable |
| **Kustomize learning curve** | Simpler than Helm/Jsonnet |
| **No complex logic** | Don't need it (catalog + script handle logic) |

---

## Summary

### The Kustomize Layer

**What it does**:
- Defines workload structures (archetypes)
- Provides optional features (components)
- Enforces standards (base, overlays)
- Generates manifests (CI pipeline)
- Commits to Git (GitOps)

**What it doesn't do**:
- ❌ Deployment (Harness does this)
- ❌ Image building (App CI does this)
- ❌ User interface (Backstage does this)

**Integration**:
```
Backstage → Updates catalog
          ↓
CI → Generates manifests
   ↓
Git → Source of truth
      ↓
Harness → Deploys from Git
```

**This is the foundation of the entire platform!**
