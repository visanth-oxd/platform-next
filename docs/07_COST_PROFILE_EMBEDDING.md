# Cost Profile Embedding Mechanism - Service Onboarding Integration

**Status**: DRAFT - Clarification Document

**Purpose**: Define the exact mechanism for embedding cost profiles into services during onboarding so that metrics, budgets, and alerts are available from deployment day 1.

---

## Executive Summary

The cost reporting integration requires a **clear data model** that embeds cost profiles directly into the service catalog. When a service is added to `catalog/services.yaml`, its cost profile must be defined simultaneously, not afterward.

**Current Gap**: `catalog/services.yaml` services lack cost configuration. This document specifies:
- The cost profile schema that gets embedded in each service
- How cost profiles flow from catalog → Kustomize → GCP labels → Apptio
- The validation gates that prevent incomplete cost configurations

---

## 1. Cost Profile Data Model

Each service in `catalog/services.yaml` must include a `cost` section with the following structure:

```yaml
services:
  - name: payment-service
    type: api
    # ... existing fields ...
    
    # NEW: Cost Profile (MANDATORY)
    cost:
      enabled: true
      
      # Cost center allocation
      allocation:
        costCenter: "CC-12345"
        businessUnit: "retail-banking"
        costOwner: "payments-team-lead@company.com"
      
      # Per-environment budgets
      budgets:
        int-stable:
          monthly: 800
          currency: USD
        pre-stable:
          monthly: 2000
          currency: USD
        prod:
          monthly: 5000
          currency: USD
      
      # Alert thresholds
      alerts:
        - name: "warning-80"
          type: "budget"
          threshold: 80
          severity: "warning"
          channels:
            teams:
              - "#team-payments"
              - "#platform-finops"
            email:
              - "payments-team-lead@company.com"
            frequency: "daily"
        
        - name: "critical-100"
          type: "budget"
          threshold: 100
          severity: "critical"
          channels:
            teams:
              - "#team-payments"
              - "#platform-leadership"
            email:
              - "payments-team-lead@company.com"
              - "finance-operations@company.com"
            pagerduty: "on-call-engineering"
            frequency: "immediate"
      
      # Optimization preferences
      optimization:
        enableAutoScaling: true
        allowSpotInstances: false
        allowRightSizing: true
      
      # Apptio integration labels
      apptioLabels:
        serviceCode: "payment-service"
        applicationId: "app-12345"
        businessService: "payments-platform"
```

---

## 2. Cost Profile Components Explained

### 2.1 Allocation Section

```yaml
allocation:
  costCenter: "CC-12345"        # Format: CC-XXXXX (validated against Apptio)
  businessUnit: "retail-banking" # Predefined values from Finance
  costOwner: "name@company.com"   # Must exist in company directory
```

**Purpose**: Enables cost chargeback and accountability

**Validation**:
- Cost center format: `CC-[0-9]{5}`
- Cost center must exist in Apptio (API validation during CI/CD)
- Business unit from predefined list
- Cost owner must exist in directory

---

### 2.2 Budgets Section

```yaml
budgets:
  int-stable:
    monthly: 800        # USD
    currency: USD
  pre-stable:
    monthly: 2000
    currency: USD
  prod:
    monthly: 5000
    currency: USD
```

**Purpose**: Define spending limits per environment

**Validation Rules**:
- Int-stable: $50-$5,000
- Pre-stable: $100-$10,000
- Production: $200-$50,000
- Budget progression: int ≤ pre < prod (logical escalation)

**When budgets are created in Apptio**:
- Immediately after catalog is merged to main branch
- Via Apptio Sync Service (polling every 5 minutes)
- Budget names: `{service-name}-{environment}` (e.g., `payment-service-prod`)

---

### 2.3 Alerts Section

```yaml
alerts:
  - name: "warning-80"
    type: "budget"
    threshold: 80              # 80% of budget
    severity: "warning"
    channels:
      teams: ["#team-payments"]
      email: ["owner@company.com"]
      frequency: "daily"
```

**Threshold Ranges**:
- 50-79%: Info level (optional)
- 80-99%: Warning level (recommended)
- 100%+: Critical level (mandatory)

