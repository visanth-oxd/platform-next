# Cost Metadata Abstraction & Complete Deployment Pipeline

**Status**: DESIGN PROPOSAL - 2025-11-15

**Purpose**: Document how cost metadata is abstracted, structured, and flows through the entire onboarding and deployment pipeline.

---

## Executive Summary

Currently, cost configuration is embedded directly in `services.yaml`. This document proposes a **modular abstraction strategy** where:

1. **Service definitions** (name, archetype, profile, size) stay in `services.yaml`
2. **Cost metadata** (budgets, alerts, cost centers) are abstracted into separate, reusable templates
3. **Cost allocation policies** are stored in a dedicated cost configuration repository
4. **Data flows** from abstracted cost config → Backstage → services.yaml → Manifests → Apptio

This approach enables:
- ✅ Different teams manage different concerns
- ✅ Cost changes without redefining services
- ✅ Reusable cost templates across services
- ✅ Separate RBAC for cost vs infrastructure changes
- ✅ Cleaner audit trail
- ✅ GitOps compliance for all components

---

## 1. Cost Metadata Abstraction Strategy

### Current State (Monolithic)

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-service
    archetype: api-service
    profile: standard
    size: medium
    cost:
      enabled: true
      owner: john.doe@company.com
      businessUnit: retail-banking
      costCenter:
        code: CC-12345
      budgets:
        int-stable:
          monthly: 800
        prod:
          monthly: 5000
      alerts:
        - name: cost-warning
          threshold: 80
          channels:
            teams: ["#team-payments"]
```

**Problems**:
- Cost config mixed with service definition
- No reuse across services
- Hard to audit cost changes
- Difficult to enforce cost policies
- Version changes require service re-definition

---

### Proposed State (Abstracted)

#### Structure: Cost Configuration Repository

```
platform-next/
├── kustomize/
│   └── catalog/
│       └── services.yaml          # Service definitions ONLY
│
cost-config-repository/            # NEW: Separate repo for cost data
├── templates/
│   ├── cost-profiles.yaml        # Reusable cost templates by team/size
│   ├── alert-policies.yaml       # Alert threshold policies
│   └── cost-center-mappings.yaml # Cost center definitions
├── services/
│   ├── payment-service.yaml      # Payment service cost config
│   ├── fraud-detection.yaml      # Fraud detection cost config
│   └── ...
├── policies/
│   ├── standard-budget-policy.yaml    # Default budgets by size
│   ├── alert-thresholds-policy.yaml  # Standard alert levels
│   └── cost-center-policy.yaml       # Cost center requirements
└── kustomize/
    └── overlays/
        └── cost-injection/       # Kustomize patches to inject cost
```

#### Option A: Separate Repository (Recommended for Large Organizations)

**Repository**: `platform-next-cost-config`

**Access Control**:
- Finance team: Can edit budgets, cost centers
- Platform team: Can edit cost templates, policies
- Service teams: Read-only access to their cost configs

**Advantages**:
- Complete separation of concerns
- Different release cadence for cost vs infrastructure
- Finance team can manage budgets independently
- RBAC enforcement via separate repo
- Cost audit trail separate from service changes

**Directory Structure**:

```
platform-next-cost-config/
├── README.md
├── GOVERNANCE.md                    # Cost governance policies
├── templates/
│   ├── cost-profiles.yaml          # Size-based cost templates
│   ├── alert-policies.yaml         # Alert routing templates
│   └── billing-policies.yaml       # Billing/chargeback policies
├── services/                        # Per-service cost config
│   ├── payment-service.yaml
│   ├── fraud-detection.yaml
│   ├── metrics-exporter.yaml
│   └── ...
├── policies/                        # Org-wide policies
│   ├── budget-ranges-by-size.yaml
│   ├── default-alerts.yaml
│   ├── cost-center-mappings.yaml
│   └── team-budgets.yaml
├── kustomize/                       # Kustomize tooling
│   ├── patches/
│   │   └── cost-labels-patch.yaml
│   └── overlays/
│       ├── dev/
│       └── prod/
└── scripts/
    ├── validate-cost-config.py
    ├── generate-cost-labels.py
    └── sync-to-apptio.py
