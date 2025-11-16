# End-to-End Service Lifecycle: Introduction to Deployment

**Status**: COMPREHENSIVE DESIGN - Complete Service Lifecycle

**Document Type**: Master Design Document

**Audience**: Platform engineers, developers, SRE teams, finance teams

**Date**: 2025-11-16

---

## Executive Summary

This document describes the **complete end-to-end journey** of a service from initial introduction through production deployment, with integrated cost and monitoring management. It serves as the master reference for understanding how all components work together.

**Key Principles**:
- ✅ **Self-Service**: Developers onboard services via Backstage (5 minutes)
- ✅ **Profile-Based**: Cost and monitoring via reusable profiles (DRY)
- ✅ **GitOps**: All configuration versioned in Git
- ✅ **Automated**: CI/CD handles validation, generation, deployment
- ✅ **Integrated**: Cost and monitoring from day 1, not bolted on

**Complete Flow**:
```
Developer → Backstage Form → Catalog Entry → CI/CD Validation → 
Profile Expansion → Manifest Generation → Git Commit → 
Apptio Sync → Harness Deployment → Production → Monitoring Active
```

---

## 1. Complete Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: Developer Interface (Backstage)                        │
├─────────────────────────────────────────────────────────────────┤
│ - Software Templates (service creation forms)                    │
│ - Service Catalog (discovery, status)                           │
│ - Cost & Monitoring configuration UI                           │
│ - Deployment triggers                                           │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: Configuration Repository (Platform-Next)               │
├─────────────────────────────────────────────────────────────────┤
│ - Service Catalog (services.yaml)                               │
│ - Cost Profiles (cost-profiles.yaml)                           │
│ - Monitoring Profiles (monitoring-profiles.yaml)                │
│ - Kustomize bases, overlays, components                         │
│ - Generated manifests (GitOps source of truth)                  │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: CI/CD Pipeline (GitHub Actions)                        │
├─────────────────────────────────────────────────────────────────┤
│ - Schema validation                                              │
│ - Profile expansion (cost + monitoring)                         │
│ - Manifest generation (Kustomize)                              │
│ - Cost center verification (Apptio API)                         │
│ - Commit to generated/ directory                                │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: Cost Management (Apptio Sync)                          │
├─────────────────────────────────────────────────────────────────┤
│ - Budget creation (per environment)                             │
│ - Alert rule configuration                                      │
│ - Notification channel setup                                    │
│ - Cost tracking activation                                      │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: Deployment Orchestration (Harness)                     │
├─────────────────────────────────────────────────────────────────┤
│ - Per-service pipelines                                         │
│ - Multi-cluster deployments                                     │
│ - Progressive delivery (canary)                                 │
│ - Approval gates                                                │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: Runtime (Kubernetes Clusters)                          │
├─────────────────────────────────────────────────────────────────┤
│ - Deployed services (with cost labels)                          │
│ - Prometheus (metrics collection)                                │
│ - Dynatrace (APM, distributed tracing)                         │
│ - Cost tracking (GCP billing + Apptio)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Service Lifecycle: Step-by-Step

### Phase 1: Service Introduction (Developer Onboarding)

#### Step 1.1: Developer Accesses Backstage

**Actor**: Developer (e.g., Alice from Payments team)

**Action**:
1. Navigate to Backstage: `https://backstage.company.com`
2. Click "Create Component"
3. Select template: "Kubernetes Service"

**Time**: 30 seconds

---

#### Step 1.2: Fill Service Information Form

**Form Section 1: Basic Information**

```yaml
Service Name: payment-processor
Description: Core payment processing service for retail banking
Archetype: api (REST API)
Team: payments-team
```

**Form Section 2: Resource Configuration**

```yaml
Profile: public-api
  - Enables: Ingress, HPA, PDB, MTLS, Circuit Breaker, Retry
  
Size: large
  - CPU: 500m
  - Memory: 1Gi
  - Replicas: 3-10 (HPA)
  
Environments: [int-stable, pre-stable, prod]
Regions: [euw1, euw2]
```

**Form Section 3: Cost Configuration** ⭐ **NEW**

```yaml
Cost Profile: standard-api-cost
  - Recommended for: REST APIs
  - Base budgets: $500 (int), $1500 (pre), $3000 (prod)
  - Size multiplier: 2.0× (large service)
  
Cost Allocation:
  Cost Center: CC-12345 (validated against Apptio)
  Business Unit: retail-banking
  Cost Owner: alice.johnson@company.com
  
Calculated Budgets (shown in form):
  Int-Stable: $1,000/month (base $500 × 2.0)
  Pre-Stable: $3,000/month (base $1500 × 2.0)
  Production: $6,000/month (base $3000 × 2.0)
  
Alert Configuration (from profile):
  - 80% warning → #team-payment-processor (daily)
  - 100% critical → #team-payment-processor, #platform-leadership
                    + alice.johnson@company.com
                    + PagerDuty (on-call-engineering)
```