**Channels**:
- **Teams**: Channel name (format: `#channel-name`)
- **Email**: Company email addresses
- **PagerDuty**: Incident creation (critical only)
- **Frequency**: once, daily, immediate

---

### 2.4 Apptio Labels Section

```yaml
apptioLabels:
  serviceCode: "payment-service"      # Unique service identifier
  applicationId: "app-12345"          # Maps to Apptio application
  businessService: "payments-platform" # Business capability name
```

**Purpose**: Links service to Apptio application hierarchy for reporting

---

## 3. Data Flow: From Catalog to Apptio

### 3.1 Complete Integration Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Service Onboarding (Backstage Template)                 │
├─────────────────────────────────────────────────────────────────┤
│ • User fills form (service basics + cost section - MANDATORY)    │
│ • Form validates all cost fields                                 │
│ • Generated files include cost profile in services.yaml          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 2: Create PR with Cost Configuration                       │
├─────────────────────────────────────────────────────────────────┤
│ • kustomize/catalog/services.yaml updated with full cost block  │
│ • Commit message: "onboard: {service-name} with cost profile"   │
│ • All cost fields populated from form                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 3: Schema Validation (CI/CD)                               │
├─────────────────────────────────────────────────────────────────┤
│ Validation checks:                                               │
│ ├─ services.yaml matches schema/services-schema.json            │
│ ├─ cost.enabled = true for all services                         │
│ ├─ cost.allocation fields present & valid                       │
│ ├─ cost.budgets defined for all environments                    │
│ ├─ cost.alerts has min 2 entries (warning + critical)           │
│ ├─ Budget amounts in valid ranges                               │
│ ├─ Cost center format validation                                │
│ └─ Cost center exists in Apptio (API call)                      │
│                                                                  │
│ ❌ Workflow blocks PR if validation fails                        │
│ ✅ Workflow allows merge only if all validations pass           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 4: PR Merged to Main                                       │
├─────────────────────────────────────────────────────────────────┤
│ • catalog/services.yaml now contains service with cost profile  │
│ • Merge triggers Apptio Sync workflow                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 5: Apptio Sync Service Processes Catalog                   │
├─────────────────────────────────────────────────────────────────┤
│ Timer: Runs every 5 minutes (Kubernetes Service Option)         │
│ Actions per service with cost.enabled=true:                     │
│                                                                  │
│ For each environment (int-stable, pre-stable, prod):            │
│ 1. Call Apptio API: Create Budget                               │
│    POST /api/budgets                                            │
│    {                                                            │
│      "name": "payment-service-prod",                            │
│      "amount": 5000,                                            │
│      "period": "MONTHLY",                                       │
│      "costCenter": "CC-12345",                                  │
│      "filters": {                                               │
│        "labels": {                                              │
│          "cost.service": "payment-service"                      │
│        }                                                        │
│      }                                                          │
│    }                                                            │
│                                                                  │
│ 2. Create Alert Rules in Apptio                                 │
│    For each threshold (80%, 100%):                              │
│      → Webhook to Teams channels                                │
│      → Email notifications                                      │
│      → PagerDuty integration (critical)                         │
│                                                                  │
│ 3. Store sync metadata                                          │
│    ConfigMap: apptio-sync-state                                │
│      lastSync: "2025-11-15T10:30:00Z"                          │
│      synced_services: ["payment-service", "events-listener"]   │
│      sync_status: "success"                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 6: Service Deployment & Label Injection                    │
├─────────────────────────────────────────────────────────────────┤
│ When service is deployed (kustomize build):                     │
│                                                                  │
│ 1. Kustomize loads: kustomize/catalog/services.yaml            │
│ 2. Extracts cost profile for service + environment              │
│ 3. Generates kustomization.yaml with cost labels:               │
│    commonLabels:                                                │
│      cost.service: "payment-service"                            │
│      cost.team: "payments-team"                                 │
│      cost.environment: "prod"                                   │
│      cost.costCenter: "CC-12345"                                │
│      cost.businessUnit: "retail-banking"                        │
│      cost.owner: "payments-team-lead@company.com"              │
│      cost.budget: "5000"                                        │
│                                                                  │
│ 4. All pod specs include labels automatically                   │
│ 5. Manifests deployed to GKE                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 7: Cost Tracking Begins                                    │
├─────────────────────────────────────────────────────────────────┤
│ Timeline:                                                        │
│                                                                  │
│ T+0h:  Pods running with cost labels                            │
│ T+24h: GCP Billing exports daily data with labels               │
│ T+48h: Apptio ingests cost data                                 │
│        → Service costs visible in Apptio dashboard              │
│        → Budgets being tracked                                  │
│ T+72h: Alerts start firing when thresholds crossed              │
│        → Teams channels receive notifications                   │
│        → Cost owner receives alerts                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Complete Example: Adding a Service