```

#### Option B: Same Repository (Recommended for Smaller Organizations)

**Location**: `platform-next/cost-config/`

**Advantages**:
- Simpler setup, single repo to manage
- Services and costs together conceptually
- Easier for teams to navigate
- Single deployment pipeline

**Directory Structure**:

```
platform-next/
├── kustomize/
│   ├── catalog/
│   │   └── services.yaml
│   ├── cost/
│   │   ├── templates/
│   │   │   ├── cost-profiles.yaml
│   │   │   ├── alert-policies.yaml
│   │   │   └── billing-policies.yaml
│   │   └── services/
│   │       ├── payment-service.yaml
│   │       ├── fraud-detection.yaml
│   │       └── ...
│   └── ...
```

---

## 2. Cost Metadata Files Structure

### 2.1 Services Catalog (Unchanged - Service Definitions Only)

```yaml
# kustomize/catalog/services.yaml
# Contains: name, archetype, profile, size, team, environments
# Does NOT contain: cost data

apiVersion: platform.internal/v1
kind: ServiceCatalog
metadata:
  name: platform-services
spec:
  services:
  
  - name: payment-service
    archetype: api-service
    profile: standard
    size: large
    team: payments-team
    environments: [int-stable, pre-stable, prod]
    description: "Core payment processing service"
    
    # Reference to cost config (instead of embedding)
    costConfigRef:
      name: payment-service-cost
      namespace: cost-config-repo
    
    # Profile defaults (influences resource requests)
    profileDefaults:
      replicas:
        int-stable: 2
        pre-stable: 4
        prod: 8
      resources:
        requests:
          cpu: "2"      # Profile + Size determines these
          memory: "2Gi"
        limits:
          cpu: "4"
          memory: "4Gi"
```

**Key Change**: `costConfigRef` points to external cost configuration instead of embedding it.

---

### 2.2 Cost Profiles Template

```yaml
# cost-config/templates/cost-profiles.yaml
# Reusable cost estimation templates by service size and profile

apiVersion: cost.platform.internal/v1
kind: CostProfileTemplate
metadata:
  name: cost-profiles
spec:
  profiles:
    # Profile: Standard API
    - name: standard-api
      description: "Standard REST API service"
      appliesTo:
        archetype: [api-service, api]
        profile: standard
      
      # Size-based cost estimation
      costBySize:
        small:
          estimatedMonthly: 150
          baselineResources:
            cpu: 0.5
            memory: 512Mi
          replicas:
            int-stable: 1
            pre-stable: 2
            prod: 3
        
        medium:
          estimatedMonthly: 400
          baselineResources:
            cpu: 1.0
            memory: 1Gi
          replicas:
            int-stable: 2
            pre-stable: 3
            prod: 5
        
        large:
          estimatedMonthly: 1000
          baselineResources:
            cpu: 2.0
            memory: 2Gi
          replicas:
            int-stable: 2
            pre-stable: 4
            prod: 8
        
        xlarge:
          estimatedMonthly: 2500
          baselineResources:
            cpu: 4.0
            memory: 4Gi
          replicas:
            int-stable: 3
            pre-stable: 5
            prod: 10
    
    # Profile: Background Worker
    - name: background-worker
      description: "Batch processing / background jobs"
      appliesTo:
        archetype: [worker, batch]
        profile: worker
      
      costBySize:
        small:
          estimatedMonthly: 80
          baselineResources:
            cpu: 0.25
            memory: 256Mi
        # ... more sizes
    
    # Profile: Stateful Service
    - name: stateful-service
      description: "Services requiring persistent state"
      appliesTo:
        archetype: [stateful]
        profile: stateful
      
      costBySize:
        medium:
          estimatedMonthly: 600    # Higher due to storage
          baselineResources:
            cpu: 1.0
            memory: 2Gi
          storage: 10Gi           # PVC required
        # ... more sizes
```

**Usage**: Backstage references this template to show cost estimates during onboarding.

---

### 2.3 Alert Policies Template

```yaml
# cost-config/templates/alert-policies.yaml
# Reusable alert and notification policies

apiVersion: cost.platform.internal/v1
kind: AlertPolicyTemplate
metadata:
  name: alert-policies