**Form Section 4: Monitoring Configuration** ⭐ **NEW**

```yaml
Monitoring Profile: api-observability
  - Recommended for: REST APIs
  - Includes: Prometheus, Dynatrace, SLOs, Alert Rules
  
Monitoring Options:
  ✅ Enable Prometheus (required for alerts)
  ✅ Enable Dynatrace (optional, full-stack APM)
  
Production SLO Overrides:
  Availability: 99.99% (stricter than profile default 99.9%)
  Latency P95: 200ms (stricter than profile default 500ms)
  Error Rate: 0.05% (stricter than profile default 0.1%)
  
Resource Thresholds (auto-calculated from size):
  Memory: 768MB (base 512MB × 1.5 for large)
  CPU: 750m (base 500m × 1.5 for large)
```

**Form Validation**:
- ✅ Service name unique
- ✅ Cost center exists in Apptio
- ✅ Email addresses valid
- ✅ Teams channels format valid
- ✅ SLO values in valid ranges

**Time**: 5 minutes

---

#### Step 1.3: Review and Confirm

**Backstage Shows Summary**:

```
┌─────────────────────────────────────────────────────────────┐
│ Service Configuration Summary                                │
├─────────────────────────────────────────────────────────────┤
│ Service: payment-processor                                  │
│ Type: API (REST)                                            │
│ Size: Large (500m CPU, 1Gi RAM)                             │
│                                                              │
│ Estimated Monthly Costs:                                     │
│ ├─ Int-Stable: $1,000                                       │
│ ├─ Pre-Stable: $3,000                                       │
│ └─ Production: $6,000                                       │
│                                                              │
│ Monitoring:                                                  │
│ ├─ Prometheus: ✅ Enabled                                   │
│ ├─ Dynatrace: ✅ Enabled                                    │
│ ├─ Availability SLO: 99.99%                                 │
│ └─ Latency SLO: 200ms (p95)                                │
│                                                              │
│ ☑ I understand cost implications                            │
│ ☑ I accept budget responsibility                            │
│ ☑ I confirm monitoring configuration                        │
└─────────────────────────────────────────────────────────────┘
```

**Developer clicks "Create"**

**Time**: 1 minute

---

### Phase 2: Catalog Entry Creation

#### Step 2.1: Backstage Creates PR

**Backstage Action**:
1. Generates service catalog entry
2. Creates PR to `platform-next` repository
3. PR includes complete service definition

**Generated Catalog Entry**:

```yaml
# kustomize/catalog/services.yaml (new entry)

services:
  - name: payment-processor
    type: api
    image: <GAR_IMAGE_PAYMENT_PROCESSOR>
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    namespaceTemplate: "{env}-{service}-{region}-stable"
    
    # Behavior configuration
    profile: public-api
    size: large
    components:
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - hpa
      - security-hardening
      - serviceaccount-rbac
      - network-policy
      - pdb
      - topology
    
    ports:
      servicePort: 80
      targetPort: 8080
    
    domains:
      int-stable: <FQDN_KEY_INT>
      pre-stable: <FQDN_KEY_PRE>
      prod: <FQDN_KEY_PROD>
    
    hpa:
      enabled: true
      minReplicas:
        defaults: 3
        overrides:
          prod: 4
      maxReplicas:
        defaults: 10
        overrides:
          prod: 15
      metrics:
        - type: Resource
          resource:
            name: cpu
            target:
              type: Utilization
              averageUtilization: 75
    
    resources:
      defaults:
        cpu: "500m"
        memory: "1Gi"
      overrides:
        prod:
          cpu: "500m"
          memory: "1Gi"
    
    # ================================================
    # COST CONFIGURATION
    # ================================================
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice.johnson@company.com"
      # No overrides - uses profile defaults
    
    # ================================================
    # MONITORING CONFIGURATION
    # ================================================
    monitoringProfile: api-observability
    monitoring:
      prometheus: true
      dynatrace: true
      overrides:
        prod:
          sloAvailability: 99.99
          sloErrorRate: 0.05
          sloLatencyP95ms: 200
    
    health:
      deployments: [payment-processor]
```

**Time**: 10 seconds (automated)

---

#### Step 2.2: CI/CD Validation

**GitHub Actions Workflow Triggers**:

```yaml
# .github/workflows/validate-service.yml

jobs:
  validate:
    steps:
      # 1. Schema validation
      - name: Validate schema
        run: |
          python scripts/validate-schema.py \
            --services kustomize/catalog/services.yaml
        # ✅ Passes: All required fields present
        
      # 2. Cost profile expansion
      - name: Expand cost profiles
        run: |
          python scripts/expand-profiles.py \
            --service payment-processor \
            --environment prod \
            --output /tmp/expanded-cost.json
        # ✅ Passes: Budgets calculated correctly
        
      # 3. Cost center verification
      - name: Verify cost center
        run: |
          python scripts/validate-cost-centers.py \
            --cost-center CC-12345 \
            --apptio-api ${{ secrets.APPTIO_API }}
        # ✅ Passes: Cost center exists in Apptio
        
      # 4. Monitoring profile expansion
      - name: Expand monitoring profiles
        run: |
          python scripts/expand-profiles.py \
            --service payment-processor \
            --environment prod \
            --output /tmp/expanded-monitoring.json
        # ✅ Passes: SLOs and thresholds valid
        
      # 5. PromQL validation
      - name: Validate Prometheus rules
        run: |
          python scripts/validate-promql.py \
            --profile api-observability
        # ✅ Passes: All PromQL expressions valid
        
      # 6. Budget range validation
      - name: Validate budgets
        run: |
          python scripts/validate-budgets.py \
            --service payment-processor
        # ✅ Passes: Budgets within acceptable ranges
          # Int: $1,000 (range: $100-$5,000) ✅
          # Pre: $3,000 (range: $200-$10,000) ✅
          # Prod: $6,000 (range: $300-$50,000) ✅
```

**Validation Results**:

```
✅ Schema validation passed
✅ Cost profile expansion successful
✅ Budgets calculated:
   Int-Stable: $1,000/month
   Pre-Stable: $3,000/month
   Prod: $6,000/month
✅ Cost center CC-12345 verified in Apptio
✅ Notification channels valid
✅ Monitoring profile expansion successful
✅ SLOs validated:
   Availability: 99.99% ✅
   Latency P95: 200ms ✅
   Error Rate: 0.05% ✅
✅ PromQL syntax valid
✅ Resource thresholds calculated:
   Memory: 768MB ✅
   CPU: 750m ✅
✅ Ready to merge
```

**Time**: 2-3 minutes

---

#### Step 2.3: PR Review and Merge

**Review Process**:
1. Platform team reviews PR
2. Validates cost allocation (finance approval if needed)
3. Checks monitoring configuration
4. Approves and merges

**Time**: 15-30 minutes (depending on review)

---

### Phase 3: Profile Expansion & Manifest Generation

#### Step 3.1: Profile Expansion (CI/CD)

**Trigger**: PR merged to `main` branch

**Expansion Process**:

```python
# scripts/expand-profiles.py execution

# Load service from catalog
service = load_service("payment-processor")

# Load cost profile
cost_profile = load_cost_profile("standard-api-cost")

# Expand cost configuration
expanded_cost = {
    "budgets": {
        "int-stable": {
            "monthly": 1000,  # $500 base × 2.0 (large)
            "base": 500,
            "scaling": 1.0,
            "sizeMultiplier": 2.0
        },
        "pre-stable": {
            "monthly": 3000,  # $1500 base × 2.0
            "base": 1500,
            "scaling": 1.33,
            "sizeMultiplier": 2.0
        },
        "prod": {
            "monthly": 6000,  # $3000 base × 2.0
            "base": 3000,
            "scaling": 1.67,
            "sizeMultiplier": 2.0
        }
    },
    "labels": {
        "service": "payment-processor",
        "team": "payments-team",
        "costCenter": "CC-12345",
        "businessUnit": "retail-banking",
        "owner": "alice.johnson@company.com"
    },
    "alerts": [
        {
            "name": "warning-80",
            "threshold": 80,
            "channels": {
                "teams": ["#team-payment-processor"],
                "email": ["alice.johnson@company.com"]
            }
        },
        {
            "name": "critical-100",
            "threshold": 100,
            "channels": {
                "teams": ["#team-payment-processor", "#platform-leadership"],
                "email": ["alice.johnson@company.com", "finance-operations@company.com"],
                "pagerduty": "on-call-engineering"
            }
        }
    ]
}

# Load monitoring profile
monitoring_profile = load_monitoring_profile("api-observability")

# Expand monitoring configuration
expanded_monitoring = {
    "enabled": True,
    "prometheus": {
        "enabled": True,
        "serviceMonitor": {...},
        "recordingRules": [
            {
                "name": "payment:http_requests:rate5m",
                "expr": "sum(rate(http_requests_total{service=\"payment-processor\"}[5m]))"
            },
            # ... more rules with {SERVICE} substituted
        ],
        "alertRules": [
            {
                "name": "PaymentProcessorHighErrorRate",
                "expr": "payment:http_error_ratio:rate5m > 0.0005",  # 0.05%
                "for": "5m"
            },
            # ... more alerts
        ]
    },
    "dynatrace": {
        "enabled": True,
        "application": {...}
    },
    "slos": {
        "availability": 99.99,  # From service override
        "errorRate": 0.05,      # From service override
        "latency": {
            "p95Baseline": 200  # From service override
        }
    },
    "resourceThresholds": {
        "memory": {
            "threshold": 768000000,  # 768MB (512MB × 1.5)
            "warningPercent": 80
        },
        "cpu": {
            "threshold": 0.750,  # 750m (500m × 1.5)
            "warningPercent": 80
        }
    }
}
```

