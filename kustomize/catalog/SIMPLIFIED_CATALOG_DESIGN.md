# Simplified Service Catalog Design

## Goal

Make it easy for developers to onboard services with minimal configuration:
- Provide service name and archetype
- Select T-shirt sizes for resources
- Choose behavior profiles
- Specify environments
- Auto-deploy via pipeline

---

## Design Principles

1. **Convention over Configuration**
   - Smart defaults for 90% use cases
   - Explicit overrides only when needed

2. **Progressive Disclosure**
   - Simple mode: 5 required fields
   - Advanced mode: Full customization

3. **T-Shirt Sizing**
   - Resources: small, medium, large, xlarge
   - Scaling: low, medium, high, burst

4. **Behavior Profiles**
   - Common patterns as presets
   - public-api, internal-worker, batch-job, etc.

5. **Self-Service**
   - Developers can add services without platform team
   - Validation prevents misconfigurations

---

## Simplified Catalog Schema

### Minimal Service Definition (Simple Mode)

```yaml
services:
  - name: account-service          # REQUIRED
    archetype: api                 # REQUIRED: api | listener | streaming | scheduler | job
    profile: public-api            # REQUIRED: behavior preset
    size: medium                   # REQUIRED: resource size
    environments: [int, pre, prod] # REQUIRED: where to deploy
    
    # OPTIONAL (has smart defaults)
    image: gcr.io/project/account-service  # Default: gcr.io/project/{name}
    regions: [euw1, euw2]                  # Default: all regions
```

**That's it! 5 fields to deploy a service.**

### Advanced Service Definition (Override Defaults)

```yaml
services:
  - name: payment-api
    archetype: api
    profile: public-api
    size: large
    environments: [int, pre, prod]
    
    # Advanced configuration (optional)
    scaling:
      profile: high         # Override default from 'size'
      min: 4
      max: 20
    
    features:              # Enable/disable features
      - ingress
      - circuit-breaker
      - mtls
    
    resources:
      overrides:           # Override T-shirt size for specific env
        prod:
          size: xlarge
    
    domains:
      prod: api.payment.company.com
```

---

## 1. T-Shirt Sizing System

### Resource Sizes

| Size | CPU Request | Memory Request | CPU Limit | Memory Limit | Typical Use Case |
|------|-------------|----------------|-----------|--------------|------------------|
| **small** | 100m | 256Mi | 200m | 512Mi | Low-traffic APIs, workers |
| **medium** | 250m | 512Mi | 500m | 1Gi | Standard APIs, listeners |
| **large** | 500m | 1Gi | 1000m | 2Gi | High-traffic APIs |
| **xlarge** | 1000m | 2Gi | 2000m | 4Gi | Heavy workloads, data processing |
| **xxlarge** | 2000m | 4Gi | 4000m | 8Gi | ML, analytics |

### Scaling Profiles

| Profile | Min Replicas | Max Replicas | CPU Target | Typical Pattern |
|---------|--------------|--------------|------------|-----------------|
| **low** | 1 | 3 | 80% | Dev/test, low traffic |
| **medium** | 2 | 6 | 75% | Standard production |
| **high** | 3 | 10 | 70% | High traffic |
| **burst** | 2 | 20 | 65% | Unpredictable spikes |

### Auto-Mapping

```yaml
# When you specify size: medium
# System automatically sets:
resources:
  cpu: 250m
  memory: 512Mi

scaling:
  profile: medium
  min: 2
  max: 6
  cpuTarget: 75
```

---

## 2. Behavior Profiles

### Profile Catalog

**Purpose**: Pre-configured bundles of archetype + components + settings

#### Profile: `public-api`

```yaml
# What it does:
archetype: api
features:
  - ingress           # External access
  - retry             # HTTP retry
  - circuit-breaker   # Resilience
  - mtls              # Service mesh
  - pdb               # High availability
  - security-hardening
  - network-policy

defaults:
  size: medium
  scaling: medium
  readinessProbe:
    path: /health/ready
  livenessProbe:
    path: /health/live
```

#### Profile: `internal-api`

```yaml
archetype: api
features:
  - mtls              # Service mesh only (no ingress)
  - circuit-breaker
  - pdb
  - security-hardening

defaults:
  size: small         # Internal APIs typically smaller
  scaling: low
```

#### Profile: `event-consumer`