spec:
  policies:
    
    # Policy: Standard Cost Alerts
    - name: standard-alerts
      description: "Default alert thresholds for most services"
      alertLevels:
        - name: info-threshold
          percentage: 50
          severity: info
          frequency: once
          defaultChannels:
            - teams: ["#team-{team-name}"]
        
        - name: warning-threshold
          percentage: 80
          severity: warning
          frequency: daily
          defaultChannels:
            - teams: ["#team-{team-name}", "#platform-finops"]
            - email: ["{cost-owner}@company.com"]
        
        - name: critical-threshold
          percentage: 100
          severity: critical
          frequency: immediate
          defaultChannels:
            - teams: ["#team-{team-name}", "#platform-leadership"]
            - email: ["{cost-owner}@company.com", "cto@company.com"]
            - pagerduty: true
    
    # Policy: Tight Controls (Critical Services)
    - name: tight-controls
      description: "For production-critical services"
      alertLevels:
        - name: early-warning
          percentage: 70
          severity: warning
          frequency: daily
          defaultChannels:
            - teams: ["#platform-leadership"]
            - email: ["cfo@company.com"]
        
        - name: hard-limit
          percentage: 90
          severity: critical
          frequency: immediate
          defaultChannels:
            - teams: ["#platform-leadership"]
            - email: ["cfo@company.com"]
            - pagerduty: true
            - action: "block-deployment"  # Prevent new deploys
    
    # Policy: Relaxed Alerts (Dev/Test)
    - name: relaxed-alerts
      description: "For dev/test environments only"
      alertLevels:
        - name: warning
          percentage: 150  # Very high threshold
          severity: warning
          frequency: weekly
          defaultChannels:
            - teams: ["#team-{team-name}"]
```

**Usage**: Services reference which alert policy applies to them.

---

### 2.4 Per-Service Cost Configuration

```yaml
# cost-config/services/payment-service.yaml
# Cost details for a specific service

apiVersion: cost.platform.internal/v1
kind: ServiceCostConfig
metadata:
  name: payment-service-cost
  labels:
    service: payment-service
    team: payments-team
spec:
  
  # Link to service definition
  serviceRef:
    name: payment-service
    catalog: platform-next/kustomize/catalog/services.yaml
  
  # Cost allocation
  costAllocation:
    owner: john.doe@company.com
    team: payments-team
    businessUnit: retail-banking
    costCenter:
      code: CC-12345
      name: "Retail Banking Cost Center"
  
  # Budget override: Can override per-environment budgets
  budgetOverrides:
    # Use cost profile defaults + apply overrides
    baseProfile: standard-api
    size: large
    
    # Override specific environment budgets
    environments:
      int-stable:
        monthly: 800
        currency: USD
        rationale: "Minimal testing, 2 replicas"
      
      pre-stable:
        monthly: 2000
        currency: USD
        rationale: "Mirror prod setup, 4 replicas"
      
      prod:
        monthly: 5000
        currency: USD
        rationale: "Production workload, HA setup, multi-region"
  
  # Alert policy selection
  alertPolicy: standard-alerts
  
  # Override alert channels if needed
  alertChannelOverrides:
    critical-threshold:
      teams: ["#team-payments", "#platform-leadership", "#finance-ops"]
      email: ["john.doe@company.com", "payments-lead@company.com", "cto@company.com"]
      pagerduty: true
  
  # Cost optimization settings
  optimization:
    rightSizing:
      enabled: true
      thresholdUtilization: 40  # Flag if CPU/mem < 40%
    
    autoScaling:
      enabled: true
      minReplicas: 2
      maxReplicas: 20
    
    spotInstances:
      allowed: false  # Production critical, don't use spot
    
    commitmentDiscounts:
      enabled: true
      recommendedCommitment: 3-year
  
  # Tagging for cost analytics
  tags:
    product: "payment-processing"
    department: "engineering"
    environment-specific: false
    compliance: ["PCI-DSS"]  # Affects placement/region costs
  
  # Chargeback model
  chargebackModel: direct
  # Options: direct (charge this cost center), shared (split across multiple), overhead (platform overhead)
```

---

### 2.5 Cost Center Mappings

```yaml
# cost-config/policies/cost-center-mappings.yaml
# Organization-wide cost center definitions

apiVersion: cost.platform.internal/v1
kind: CostCenterMapping
metadata:
  name: cost-center-mappings
spec:
  costCenters:
    
    - code: CC-10001
      name: "Finance Department"
      description: "Finance systems and tools"
      owner: finance-director@company.com
      budgetApprover: cfo@company.com
      services:
        - payment-service
        - settlement-service
    
    - code: CC-20001
      name: "Retail Banking"
      description: "Retail banking platform"
      owner: retail-banking-director@company.com
      budgetApprover: cfo@company.com
      services:
        - account-service
        - lending-service
    
    - code: CC-30001
      name: "Platform Engineering"
      description: "Platform and infrastructure services"
      owner: vp-engineering@company.com
      budgetApprover: vp-engineering@company.com
      services:
        - metrics-exporter
        - log-aggregator
        - api-gateway
    
    - code: CC-40001
      name: "Operations"
      description: "Operations and compliance"
      owner: ops-director@company.com
      budgetApprover: cfo@company.com
      services:
        - audit-logger
        - compliance-reporter
  
  # Validation rules
  validationRules:
    - code must match pattern: CC-XXXXX
    - code must exist in Apptio before use
    - owner must be valid directory user
    - services list must reference valid services in catalog
