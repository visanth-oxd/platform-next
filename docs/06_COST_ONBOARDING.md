# Cost Metrics in Service Onboarding - Mandatory Integration

**Status**: ACCEPTED - 2025-11-15

**Document Type**: Operational Guide + Technical Specification

**Audience**: 
- Development teams onboarding services
- Platform engineers implementing cost tracking
- Finance & FinOps teams

---

## Executive Summary

Cost management is **not an afterthought** in Platform-Next. Every service **must** define budgets, cost allocation parameters, and alert thresholds **at onboarding time**.

This document defines:
- How cost metrics become mandatory in the onboarding workflow
- How to configure budgets per environment
- How alerts are automatically set up in Apptio
- How cost tracking begins at deployment, not after

**Key Principle**: *Separate cost setup from service creation and you get neither cost control nor compliance visibility. Integrate cost directly into onboarding and you get both from day 1.*

---

## 1. Cost Onboarding: Three Enforcement Layers

### 1.1 Layer 1: User Interface Enforcement (Backstage Template)

**Purpose**: Make cost configuration mandatory at the point of service creation

**Implementation**: The Backstage template has four sections:
1. Service Basics (required)
2. **💰 Cost & Budget Configuration (MANDATORY - cannot skip)**
3. Cost Optimization Preferences
4. Review & Confirm

**Cost Section Fields** (All REQUIRED):

```
SECTION: 💰 Cost & Budget Configuration (REQUIRED)

┌─────────────────────────────────────────────────────────┐
│ Service Size Estimation                                │
├─────────────────────────────────────────────────────────┤
│ Estimated Size: [Small ▼]                              │
│                                                         │
│ This determines baseline cost estimate:                │
│ • Small: $100-200/month (simple stateless API)         │
│ • Medium: $300-500/month (mid-tier, moderate traffic)  │
│ • Large: $800-1500/month (complex, high traffic)       │
│ • XLarge: $2000+/month (heavy compute, real-time)      │
│                                                         │
│ ℹ️ Estimated Monthly Cost (Auto-calculated):           │
│   Based on 'Large' size:                               │
│   • Int-Stable: $500-800/month                         │
│   • Pre-Stable: $800-1200/month                        │
│   • Production: $1200-2000/month                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Budget Configuration (Per Environment)                  │
├─────────────────────────────────────────────────────────┤
│ Budget for Int-Stable (USD/month):                     │
│ [$800____] (Range: $50-$5000)                          │
│ ⚠️ Set 20-30% higher than estimate                      │
│                                                         │
│ Budget for Pre-Stable (USD/month):                     │
│ [$2000___] (Range: $100-$10000)                        │
│                                                         │
│ Budget for Production (USD/month):                     │
│ [$5000___] (Range: $200-$50000)                        │
│ 🚨 CRITICAL: This is your safety net. Set realistically│
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Cost Center & Business Allocation                       │
├─────────────────────────────────────────────────────────┤
│ Cost Center Code: [CC-12345____] (Format: CC-XXXXX)    │
│ ⓘ Required for chargeback. Get from Finance team.      │
│                                                         │
│ Business Unit: [Retail-Banking ▼]                      │
│ Options:                                               │
│  - retail-banking                                      │
│  - wealth-management                                   │
│  - corporate-banking                                   │
│  - technology                                          │
│  - operations                                          │
│                                                         │
│ Cost Owner: [john.doe@company.com__]                   │
│ ⓘ Usually tech lead. Will receive cost alerts.         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Alert Thresholds & Notification Channels               │
├─────────────────────────────────────────────────────────┤
│ Warning Threshold: [80% ▼]                             │
│ When to alert: 70%, 75%, 80%, 85%, 90%                │
│ ⓘ Gives time to investigate before hitting limit       │
│                                                         │
│ Critical Threshold: [100% ▼]                           │
│ When to alert: 95%, 100%, 105%, 110%                  │
│ ⓘ 100% = exactly at budget limit                       │
│                                                         │
│ Teams Channel for Warnings (80%):                      │
│ [#team-payments_____] (Format: #channel-name)          │
│                                                         │
│ Teams Channels for Critical (100%):                    │
│ [#team-payments_____] [+] (Add multiple)               │
│ [#platform-leadership] [+]                             │
│ [#finance-ops_______] [+]                              │
│                                                         │
│ Email for Critical Alerts:                             │
│ [john.doe@company.com_]                                │
│ ⓘ Will also notify via email when critical             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Cost Optimization Preferences                          │
├─────────────────────────────────────────────────────────┤
│ ☑ Enable Auto-Scaling (HPA)                            │
│   Reduces costs during low-traffic periods             │
│                                                         │
│ ☐ Allow Spot Instances (Dev/Test only)                 │
│   70% cheaper, but 2-3hr interruption window           │
│                                                         │
│ ☑ Allow Automated Right-Sizing                         │
│   Apptio can recommend downsizing if CPU/mem < 40%    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Cost Responsibility Confirmation                       │
├─────────────────────────────────────────────────────────┤
│ ☐ I understand the cost implications                    │
│   □ Confirm you've reviewed estimates                   │
│   □ Confirm budgets are approved by Finance            │
│   □ Confirm you'll monitor costs regularly              │
│   □ Confirm you understand cost alerts                  │
│                                                         │
│ ☐ I accept responsibility for cost management          │
│   □ Team leads will receive cost alerts                │
│   □ Budget overruns require management approval        │
│   □ Will investigate spikes & optimize                 │
│   □ Cost is treated as seriously as reliability        │
└─────────────────────────────────────────────────────────┘
```