```yaml
archetype: listener
features:
  - pdb
  - security-hardening
  - network-policy

defaults:
  size: small
  scaling: medium     # Scale based on queue depth
```

#### Profile: `batch-job`

```yaml
archetype: job
features:
  - security-hardening

defaults:
  size: large         # Jobs need resources
  backoffLimit: 3
  ttlSecondsAfterFinished: 3600
```

#### Profile: `scheduled-task`

```yaml
archetype: scheduler
features:
  - security-hardening

defaults:
  size: medium
  schedule: "0 0 * * *"  # Daily
  concurrencyPolicy: Forbid
```

#### Profile: `websocket-server`

```yaml
archetype: streaming
features:
  - ingress
  - session-affinity  # Sticky sessions
  - pdb
  - mtls

defaults:
  size: medium
  scaling: high       # WebSocket = high connection count
  sessionAffinity: ClientIP
```

### Profile Inheritance

```yaml
# Developer specifies minimal config
services:
  - name: account-service
    profile: public-api
    size: medium
    environments: [int, pre, prod]

# System expands to full configuration:
# archetype: api
# features: [ingress, retry, circuit-breaker, mtls, pdb, security-hardening, network-policy]
# resources: { cpu: 250m, memory: 512Mi }
# scaling: { min: 2, max: 6, cpuTarget: 75 }
```

---

## 3. Smart Defaults System

### Default Resolution Order

```
1. Profile defaults
   ↓
2. Archetype defaults
   ↓
3. Size-based defaults
   ↓
4. Environment-specific defaults
   ↓
5. Explicit service overrides
```

### Examples

#### Example 1: Minimal Configuration

```yaml
# Developer writes:
services:
  - name: user-api
    profile: public-api
    size: medium
    environments: [int, pre, prod]

# System resolves to:
services:
  - name: user-api
    archetype: api                          # From profile
    image: gcr.io/project/user-api          # Default pattern
    tagStrategy: gar-latest-by-branch       # Default
    channel: stable                         # Default
    regions: [euw1, euw2]                   # Default
    enabledIn: [int-stable, pre-stable, prod]  # Mapped from environments
    
    features:                               # From profile
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - pdb
      - security-hardening
      - network-policy
    
    resources:                              # From size: medium
      cpu: 250m
      memory: 512Mi
    
    scaling:                                # From size: medium
      min: 2
      max: 6
      cpuTarget: 75
    
    probes:                                 # From profile
      readiness: /health/ready
      liveness: /health/live
```

#### Example 2: Override Defaults

```yaml
# Developer writes:
services:
  - name: payment-api
    profile: public-api
    size: large
    environments: [int, pre, prod]
    
    # Override specific values
    scaling:
      profile: high     # Override default scaling from size
    
    resources:
      overrides:
        prod:
          size: xlarge  # Production needs more resources

# System resolves:
# - Base from profile: public-api
# - Resources from size: large (500m CPU, 1Gi mem)
# - Scaling from profile: high (min:3, max:10)
# - Production gets xlarge resources (1000m CPU, 2Gi mem)
```

---

## 4. Simplified Catalog File Structure

### profiles.yaml (New File)

```yaml
# Define reusable behavior profiles
profiles:
  public-api:
    description: "External-facing REST API"
    archetype: api
    features:
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - pdb
      - security-hardening
      - network-policy
    defaults:
      size: medium
      scaling: medium
      probes:
        readiness: /health/ready
        liveness: /health/live
  
  internal-api:
    description: "Internal-only service"
    archetype: api
    features:
      - mtls
      - circuit-breaker
      - pdb
      - security-hardening
    defaults:
      size: small
      scaling: low
  
  event-consumer:
    description: "Kafka/PubSub consumer"
    archetype: listener
    features:
      - pdb
      - security-hardening
      - network-policy
    defaults:
      size: small
      scaling: medium
  
  batch-job:
    description: "One-time batch processing"
    archetype: job
    features:
      - security-hardening
    defaults:
      size: large
  
  scheduled-task:
    description: "Periodic cron job"
    archetype: scheduler
    features:
      - security-hardening
    defaults:
      size: medium
      schedule: "0 0 * * *"
```

### sizes.yaml (New File)

```yaml
# Define resource sizes
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
  
  xlarge:
    cpu: 1000m
    memory: 2Gi
    limits:
      cpu: 2000m
      memory: 4Gi
    scaling:
      min: 4
      max: 15
      cpuTarget: 65
```