```

---

### 2.6 Budget Policy Template

```yaml
# cost-config/policies/standard-budget-policy.yaml
# Organization-wide budget guidelines

apiVersion: cost.platform.internal/v1
kind: BudgetPolicy
metadata:
  name: standard-budget-policy
spec:
  
  # Budget ranges by service size
  budgetRanges:
    small:
      minMonthly: 50
      maxMonthly: 500
      recommendedBuffer: 25%  # 25% higher than estimated
    
    medium:
      minMonthly: 200
      maxMonthly: 2000
      recommendedBuffer: 25%
    
    large:
      minMonthly: 500
      maxMonthly: 10000
      recommendedBuffer: 30%  # Larger buffer for larger services
    
    xlarge:
      minMonthly: 2000
      maxMonthly: 50000
      recommendedBuffer: 30%
  
  # Environment-based multipliers
  environmentMultipliers:
    int-stable:
      percentOfProduction: 10
      minBudget: 50
    
    pre-stable:
      percentOfProduction: 30
      minBudget: 100
    
    prod:
      percentOfProduction: 100
      minBudget: 200  # Production minimum
  
  # Escalation rules
  escalationRules:
    budgetApprovalRequired:
      - amount > 10000  # Need VP approval for >$10K/month
      - exceeds profile estimate by more than 50%
    
    budgetVetoRequired:
      - amount > 30000  # Need CFO approval for >$30K/month
      - violates cost center budget
  
  # Policy enforcement
  enforcement:
    blockOnboarding: true  # Block if budget outside ranges
    requireApproval: true
    allowException: true   # Exceptions require VP sign-off
```

---

## 3. Data Flow: From Abstraction to Manifests

### 3.1 Complete Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     ONBOARDING PHASE                              │
└────────────────────────────────────────────────────────────────────┘

Developer fills Backstage form
├─ Service name, archetype, profile, size
└─ Backstage queries:
    ├─ services.yaml → Profile defaults
    ├─ cost-profiles.yaml → Cost estimate
    ├─ alert-policies.yaml → Default alerts
    └─ cost-center-mappings.yaml → Available cost centers
        ↓
    Form shows:
    • Estimated monthly cost (from profile)
    • Default budget recommendation (estimate + buffer)
    • Available cost centers
    • Default alert channels


┌────────────────────────────────────────────────────────────────────┐
│                     CATALOG UPDATE PHASE                          │
└────────────────────────────────────────────────────────────────────┘

Developer confirms and submits
├─ Create PR: services.yaml
│   (Service definition: name, archetype, profile, size, team)
│
├─ Create PR: cost-config/{service}.yaml
│   (Cost details: budgets, alerts, cost center, owner)
│
└─ Both PRs trigger CI/CD


┌────────────────────────────────────────────────────────────────────┐
│                   VALIDATION PHASE (CI/CD)                        │
└────────────────────────────────────────────────────────────────────┘

GitHub Actions CI validates:

For services.yaml:
├─ Service definition schema
├─ Valid archetype, profile, size
├─ Team exists in directory
└─ costConfigRef points to valid cost config

For cost-config/{service}.yaml:
├─ Service exists in services.yaml
├─ Cost center exists in mappings
├─ Budget within policy ranges
├─ Alert policy exists and valid
├─ Owner email valid
├─ All required fields present
└─ Compliance checks (PCI, SOC2, etc.)


┌────────────────────────────────────────────────────────────────────┐
│               MANIFEST GENERATION PHASE (CI/CD)                    │
└────────────────────────────────────────────────────────────────────┘

Script: generate-kz-v3.sh
├─ Read: services.yaml (Service definition)
├─ Read: cost-config/{service}.yaml (Cost details)
├─ Read: cost-profiles.yaml (Profile defaults)
├─ Merge:
│   ├─ Profile resources (CPU, memory) → kustomization.yaml
│   ├─ Cost labels (team, cost center, owner) → commonLabels
│   ├─ Size-based replicas → replica counts
│   └─ Profile settings → configuration overrides
│
├─ Inject Kustomize patches:
│   ├─ commonLabels with cost.* labels
│   ├─ Replica counts from profile
│   └─ Resource requests/limits from size
│
├─ Build manifests:
│   └─ kubectl build kustomize/overlays/{service}/{env}/{region}/
│       (This generates final K8s manifests with all labels)
│
└─ Validate:
    └─ All cost.* labels present in manifests


┌────────────────────────────────────────────────────────────────────┐
│                   APPTIO SYNC PHASE (CI/CD)                        │
└────────────────────────────────────────────────────────────────────┘

Trigger: cost-config/{service}.yaml merged to main

Apptio Sync Service (Cloud Function or K8s Service):
├─ Read: cost-config/{service}.yaml
├─ Create/Update budgets in Apptio:
│   ├─ Budget name: {service}-{environment}
│   ├─ Amount: {budgets.environments[env].monthly}
│   ├─ Filters: cost.service = {service}
│   └─ Owner: {costAllocation.owner}
│
├─ Configure alerts in Apptio:
│   ├─ Apply alert policy
│   ├─ Set thresholds
│   └─ Configure channels
│
└─ Result: Budgets + Alerts ready in Apptio


┌────────────────────────────────────────────────────────────────────┐
│                  DEPLOYMENT PHASE (Harness)                       │
└────────────────────────────────────────────────────────────────────┘

Developer triggers deployment in Harness
├─ Select service, environment, region
├─ Harness fetches manifests from Git
│   (Manifests already have cost.* labels from generation phase)
│
├─ Deploy to Kubernetes cluster
│   └─ Pods get cost labels from manifests
│
└─ Labels flow to:
    ├─ GCP Billing (24 hours)
    ├─ Apptio (48 hours)
    └─ Cost tracking dashboards


┌────────────────────────────────────────────────────────────────────┐
│                    COST TRACKING PHASE                            │
└────────────────────────────────────────────────────────────────────┘

Daily/Weekly:
├─ Costs appear in Apptio dashboard
├─ Alerts fire when thresholds exceeded
├─ Cost reports by team/cost-center/service
└─ Optimization recommendations generated
```