**Time**: 30 seconds

---

#### Step 3.2: Manifest Generation (CI/CD)

**Generation Process**:

```bash
# For each environment and region
for ENV in int-stable pre-stable prod; do
  for REGION in euw1 euw2; do
    ./scripts/generate-kz.sh payment-processor $ENV $REGION
  done
done
```

**Generated Structure**:

```
tmp/payment-processor/prod/euw1/
├── kustomization.yaml
│   ├── resources: [cb-base, archetype/api, envs/prod, regions/euw1]
│   ├── components: [ingress, hpa, pdb, ...]
│   ├── commonLabels:
│   │   ├── cost.service: payment-processor
│   │   ├── cost.costCenter: CC-12345
│   │   ├── cost.budget: "6000"
│   │   ├── monitoring.profile: api-observability
│   │   └── prometheus.io/scrape: "true"
│   └── images: [payment-processor:PLACEHOLDER_TAG]
│
└── monitoring/
    ├── service-monitor.yaml
    ├── prometheus-rules-recording.yaml
    ├── prometheus-rules-alerts.yaml
    └── dynatrace-app-config.yaml
```

**Kustomize Build**:

```bash
kustomize build tmp/payment-processor/prod/euw1/ > \
  generated/payment-processor/prod/euw1/manifests.yaml
```

**Generated Manifests Include**:

```yaml
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: prod-payment-processor-euw1-stable
  labels:
    cost.service: payment-processor
    cost.costCenter: CC-12345
    cost.budget: "6000"
    monitoring.profile: api-observability

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-processor
  namespace: prod-payment-processor-euw1-stable
  labels:
    cost.service: payment-processor
    cost.costCenter: CC-12345
    cost.budget: "6000"
spec:
  replicas: 4
  template:
    metadata:
      labels:
        app: payment-processor
        cost.service: payment-processor
        cost.costCenter: CC-12345
        cost.businessUnit: retail-banking
        cost.owner: alice.johnson@company.com
        cost.budget: "6000"
        monitoring.profile: api-observability
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      containers:
        - name: app
          image: gcr.io/project/payment-processor:PLACEHOLDER_TAG
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
          # ... probes, security context, etc.

---
# ServiceMonitor (Prometheus)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: payment-processor-monitor
  namespace: prod-payment-processor-euw1-stable
spec:
  selector:
    matchLabels:
      app: payment-processor
  endpoints:
    - port: http
      path: /metrics
      interval: 30s

---
# PrometheusRule (Recording Rules)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-processor-recording-rules
  namespace: prod-payment-processor-euw1-stable
spec:
  groups:
    - name: payment_processor_recording
      rules:
        - record: payment:http_requests:rate5m
          expr: sum(rate(http_requests_total{service="payment-processor"}[5m]))
        # ... more recording rules

---
# PrometheusRule (Alert Rules)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-processor-alert-rules
  namespace: prod-payment-processor-euw1-stable
spec:
  groups:
    - name: payment_processor_alerts
      rules:
        - alert: PaymentProcessorHighErrorRate
          expr: payment:http_error_ratio:rate5m > 0.0005
          for: 5m
          annotations:
            summary: "High error rate for payment-processor"
        # ... more alert rules

---
# Dynatrace ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-processor-dynatrace-config
  namespace: prod-payment-processor-euw1-stable
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "prod"
      },
      "monitoring": {
        "technologies": ["java", "http", "databases"],
        "requestAttributes": [...]
      }
    }
```

**Time**: 2-3 minutes (for all environments/regions)

---

#### Step 3.3: Commit to Git

**CI/CD Action**:
1. Validates generated manifests (kubeconform)
2. Commits to `generated/` directory
3. Creates commit message with service details

**Git Commit**:

```
🤖 Generated manifests for payment-processor

Services: payment-processor
Environments: int-stable, pre-stable, prod
Regions: euw1, euw2

Cost Profile: standard-api-cost
- Int-Stable: $1,000/month
- Pre-Stable: $3,000/month
- Prod: $6,000/month

Monitoring Profile: api-observability
- Prometheus: ✅
- Dynatrace: ✅
- SLOs: 99.99% availability, 200ms p95 latency
```

**Time**: 1 minute

---

### Phase 4: Cost Management Setup

#### Step 4.1: Apptio Sync Triggered

**Trigger**: Catalog merged to `main` (webhook or polling)

**Apptio Sync Service**:

```python
# services/apptio-sync/sync.py

def sync_service(service_name):
    # Load service from catalog
    service = load_service(service_name)
    
    # Expand cost profile
    expanded_cost = expand_cost_profile(service)
    
    # For each environment
    for env in service["enabledIn"]:
        budget = expanded_cost["budgets"][env]
        
        # Create budget in Apptio
        apptio.create_budget(
            name=f"{service_name}-{env}",
            amount=budget["monthly"],
            period="monthly",
            filters={
                "cost.service": service_name,
                "cost.environment": env
            }
        )
        
        # Configure alert rules
        for alert in expanded_cost["alerts"]:
            apptio.create_alert_rule(
                budget_name=f"{service_name}-{env}",
                threshold=alert["threshold"],
                channels=alert["channels"]
            )
    
    print(f"✅ Synced {service_name} to Apptio")
```

**Apptio Actions**:
- ✅ Creates budget: `payment-processor-int-stable` ($1,000/month)
- ✅ Creates budget: `payment-processor-pre-stable` ($3,000/month)
- ✅ Creates budget: `payment-processor-prod` ($6,000/month)
- ✅ Configures alert: 80% warning → Teams + Email
- ✅ Configures alert: 100% critical → Teams + Email + PagerDuty
- ✅ Enables cost tracking

**Time**: 2-3 minutes

---

### Phase 5: Deployment Orchestration

#### Step 5.1: Harness Pipeline Created

**Trigger**: Service added to catalog (automated or manual)

**Pipeline Creation**:
1. Platform team (or automation) creates Harness pipeline
2. Pipeline template: `harness-pipelines/templates/api-pipeline-template.yaml`
3. Variables replaced: `{{SERVICE_NAME}}` → `payment-processor`

**Pipeline Structure**:

```yaml
pipeline:
  name: payment-processor-cd
  variables:
    - name: imageTag
      type: String
      required: true
    - name: targetEnvironment
      type: String
      allowedValues: [int-stable, pre-stable, prod]
    - name: targetRegion
      type: String
      allowedValues: [euw1, euw2]
  
  stages:
    - stage:
        name: Deploy to <+pipeline.variables.targetEnvironment>
        type: Deployment
        spec:
          service:
            serviceRef: payment-processor
          environment:
            environmentRef: <+pipeline.variables.targetEnvironment>
          infrastructure:
            connectorRef: k8s_<+pipeline.variables.targetEnvironment>_<+pipeline.variables.targetRegion>
            namespace: <+pipeline.variables.targetEnvironment>-payment-processor-<+pipeline.variables.targetRegion>
          
          execution:
            steps:
              # Approval gate (prod only)
              - step:
                  type: HarnessApproval
                  when:
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
              
              # Fetch manifests from Git
              - step:
                  type: K8sApply
                  spec:
                    filePaths:
                      - generated/payment-processor/<+pipeline.variables.targetEnvironment>/<+pipeline.variables.targetRegion>/manifests.yaml
              
              # Canary deployment (prod only)
              - step:
                  type: K8sCanaryDeploy
                  when:
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
```

**Time**: 5 minutes (one-time setup)

---

#### Step 5.2: First Deployment (Int-Stable)

**Developer Action**:
1. Opens Harness console
2. Selects pipeline: `payment-processor-cd`
3. Enters inputs:
   - `imageTag`: `v1.0.0`
   - `targetEnvironment`: `int-stable`
   - `targetRegion`: `euw1`
4. Clicks "Run Pipeline"

**Deployment Flow**:

```
Step 1: Fetch Manifests
  ├─ Source: Git (platform-next repo)
  ├─ Path: generated/payment-processor/int-stable/euw1/manifests.yaml
  ├─ Content: All resources with cost labels
  └─ ✅ Fetched successfully

Step 2: Inject Image Tag
  ├─ Replace: PLACEHOLDER_TAG → v1.0.0
  ├─ Final image: gcr.io/project/payment-processor:v1.0.0
  └─ ✅ Tag injected

Step 3: Deploy to Cluster
  ├─ Cluster: int-stable (via delegate)
  ├─ Namespace: int-stable-payment-processor-euw1-stable
  ├─ Resources:
  │   ├─ Namespace ✅
  │   ├─ ServiceAccount ✅
  │   ├─ Deployment ✅
  │   ├─ Service ✅
  │   ├─ ServiceMonitor ✅
  │   ├─ PrometheusRule (recording) ✅
  │   ├─ PrometheusRule (alerts) ✅
  │   └─ Dynatrace ConfigMap ✅
  └─ ✅ All resources deployed

Step 4: Health Check
  ├─ Pods: 3/3 running ✅
  ├─ Readiness: All ready ✅
  ├─ Liveness: All healthy ✅
  └─ ✅ Deployment successful
```

**Deployed Resources**:

```bash
# Namespace with cost labels
kubectl get namespace prod-payment-processor-euw1-stable -o yaml
# Labels: cost.service, cost.costCenter, cost.budget

# Pods with cost labels
kubectl get pods -n prod-payment-processor-euw1-stable -o yaml
# Labels: cost.service, cost.costCenter, cost.owner, cost.budget

# ServiceMonitor (Prometheus)
kubectl get servicemonitor payment-processor-monitor -n prod-payment-processor-euw1-stable

# PrometheusRules
kubectl get prometheusrule -n prod-payment-processor-euw1-stable
```