### services-simple.yaml (Simplified)

```yaml
# Simple service catalog - developers edit this
services:
  - name: account-service
    profile: public-api
    size: medium
    environments: [int, pre, prod]
  
  - name: payment-api
    profile: public-api
    size: large
    environments: [int, pre, prod]
    scaling:
      profile: high
    resources:
      overrides:
        prod:
          size: xlarge
  
  - name: events-listener
    profile: event-consumer
    size: small
    environments: [int, prod]
  
  - name: db-migration
    profile: batch-job
    size: large
    environments: [int, pre, prod]
  
  - name: daily-cleanup
    profile: scheduled-task
    size: medium
    environments: [prod]
    schedule: "0 2 * * *"  # 2 AM daily
```

---

## 5. Enhanced Generation Script

### generate-kz-v3.sh (Simplified Input)

**New Features**:
1. Read profiles from `profiles.yaml`
2. Read sizes from `sizes.yaml`
3. Expand service definition with defaults
4. Validate against schema

**Usage**:
```bash
./scripts/generate-kz-v3.sh account-service int-stable euw1

# Script does:
# 1. Load service from services-simple.yaml
# 2. Load profile definition (public-api)
# 3. Load size definition (medium)
# 4. Merge: service + profile + size
# 5. Generate full kustomization
```

**Expanded Configuration (Internal)**:
```yaml
# Script expands simple definition to full config
# Then uses existing generation logic

expanded_service:
  name: account-service
  archetype: api                    # From profile
  image: gcr.io/project/account-service
  features:                         # From profile
    - ingress
    - retry
    - circuit-breaker
    - mtls
    - pdb
  resources:                        # From size
    cpu: 250m
    memory: 512Mi
  scaling:                          # From size
    min: 2
    max: 6
```

---

## 6. UI Design Concept

### Self-Service Portal: "Deploy a Service"

#### Step 1: Basic Information

```
┌─────────────────────────────────────────────────┐
│  Deploy New Service                             │
├─────────────────────────────────────────────────┤
│                                                  │
│  Service Name: [account-service____________]    │
│                                                  │
│  Image Repository (optional):                   │
│  [gcr.io/project/account-service_________]      │
│  ℹ Default: gcr.io/project/{service-name}      │
│                                                  │
│  What type of service is this?                  │
│  ○ Public API (REST/gRPC)                       │
│  ○ Internal API                                 │
│  ○ Event Consumer (Kafka/PubSub)                │
│  ○ WebSocket/Streaming Server                   │
│  ○ Scheduled Job (CronJob)                      │
│  ○ Batch Job                                    │
│                                                  │
│        [Next] [Cancel]                          │
└─────────────────────────────────────────────────┘
```

#### Step 2: Resource & Scaling

```
┌─────────────────────────────────────────────────┐
│  Configure Resources                            │
├─────────────────────────────────────────────────┤
│                                                  │
│  How much resources does this service need?     │
│                                                  │
│  ○ Small     (100m CPU, 256Mi RAM) - Low        │
│  ● Medium    (250m CPU, 512Mi RAM) - Standard   │
│  ○ Large     (500m CPU, 1Gi RAM)   - High       │
│  ○ X-Large   (1000m CPU, 2Gi RAM)  - Very High  │
│                                                  │
│  ℹ Selected: Medium                             │
│    • 2-6 replicas (auto-scaling)                │
│    • CPU target: 75%                            │
│                                                  │
│  ☑ Different size for production                │
│    Production: [Large ▼]                        │
│                                                  │
│        [Back] [Next] [Cancel]                   │
└─────────────────────────────────────────────────┘
```

#### Step 3: Environments & Features

```
┌─────────────────────────────────────────────────┐
│  Select Environments & Features                 │
├─────────────────────────────────────────────────┤
│                                                  │
│  Deploy to which environments?                  │
│  ☑ Integration (int-stable)                     │
│  ☑ Pre-Production (pre-stable)                  │
│  ☑ Production (prod)                            │
│                                                  │
│  Deploy to which regions?                       │
│  ☑ EU West 1 (euw1) - Primary                   │
│  ☑ EU West 2 (euw2) - DR                        │
│                                                  │
│  Additional Features (auto-selected for         │
│  Public API):                                   │
│  ☑ External Ingress                             │
│  ☑ Retry Policies                               │
│  ☑ Circuit Breaker                              │
│  ☑ Mutual TLS                                   │
│  ☑ High Availability (PDB)                      │
│  ☐ Advanced Monitoring                          │
│                                                  │
│        [Back] [Next] [Cancel]                   │
└─────────────────────────────────────────────────┘
```