---

## 4. Mapping: Catalog → Kustomize → Manifests

### 4.1 Complete Example: Payment Service

#### Step 1: Services Catalog Entry

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-service
    archetype: api-service
    profile: standard
    size: large
    team: payments-team
    environments: [int-stable, pre-stable, prod]
    
    costConfigRef:
      name: payment-service-cost
      namespace: cost-config/services/
```

#### Step 2: Cost Config Entry

```yaml
# cost-config/services/payment-service.yaml
apiVersion: cost.platform.internal/v1
kind: ServiceCostConfig
metadata:
  name: payment-service-cost
spec:
  serviceRef:
    name: payment-service
  
  costAllocation:
    owner: john.doe@company.com
    team: payments-team
    businessUnit: retail-banking
    costCenter:
      code: CC-12345
  
  budgetOverrides:
    baseProfile: standard-api
    size: large
    environments:
      int-stable:
        monthly: 800
      pre-stable:
        monthly: 2000
      prod:
        monthly: 5000
  
  alertPolicy: standard-alerts
  
  optimization:
    rightSizing:
      enabled: true
    autoScaling:
      enabled: true
    spotInstances:
      allowed: false
```

#### Step 3: Cost Profile Used

```yaml
# cost-config/templates/cost-profiles.yaml (excerpt)
- name: standard-api
  appliesTo:
    archetype: api-service
    profile: standard
  costBySize:
    large:
      estimatedMonthly: 1000
      baselineResources:
        cpu: 2.0
        memory: 2Gi
      replicas:
        int-stable: 2
        pre-stable: 4
        prod: 8
```

#### Step 4: Manifest Generation Script

```bash
#!/bin/bash
# scripts/generate-kz-v3.sh

SERVICE_NAME="payment-service"
ENVIRONMENT="prod"
REGION="euw1"

# Load service definition
SERVICE_DEF=$(yq ".services[] | select(.name==\"$SERVICE_NAME\")" kustomize/catalog/services.yaml)

# Load cost config
COST_CONFIG=$(yq . "cost-config/services/${SERVICE_NAME}.yaml")

# Load cost profile
PROFILE=$(yq ".profiles[] | select(.name==\"standard-api\")" cost-config/templates/cost-profiles.yaml)

# Extract values
COST_CENTER=$(echo "$COST_CONFIG" | yq '.spec.costAllocation.costCenter.code')
COST_OWNER=$(echo "$COST_CONFIG" | yq '.spec.costAllocation.owner')
BUSINESS_UNIT=$(echo "$COST_CONFIG" | yq '.spec.costAllocation.businessUnit')
TEAM=$(echo "$SERVICE_DEF" | yq '.team')
BUDGET=$(echo "$COST_CONFIG" | yq ".spec.budgetOverrides.environments.${ENVIRONMENT}.monthly")