**Time**: 5-10 minutes

---

#### Step 5.3: Production Deployment (with Canary)

**Developer Action**:
1. After int-stable validation (1-2 days)
2. Opens Harness pipeline
3. Enters inputs:
   - `imageTag`: `v1.0.0`
   - `targetEnvironment`: `prod`
   - `targetRegion`: `euw1`
4. Clicks "Run Pipeline"

**Deployment Flow**:

```
Step 1: Production Approval Gate
  ├─ Required: 2 approvers
  ├─ Approver 1: Team lead ✅
  ├─ Approver 2: Platform team ✅
  ├─ Change ticket: CHG0123456 ✅
  ├─ Rollback plan: Provided ✅
  └─ ✅ Approved

Step 2: Change Window Check
  ├─ Current time: Monday 14:00 UTC
  ├─ Change window: Mon-Thu 10:00-16:00
  ├─ Policy evaluation: ✅ Allowed
  └─ ✅ Passed

Step 3: Fetch Manifests
  ├─ Path: generated/payment-processor/prod/euw1/manifests.yaml
  └─ ✅ Fetched

Step 4: Canary 10%
  ├─ Deploy: 1 pod (10% of 4 replicas)
  ├─ Image: gcr.io/project/payment-processor:v1.0.0
  ├─ Monitor: 5 minutes
  ├─ Metrics:
  │   ├─ Error rate: 0.02% ✅ (< 0.05% SLO)
  │   ├─ Latency p95: 150ms ✅ (< 200ms SLO)
  │   └─ Availability: 100% ✅ (> 99.99% SLO)
  └─ ✅ Canary healthy

Step 5: Canary 50%
  ├─ Deploy: 2 pods (50% of 4 replicas)
  ├─ Monitor: 10 minutes
  ├─ Metrics: All within SLO ✅
  └─ ✅ Canary healthy

Step 6: Complete Rollout (100%)
  ├─ Deploy: All 4 pods
  ├─ Delete canary resources
  └─ ✅ Rollout complete

Step 7: Verify Health
  ├─ Pods: 4/4 running ✅
  ├─ Service: Healthy ✅
  ├─ Monitoring: Active ✅
  └─ ✅ Production deployment successful
```

**Time**: 20-30 minutes (with canary validation)

---

### Phase 6: Runtime & Monitoring

#### Step 6.1: Cost Tracking Begins

**Timeline**:

```
T+0 hours: Pods deployed with cost labels
  ├─ Labels on all pods:
  │   ├─ cost.service: payment-processor
  │   ├─ cost.costCenter: CC-12345
  │   ├─ cost.businessUnit: retail-banking
  │   ├─ cost.owner: alice.johnson@company.com
  │   └─ cost.budget: "6000"
  └─ ✅ Labels active

T+24 hours: GCP Billing Export
  ├─ Daily export includes all labels
  ├─ Cost entries tagged with:
  │   ├─ cost.service=payment-processor
  │   ├─ cost.costCenter=CC-12345
  │   └─ cost.environment=prod
  └─ ✅ Costs exported

T+48 hours: Apptio Ingestion
  ├─ Apptio reads labeled costs from GCP
  ├─ Allocates to: payment-processor-prod
  ├─ Matches with budget: $6,000/month
  ├─ Starts tracking: $XXX spent vs $6,000 budget
  └─ ✅ Cost tracking active

T+72 hours: First Cost Data Visible
  ├─ Apptio dashboard shows:
  │   ├─ Service: payment-processor
  │   ├─ Environment: prod
  │   ├─ Month-to-date: $450
  │   ├─ Budget: $6,000
  │   ├─ % Used: 7.5%
  │   └─ Status: ✅ Healthy
  └─ ✅ Cost visibility achieved
```

---

#### Step 6.2: Monitoring Active

**Prometheus**:

```
T+0 minutes: ServiceMonitor deployed
  ├─ Prometheus operator discovers ServiceMonitor
  ├─ Starts scraping: /metrics endpoint
  ├─ Interval: Every 30 seconds
  └─ ✅ Metrics collection active

T+5 minutes: Recording Rules Active
  ├─ Prometheus calculates:
  │   ├─ payment:http_requests:rate5m
  │   ├─ payment:http_error_ratio:rate5m
  │   ├─ payment:http_latency:p95
  │   └─ payment:http_latency:p99
  └─ ✅ Recording rules active

T+5 minutes: Alert Rules Armed
  ├─ Alerts monitoring:
  │   ├─ HighErrorRate (> 0.05%)
  │   ├─ HighLatency (> 200ms p95)
  │   ├─ ServiceDown (no requests)
  │   └─ HighResourceUsage
  └─ ✅ Alerts active (not firing)
```

**Dynatrace**:

```
T+10 minutes: OneAgent Detects Service
  ├─ Auto-instruments: Java application
  ├─ Captures: HTTP requests, DB queries
  ├─ Traces: Distributed calls
  └─ ✅ APM active

T+15 minutes: Application Visible in Dynatrace
  ├─ Dashboard: payment-processor-prod
  ├─ Metrics: Response time, error rate, throughput
  ├─ Traces: Request flows
  └─ ✅ Full observability active
```

**Grafana**:

```
T+5 minutes: Dashboard Available
  ├─ Auto-generated from monitoring profile
  ├─ Panels:
  │   ├─ Request Rate
  │   ├─ Error Rate
  │   ├─ Latency (p50, p95, p99)
  │   ├─ Resource Usage
  │   └─ SLO Compliance
  └─ ✅ Dashboard ready
```

---

#### Step 6.3: Ongoing Operations

**Daily Operations**:

```
Cost Monitoring:
  ├─ Apptio tracks daily spend
  ├─ Budget alerts fire at thresholds:
  │   ├─ 80% ($4,800) → Warning to team
  │   └─ 100% ($6,000) → Critical alert
  └─ ✅ Cost visibility maintained

Performance Monitoring:
  ├─ Prometheus alerts fire on SLO violations:
  │   ├─ Error rate > 0.05% → Alert
  │   ├─ Latency p95 > 200ms → Alert
  │   └─ Availability < 99.99% → Critical
  └─ ✅ SLOs monitored

Observability:
  ├─ Grafana dashboards: Real-time metrics
  ├─ Dynatrace: Full-stack APM
  ├─ Logs: Centralized logging (if configured)
  └─ ✅ Complete observability
```

---

## 3. Complete Data Flow

### 3.1 Cost Data Flow

```
Developer (Backstage)
  ↓
  Cost Profile Selection (standard-api-cost)
  ↓
  Cost Allocation (CC-12345, alice@company.com)
  ↓
  Catalog Entry (services.yaml)
  ↓
  CI/CD Expansion
  ├─ Calculate budgets: $1K, $3K, $6K
  ├─ Generate cost labels
  └─ Validate cost center
  ↓
  Manifest Generation
  ├─ Inject cost labels into commonLabels
  └─ All resources tagged
  ↓
  Git Commit (generated/manifests.yaml)
  ↓
  Apptio Sync
  ├─ Create budgets in Apptio
  ├─ Configure alert rules
  └─ Enable tracking
  ↓
  Harness Deployment
  ├─ Deploy pods with cost labels
  └─ Labels inherited by all resources
  ↓
  GCP Billing
  ├─ Daily export includes labels
  └─ Cost entries tagged
  ↓
  Apptio Ingestion
  ├─ Read labeled costs
  ├─ Allocate to service/budget
  ├─ Track vs budget
  └─ Fire alerts at thresholds
  ↓
  Cost Visibility
  ├─ Apptio dashboards
  ├─ Team notifications
  └─ Finance reports
```

---

### 3.2 Monitoring Data Flow

```
Developer (Backstage)
  ↓
  Monitoring Profile Selection (api-observability)
  ↓
  SLO Configuration (99.99% availability, 200ms p95)
  ↓
  Catalog Entry (services.yaml)
  ↓
  CI/CD Expansion
  ├─ Substitute variables ({SERVICE}, {TEAM})
  ├─ Calculate thresholds (768MB, 750m CPU)
  ├─ Apply SLO overrides
  └─ Generate Prometheus rules
  ↓
  Manifest Generation
  ├─ Generate ServiceMonitor
  ├─ Generate PrometheusRule (recording)
  ├─ Generate PrometheusRule (alerts)
  └─ Generate Dynatrace config
  ↓
  Git Commit (generated/manifests.yaml)
  ↓
  Harness Deployment
  ├─ Deploy ServiceMonitor → Prometheus discovers
  ├─ Deploy PrometheusRules → Alerts armed
  └─ Deploy Dynatrace config → OneAgent configures
  ↓
  Runtime Collection
  ├─ Prometheus: Scrapes /metrics every 30s
  ├─ Dynatrace: Auto-instruments application
  └─ Both collect in parallel
  ↓
  Metrics Processing
  ├─ Prometheus: Stores time-series, evaluates rules
  ├─ Dynatrace: Analyzes traces, detects anomalies
  └─ Both: Calculate SLO compliance
  ↓
  Alerting & Visualization
  ├─ Prometheus: Fires alerts on SLO violations
  ├─ Grafana: Real-time dashboards
  ├─ Dynatrace: APM dashboards, anomaly detection
  └─ Teams: Notifications on alerts
```

---

## 4. Integration Points Summary

### 4.1 Backstage → Catalog

**Integration**: Software Template → PR Creation
- Form data → YAML catalog entry
- Cost profile selection → `costProfile` field
- Monitoring profile selection → `monitoringProfile` field
- Validation → Schema checks

---

### 4.2 Catalog → CI/CD