**Validation in Form**:
- Cannot proceed to next section without completing all cost fields
- Real-time validation of:
  - Cost center format (CC-XXXXX)
  - Budget amounts (min/max ranges)
  - Email format
  - Teams channel format (#channel-name)
- Cost owner must exist in directory
- Both confirmation checkboxes required

---

### 1.2 Layer 2: Schema Validation (Catalog Data)

**Purpose**: Enforce cost configuration in the actual catalog file

**Schema Location**: `platform-next/schema/services-schema.json`

**Key Requirements**:

```json
{
  "services": {
    "type": "array",
    "items": {
      "required": [
        "name",
        "archetype",
        "team",
        "metadata",
        "cost"
      ],
      
      "properties": {
        "cost": {
          "type": "object",
          "required": ["enabled", "budgets", "alerts"],
          
          "properties": {
            "enabled": {
              "type": "boolean",
              "const": true,
              "description": "Cost tracking MUST be enabled"
            },
            
            "budgets": {
              "type": "object",
              "required": ["int-stable", "pre-stable", "prod"],
              
              "properties": {
                "int-stable": {
                  "type": "object",
                  "required": ["monthly", "costCenter", "businessUnit"],
                  "properties": {
                    "monthly": {
                      "type": "number",
                      "minimum": 50,
                      "maximum": 5000
                    }
                  }
                },
                "pre-stable": {
                  "type": "object",
                  "required": ["monthly", "costCenter", "businessUnit"],
                  "properties": {
                    "monthly": {
                      "type": "number",
                      "minimum": 100,
                      "maximum": 10000
                    }
                  }
                },
                "prod": {
                  "type": "object",
                  "required": ["monthly", "costCenter", "businessUnit"],
                  "properties": {
                    "monthly": {
                      "type": "number",
                      "minimum": 200,
                      "maximum": 50000,
                      "description": "Production budget minimum $200/month"
                    }
                  }
                }
              }
            },
            
            "alerts": {
              "type": "array",
              "minItems": 2,
              "description": "Must have at least 2 alerts (warning + critical)",
              "items": {
                "type": "object",
                "required": ["name", "type", "threshold", "severity", "channels"]
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

### 1.3 Layer 3: CI/CD Enforcement

**Purpose**: Reject catalog updates that don't include proper cost configuration

**Workflow**: `.github/workflows/validate-cost-metrics.yml`

```yaml
Validation Chain:
├── Schema Validation
│   └─ Does catalog match services-schema.json?
├── Mandatory Field Check
│   ├─ Every service has cost.enabled = true
│   ├─ Every service has budgets for all environments
│   ├─ Every service has at least 2 alert rules
│   └─ Every service has cost.apptioLabels
├── Budget Amount Validation
│   ├─ Int budget: $50-$5000
│   ├─ Pre budget: $100-$10000
│   ├─ Prod budget: $200-$50000
│   └─ Budget progression makes sense (pre > int, prod > pre)
├── Alert Threshold Validation
│   ├─ Thresholds between 50-110%
│   ├─ At least one warning (<100%)
│   ├─ At least one critical (>=100%)
│   └─ Warning threshold < Critical threshold
├── Cost Center Verification
│   ├─ Format CC-XXXXX
│   └─ Exists in Apptio (API call)
└── Notification Channels Validation
    ├─ Teams channels format: #channel-name
    ├─ Email addresses valid
    └─ At least one channel per alert
```

**Failure Behavior**: PR blocked, cannot merge without fixing cost config

---

### 1.4 Layer 4: Manifest Generation (Kustomize)

**Purpose**: Ensure cost labels are injected into every deployed resource

**Script**: `platform-next/scripts/generate-kz-v3.sh`

```bash
Validation Flow:
├── Load service from catalog
├── Check: Does service exist?
├── Check: Is cost.enabled = true?
│   └─ FAIL: Exit with error if false
├── Extract: cost.budgets for environment
│   └─ FAIL: Exit with error if environment budget missing
├── Extract: metadata (costCenter, businessUnit, costOwner)
│   └─ FAIL: Exit with error if any missing
├── Generate: kustomization.yaml
├── Inject: Mandatory cost labels
│   ├─ cost.service
│   ├─ cost.team
│   ├─ cost.environment
│   ├─ cost.costCenter
│   ├─ cost.businessUnit
│   ├─ cost.owner
│   └─ cost.budget
└── Success: Manifests generated with cost labels

If any cost config missing:
└─ ❌ ERROR: Generate script fails
   └─ Deployment cannot proceed
   └─ User must update catalog with cost config
```

---

### 1.5 Layer 5: Apptio Sync (Automatic Setup)

**Purpose**: Create budgets and alerts in Apptio without manual intervention

**Trigger**: When catalog is merged to main branch

```
Workflow:
├── Cloud Function: budget-sync triggered
├── Fetch: Latest catalog from platform-next
├── Parse: Every service with cost config
└── For each service:
    ├── Create: Cloud Budget (per environment)
    │   ├─ budget-name: {service}-{environment}
    │   ├─ amount: {budgets[environment].monthly}
    │   └─ filters: cost.service label
    ├── Store: Alert config in BigQuery
    │   └─ Table: cost_analytics.service_alert_config
    └── Result: Service immediately monitored in Apptio
```

---

## 2. Service Catalog Integration

### 2.1 Example Catalog Entry (Complete)

```yaml
# catalog/services.yaml

services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    team: payments-team
    environments: [int-stable, pre-stable, prod]
    description: "Core payment processing service"
    
    # ====================================================
    # METADATA SECTION (Required for cost allocation)
    # ====================================================
    metadata:
      costCenter: CC-12345           # For chargeback
      businessUnit: retail-banking    # For reporting
      costOwner: john.doe@company.com # Cost responsible person
      estimatedSize: large
      autoScaling: true
      spotInstances: false
      rightsizingAllowed: true
    
    # ====================================================
    # COST CONFIGURATION SECTION (Mandatory)
    # Every service MUST have this section
    # ====================================================
    cost:
      enabled: true                   # Must be true
      
      # Per-environment budgets (all required)
      budgets:
        int-stable:
          monthly: 800                # $800/month
          costCenter: CC-12345
          businessUnit: retail-banking
        
        pre-stable:
          monthly: 2000               # $2000/month
          costCenter: CC-12345
          businessUnit: retail-banking
        
        prod:
          monthly: 5000               # $5000/month
          costCenter: CC-12345
          businessUnit: retail-banking
      
      # Alert thresholds and routing (at least 2 required)
      alerts:
        # Info-level alert at 50%
        - name: cost-info-threshold
          type: budget
          threshold: 50
          severity: info
          channels:
            teams: ["#team-payments"]
          frequency: once
        
        # Warning-level alert at 80%
        - name: cost-warning-threshold
          type: budget
          threshold: 80
          severity: warning
          channels:
            teams: ["#team-payments", "#platform-finops"]
            email: ["john.doe@company.com", "finance@company.com"]
          frequency: daily
        
        # Critical alert at 100%
        - name: cost-critical-threshold
          type: budget
          threshold: 100
          severity: critical
          channels:
            teams: ["#team-payments", "#platform-leadership"]
            email: ["john.doe@company.com", "cto@company.com"]
          frequency: immediate
          actions:
            pagerduty: true           # Create PagerDuty incident
      
      # Labels sent to Apptio (auto-populated)
      apptioLabels:
        cost.service: payment-service
        cost.team: payments-team
        cost.environment: dynamic      # Changes per deployment
        cost.costCenter: CC-12345
        cost.businessUnit: retail-banking
        cost.owner: john.doe@company.com
```

---

## 3. Onboarding Workflow: Step-by-Step

### 3.1 Complete Flow Diagram

```
┌─────────────────────────────────────────────┐
│ Step 1: Access Backstage                    │
│ "Create Service" → Kubernetes Service       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 2: Fill Service Basics Section         │
│ • Name: payment-service                     │
│ • Type: api                                 │
│ • Team: payments-team                       │
│ • Description: "Core payment processing"    │
│                                             │
│ [Next →]                                    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 3: MANDATORY - Cost & Budget Config    │
│                                             │
│ Service Size: [Large ▼]                     │
│   → Shows estimate: $1200-2000/month        │
│                                             │
│ Budget Int: [$800]   (Min: $50, Max: $5K)   │
│ Budget Pre: [$2000]  (Min: $100, Max: $10K) │
│ Budget Prod: [$5000] (Min: $200, Max: $50K) │
│                                             │
│ Cost Center: [CC-12345] (Format required)   │
│ Business Unit: [retail-banking ▼]           │
│ Cost Owner: [john.doe@company.com]          │
│                                             │
│ Warning Threshold: [80% ▼]                  │
│ Critical Threshold: [100% ▼]                │
│                                             │
│ Alert Channels:                             │
│   Warning → #team-payments                  │
│   Critical → #team-payments, #leadership    │
│                                             │
│ Email Alerts: john.doe@company.com          │
│                                             │
│ Cannot skip this section ⚠️                 │
│ [Back] [Next →]                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 4: Cost Optimization Preferences       │
│                                             │
│ ☑ Auto-Scaling (HPA)                        │
│   Reduces cost during low-traffic           │
│                                             │
│ ☐ Spot Instances                            │
│   70% cheaper, but can interrupt            │
│                                             │
│ ☑ Auto Right-Sizing                         │
│   Downsize if under-utilized                │
│                                             │
│ [Back] [Next →]                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 5: Review & Confirm                    │
│                                             │
│ 📊 SUMMARY:                                 │
│ ─────────────────────────────────────────── │
│ Service: payment-service                    │
│ Team: payments-team                         │
│                                             │
│ ANNUAL COST PROJECTION:                     │
│ $108,000 ($9.6K int + $24K pre + $60K prod)│
│                                             │
│ BUDGETS:                                    │
│ • Int-Stable: $800/month                    │
│ • Pre-Stable: $2000/month                   │
│ • Production: $5000/month                   │
│                                             │
│ ALERT ROUTING:                              │
│ • 80% → #team-payments (daily)              │
│ • 100% → #team-payments, #leadership        │
│         john.doe@company.com                │
│                                             │
│ ☐ I understand cost implications            │
│ ☐ I accept budget responsibility            │
│                                             │
│ [Back] [Create Service →]                   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 6: CI/CD Validation                    │
│                                             │
│ ✅ Schema validation: PASS                  │
│ ✅ Cost fields mandatory: PASS              │
│ ✅ Budget amounts realistic: PASS           │
│ ✅ Alert thresholds valid: PASS             │
│ ✅ Cost center exists: PASS                 │
│                                             │
│ PR created: #1234                           │
│ Title: "feat: onboard payment-service"      │
│                                             │
│ Ready for review                            │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 7: Merge PR                            │
│                                             │
│ Catalog updated in main branch              │
│ Workflow triggered: sync-to-apptio          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 8: Apptio Sync (Automatic)             │
│                                             │
│ Cloud Function: budget-sync                 │
│ • Parse catalog/services.yaml               │
│ • Create 3 budgets (int, pre, prod)         │
│ • Store alert config                        │
│ • Enable monitoring                         │
│                                             │
│ ✅ Apptio now tracking costs               │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ Step 9: Service Ready for Deployment        │
│                                             │
│ • Cost config in catalog ✅                 │
│ • Budgets created in Apptio ✅              │
│ • Alerts configured ✅                      │
│ • Ready to deploy ✅                        │
│                                             │
│ When deployed:                              │
│ • Kustomize injects cost labels             │
│ • K8s resources tagged with cost.*           │
│ • GCP billing includes labels               │
│ • Apptio allocates costs                    │
│ • Cost tracking begins immediately          │
└─────────────────────────────────────────────┘
```

---

## 4. Budget Guidelines & Examples

### 4.1 Sizing & Cost Estimates

| Size | Cores | Memory | Monthly Cost | Per Environment |
|------|-------|--------|--------------|-----------------|
| **Small** | 0.5 | 512Mi | $100-200 | Int: $100, Pre: $150, Prod: $300 |
| **Medium** | 1.0 | 1Gi | $300-500 | Int: $300, Pre: $600, Prod: $1200 |
| **Large** | 2.0 | 2Gi | $800-1500 | Int: $800, Pre: $1500, Prod: $5000 |
| **XLarge** | 4.0 | 4Gi | $2000-3000 | Int: $2000, Pre: $4000, Prod: $8000 |

**Costs include**:
- CPU & Memory (compute)
- Storage (persistent volumes)
- Network (egress)
- Platform overhead

**Excludes** (if not used):
- GPUs, TPUs
- External databases
- Additional services

---

### 4.2 Budget Setting Strategy

**Formula for Each Environment**:

```
Base Cost (from size estimate)
+ 25% Buffer (account for peaks)
+ 10% Platform overhead
─────────────────────────────────
= Recommended Budget
```

**Example: Large Service**

```
Base estimate: $1500
+ 25% buffer: $375
+ 10% overhead: $150
────────────────────
= $2025 monthly

Set as: $2500 (round up)
```

**Per Environment Allocation**:

```
Total Monthly: $6000

Typical split:
• Int-Stable: 10% = $600
• Pre-Stable: 25% = $1500
• Production: 65% = $3900

Set as:
• Int: $800 (20% buffer)
• Pre: $1500
• Prod: $5000 (28% buffer)
```

---

### 4.3 Real-World Examples

#### Example 1: Payment Service (Large API)

```yaml
Service: payment-service
Archetype: API
Size: Large
Environment: Multi-region production

Cost Allocation:
  Cost Center: CC-12345 (Retail Banking)
  Business Unit: retail-banking
  Owner: payments-lead@company.com

Budgets:
  Int-Stable: $800/month
    (Simple testing, few replicas)
  
  Pre-Stable: $2000/month
    (Mirror prod, full replication)
  
  Production: $5000/month
    (Multi-region, 10-50 replicas, HA)

Alerts:
  50% ($2500) → #team-payments (info, once)
  80% ($4000) → #team-payments, #finance (daily)
  100% ($5000) → #leadership (immediate, PagerDuty)

Total Annual: $84,000
```

#### Example 2: Background Worker (Medium)

```yaml
Service: fraud-detection
Archetype: Worker
Size: Medium
Environment: Batch processing

Cost Allocation:
  Cost Center: CC-20001 (Risk Management)
  Business Unit: operations
  Owner: fraud-team@company.com

Budgets:
  Int-Stable: $200/month
    (Low volume testing)
  
  Pre-Stable: $400/month
    (Dev data set)
  
  Production: $1200/month
    (Full production batch, hourly jobs)

Alerts:
  50% ($600) → #team-fraud (info, once)
  80% ($960) → #team-fraud, #finance (daily)
  100% ($1200) → #leadership (immediate)

Total Annual: $19,200
```

#### Example 3: Internal Tool (Small)

```yaml
Service: metrics-exporter
Archetype: Tool
Size: Small
Environment: Single environment

Cost Allocation:
  Cost Center: CC-50001 (Technology)
  Business Unit: technology
  Owner: platform-team@company.com

Budgets:
  Int-Stable: $100/month
  Pre-Stable: $150/month
  Production: $300/month

Alerts:
  80% → #platform-team (daily)
  100% → #platform-leadership (immediate)

Total Annual: $6,600
```

---

## 5. Alert Threshold Strategy

### 5.1 Recommended Alert Levels

```
Budget Threshold   Severity    Channel(s)              Action
──────────────────────────────────────────────────────────────
50%               INFO        Team channel            Monitor trend
                              (once, no daily repeat)

80%               WARNING     Team + Finance          Investigate
                              (daily digest)          & optimize

100%              CRITICAL    Team + Leadership       STOP spending
                              + Email + PagerDuty     Block deploys
                              (immediate)
```

### 5.2 Notification Channels

**Teams Channels**:
- `#team-{name}`: Service team channel (always)
- `#platform-finops`: Finance/FinOps team (for warning+)
- `#platform-leadership`: C-level visibility (critical only)

**Email**:
- `{service-owner}@company.com`: Cost owner (always at critical)
- `{team-lead}@company.com`: Technical lead (warning+)
- `finance-operations@company.com`: Finance team (critical only)

**PagerDuty**:
- Only for critical alerts (100% threshold)
- Creates immediate incident
- Pages on-call engineering

---

## 6. Cost Center Management

### 6.1 Getting a Cost Center Code

**Format**: `CC-XXXXX` (must match exactly)

**Examples**:
- `CC-10001` = Finance Department
- `CC-20001` = Retail Banking
- `CC-30001` = Technology
- `CC-40001` = Operations
- `CC-50001` = Risk Management

**Process**:
1. Identify which department/cost center owns the service
2. Contact Finance team for the code
3. Verify code exists in Apptio before using
4. Use in service onboarding

**Validation**: During CI/CD, platform verifies cost center exists in Apptio

---

## 7. Common Scenarios & How to Handle

### 7.1 "My service will scale from 2 to 50 replicas"

**Approach**:
```
Estimate max cost: 50 replicas * $100/month = $5000
Add 30% safety buffer: $5000 * 1.3 = $6500

Set Budget: $7000
Alert thresholds:
  80% ($5600) → Warning
  100% ($7000) → Critical, block new deploys
```

### 7.2 "Budget rejected - unrealistic"

**Solution**:
- Small service: Cannot budget $20K
- Medium service: Cannot budget $30K
- Check size estimate
- Adjust to reasonable range
- Contact Finance for exception (VP approval needed)

### 7.3 "I don't know which cost center"

**Solution**:
```
1. Identify service owner (team/department)
2. Email Finance: "What's the cost center for [team]?"
3. Wait for response (usually < 24 hours)
4. Use that code in onboarding
5. Cannot proceed without valid code
```

### 7.4 "Alerts not firing in Teams"

**Debug Steps**:
```
1. Check: Team channel exists (#team-payments)
2. Check: Service is in catalog with cost.enabled=true
3. Check: Apptio sync completed (check logs)
4. Check: Budget created in Apptio
5. Check: Cost has started (takes 24 hours for first data)

If still not working:
  → Contact platform team
  → Provide: service name, cost center, team channel name
```

### 7.5 "We need to change budgets"

**Process**:
```
1. Edit catalog/services.yaml
2. Update budget amounts
3. Create PR, get approved
4. Merge to main
5. Apptio sync runs (auto, ~15 mins)
6. New budgets active in Apptio
```

---

## 8. After Onboarding: Day 1 & Beyond

### 8.1 Deployment Day

When you deploy the service:

```
1. Kustomize generates manifests
   └─ Injects cost labels automatically
   
2. Manifests deployed to GKE
   └─ All pods get cost.* labels
   
3. GCP billing includes labels
   └─ Automatic daily export
   
4. Apptio ingests costs
   └─ Allocates to service/team/cost-center
   
5. Cost tracking begins
   └─ Data visible in Apptio dashboard
```

### 8.2 Day 1-7: Baseline Collection

```
• Apptio collects usage data
• First full week of costs captured
• Helps refine budget estimates
• Identify actual usage patterns
```

### 8.3 Week 2+: Alert Monitoring

```
• Alerts start firing when thresholds crossed
• Teams see notifications
• Cost owner responds
• Optimization recommendations generated
```

### 8.4 Monthly: Review & Adjust

```
Action Items:
□ Review actual vs budgeted costs
□ Adjust replicas/resources if needed
□ Implement optimization recommendations
□ Update budget if needed (via PR)
□ Document learnings
```

---

## 9. Troubleshooting Guide

### Problem: Form won't submit - "Cost section required"

**Cause**: Missing or invalid cost fields
**Solution**: 
- Check all cost fields are filled
- Validate budget amounts (min/max ranges)
- Verify cost center format: CC-XXXXX
- Ensure email is valid
- Check Teams channel: #channel-name

---

### Problem: CI/CD fails - "Cost config invalid"

**Cause**: Catalog schema validation failure
**Solution**:
```bash
# Run validation locally
python scripts/validate-catalog-schema.py \
  --catalog catalog/services.yaml \
  --schema schema/services-schema.json

# Check output for specific errors
# Fix issues and push again
```

---

### Problem: Manifest generation fails - "Cost config missing"

**Cause**: Service not found in catalog or cost.enabled = false
**Solution**:
- Verify service exists in catalog
- Check: `cost.enabled: true`
- Check: Budget exists for environment

---

### Problem: Budgets not appearing in Apptio

**Cause**: Apptio sync hasn't run yet
**Solution**:
```
Timeline:
• PR merged → Sync workflow triggered (immediate)
• Sync runs → 2-5 minutes
• Budgets created → 1-2 minutes more
• Visible in Apptio → 5-15 minutes after creation

If no budgets after 20 minutes:
1. Check workflow logs in GitHub
2. Check Apptio connection status
3. Verify cost center exists in Apptio
4. Contact platform team
```

---

### Problem: Service costs not showing in Apptio

**Cause**: Labels not flowing through to GCP billing
**Solution**:
```
Check:
1. Service deployed? (pods running)
2. Cost labels on pods?
   → kubectl get pods -L cost.service,cost.team
3. Labels in GCP? (takes 24 hours)
4. In Apptio? (takes 1-2 days)

Typical timeline:
• Deploy at 10 AM
• Labels visible on pods: immediate
• In GCP billing export: next day (around 10 AM)
• In Apptio: day after (1-2 days total)
```

---

## 10. FAQ

### Q: Can I skip the cost section?
**A**: No. The form will not let you proceed without completing all cost fields. Cost management is mandatory.

---

### Q: What if I don't know the right budget?
**A**: Use the size-based estimate from the form, then add 25%. You can adjust later by editing the catalog. The budget is not locked.

---

### Q: Who should be the cost owner?
**A**: Usually:
- Tech Lead (responsible for resource optimization)
- Engineering Manager (approves budget changes)
- Team Lead (receives alerts)

---

### Q: Can I have multiple alert channels?
**A**: Yes. For critical alerts, it's common to have:
- `#team-payments` (team discussion)
- `#platform-leadership` (C-level visibility)
- `email:lead@company.com` (direct notification)
- `pagerduty:on-call` (immediate escalation)

---

### Q: When do costs start showing?
**A**: 
- Cost labels on pods: Immediate (after deployment)
- In GCP Billing: ~24 hours
- In Apptio: 1-2 days
- Alerts firing: After 2-3 days of data

---

### Q: Can I change budgets after onboarding?
**A**: Yes. Edit catalog → Create PR → Merge. Changes sync to Apptio within 15 minutes. No impact to running service.

---

### Q: What if my service is free tier?
**A**: Set minimum budget ($50-100). Even free-tier services should have budgets to catch unexpected costs.

---

### Q: Do I need different budgets per environment?
**A**: Yes, required. Typical split:
- Int: 10% of prod
- Pre: 30% of prod
- Prod: 60% of prod (or full budget)

---

## 11. Related Documentation

- **Architecture Decision**: [00_Architecture_decision.md](./00_Architecture_decision.md)
- **Cost Management Design**: [04_COST_MANAGEMENT_DESIGN.md](./04_COST_MANAGEMENT_DESIGN.md)
- **GCP Native Tools**: [04b_COST_MANAGEMENT_GCP_NATIVE.md](./04b_COST_MANAGEMENT_GCP_NATIVE.md)
- **Apptio Integration**: [Apptio API Guide](https://docs.apptio.com/api)
- **Kustomize Configuration**: [02_KUSTOMIZE_CONFIG_MANAGEMENT.md](./02_KUSTOMIZE_CONFIG_MANAGEMENT.md)

---

## 12. Summary

**Cost metrics are integrated into Platform-Next at the onboarding stage, not added afterward:**

1. **UI Enforcement** (Backstage): Form requires cost fields
2. **Data Validation** (Schema): Catalog enforces structure
3. **CI/CD Gates**: PRs blocked without cost config
4. **Code Generation** (Kustomize): Labels injected automatically
5. **Auto-Setup** (Apptio): Budgets created without manual intervention

**Result**: From day 1, every service has:
- ✅ Defined budgets
- ✅ Cost allocation
- ✅ Alert thresholds
- ✅ Monitoring in Apptio
- ✅ Cost tracking visibility

**This transforms cost management from an afterthought to a core platform capability.**

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: ACTIVE