# Extract profile defaults for this size
REPLICAS=$(echo "$PROFILE" | yq ".costBySize.large.replicas.${ENVIRONMENT}")
CPU=$(echo "$PROFILE" | yq ".costBySize.large.baselineResources.cpu")
MEMORY=$(echo "$PROFILE" | yq ".costBySize.large.baselineResources.memory")

# Generate Kustomize patch with cost labels
cat > "kustomize/components/cost-labels/${SERVICE_NAME}-cost-labels.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

commonLabels:
  cost.service: $SERVICE_NAME
  cost.team: $TEAM
  cost.environment: $ENVIRONMENT
  cost.costCenter: $COST_CENTER
  cost.businessUnit: $BUSINESS_UNIT
  cost.owner: $COST_OWNER
  cost.budget: "$BUDGET"

replicas:
  - name: $SERVICE_NAME
    count: $REPLICAS

patchesStrategicMerge:
  - |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: $SERVICE_NAME
    spec:
      template:
        spec:
          containers:
          - name: $SERVICE_NAME
            resources:
              requests:
                cpu: $CPU
                memory: $MEMORY
              limits:
                cpu: $(echo "$CPU * 2" | bc)
                memory: $(echo "$MEMORY" | sed 's/Mi/Gi/g')
EOF

# Build final manifests
kustomize build \
  --enable-alpha-plugins \
  "kustomize/overlays/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}" \
  -o "manifests/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}/generated.yaml"

# Validate cost labels
echo "Checking cost labels in generated manifests..."
grep -E "cost\.(service|team|costCenter|owner)" \
  "manifests/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}/generated.yaml" \
  | head -10
```

#### Step 5: Generated Manifest

```yaml
# manifests/payment-service/prod/euw1/generated.yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  labels:
    app: payment-service
    # INJECTED COST LABELS from cost-config
    cost.service: payment-service
    cost.team: payments-team
    cost.environment: prod
    cost.costCenter: CC-12345
    cost.businessUnit: retail-banking
    cost.owner: john.doe@company.com
    cost.budget: "5000"
spec:
  replicas: 8  # From cost profile (large, prod = 8)
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
        # Labels inherited by pods
        cost.service: payment-service
        cost.team: payments-team
        cost.costCenter: CC-12345
        # ... all other cost labels
    spec:
      containers:
      - name: payment-service
        image: payment-service:latest
        resources:
          # From cost profile (large size)
          requests:
            cpu: "2"      # standard-api large profile
            memory: "2Gi"
          limits:
            cpu: "4"
            memory: "4Gi"
```

#### Step 6: Apptio Creation

```yaml
# Apptio Sync creates:
- Service: payment-service
  Environment: prod
  CostCenter: CC-12345
  BusinessUnit: retail-banking
  Owner: john.doe@company.com
  Budget: $5000/month
  Alerts:
    - 50%:  $2500 → #team-payments (info, once)
    - 80%:  $4000 → #team-payments, #platform-finops (daily)
    - 100%: $5000 → #team-payments, #leadership (immediate, PagerDuty)
```

---

## 5. How Profiles, Sizes & Cost Interact

### 5.1 The Three-Dimensional Model

```
┌─────────────────────────────────────────────────────────┐
│  ARCHETYPE × PROFILE × SIZE = RESOURCE + COST          │
└─────────────────────────────────────────────────────────┘

ARCHETYPE (What type of service?)
├─ api-service      → Needs ingress, horizontal scaling
├─ worker           → Batch processing, fewer resources
├─ stateful         → Needs storage, persistent state
└─ tool             → Utility services, minimal resources

      ↓ Combined with

PROFILE (How is it deployed?)
├─ standard         → Standard containerized workload
├─ stateful         → With persistent volumes
├─ high-performance → GPU, special hardware
└─ cost-optimized   → Spot instances, lower SLA

      ↓ Combined with

SIZE (How big is the workload?)
├─ small            → Minimal: 0.5 CPU, 512Mi RAM
├─ medium           → Standard: 1 CPU, 1Gi RAM
├─ large            → Heavy: 2 CPU, 2Gi RAM
└─ xlarge           → Very Heavy: 4 CPU, 4Gi RAM

      ↓ Results in

RESOURCE ALLOCATION (from cost profiles)
├─ Container requests (CPU, Memory)
├─ Replica counts (per environment)
├─ Storage size (if stateful)
└─ Special features (autoscaling, spot instances)

      ↓ Which creates