**Integration**: Git Webhook → GitHub Actions
- PR created → Validation workflow
- Profile expansion → Python scripts
- Manifest generation → Kustomize build
- Git commit → Generated manifests

---

### 4.3 CI/CD → Apptio

**Integration**: Webhook/Polling → Apptio Sync Service
- Catalog merged → Sync triggered
- Budget creation → Apptio API
- Alert configuration → Apptio API
- Cost tracking → Enabled

---

### 4.4 CI/CD → Harness

**Integration**: Git → Harness Manifests
- Generated manifests → Git repository
- Harness fetches → From Git
- Image tag injection → Runtime replacement
- Deployment → Kubernetes clusters

---

### 4.5 Harness → Kubernetes

**Integration**: Delegate → Cluster API
- Multi-cluster → Per-cluster delegates
- Resource deployment → kubectl apply
- Health checks → K8s native
- Canary deployment → Harness CV

---

### 4.6 Kubernetes → Cost Tracking

**Integration**: Labels → GCP Billing → Apptio
- Cost labels → On all resources
- GCP billing → Includes labels
- Apptio ingestion → Reads labels
- Cost allocation → By service/team/cost-center

---

### 4.7 Kubernetes → Monitoring

**Integration**: ServiceMonitor → Prometheus → Alerts
- ServiceMonitor → Prometheus discovers
- Metrics collection → Every 30s
- Alert evaluation → Prometheus rules
- Notifications → Teams, PagerDuty

---

## 5. Key Success Metrics

### 5.1 Onboarding Metrics

- **Time to Onboard**: Target: < 10 minutes
- **First Deployment**: Target: < 1 hour from onboarding
- **Validation Pass Rate**: Target: > 95%

---

### 5.2 Deployment Metrics

- **Deployment Frequency**: Target: Multiple per day
- **Lead Time**: Target: < 1 hour
- **Change Failure Rate**: Target: < 5%
- **MTTR**: Target: < 15 minutes

---

### 5.3 Cost Metrics

- **Budget Adherence**: Target: > 90% of services within budget
- **Cost Visibility**: Target: 100% of services tracked
- **Alert Accuracy**: Target: < 5% false positives

---

### 5.4 Monitoring Metrics

- **SLO Compliance**: Target: > 99% of time
- **Alert Coverage**: Target: 100% of services
- **Dashboard Availability**: Target: < 5 minutes after deployment

---

## 6. Troubleshooting Guide

### 6.1 Common Issues

**Issue**: Cost labels not appearing on pods
- **Check**: Manifest generation includes cost labels in commonLabels
- **Check**: Harness not stripping labels
- **Fix**: Verify kustomization.yaml has cost labels

**Issue**: Monitoring not collecting metrics
- **Check**: ServiceMonitor deployed and discovered
- **Check**: /metrics endpoint accessible
- **Fix**: Verify ServiceMonitor selector matches pod labels

**Issue**: Budget alerts not firing
- **Check**: Apptio sync completed successfully
- **Check**: Cost labels present in GCP billing
- **Fix**: Verify Apptio budget configuration

---

## 7. Summary

### Complete Lifecycle

1. **Introduction** (5 min): Developer fills Backstage form with cost & monitoring
2. **Catalog Entry** (10 min): PR created, validated, merged
3. **Manifest Generation** (3 min): Profiles expanded, manifests generated
4. **Cost Setup** (3 min): Apptio budgets and alerts configured
5. **Deployment** (10-30 min): Harness deploys with canary validation
6. **Runtime** (Ongoing): Cost tracking and monitoring active

### Key Achievements

- ✅ **Self-Service**: Developers onboard in 5 minutes
- ✅ **Integrated**: Cost and monitoring from day 1
- ✅ **Automated**: CI/CD handles all generation
- ✅ **GitOps**: All config versioned in Git
- ✅ **Observable**: Full metrics, logs, traces
- ✅ **Cost-Aware**: Budgets and tracking automatic

### Result

**Every service deployed has**:
- ✅ Cost labels for allocation
- ✅ Budgets in Apptio
- ✅ Monitoring resources (Prometheus, Dynatrace)
- ✅ SLOs defined and tracked
- ✅ Alert rules active
- ✅ Complete observability

**This is a modern, production-ready platform!** 🚀

---

**Document Status**: ✅ Complete End-to-End Design

**Related Documents**:
- [01_BACKSTAGE_DESIGN.md](./01_BACKSTAGE_DESIGN.md) - Backstage integration
- [07_COST_MANAGEMENT_WITH_PROFILES.md](./07_COST_MANAGEMENT_WITH_PROFILES.md) - Cost profiles
- [08_MONITORING_METRICS_PROFILES.md](./08_MONITORING_METRICS_PROFILES.md) - Monitoring profiles
- [09_PROFILES_KUSTOMIZE_INTEGRATION.md](./09_PROFILES_KUSTOMIZE_INTEGRATION.md) - Technical integration