#### Step 4: Review & Deploy

```
┌─────────────────────────────────────────────────┐
│  Review Configuration                           │
├─────────────────────────────────────────────────┤
│                                                  │
│  Service Name:    account-service               │
│  Profile:         Public API                    │
│  Archetype:       api                           │
│  Size:            Medium                        │
│  Environments:    int, pre, prod                │
│  Regions:         euw1, euw2                    │
│                                                  │
│  Resources:                                     │
│    • Int/Pre: 250m CPU, 512Mi RAM              │
│    • Prod:    500m CPU, 1Gi RAM (Large)        │
│                                                  │
│  Scaling:                                       │
│    • 2-6 replicas (auto)                        │
│    • CPU target: 75%                            │
│                                                  │
│  Features:                                      │
│    ✓ Ingress  ✓ Retry  ✓ Circuit Breaker       │
│    ✓ mTLS     ✓ PDB    ✓ Security Hardening    │
│                                                  │
│  Generated YAML: [View] [Download]              │
│                                                  │
│  ☐ Create Pull Request (recommended)            │
│  ☑ Deploy immediately to int-stable             │
│                                                  │
│        [Back] [Deploy] [Cancel]                 │
└─────────────────────────────────────────────────┘
```

### UI Backend Actions

When user clicks **Deploy**:

1. **Generate Service Definition**
   ```yaml
   # POST /api/services
   {
     "name": "account-service",
     "profile": "public-api",
     "size": "medium",
     "environments": ["int", "pre", "prod"],
     "resources": {
       "overrides": {
         "prod": { "size": "large" }
       }
     }
   }
   ```

2. **Update Catalog**
   - Add entry to `services-simple.yaml`
   - Validate against schema
   - Create git branch

3. **Trigger Pipeline**
   - Run validation
   - Generate kustomizations for all envs
   - Build manifests
   - Deploy to int-stable (if selected)
   - Create PR for review

---

## 7. Pipeline Integration

### GitOps Workflow

```
┌─────────────────────────────────────────────────┐
│  Developer adds service via UI                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Backend API updates services-simple.yaml        │
│  • Validate input                                │
│  • Expand with profiles/sizes                    │
│  • Create git branch: add-account-service        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  CI Pipeline Triggered                           │
│  1. Validate YAML schema                         │
│  2. Run generate-kz-v3.sh for all envs           │
│  3. Build manifests with kustomize               │
│  4. Validate with kubeconform                    │
│  5. Run OPA policy checks                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Auto-Deploy to Int-Stable (if selected)         │
│  • Apply manifests to int-stable cluster         │
│  • Monitor rollout                               │
│  • Report status back to UI                      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Create Pull Request                             │
│  • PR Description with config summary            │
│  • Request review from platform team             │
│  • Auto-approve if validation passes             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Merge to Main → Deploy to Pre/Prod              │
│  • ArgoCD/Flux syncs changes                     │
│  • Progressive rollout (pre → prod)              │
└─────────────────────────────────────────────────┘
```

### Pipeline Configuration

```yaml
# .github/workflows/service-onboarding.yml
name: Service Onboarding

on:
  push:
    paths:
      - 'kustomize/catalog/services-simple.yaml'

jobs:
  validate-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Validate Schema
        run: |
          yq eval -o=json catalog/services-simple.yaml | \
          ajv validate -s catalog/service-schema.json
      
      - name: Expand Services
        run: |
          ./scripts/expand-services.sh  # Merges profiles + sizes
      
      - name: Generate Manifests
        run: |
          for service in $(yq eval '.services[].name' catalog/services-simple.yaml); do
            for env in int-stable pre-stable prod; do
              for region in euw1 euw2; do
                ./scripts/generate-kz-v3.sh $service $env $region
              done
            done
          done
      
      - name: Validate Manifests
        run: |
          find tmp -name "*.yaml" -exec kubeconform --strict {} \;
      
      - name: OPA Policy Check
        run: |
          opa test policies/ --bundle tmp/
      
      - name: Deploy to Int-Stable
        if: contains(github.event.head_commit.message, '[deploy-int]')
        run: |
          kubectl apply -k tmp/*/int-stable/euw1/
      
      - name: Create Deployment Summary
        run: |
          ./scripts/create-summary.sh > $GITHUB_STEP_SUMMARY
```