MONTHLY COST (estimated)
└─ Calculated from resources × cloud pricing
```

### 5.2 Complete Decision Tree

```
Service: payment-service
│
├─ Archetype: api-service
│   └─ Implies: REST endpoint, horizontal scaling, ingress
│
├─ Profile: standard
│   └─ Implies: Standard K8s deployment, no special features
│
└─ Size: large
    ├─ Baseline: 2 CPU, 2Gi RAM
    ├─ Cost profile: standard-api → large
    ├─ Est. monthly: $1000
    │
    └─ Environment-specific from cost profile:
        ├─ int-stable: 2 replicas → ~$100/month
        ├─ pre-stable: 4 replicas → ~$250/month
        └─ prod: 8 replicas → ~$500/month
            (These become reference values)
            ↓
        Cost config overrides:
        ├─ int-stable: budgeted $800 (with buffer)
        ├─ pre-stable: budgeted $2000 (with buffer)
        └─ prod: budgeted $5000 (with buffer)
```

---

## 6. Complete Onboarding Data Flow

### 6.1 End-to-End Example

#### Stage 1: Backstage Form

```
User fills form:
├─ Service Name: "payment-service"
├─ Archetype: "api-service" → Backstage queries profiles
├─ Profile: "standard" → Backstage queries cost-profiles.yaml
├─ Size: "large" → Gets estimated cost from profile
│   Display shows: "Estimated: $800-1500/month per environment"
│
└─ Backstage queries:
    ├─ cost-center-mappings.yaml → Shows available cost centers
    ├─ alert-policies.yaml → Shows alert policy options
    └─ budget-policy.yaml → Shows recommended budget ranges
        
        Based on all this:
        • Int budget recommendation: $800 (estimate + buffer)
        • Pre budget recommendation: $2000 (estimate + buffer + 25%)
        • Prod budget recommendation: $5000 (estimate + buffer + 30%)
```

#### Stage 2: PRs Created

```
PR #1: Add service to catalog
├─ File: kustomize/catalog/services.yaml
├─ Changes:
│   - name: payment-service
│     archetype: api-service
│     profile: standard
│     size: large
│     team: payments-team
│     costConfigRef:
│       name: payment-service-cost
│
└─ CI checks:
    ├─ Schema validation (service definition)
    ├─ Profile/size valid combination
    ├─ Team exists in directory
    └─ costConfigRef points to valid config

PR #2: Add cost config
├─ File: cost-config/services/payment-service.yaml
├─ Changes:
│   apiVersion: cost.platform.internal/v1
│   kind: ServiceCostConfig
│   spec:
│     costAllocation:
│       owner: john.doe@company.com
│       costCenter: CC-12345
│     budgetOverrides:
│       environments:
│         int-stable: 800
│         pre-stable: 2000
│         prod: 5000
│     alertPolicy: standard-alerts
│
└─ CI checks:
    ├─ Cost center exists (API call to Apptio)
    ├─ Budget within policy ranges
    ├─ Alert policy exists
    ├─ Owner email valid
    └─ Service exists in catalog
```

#### Stage 3: Merge & Generation

```
Both PRs approved and merged to main
│
├─ GitHub Actions triggered for kustomize/catalog/services.yaml
│   └─ Runs: generate-kz-v3.sh
│       ├─ Reads service definition
│       ├─ Loads cost config
│       ├─ Loads cost profile
│       ├─ Merges all data
│       ├─ Generates kustomization.yaml with:
│       │   ├─ cost.* labels
│       │   ├─ Replica counts from profile
│       │   ├─ Resource requests from size
│       │   └─ Environment overrides
│       └─ Builds manifests (kubectl kustomize build)
│
├─ GitHub Actions triggered for cost-config/services/payment-service.yaml
│   └─ Runs: sync-to-apptio.py
│       ├─ Reads cost config
│       ├─ Creates budgets in Apptio
│       ├─ Configures alert policy
│       └─ Updates cost-allocation mapping
│
└─ Result: Service ready for deployment
    ├─ Manifests in Git with cost labels ✓
    ├─ Budgets created in Apptio ✓
    ├─ Alerts configured ✓
    └─ Cost tracking ready ✓
```

---

## 7. Implementation Guide

### 7.1 Phase 1: Refactor (Weeks 1-2)

```bash
# Create cost-config directory structure
mkdir -p cost-config/{templates,services,policies}

# 1. Extract cost profiles
# Move cost estimation logic from Backstage to templates/cost-profiles.yaml
touch cost-config/templates/cost-profiles.yaml