### Scenario
A payments team is onboarding "payment-processor" service to production.

### Step 1: Backstage Onboarding Form
Team fills:
- Service name: `payment-processor`
- Size estimate: `Large` ($1200-2000/month prod estimate)
- Int-Stable budget: `$800`
- Pre-Stable budget: `$2000`
- Production budget: `$5000`
- Cost center: `CC-12345` (Retail Banking)
- Business unit: `retail-banking`
- Cost owner: `alice.johnson@company.com`
- Warning threshold: `80%`
- Critical threshold: `100%`
- Warning channel: `#team-payments`
- Critical channels: `#team-payments`, `#platform-leadership`
- Critical email: `alice.johnson@company.com`, `finance-operations@company.com`

### Step 2: Generated catalog/services.yaml Entry

```yaml
  - name: payment-processor
    type: api
    image: <GAR_IMAGE_PAYMENT_PROCESSOR>
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    namespaceTemplate: "{env}-{service}-{region}-stable"
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
    hpa:
      enabled: true
      minReplicas:
        defaults: 2
        overrides:
          prod: 4
      maxReplicas:
        defaults: 6
        overrides:
          prod: 10
    resources:
      defaults:
        cpu: "250m"
        memory: "512Mi"
      overrides:
        prod:
          cpu: "500m"
          memory: "1Gi"
    
    # ✅ NEW: Cost Profile Embedded at Onboarding
    cost:
      enabled: true
      
      allocation:
        costCenter: "CC-12345"
        businessUnit: "retail-banking"
        costOwner: "alice.johnson@company.com"
      
      budgets:
        int-stable:
          monthly: 800
          currency: USD
        pre-stable:
          monthly: 2000
          currency: USD
        prod:
          monthly: 5000
          currency: USD
      
      alerts:
        - name: "warning-80"
          type: "budget"
          threshold: 80
          severity: "warning"
          channels:
            teams:
              - "#team-payments"
            email:
              - "alice.johnson@company.com"
            frequency: "daily"
        
        - name: "critical-100"
          type: "budget"
          threshold: 100
          severity: "critical"
          channels:
            teams:
              - "#team-payments"
              - "#platform-leadership"
            email:
              - "alice.johnson@company.com"
              - "finance-operations@company.com"
            pagerduty: "on-call-engineering"
            frequency: "immediate"
      
      optimization:
        enableAutoScaling: true
        allowSpotInstances: false
        allowRightSizing: true
      
      apptioLabels:
        serviceCode: "payment-processor"
        applicationId: "app-54321"
        businessService: "payments-platform"
```

### Step 3: CI/CD Validation Passes
- Schema validation ✅
- Budget ranges ✅
- Cost center CC-12345 exists ✅
- All required fields present ✅
- PR merged to main ✅

### Step 4: Apptio Sync Creates Budgets
Budget created in Apptio:
- Name: `payment-processor-prod`
- Amount: $5,000/month
- Cost center: CC-12345
- Filters: `cost.service=payment-processor`

Alert rules created:
- 80% threshold → Teams: #team-payments (daily)
- 100% threshold → Teams: #team-payments, #platform-leadership (immediate + PagerDuty)

### Step 5: Service Deployed
Kustomize injects labels:
```yaml
spec:
  template:
    metadata:
      labels:
        cost.service: "payment-processor"
        cost.team: "payments-team"
        cost.environment: "prod"
        cost.costCenter: "CC-12345"
        cost.businessUnit: "retail-banking"
        cost.owner: "alice.johnson@company.com"
        cost.budget: "5000"
```