---

## 8. Validation & Schema

### JSON Schema for Simple Catalog

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["services"],
  "properties": {
    "services": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "profile", "size", "environments"],
        "properties": {
          "name": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9-]*$",
            "description": "Service name (lowercase, hyphens)"
          },
          "profile": {
            "type": "string",
            "enum": [
              "public-api",
              "internal-api",
              "event-consumer",
              "websocket-server",
              "batch-job",
              "scheduled-task"
            ],
            "description": "Behavior profile"
          },
          "size": {
            "type": "string",
            "enum": ["small", "medium", "large", "xlarge", "xxlarge"],
            "description": "Resource size"
          },
          "environments": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["int", "pre", "prod"]
            },
            "minItems": 1,
            "description": "Environments to deploy to"
          },
          "image": {
            "type": "string",
            "description": "Container image (optional)"
          },
          "regions": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["euw1", "euw2"]
            },
            "description": "Regions to deploy to (optional)"
          },
          "scaling": {
            "type": "object",
            "properties": {
              "profile": {
                "type": "string",
                "enum": ["low", "medium", "high", "burst"]
              },
              "min": { "type": "integer", "minimum": 1 },
              "max": { "type": "integer", "minimum": 1 }
            }
          }
        }
      }
    }
  }
}
```

---

## 9. Migration Path

### Phase 1: Introduce Profiles & Sizes (Week 1)

1. Create `profiles.yaml`
2. Create `sizes.yaml`
3. Keep existing `services.yaml` working
4. Add expansion script

### Phase 2: Simplified Catalog (Week 2)

1. Create `services-simple.yaml`
2. Update `generate-kz-v3.sh` to read both formats
3. Migrate 5 pilot services to simple format
4. Validate equivalence

### Phase 3: UI Development (Week 3-4)

1. Build UI mockups
2. Implement backend API
3. Add schema validation
4. Connect to pipeline

### Phase 4: Full Migration (Week 5-6)

1. Migrate all services to simple format
2. Deprecate old `services.yaml`
3. Enable self-service for developers
4. Monitor and iterate

---

## 10. Benefits

### For Developers

✅ **5 fields to deploy a service** (vs 50+ fields before)
✅ **No Kubernetes expertise needed**
✅ **Self-service** (no platform team bottleneck)
✅ **Preview changes** before applying
✅ **Fast onboarding** (minutes, not days)

### For Platform Team

✅ **Enforce standards** (via profiles)
✅ **Reduce support burden** (self-service)
✅ **Easy to add new profiles** (one file change)
✅ **Consistent deployments** (no ad-hoc configs)
✅ **Auditable** (all changes in git)

### For Organization

✅ **Faster time to market** (deploy services quickly)
✅ **Cost optimization** (right-sized resources)
✅ **Better security** (hardened defaults)
✅ **Improved reliability** (battle-tested profiles)

---

## Summary

### Before (Complex)

```yaml
services:
  - name: account-service
    type: api
    image: gcr.io/project/account-service
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    namespaceTemplate: "{env}-{service}-{region}-stable"
    components: [ingress, retry, circuit-breaker, mtls, hpa, pdb, security-hardening, network-policy]
    hpa:
      enabled: true
      minReplicas: { defaults: 2, overrides: { prod: 4 } }
      maxReplicas: { defaults: 6, overrides: { prod: 10 } }
      metrics: [ ... ]
    resources:
      defaults: { cpu: "250m", memory: "512Mi" }
      overrides: { prod: { cpu: "500m", memory: "1Gi" } }
    retry: { ... }
    trafficPolicy: { ... }
    # 50+ lines of configuration
```

### After (Simple)

```yaml
services:
  - name: account-service
    profile: public-api
    size: medium
    environments: [int, pre, prod]
    resources:
      overrides:
        prod:
          size: large
    # 5 lines - same result!
```

### UI-Generated (Future)

```
Click → Click → Click → Deploy
```

**Developers spend time building features, not wrestling with YAML.**
