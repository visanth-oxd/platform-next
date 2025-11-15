# Platform-Next: Complete Architecture with Cost Integration

**Document Type**: Architecture Overview + Integration Guide

**Audience**: Technical architects, platform engineers, finance teams

**Status**: ACTIVE - 2025-11-15

---

## Executive Summary

Platform-Next is a **complete service management platform** that seamlessly integrates:
- ✅ **Service Onboarding** (Backstage)
- ✅ **Configuration Management** (Kustomize)
- ✅ **Deployment Automation** (Harness)
- ✅ **Cost Tracking & Budget Management** (Apptio)

**Key Innovation**: Cost is integrated into the onboarding workflow, not bolted on afterward. This ensures every service has budget accountability from day 1.

---

## 1. Complete Architecture Overview

### 1.1 The Four-Component System

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: SERVICE CREATION (Backstage)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input:                                                          │
│  ✓ Service name, type, team                                    │
│  ✓ Estimated size (small/medium/large/xlarge)                  │
│  ✓ Service budgets (int-stable, pre-stable, prod)    [MANDATORY]
│  ✓ Cost center code (CC-XXXXX)                       [MANDATORY]
│  ✓ Business unit                                      [MANDATORY]
│  ✓ Cost owner (email)                                [MANDATORY]
│  ✓ Alert thresholds & channels                       [MANDATORY]
│                                                                  │
│  Process:                                                        │
│  1. Form validation (all cost fields required)                  │
│  2. Cost estimates shown (based on size)                        │
│  3. Confirmation of cost responsibility                         │
│  4. Create PR with full cost config                             │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: CATALOG & VALIDATION (Platform-Next Repo)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Catalog stores:                                                 │
│  ✓ Service metadata (archetype, profile, size, team)           │
│  ✓ Cost configuration (budgets, cost center, alerts)           │
│  ✓ Cost labels (service, team, cost-center, business-unit)    │
│                                                                  │
│  CI/CD Validation:                                               │
│  ✓ Schema validation (all required fields present)             │
│  ✓ Budget validation (realistic ranges: $50-$50K)              │
│  ✓ Cost center exists in Apptio                                │
│  ✓ Alert thresholds valid (50-110%)                            │
│  ✓ Teams channels format valid (#channel)                      │
│  ✓ Email addresses valid                                        │
│                                                                  │
│  Failure: PR cannot merge without valid cost config             │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: MANIFEST GENERATION (Kustomize CI)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each environment (int-stable, pre-stable, prod):           │
│                                                                  │
│  1. Load service from catalog                                   │
│  2. Validate cost config exists                                 │
│  3. Extract: budgets, cost labels                               │
│  4. Generate K8s manifests                                      │
│  5. Inject mandatory cost labels:                               │
│     - cost.service                                              │
│     - cost.team                                                 │
│     - cost.environment                                          │
│     - cost.costCenter                                           │
│     - cost.businessUnit                                         │
│     - cost.owner                                                │
│     - cost.budget                                               │
│  6. Commit to Git (versioned, auditable)                        │
│                                                                  │
│  Failure: Script exits if cost config missing                   │
│           (Cannot generate manifests without cost labels)       │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: COST SETUP (Apptio Sync - Automatic)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Trigger: When catalog is merged to main                        │
│                                                                  │
│  Cloud Function: budget-sync                                     │
│  1. Fetch catalog from platform-next                            │
│  2. For each service with cost config:                          │
│     a. Create Cloud Budget (per environment)                    │
│        • Amount: from budgets[env].monthly                      │
│        • Filter: cost.service label                             │
│        • Thresholds: 50%, 80%, 100%                             │
│     b. Store alert config in Apptio                             │
│        • Channels: Teams, email, PagerDuty                      │
│        • Severity: info, warning, critical                      │
│        • Frequency: once, daily, immediate                      │
│     c. Enable monitoring                                         │
│                                                                  │
│  Result: Budgets active in Apptio within 15 minutes             │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: DEPLOYMENT (Harness + GKE)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Deployment Process:                                             │
│  1. Developer opens Harness Console                             │
│  2. Selects pipeline for service                                │
│  3. Provides image tag                                          │
│  4. Harness fetches manifests from Git                          │
│     (Manifests already have cost labels)                        │
│  5. Injects image tag                                           │
│  6. Deploys to GKE cluster                                      │
│  7. Pods created with cost labels:                              │
│     • Labels attached to every pod                              │
│     • Labels inherited by all resources                         │
│                                                                  │
│  Cost Tracking Begins:                                           │
│  • GCP billing automatically includes labels                    │
│  • Apptio ingests labeled costs                                 │
│  • Cost allocation per service/team/cost-center starts          │
│  • Budgets monitoring active                                    │
│  • Alerts ready to fire                                         │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: COST MONITORING (Apptio)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Daily Operations:                                               │
│  1. GCP billing exports labeled costs                           │
│  2. Apptio ingests and allocates                                │
│  3. Cost visible per service/team/cost-center                   │
│  4. Budgets tracked against actuals                             │
│  5. Alerts fire when thresholds crossed:                        │
│     50% → Info alert to team channel                            │
│     80% → Warning to team + finance                             │
│     100% → Critical to leadership + email + PagerDuty           │
│  6. Optimization recommendations generated                      │
│  7. Chargeback data ready for Finance                           │
│                                                                  │
│  Monthly Reviews:                                                │
│  • Service teams review costs                                   │
│  • Finance reviews allocations                                  │
│  • Optimization recommendations actioned                        │
│  • Budgets adjusted if needed (via catalog PR)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow: From Creation to Cost Tracking

### 2.1 The Complete Journey

```
START: Developer Needs New Service
│
├─ Step 1: Access Backstage
│  └─ Click "Create Service" → Select "Kubernetes Service"
│
├─ Step 2: Fill Service Basics
│  ├─ Name: payment-service
│  ├─ Type: api
│  ├─ Team: payments-team
│  └─ Description: "Core payment processing"
│
├─ Step 3: MANDATORY - Cost & Budget Section
│  ├─ Size: Large ($1500 base estimate)
│  ├─ Budget Int: $800/month
│  ├─ Budget Pre: $2000/month
│  ├─ Budget Prod: $5000/month (CRITICAL)
│  ├─ Cost Center: CC-12345 (validated against Apptio)
│  ├─ Business Unit: retail-banking
│  ├─ Cost Owner: john.doe@company.com
│  ├─ Alert 50% → #team-payments (info)
│  ├─ Alert 80% → #team-payments, #finance (daily)
│  └─ Alert 100% → #leadership (critical, PagerDuty)
│
├─ Step 4: Confirm Cost Responsibility
│  ├─ ☑ "I understand cost implications"
│  └─ ☑ "I accept budget responsibility"
│
├─ Step 5: Submit Form
│  ├─ Backstage validates all cost fields
│  └─ Creates PR to platform-next repo
│
├─ Step 6: CI/CD Validation
│  ├─ Schema check: ✓ All cost fields present
│  ├─ Budget check: ✓ $800, $2000, $5000 realistic
│  ├─ Cost center check: ✓ CC-12345 exists in Apptio
│  ├─ Alert check: ✓ Thresholds 50%/80%/100%
│  └─ PR passes → Ready to merge
│
├─ Step 7: Merge to Main
│  └─ Catalog updated with full cost config
│
├─ Step 8: Apptio Sync (Automatic)
│  ├─ Cloud Function triggered
│  ├─ Parse catalog
│  ├─ Create budgets in Apptio:
│  │  ├─ payment-service-int-stable: $800/month
│  │  ├─ payment-service-pre-stable: $2000/month
│  │  └─ payment-service-prod: $5000/month
│  ├─ Store alert config
│  └─ Enable monitoring (15 mins)
│
├─ Step 9: Manifest Generation (CI)
│  ├─ Load service from catalog
│  ├─ Validate cost config exists
│  ├─ For each environment:
│  │  ├─ Generate K8s manifests
│  │  ├─ Inject cost labels
│  │  ├─ Commit to Git
│  │  └─ Versioned & auditable
│  └─ Manifests ready to deploy
│
├─ Step 10: Harness Pipeline Created
│  └─ Service ready to deploy
│
├─ Step 11: First Deployment
│  ├─ Developer: Open Harness → Select pipeline
│  ├─ Provide: Image tag v1.2.3
│  ├─ Harness: Fetch manifests from Git
│  ├─ Manifests: Already have cost labels
│  ├─ Harness: Inject image tag
│  ├─ Deploy: To GKE cluster
│  └─ Pods: Created with cost labels attached
│
├─ Step 12: Cost Labels → GCP Billing
│  ├─ Timeline: Next 24 hours
│  ├─ GCP: Exports labeled costs
│  └─ Labels: cost.service, cost.team, cost.costCenter, etc.
│
├─ Step 13: Apptio Ingestion
│  ├─ Timeline: 1-2 days after deployment
│  ├─ Apptio: Reads labeled costs from GCP
│  ├─ Allocation: By service, team, cost-center
│  └─ Budgets: Start monitoring against actuals
│
├─ Step 14: Cost Tracking Active
│  ├─ Real-time: Costs visible in Apptio
│  ├─ Budgets: Tracked daily
│  ├─ Alerts: Fire when thresholds crossed
│  ├─ Notifications: Teams, email, PagerDuty
│  └─ Optimization: Recommendations generated
│
└─ END: Service fully managed with cost tracking
   ✅ Cost config in catalog
   ✅ Labels in manifests
   ✅ Budgets in Apptio
   ✅ Monitoring active
   ✅ Alerts ready
   ✅ Cost owner assigned
   ✅ Finance has allocation data
```

---

## 3. Cost Config Schema (What Goes in Catalog)

```yaml
# catalog/services.yaml - Complete Example

services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    team: payments-team
    environments: [int-stable, pre-stable, prod]
    
    # ========================================
    # COST CONFIGURATION (Mandatory)
    # ========================================
    cost:
      enabled: true  # Must be true
      
      # Budgets per environment (all required)
      budgets:
        int-stable:
          monthly: 800              # $800/month
          costCenter: CC-12345
          businessUnit: retail-banking
        
        pre-stable:
          monthly: 2000             # $2000/month
          costCenter: CC-12345
          businessUnit: retail-banking
        
        prod:
          monthly: 5000             # $5000/month
          costCenter: CC-12345
          businessUnit: retail-banking
      
      # Alerts (at least 2 required)
      alerts:
        - name: budget-50-percent
          type: budget
          threshold: 50
          severity: info
          channels:
            teams: ["#team-payments"]
          frequency: once
        
        - name: budget-80-percent
          type: budget
          threshold: 80
          severity: warning
          channels:
            teams: ["#team-payments", "#platform-finops"]
            email: ["john.doe@company.com"]
          frequency: daily
        
        - name: budget-100-percent
          type: budget
          threshold: 100
          severity: critical
          channels:
            teams: ["#team-payments", "#platform-leadership"]
            email: ["cto@company.com"]
          frequency: immediate
          actions:
            pagerduty: true
      
      # Labels (auto-generated, but shown here for clarity)
      labels:
        cost.service: payment-service
        cost.team: payments-team
        cost.environment: prod  # Varies per deployment
        cost.costCenter: CC-12345
        cost.businessUnit: retail-banking
        cost.owner: john.doe@company.com
        cost.budget: "5000"
```

---

## 4. Label Injection in Manifests

### 4.1 How Labels Flow Through System

```
Catalog (services.yaml)
└─ cost.budgets[environment].costCenter: CC-12345
└─ cost.labels.cost.team: payments-team
└─ cost.labels.cost.service: payment-service
│
├─ Kustomize Generation (CI)
│  └─ Extract labels from catalog
│  └─ Inject into commonLabels
│
├─ Generated Manifest (Git - Versioned)
│  └─ commonLabels:
│     ├─ cost.service: payment-service
│     ├─ cost.team: payments-team
│     ├─ cost.costCenter: CC-12345
│     ├─ cost.businessUnit: retail-banking
│     └─ cost.environment: prod
│
├─ Harness Deployment
│  └─ Fetch manifest
│  └─ Inject image tag (keep all labels)
│  └─ Deploy to GKE
│
├─ GKE Resources
│  └─ All pods inherit labels
│  └─ cost.service, cost.team, cost.costCenter, etc.
│
├─ GCP Billing Export
│  └─ Daily export includes labels
│  └─ Every billing entry tagged with cost dimensions
│
└─ Apptio Ingestion
   └─ Read labels from GCP billing
   └─ Group costs by:
      ├─ Service (cost.service)
      ├─ Team (cost.team)
      ├─ Cost Center (cost.costCenter)
      ├─ Business Unit (cost.businessUnit)
      └─ Environment (cost.environment)
   
   └─ Match with budgets from catalog
   └─ Track spending against $800/$2000/$5000
   └─ Fire alerts at 50%/80%/100% thresholds
```

### 4.2 Example Generated Manifest

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml

apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: payment-service

# ================================================
# COST LABELS (Mandatory, injected by Kustomize)
# ================================================

commonLabels:
  # Functional labels
  app: payment-service
  version: v1
  
  # ========== COST ALLOCATION LABELS ==========
  # Read by GCP billing → Apptio for allocation
  cost.service: payment-service
  cost.team: payments-team
  cost.environment: prod
  cost.region: euw1
  cost.costCenter: CC-12345
  cost.businessUnit: retail-banking
  cost.owner: john.doe@company.com
  cost.budget: "5000"

commonAnnotations:
  cost.tracking.enabled: "true"
  cost.budget.monthly: "5000"
  cost.allocated.to: "payments-team"
```

---

## 5. Apptio Integration Points

### 5.1 How Apptio Gets Configured

```
Platform-Next Catalog
├─ Service: payment-service
├─ cost.budgets:
│  ├─ int-stable: $800
│  ├─ pre-stable: $2000
│  └─ prod: $5000
├─ cost.labels:
│  ├─ cost.costCenter: CC-12345
│  └─ cost.businessUnit: retail-banking
└─ cost.alerts:
   ├─ 50% → info
   ├─ 80% → warning
   └─ 100% → critical
│
├─ Cloud Function: budget-sync
│  └─ Read catalog
│  └─ Create in Apptio:
│     ├─ Budget: payment-service-int-stable, $800/month
│     ├─ Budget: payment-service-pre-stable, $2000/month
│     ├─ Budget: payment-service-prod, $5000/month
│     ├─ Thresholds: 50%, 80%, 100%
│     └─ Channels: Teams, email, PagerDuty
│
└─ Apptio Configuration Active
   ├─ Monitoring: 3 budgets per service
   ├─ Alerts: Ready to fire
   ├─ Notifications: Configured per threshold
   └─ Data: Allocating costs by labels
```

### 5.2 Alert Firing Example

```
GCP Billing
├─ Payment-service pods using resources
├─ Labels attached: cost.service=payment-service, cost.costCenter=CC-12345
├─ Daily costs tracked: Oct 1 = $160, Oct 2 = $165, Oct 3 = $170
└─ Month-to-date: Oct 15 = $2,400 (48% of $5000 monthly budget)

Apptio Monitoring
├─ Budget: $5000/month for payment-service-prod
├─ Current spend: $2,400
├─ Percentage: 48% (below all thresholds)
└─ Status: Healthy ✅

Scenario: Service auto-scales due to spike
├─ Oct 16: Traffic surge
├─ Pods scale from 5 to 50 replicas
├─ Daily cost jumps to $450
├─ Month-to-date now: Oct 16 = $2,850 (57%)

Apptio Monitoring
├─ Recalculates: 57% of budget used
├─ Still below 80% threshold
└─ Status: Monitoring

Scenario: Continues for 2 more days
├─ Oct 17: $450 → Month-to-date = $3,300 (66%)
├─ Oct 18: $450 → Month-to-date = $3,750 (75%)

Scenario: Oct 19 reaches 80% threshold
├─ Oct 19: $450 → Month-to-date = $4,200 (84%)
├─ Threshold crossed: 80% alert fires!

Apptio Actions:
├─ Alert type: Budget Warning
├─ Severity: warning
├─ Channels:
│  ├─ Teams: #team-payments, #platform-finops
│  ├─ Email: john.doe@company.com, finance@company.com
│  └─ Frequency: daily (won't repeat until next hour/day based on config)

Notifications Sent:
├─ Teams card in #team-payments:
│  └─ "⚠️ Budget Alert: payment-service"
│     "Current Cost: $4,200"
│     "Monthly Budget: $5,000"
│     "% Used: 84%"
│     "Status: WARNING - approaching limit"
│
├─ Teams card in #platform-finops:
│  └─ Same alert for finance review
│
└─ Emails sent:
   ├─ john.doe@company.com
   └─ finance@company.com

Team Response:
├─ John (cost owner) sees Teams alert
├─ Investigates: "Why the spike?"
├─ Finds: 50x scale-up in replicas
├─ Actions: Scale back to 10 replicas, investigate root cause
├─ Trend: Costs normalize back to $170/day

Scenario: Oct 20 continues high
├─ Oct 20: Sustained high cost
├─ Month-to-date: ~$4,650 (93%)

Scenario: Oct 21 reaches 100% threshold
├─ Oct 21: Small additional spike
├─ Month-to-date: $5,100 (102%)
├─ Budget exceeded! 100% threshold crossed

Apptio Actions:
├─ Alert type: Budget Critical
├─ Severity: critical
├─ Channels:
│  ├─ Teams: #team-payments, #platform-leadership
│  ├─ Email: john.doe@company.com, cto@company.com
│  ├─ PagerDuty: Create incident
│  └─ Frequency: immediate (escalate immediately)

Notifications Sent:
├─ Teams: CRITICAL notification to #team-payments
├─ Teams: CRITICAL notification to #platform-leadership
├─ Email: Critical alerts to john@, cto@
├─ PagerDuty: Incident created, pages on-call engineer

Leadership Response:
├─ CTO sees critical alert
├─ Escalates to VP Engineering
├─ Emergency meeting to address cost overrun
├─ Likely actions: Reduce service scope, optimize resources, negotiate increase
```

---

## 6. Four Enforcement Layers

### Layer 1: Form (Backstage)
- Cannot submit without filling all cost fields
- Real-time validation of amounts and formats
- Cost estimates shown to guide decisions
- Confirmation required

### Layer 2: Schema (Catalog)
- services.yaml must match JSON schema
- All cost fields required at schema level
- Budget ranges enforced ($50-$50K)
- Cost center format validated (CC-XXXXX)

### Layer 3: CI/CD (GitHub Actions)
- PRs validated against schema
- Cost validation tests run
- Cost centers checked against Apptio
- PR blocked if validation fails

### Layer 4: Manifest Generation (Kustomize)
- Script fails if cost config missing
- Cannot generate manifests without cost labels
- Labels must be present to deploy

**Result**: Cost config cannot be bypassed at any step.

---

## 7. Timeline: From Creation to Cost Tracking

```
Day 1 - Service Creation
├─ 9:00 AM - Developer fills Backstage form (15 min)
├─ 9:15 AM - CI validation (5 min)
├─ 9:20 AM - PR merged
└─ 9:22 AM - Apptio sync completes
   └─ Budgets created & active

Day 1 - Deployment
├─ 2:00 PM - Developer initiates deployment
├─ 2:05 PM - Manifests fetched (with cost labels)
├─ 2:07 PM - Pods deployed to GKE
└─ 2:08 PM - Cost labels active on pods

Days 2-3 - GCP Billing Export
├─ Oct 2 10 AM - GCP exports labeled costs
├─ Data includes cost.service, cost.team, cost.costCenter
└─ Apptio begins ingesting labeled costs

Days 3-4 - Cost Visible in Apptio
├─ Oct 3 - First full day of cost data
├─ Apptio: Allocates to payment-service
├─ Budget: Starts tracking $XXX/day against $5000/month
└─ Alerts: Monitoring active

Week 1+ - Cost Monitoring
├─ Real-time budget tracking
├─ Alerts fire when thresholds crossed
├─ Teams receive Teams/email notifications
├─ Cost owner responds to anomalies
├─ Finance has allocation data for chargeback

Month 1 - Monthly Review
├─ Service team reviews actual vs budgeted
├─ Optimization recommendations from Apptio
├─ Adjust budget if needed (via catalog PR)
├─ Finance reviews all allocations
└─ Plan for next month
```

---

## 8. Success Metrics

### Deployment Metrics
- ✅ 100% of services have cost config (mandatory)
- ✅ 100% of manifests have cost labels
- ✅ 100% of services have budgets in Apptio

### Cost Management Metrics
- ✅ Budget alerts fire at correct thresholds (50%, 80%, 100%)
- ✅ Costs visible in Apptio within 48 hours of deployment
- ✅ Chargeback data ready for Finance (cost center accurate)
- ✅ Optimization recommendations generated (right-sizing, RIs, etc.)

### FinOps Maturity
- ✅ Level 1: Visibility (all services tracked) ✓
- ✅ Level 2: Accountability (budgets per team/cost-center) ✓
- ✅ Level 3: Optimization (recommendations, right-sizing) ✓
- ✅ Level 4: Automation (auto-scaling, spot instances) 🔜

---

## 9. Key Documents

1. **[00_Architecture_decision.md](./00_Architecture_decision.md)** - Strategic decisions, 4-component architecture
2. **[06_COST_ONBOARDING.md](./06_COST_ONBOARDING.md)** - Detailed onboarding guide (READ FIRST for teams)
3. **[04_COST_MANAGEMENT_DESIGN.md](./04_COST_MANAGEMENT_DESIGN.md)** - Original cost design (OpenCost approach)
4. **[04b_COST_MANAGEMENT_GCP_NATIVE.md](./04b_COST_MANAGEMENT_GCP_NATIVE.md)** - GCP-native alternative (reference)

---

## 10. The Core Principle

**Cost management is not a feature you add after building your platform; it is a fundamental design principle that must be integrated from day 1.**

### Why This Matters
- ✅ **Financial accountability** - Teams own their costs from creation
- ✅ **Budget enforcement** - Apptio alerts prevent surprises
- ✅ **Chargeback ready** - Finance can allocate immediately
- ✅ **FinOps culture** - Cost is everyone's responsibility
- ✅ **Optimization** - Apptio identifies savings opportunities
- ✅ **Compliance** - Audit trail of all cost allocations

### How We Achieve It
1. Make cost config mandatory in onboarding form
2. Validate cost fields in schema
3. Enforce via CI/CD gates
4. Inject labels automatically
5. Sync to Apptio automatically
6. Monitor continuously

---

## 11. Summary

**Platform-Next delivers:**

| Component | Purpose | Technology |
|-----------|---------|-----------|
| Onboarding | Service creation | Backstage (with mandatory cost section) |
| Configuration | K8s config-as-code | Kustomize + Platform-Next Repo |
| Deployment | CD automation | Harness |
| Cost Tracking | Budget & optimization | Apptio (via label-based allocation) |

**Integration**: Cost is woven throughout, not bolted on.

**Result**: Every service has cost visibility, budget accountability, and optimization recommendations from day 1.

---

**Document Status**: ✅ Complete

**Last Updated**: 2025-11-15

**For Questions**: See related documents or contact platform team