# 2. Extract alert policies
# Move alert definitions from services.yaml to templates/alert-policies.yaml
touch cost-config/templates/alert-policies.yaml

# 3. Create cost center mappings
touch cost-config/policies/cost-center-mappings.yaml

# 4. Create budget policy
touch cost-config/policies/standard-budget-policy.yaml
```

### 7.2 Phase 2: Migration (Weeks 3-4)

```bash
# For each existing service:
# 1. Update services.yaml to remove cost config, add costConfigRef
# 2. Create corresponding cost-config/services/{service}.yaml
# 3. Update CI/CD to validate both files
```

### 7.3 Phase 3: Backstage Integration (Weeks 5-6)

```bash
# Update Backstage template to:
# 1. Query cost-profiles.yaml for estimates
# 2. Query cost-center-mappings.yaml for cost centers
# 3. Query budget-policy.yaml for ranges
# 4. Create separate PRs for catalog and cost-config
```

### 7.4 Phase 4: Manifest Generation (Weeks 7-8)

```bash
# Update generate-kz-v3.sh to:
# 1. Load cost-config/{service}.yaml
# 2. Load cost profile template
# 3. Merge profile + cost config
# 4. Inject all labels and settings
```

---

## 8. Recommended Approach: Which Option?

### Option A: Separate Repository (Recommended for large orgs)

```
Advantages:
✅ Finance team can manage budgets independently
✅ Different RBAC per repo
✅ Cost changes don't require service changes
✅ Easier cost auditing
✅ Clearer separation of concerns
✅ Can have different release cadence

Disadvantages:
❌ More repos to manage
❌ Slightly more complex setup
❌ Teams must understand both repos
```

**Use if**: Multiple teams managing cost, need strict RBAC, frequent cost changes, large organization

---

### Option B: Same Repository (Recommended for small/medium orgs)

```
Advantages:
✅ Single repo to manage
✅ Services and costs conceptually together
✅ Simpler onboarding process
✅ Easier to coordinate changes
✅ Single CI/CD pipeline

Disadvantages:
❌ Less separation of concerns
❌ Cost and service PRs must be coordinated
❌ Single RBAC policy for both
```

**Use if**: Single team managing platform, simpler structure, faster iteration, smaller organization

---

## 9. Benefits of Abstraction

| Aspect | Before | After |
|--------|--------|-------|
| **Cost Changes** | Require service re-onboarding | Update cost-config file only |
| **Reuse** | Copy/paste cost configs | Reference templates |
| **RBAC** | Single policy for all | Different teams, different policies |
| **Audit Trail** | Mixed with service changes | Dedicated cost change history |
| **Governance** | Embedded in manifests | Centralized policies |
| **Testing** | Hard to test cost logic | Easy to test cost templates |
| **Documentation** | In service definitions | In dedicated cost docs |
| **Cost Profile Updates** | Requires all services to change | Single template change |

---

## 10. Example: Updating Cost Without Changing Service

### Before (Monolithic)

```yaml
# Must edit services.yaml
services:
  - name: payment-service
    # ... service definition ...
    cost:
      budgets:
        prod: 5000  # Changed from 4000 to 5000
      # ... rest of cost config ...
```

**PR Impact**: Service definition change (even though only cost changed)

### After (Abstracted)

```yaml
# Only edit cost-config
# kustomize/catalog/services.yaml (unchanged)
services:
  - name: payment-service
    archetype: api-service
    # No cost details here anymore
    costConfigRef:
      name: payment-service-cost

# cost-config/services/payment-service.yaml (changed)
spec:
  budgetOverrides:
    environments:
      prod: 5000  # Changed from 4000 to 5000
```

**PR Impact**: Cost-only change (service definition untouched)

**Benefits**:
- Finance team can make changes without understanding service definition
- Service changes don't trigger cost validation
- Cleaner audit trail for cost changes

---

## 11. Summary

**Cost Metadata Abstraction Strategy**:

1. **Separation**: Service definitions and cost configs in separate files/repos
2. **Reusability**: Cost profiles and policies as templates
3. **Data Flow**: Abstracted configs → Backstage form → Manifests → Apptio
4. **Integration**: Kustomize merges profiles + cost configs + size settings
5. **Automation**: Scripts inject labels and settings from abstracted configs
6. **Governance**: Cost policies enforced in CI/CD, not embedded in services

**Result**: Cost management becomes a first-class, reusable, auditable system that scales with your organization.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: PROPOSAL - Ready for Implementation Review