### Step 6: Cost Tracking Active
- Day 1: Pods running, labels applied
- Day 2: GCP billing export with labels
- Day 3: Apptio sees costs
- Day 4-5: Alerts firing if thresholds approached

---

## 5. Schema Definition

### services-schema.json (Cost Section)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "services": {
      "type": "array",
      "items": {
        "properties": {
          "cost": {
            "type": "object",
            "required": ["enabled", "allocation", "budgets", "alerts"],
            "properties": {
              "enabled": {
                "type": "boolean",
                "const": true,
                "description": "Cost tracking must be enabled"
              },
              
              "allocation": {
                "type": "object",
                "required": ["costCenter", "businessUnit", "costOwner"],
                "properties": {
                  "costCenter": {
                    "type": "string",
                    "pattern": "^CC-[0-9]{5}$",
                    "description": "Cost center code (CC-XXXXX format)"
                  },
                  "businessUnit": {
                    "type": "string",
                    "enum": [
                      "retail-banking",
                      "wealth-management",
                      "corporate-banking",
                      "technology",
                      "operations"
                    ]
                  },
                  "costOwner": {
                    "type": "string",
                    "format": "email",
                    "description": "Email of cost owner"
                  }
                }
              },
              
              "budgets": {
                "type": "object",
                "required": ["int-stable", "pre-stable", "prod"],
                "properties": {
                  "int-stable": {
                    "type": "object",
                    "required": ["monthly", "currency"],
                    "properties": {
                      "monthly": {
                        "type": "number",
                        "minimum": 50,
                        "maximum": 5000
                      },
                      "currency": {
                        "type": "string",
                        "const": "USD"
                      }
                    }
                  },
                  "pre-stable": {
                    "type": "object",
                    "required": ["monthly", "currency"],
                    "properties": {
                      "monthly": {
                        "type": "number",
                        "minimum": 100,
                        "maximum": 10000
                      },
                      "currency": {
                        "type": "string",
                        "const": "USD"
                      }
                    }
                  },
                  "prod": {
                    "type": "object",
                    "required": ["monthly", "currency"],
                    "properties": {
                      "monthly": {
                        "type": "number",
                        "minimum": 200,
                        "maximum": 50000
                      },
                      "currency": {
                        "type": "string",
                        "const": "USD"
                      }
                    }
                  }
                }
              },
              
              "alerts": {
                "type": "array",
                "minItems": 2,
                "description": "At least 2 alerts required (warning + critical)",
                "items": {
                  "type": "object",
                  "required": ["name", "type", "threshold", "severity", "channels"],
                  "properties": {
                    "name": {
                      "type": "string",
                      "pattern": "^[a-z0-9-]+$"
                    },
                    "type": {
                      "type": "string",
                      "enum": ["budget"]
                    },
                    "threshold": {
                      "type": "number",
                      "minimum": 50,
                      "maximum": 110,
                      "description": "Threshold as percentage of budget"
                    },
                    "severity": {
                      "type": "string",
                      "enum": ["info", "warning", "critical"]
                    },
                    "channels": {
                      "type": "object",
                      "properties": {
                        "teams": {
                          "type": "array",
                          "items": {
                            "type": "string",
                            "pattern": "^#[a-z0-9-]+$"
                          }
                        },
                        "email": {
                          "type": "array",
                          "items": {
                            "type": "string",
                            "format": "email"
                          }
                        },
                        "pagerduty": {
                          "type": "string"
                        },
                        "frequency": {
                          "type": "string",
                          "enum": ["once", "daily", "immediate"]
                        }
                      }
                    }
                  }
                }
              },
              
              "optimization": {
                "type": "object",
                "properties": {
                  "enableAutoScaling": {
                    "type": "boolean"
                  },
                  "allowSpotInstances": {
                    "type": "boolean"
                  },
                  "allowRightSizing": {
                    "type": "boolean"
                  }
                }
              },
              
              "apptioLabels": {
                "type": "object",
                "required": ["serviceCode", "applicationId", "businessService"],
                "properties": {
                  "serviceCode": {
                    "type": "string"
                  },
                  "applicationId": {
                    "type": "string"
                  },
                  "businessService": {
                    "type": "string"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 6. Validation Workflow (CI/CD)

### .github/workflows/validate-cost-metrics.yml

```yaml
name: Validate Cost Metrics

on:
  pull_request:
    paths:
      - 'kustomize/catalog/services.yaml'

jobs:
  validate-cost-config:
    runs-on: ubuntu-latest
    steps:
      
      # 1. Schema Validation
      - uses: actions/checkout@v3
      - name: Validate schema
        run: |
          python scripts/validate-catalog-schema.py \
            --catalog kustomize/catalog/services.yaml \
            --schema schema/services-schema.json
      
      # 2. Cost Fields Validation
      - name: Check required cost fields
        run: |
          python scripts/validate-cost-fields.py \
            --catalog kustomize/catalog/services.yaml
          # Ensures every service has cost.enabled=true
          # Ensures every service has budgets for all environments
          # Ensures every service has at least 2 alerts
      
      # 3. Budget Range Validation
      - name: Validate budget amounts
        run: |
          python scripts/validate-budget-ranges.py \
            --catalog kustomize/catalog/services.yaml
          # int-stable: $50-$5000
          # pre-stable: $100-$10000
          # prod: $200-$50000
      
      # 4. Cost Center Verification (Apptio API)
      - name: Verify cost centers exist
        run: |
          python scripts/validate-cost-centers.py \
            --catalog kustomize/catalog/services.yaml \
            --apptio-api-url ${{ secrets.APPTIO_API_URL }} \
            --apptio-api-key ${{ secrets.APPTIO_API_KEY }}
      
      # 5. Notification Channel Validation
      - name: Validate notification channels
        run: |
          python scripts/validate-notification-channels.py \
            --catalog kustomize/catalog/services.yaml
          # Teams channels format: #channel-name
          # Email format valid
          # At least one channel per alert
      
      # 6. Report & Fail if Issues Found
      - name: Generate validation report
        if: failure()
        run: |
          echo "❌ Cost metrics validation failed"
          echo "See details above"
          exit 1
```

---

## 7. Kustomize Integration: Label Injection

### kustomize/overlays/{environment}/kustomization.yaml

When Kustomize processes the catalog, it:

1. **Loads service definition** from `kustomize/catalog/services.yaml`
2. **Extracts cost profile** for the environment
3. **Injects commonLabels** into all resources

**Example for payment-processor in prod**:

```yaml
# kustomize/overlays/prod/kustomization.yaml

bases:
  - ../../base

resources:
  - ../../base/payment-processor

commonLabels:
  app: payment-processor
  cost.service: payment-processor          # From cost.allocation
  cost.team: payments-team                 # From service metadata
  cost.environment: prod                   # Current environment
  cost.costCenter: CC-12345                # From cost.allocation
  cost.businessUnit: retail-banking        # From cost.allocation
  cost.owner: alice.johnson@company.com    # From cost.allocation
  cost.budget: "5000"                      # From cost.budgets[prod]
```

**Result**: Every pod in payment-processor deployment gets these labels:
```bash
kubectl get pods -L cost.service,cost.team,cost.budget
NAME                                      COST.SERVICE          COST.TEAM      COST.BUDGET
payment-processor-65d4b8f4c9-abc12        payment-processor     payments-team  5000
payment-processor-65d4b8f4c9-def45        payment-processor     payments-team  5000
```

---

## 8. Apptio Sync Service: Implementation Details

### How Apptio Sync Processes Cost Profiles

**Trigger**: Every 5 minutes (Kubernetes native service)

**Algorithm**:
```python
def sync_catalogs_to_apptio():
    # 1. Poll Git for latest catalog
    catalog = fetch_latest_catalog()
    
    # 2. For each service with cost.enabled=true
    for service in catalog.services:
        if not service.cost.enabled:
            continue
        
        # 3. For each environment (int-stable, pre-stable, prod)
        for env in ['int-stable', 'pre-stable', 'prod']:
            budget = service.cost.budgets[env]
            
            # 4. Create/Update Budget in Apptio
            apptio.create_budget(
                name=f"{service.name}-{env}",
                amount=budget.monthly,
                period="MONTHLY",
                cost_center=service.cost.allocation.costCenter,
                filters={
                    "labels": {
                        "cost.service": service.name,
                        "cost.environment": env
                    }
                }
            )
            
            # 5. Create Alert Rules
            for alert in service.cost.alerts:
                apptio.create_alert_rule(
                    budget_name=f"{service.name}-{env}",
                    threshold_percentage=alert.threshold,
                    severity=alert.severity,
                    channels=alert.channels,
                    frequency=alert.frequency
                )
        
        # 6. Store sync metadata
        update_sync_state(
            service_name=service.name,
            sync_status="success",
            sync_timestamp=now()
        )
```

---

## 9. Missing Pieces: What Needs Implementation

### 9.1 Backstage Template Enhancement

**File**: `backstage-templates/service-onboarding/template.yaml`

**Needs**: 
- Cost section with all mandatory fields
- Real-time validation
- Links to Finance team for cost center lookup
- Pre-populated budget estimates based on service size

### 9.2 Schema Definition

**File**: `schema/services-schema.json`

**Needs**:
- Complete JSON Schema for cost object
- Validation rules for all fields
- Enum values for business units
- Regex patterns for cost centers, channels

### 9.3 Validation Scripts

**Files needed**:
- `scripts/validate-catalog-schema.py` - Schema validation
- `scripts/validate-cost-fields.py` - Mandatory field checks
- `scripts/validate-budget-ranges.py` - Range validation
- `scripts/validate-cost-centers.py` - Apptio API verification
- `scripts/validate-notification-channels.py` - Channel format checks

### 9.4 Apptio Sync Service

**Location**: `services/apptio-sync/`

**Implements**:
- Git polling (every 5 minutes)
- YAML parsing
- Apptio API client
- Prometheus metrics
- Health checks

### 9.5 Kustomize Enhancement

**File**: `kustomize/overlays/*/kustomization.yaml`

**Enhancement**:
- Load service from catalog
- Extract cost profile for environment
- Inject cost.* labels into commonLabels

---

## 10. Cost Profile Lifecycle

### At Service Creation Time
- ✅ Cost profile defined in form
- ✅ All fields validated
- ✅ Cost center verified
- ✅ Budget amounts approved
- ✅ Alert thresholds set
- ✅ Notification channels configured

### At Catalog Update (Merge to Main)
- ✅ Schema validation passes
- ✅ Cost center still valid (re-checked)
- ✅ Apptio Sync triggered
- ✅ Budgets created in Apptio
- ✅ Alert rules configured
- ✅ Sync status logged

### At Deployment Time
- ✅ Cost labels injected by Kustomize
- ✅ All pods get cost.* labels
- ✅ Labels flow to GCP billing
- ✅ Apptio begins ingesting costs

### At Runtime (Day 1+)
- ✅ Costs accumulate in Apptio
- ✅ Budgets tracked in real-time
- ✅ Alerts fire at thresholds
- ✅ Team/owner notified
- ✅ Finance has visibility

---

## 11. Summary: The Mechanism

**Cost Profile Embedding Answer**:

When a service is added to the catalog via Backstage onboarding:

1. **Form captures** all cost parameters (budget, cost center, alerts)
2. **Generated entry** in `catalog/services.yaml` includes complete `cost` object
3. **Schema validates** the cost object structure and values
4. **CI/CD gates** prevent merge without valid cost configuration
5. **Apptio Sync** automatically creates budgets & alerts from catalog
6. **Kustomize** injects cost labels into deployed resources
7. **GCP billing** captures labels in daily exports
8. **Apptio** ingests costs and tracks against budgets
9. **Alerts** fire to teams when thresholds crossed
10. **Finance** sees costs broken down by service, team, cost center

**Result**: From day 1, cost management is integrated, not bolted-on.

---

**Next Steps**:
1. Implement services-schema.json with full cost definition
2. Create validation scripts referenced in CI/CD workflow
3. Update Backstage template with cost fields
4. Implement Apptio Sync Service (Kubernetes native)
5. Update Kustomize to extract and inject cost labels
6. Migrate existing services.yaml to include cost profiles

---

**Document Version**: 1.0
**Created**: 2025-11-15
**Status**: DRAFT - Ready for Implementation Planning
