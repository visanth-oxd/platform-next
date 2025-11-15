# Cost Management with Profiles - Complete Guide

**Status**: ACTIVE

**Document Type**: Operational Guide + Technical Specification

**Audience**: 
- Development teams onboarding services
- Platform engineers implementing cost tracking
- Finance & FinOps teams

---

## Executive Summary

Cost management is integrated into Platform-Next using **cost profiles** - reusable templates that define budgets, alerts, and cost policies. Every service references a profile and specifies only essential cost allocation parameters (cost center, business unit, owner).

**Key Principle**: Cost configuration scales through templates, not repetition. 100 services share 6 profiles instead of each defining 40+ lines of cost configuration.

---

## 1. Cost Architecture

### 1.1 Core Components

```
Service Definition (services.yaml)
    ↓
    ├─ References: costProfile: "standard-api-cost"
    ├─ Specifies: size: "large" (multiplier for budgets)
    └─ Provides: costCenter, businessUnit, costOwner
    
         ↓
    
Cost Profile (cost-profiles.yaml)
    ├─ Budget base amounts + scaling factors
    ├─ Alert thresholds & channels (with variables)
    └─ Optimization preferences
    
         ↓
    
Expansion Engine (at validation time)
    ├─ Calculate budgets: base × size-multiplier
    ├─ Substitute variables: {service}, {costOwner}, etc.
    └─ Generate complete cost config
    
         ↓
    
Apptio Sync
    ├─ Create budgets in Apptio
    ├─ Configure alert rules
    └─ Enable cost tracking
```

### 1.2 Size-Based Budget Multipliers

Services are sized (small, medium, large, xlarge, xxlarge) and cost scales accordingly:

```
Size Multiplier:
├─ small:    0.3×  (1/3 of profile base)
├─ medium:   1.0×  (standard)
├─ large:    2.0×  (2× standard)
├─ xlarge:   3.5×  (3.5× standard)
└─ xxlarge:  6.0×  (6× standard)
```

Example: **standard-api-cost** profile with **large** service
```
Int-Stable:  base=$500  × 2.0 = $1,000/month
Pre-Stable:  base=$1500 × 2.0 = $3,000/month
Production:  base=$3000 × 2.0 = $6,000/month
```

---

## 2. Cost Profiles Catalog

### 2.1 Profile Overview

Each profile defines a **cost policy template** for similar service types. Profiles live in `kustomize/catalog/cost-profiles.yaml`.

| Profile | Use Case | Base Budget (Prod) | Alert Frequency |
|---------|----------|-------------------|-----------------|
| `standard-api-cost` | REST APIs, typical workloads | $3000 | Daily warnings, immediate critical |
| `premium-api-cost` | High-traffic, mission-critical | $6000 | Proactive monitoring (70% warning) |
| `batch-job-cost` | One-off batch processing | $1200 | Standard (80% warning) |
| `internal-tool-cost` | Internal utilities | $300 | Minimal monitoring |
| `ml-workload-cost` | ML training/inference | $8000 | Spike detection at 50% |
| `event-consumer-cost` | Message queue consumers | $600 | Standard |

### 2.2 Standard API Profile (Most Common)

```yaml
costProfiles:
  
  standard-api-cost:
    description: "REST API with standard cost management"
    
    # Budget scaling: base × scaling-factor × size-multiplier
    budgets:
      int-stable:
        base: 500         # $500 for medium service
        scaling: 1.0
      pre-stable:
        base: 1500        # $1500 for medium service
        scaling: 1.33
      prod:
        base: 3000        # $3000 for medium service
        scaling: 1.67
    
    # Alert thresholds with dynamic variables
    alerts:
      - name: "warning-80"
        threshold: 80     # 80% of budget
        severity: warning
        channels:
          teams:
            - "#team-{service}"           # Substituted per service
          email:
            - "{costOwner}@company.com"   # Substituted per service
          frequency: daily
      
      - name: "critical-100"
        threshold: 100    # At budget limit
        severity: critical
        channels:
          teams:
            - "#team-{service}"
            - "#platform-leadership"
          email:
            - "{costOwner}@company.com"
            - "finance-operations@company.com"
          pagerduty: "on-call-engineering"
          frequency: immediate
    
    # Cost optimization settings
    optimization:
      enableAutoScaling: true      # HPA recommended
      allowSpotInstances: false    # Not recommended for prod APIs
      allowRightSizing: true       # Apptio can recommend downsizing
```

### 2.3 Premium API Profile (High-Traffic)

```yaml
  premium-api-cost:
    description: "High-traffic API with enhanced cost control"
    
    budgets:
      int-stable:
        base: 800
        scaling: 1.0
      pre-stable:
        base: 2500
        scaling: 1.4
      prod:
        base: 6000
        scaling: 1.67
    
    alerts:
      - name: "warning-70"
        threshold: 70     # Earlier warning
        severity: warning
        channels:
          teams:
            - "#team-{service}"
            - "#platform-finops"
          frequency: daily
      
      - name: "critical-90"
        threshold: 90     # Tighter threshold
        severity: critical
        channels:
          teams:
            - "#team-{service}"
            - "#platform-leadership"
          email:
            - "{costOwner}@company.com"
            - "finance-operations@company.com"
          pagerduty: "on-call-engineering"
          frequency: immediate
      
      - name: "spike-detection"
        threshold: 110    # Unusual spikes
        severity: warning
        channels:
          teams:
            - "#platform-finops"
          frequency: once
    
    optimization:
      enableAutoScaling: true
      allowSpotInstances: false
      allowRightSizing: true
```

### 2.4 Batch Job Profile

```yaml
  batch-job-cost:
    description: "Batch job with time-based cost management"
    
    budgets:
      int-stable:
        base: 200
        scaling: 1.0
      pre-stable:
        base: 400
        scaling: 1.5
      prod:
        base: 1200
        scaling: 2.0
    
    alerts:
      - name: "warning-80"
        threshold: 80
        severity: warning
        channels:
          teams:
            - "#team-{service}"
          frequency: daily
      
      - name: "critical-100"
        threshold: 100
        severity: critical
        channels:
          teams:
            - "#team-{service}"
            - "#platform-finops"
          email:
            - "{costOwner}@company.com"
          frequency: immediate
    
    optimization:
      enableAutoScaling: false      # Batch jobs don't auto-scale
      allowSpotInstances: true      # Can use cheaper spot instances
      allowRightSizing: false
```

### 2.5 Internal Tool Profile

```yaml
  internal-tool-cost:
    description: "Internal tool with minimal cost tracking"
    
    budgets:
      int-stable:
        base: 100
        scaling: 1.0
      pre-stable:
        base: 150
        scaling: 1.0
      prod:
        base: 300
        scaling: 1.0
    
    alerts:
      - name: "warning-80"
        threshold: 80
        severity: warning
        channels:
          teams:
            - "#platform-team"
          frequency: daily
      
      - name: "critical-100"
        threshold: 100
        severity: critical
        channels:
          teams:
            - "#platform-team"
            - "#platform-finops"
          email:
            - "{costOwner}@company.com"
          frequency: immediate
    
    optimization:
      enableAutoScaling: false
      allowSpotInstances: true
      allowRightSizing: true
```

---

## 3. Service Definition with Profiles

### 3.1 Service Cost Configuration

Services specify **minimal cost information** and reference a profile:

```yaml
services:
  - name: payment-processor
    type: api
    image: <GAR_IMAGE>
    
    # Behavior & Size (existing)
    profile: public-api
    size: large
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # NEW: Cost profile reference + allocation
    costProfile: standard-api-cost    # Use this cost template
    cost:
      costCenter: "CC-12345"          # From Finance
      businessUnit: "retail-banking"  # Predefined enum
      costOwner: "alice@company.com"  # Receives cost alerts
      
      # OPTIONAL: Override budget for specific environment
      overrides:
        prod:
          budgetMultiplier: 1.5       # Scale profile budget by 1.5×
```

### 3.2 What Gets Calculated

At validation time, the expansion engine calculates:

```
Profile: standard-api-cost
Size: large (multiplier 2.0)

↓

Calculated budgets:
├─ Int-Stable: $500 × 2.0 = $1,000/month
├─ Pre-Stable: $1500 × 2.0 = $3,000/month
└─ Prod: $3000 × 2.0 = $6,000/month

Variable substitution:
├─ {service} → payment-processor
├─ {costOwner} → alice@company.com
└─ {costCenter} → CC-12345

↓

Complete alert configuration:
└─ Alerts fire to:
   ├─ Teams: #team-payment-processor, #platform-leadership
   ├─ Email: alice@company.com, finance-operations@company.com
   └─ PagerDuty: on-call-engineering (critical only)
```

### 3.3 Example Services

```yaml
services:
  
  # REST API: Medium size
  - name: user-service
    profile: public-api
    size: medium
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12346"
      businessUnit: "retail-banking"
      costOwner: "bob@company.com"
  
  # REST API: Large, high-traffic
  - name: search-service
    profile: public-api
    size: large
    costProfile: premium-api-cost    # Stricter monitoring
    cost:
      costCenter: "CC-12347"
      businessUnit: "retail-banking"
      costOwner: "carol@company.com"
  
  # Batch job
  - name: data-export
    profile: batch-job
    size: large
    costProfile: batch-job-cost
    cost:
      costCenter: "CC-30001"
      businessUnit: "operations"
      costOwner: "david@company.com"
  
  # Internal tool
  - name: metrics-exporter
    profile: internal-tool
    size: small
    costProfile: internal-tool-cost
    cost:
      costCenter: "CC-50001"
      businessUnit: "technology"
      costOwner: "eve@company.com"
```

---

## 4. Cost Management Workflow

### 4.1 Complete Integration Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Service Onboarding (Backstage Template)                 │
├─────────────────────────────────────────────────────────────────┤
│ • User fills form with service basics & cost allocation         │
│ • Selects cost profile (standard-api, premium-api, etc.)        │
│ • Specifies cost center, business unit, cost owner              │
│ • Form validates all fields                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 2: Create PR with Service Definition                       │
├─────────────────────────────────────────────────────────────────┤
│ • kustomize/catalog/services.yaml updated                       │
│ • Service references costProfile                                │
│ • Only 5 required cost fields (allocation)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 3: CI/CD Validation                                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. Schema validation (services.yaml structure)                  │
│ 2. Expand cost profiles:                                        │
│    • Load profile from cost-profiles.yaml                       │
│    • Calculate budgets: base × scaling × size-multiplier        │
│    • Substitute variables: {service}, {costOwner}               │
│ 3. Validate expanded costs:                                     │
│    • Budget ranges                                              │
│    • Cost center exists in Apptio                               │
│    • Notification channels valid                                │
│ 4. Block PR if any validation fails                             │
│ 5. Allow merge if all checks pass                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 4: PR Merged to Main                                       │
├─────────────────────────────────────────────────────────────────┤
│ • catalog/services.yaml now contains service entry              │
│ • Merge triggers Apptio Sync                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 5: Apptio Sync Service Processes Catalog                   │
├─────────────────────────────────────────────────────────────────┤
│ Timer: Every 5 minutes (Kubernetes native service)              │
│ Actions:                                                         │
│ • For each service with costProfile defined:                    │
│   1. Load profile and service definition                        │
│   2. Expand cost config (budgets + alerts)                      │
│   3. For each environment (int-stable, pre-stable, prod):       │
│      • Create/update budget in Apptio                           │
│      • Configure alert rules                                    │
│      • Set notification channels                                │
│   4. Store sync metadata (lastSync, status)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 6: Service Deployment & Label Injection                    │
├─────────────────────────────────────────────────────────────────┤
│ When service is deployed via Kustomize:                         │
│ • Load service from catalog with expanded cost config           │
│ • Inject cost labels into all pods:                             │
│   - cost.service = service name                                 │
│   - cost.environment = environment                              │
│   - cost.costCenter = from service                              │
│   - cost.businessUnit = from service                            │
│   - cost.owner = from service                                   │
│   - cost.budget = calculated monthly amount                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ STEP 7: Cost Tracking Begins                                    │
├─────────────────────────────────────────────────────────────────┤
│ Timeline:                                                        │
│ • T+0h:   Pods running with cost labels                         │
│ • T+24h:  GCP billing exports daily data with labels            │
│ • T+48h:  Apptio ingests costs, budgets visible                 │
│ • T+72h:  Alerts fire when thresholds crossed                   │
│           → Teams channels receive notifications                │
│           → Cost owner receives alerts                          │
│           → Finance has visibility                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Cost Profile Expansion (Technical Details)

### 5.1 Resolution Algorithm

```python
def calculate_service_cost(service, profile, sizes):
    """
    Expand service cost from profile reference.
    Called during CI/CD validation.
    """
    
    # Get profile definition
    profile_def = load_profile(service.costProfile)
    
    # Get size multiplier
    size_multiplier = sizes[service.size].cost_multiplier
    
    # Calculate budgets per environment
    budgets = {}
    for env in ['int-stable', 'pre-stable', 'prod']:
        base = profile_def.budgets[env].base
        scaling = profile_def.budgets[env].scaling
        
        monthly = base * scaling * size_multiplier
        
        # Apply environment-specific override if present
        if service.cost.overrides and env in service.cost.overrides:
            monthly *= service.cost.overrides[env].budgetMultiplier
        
        # Round to nearest $50
        monthly = round(monthly / 50) * 50
        budgets[env] = monthly
    
    # Substitute variables in alert channels
    variables = {
        '{service}': service.name,
        '{costOwner}': service.cost.costOwner,
        '{costCenter}': service.cost.costCenter,
        '{businessUnit}': service.cost.businessUnit
    }
    
    alerts = substitute_variables(profile_def.alerts, variables)
    
    return {
        'budgets': budgets,
        'alerts': alerts,
        'optimization': profile_def.optimization
    }
```

### 5.2 Variable Substitution

Profiles use template variables that get replaced per service:

```yaml
# Profile definition
alerts:
  - threshold: 80
    channels:
      teams:
        - "#team-{service}"          # Template variable
      email:
        - "{costOwner}@company.com"  # Template variable

# Service definition
name: payment-processor
cost:
  costOwner: alice.johnson@company.com

# After expansion
alerts:
  - threshold: 80
    channels:
      teams:
        - "#team-payment-processor"   # Substituted
      email:
        - "alice.johnson@company.com" # Substituted
```

### 5.3 Supported Variables

| Variable | Replaced With | Example |
|----------|---------------|---------|
| `{service}` | Service name | `payment-processor` |
| `{costOwner}` | Cost owner email | `alice@company.com` |
| `{costCenter}` | Cost center code | `CC-12345` |
| `{businessUnit}` | Business unit | `retail-banking` |
| `{environment}` | Current environment | `prod` |

---

## 6. CI/CD Validation Workflow

### 6.1 Validation Steps

```yaml
# .github/workflows/validate-cost-config.yml

jobs:
  validate:
    steps:
      
      # 1. Load catalog files
      - name: Load configuration
        run: |
          cat kustomize/catalog/services.yaml
          cat kustomize/catalog/cost-profiles.yaml
      
      # 2. Schema validation
      - name: Validate schema
        run: |
          python scripts/validate-schema.py \
            --services kustomize/catalog/services.yaml \
            --profiles kustomize/catalog/cost-profiles.yaml
      
      # 3. Expand profiles and substitute variables
      - name: Expand cost profiles
        run: |
          python scripts/expand-cost-config.py \
            --services kustomize/catalog/services.yaml \
            --profiles kustomize/catalog/cost-profiles.yaml \
            --output /tmp/expanded-services.yaml
      
      # 4. Validate expanded costs
      - name: Validate expanded configuration
        run: |
          python scripts/validate-costs.py \
            --catalog /tmp/expanded-services.yaml
      
      # 5. Verify cost centers exist
      - name: Verify cost centers
        run: |
          python scripts/validate-cost-centers.py \
            --catalog /tmp/expanded-services.yaml \
            --apptio-api-url ${{ secrets.APPTIO_API_URL }} \
            --apptio-api-key ${{ secrets.APPTIO_API_KEY }}
      
      # 6. Validate channels
      - name: Validate notification channels
        run: |
          python scripts/validate-channels.py \
            --catalog /tmp/expanded-services.yaml
```

### 6.2 What Validation Checks

```
✅ Schema validation
   • Services.yaml structure correct
   • costProfile field references valid profile
   • Required fields present: costCenter, costOwner, businessUnit

✅ Profile expansion
   • Profile exists in cost-profiles.yaml
   • Budget base values reasonable
   • Size multiplier valid

✅ Budget ranges
   • Int-stable: $100-$5,000 (after expansion)
   • Pre-stable: $200-$10,000 (after expansion)
   • Prod: $300-$50,000 (after expansion)
   • Budget progression: int < pre < prod (logical)

✅ Cost center verification
   • Format: CC-XXXXX
   • Exists in Apptio (via API call)

✅ Notification channels
   • Teams channels: #channel-name format
   • Email addresses valid
   • At least one channel per alert
```

---

## 7. Onboarding a Service

### 7.1 Step-by-Step

**Scenario**: Payments team onboarding "payment-processor" service

#### Step 1: Fill Backstage Form

```
Service Name: payment-processor
Service Type: REST API
Service Size: Large
Estimated Traffic: 1000 req/sec

Cost Center: CC-12345 (get from Finance)
Business Unit: retail-banking
Cost Owner: alice.johnson@company.com
Cost Profile: standard-api-cost (recommended for APIs)
```

#### Step 2: Review Calculated Budgets

Form shows:
```
Estimated monthly costs (Large service):
├─ Int-Stable: $1,000
├─ Pre-Stable: $3,000
└─ Production: $6,000

Based on profile: standard-api-cost
Alert settings:
├─ 80% warning → #team-payment-processor (daily)
└─ 100% critical → #team-payment-processor, #platform-leadership
                    (immediate + PagerDuty)
```

#### Step 3: Generate catalog entry

```yaml
# Added to kustomize/catalog/services.yaml
- name: payment-processor
  type: api
  image: <GAR_IMAGE_PAYMENT_PROCESSOR>
  profile: public-api
  size: large
  regions: [euw1, euw2]
  enabledIn: [int-stable, pre-stable, prod]
  
  costProfile: standard-api-cost
  cost:
    costCenter: "CC-12345"
    businessUnit: "retail-banking"
    costOwner: "alice.johnson@company.com"
```

#### Step 4: CI/CD Validation Passes

```
✅ Schema validation passed
✅ Profile expansion successful
✅ Budgets calculated:
   Int-Stable: $1000/month
   Pre-Stable: $3000/month
   Prod: $6000/month
✅ Cost center CC-12345 verified
✅ Notification channels valid
✅ Ready to merge
```

#### Step 5: Merge to Main

Apptio Sync runs immediately and:
- Creates budget "payment-processor-int-stable" ($1000/month)
- Creates budget "payment-processor-pre-stable" ($3000/month)
- Creates budget "payment-processor-prod" ($6000/month)
- Configures alert rules for each budget
- Sets up notification channels

#### Step 6: Deploy Service

Kustomize injects cost labels:
```yaml
pods:
  labels:
    cost.service: payment-processor
    cost.environment: prod
    cost.costCenter: CC-12345
    cost.businessUnit: retail-banking
    cost.owner: alice.johnson@company.com
    cost.budget: "6000"
```

#### Step 7: Cost Tracking Begins

- Day 1: Pods running with labels
- Day 2: GCP exports daily billing with labels
- Day 3: Apptio ingests costs
- Day 4+: Alerts fire at 80% and 100% thresholds

---

## 8. Cost Center Management

### 8.1 Getting a Cost Center Code

**Format**: `CC-XXXXX` (required)

**Common Cost Centers**:
```
CC-10001 = Finance Department
CC-20001 = Retail Banking
CC-30001 = Operations
CC-40001 = Risk Management
CC-50001 = Technology
```

**Process**:
1. Identify which department owns the service
2. Contact Finance team for cost center code
3. Verify code exists in Apptio (validated during onboarding)
4. Use in service cost configuration

---

## 9. Modifying Cost Profiles

### 9.1 Creating a New Profile

When you have services that don't fit existing profiles:

```yaml
# cost-profiles.yaml
costProfiles:
  
  # NEW: For real-time streaming services
  realtime-streaming-cost:
    description: "WebSocket/streaming service with high resource usage"
    
    budgets:
      int-stable:
        base: 600
        scaling: 1.0
      pre-stable:
        base: 2000
        scaling: 1.5
      prod:
        base: 5000
        scaling: 2.0
    
    alerts:
      - name: "warning-75"
        threshold: 75
        severity: warning
        channels:
          teams:
            - "#team-{service}"
          frequency: daily
      
      - name: "critical-95"
        threshold: 95
        severity: critical
        channels:
          teams:
            - "#team-{service}"
            - "#platform-leadership"
          email:
            - "{costOwner}@company.com"
          pagerduty: "on-call-engineering"
          frequency: immediate
    
    optimization:
      enableAutoScaling: true
      allowSpotInstances: false
      allowRightSizing: true
```

Services then reference it:
```yaml
- name: notification-service
  costProfile: realtime-streaming-cost
  cost:
    costCenter: "CC-12345"
    businessUnit: "retail-banking"
    costOwner: "alice@company.com"
```

### 9.2 Updating an Existing Profile

Changes to a profile affect ALL services using it:

```yaml
# Update standard-api-cost to add spike detection
costProfiles:
  standard-api-cost:
    description: "REST API with standard cost management"
    
    budgets: # ... unchanged
    
    alerts:
      - name: "warning-80"
        threshold: 80
        # ... unchanged
      
      - name: "critical-100"
        threshold: 100
        # ... unchanged
      
      - name: "spike-detection"  # NEW
        threshold: 110
        severity: warning
        channels:
          teams:
            - "#platform-finops"
          frequency: once
    
    optimization: # ... unchanged
```

**Result**: All services using `standard-api-cost` now have spike detection (effective at next Apptio sync).

---

## 10. Troubleshooting

### Problem: Validation fails - "Profile not found"

**Cause**: costProfile references non-existent profile

**Solution**:
```bash
# List valid profiles
grep "^  [a-z]" kustomize/catalog/cost-profiles.yaml

# Use one of the listed profiles in your service definition
costProfile: standard-api-cost  # ✅ Valid
```

---

### Problem: "Budgets out of range after expansion"

**Cause**: Calculated budget exceeds max limit

**Example**:
```
Service: xlarge API
Profile base: $3000 (prod)
Size multiplier: 6.0×

Calculated: $3000 × 6.0 = $18,000 (exceeds $50k max, but just barely)
```

**Solution**: Option 1 - Use larger profile:
```yaml
costProfile: premium-api-cost  # Higher base budgets
```

Option 2 - Reduce size multiplier via override:
```yaml
cost:
  costCenter: "CC-12345"
  overrides:
    prod:
      budgetMultiplier: 0.8  # Scale down by 20%
```

---

### Problem: Alerts not firing in Teams

**Cause**: Channel variable not substituting correctly

**Debug**:
```bash
# View expanded configuration
python scripts/expand-cost-config.py \
  --services kustomize/catalog/services.yaml \
  --profiles kustomize/catalog/cost-profiles.yaml \
  --output /tmp/expanded.yaml

# Check alerts section
grep -A10 "alerts:" /tmp/expanded.yaml | grep "teams:"
```

Expected: `- "#team-payment-processor"`
If you see: `- "#team-{service}"` → Variable not substituted

---

### Problem: Service cost not showing in Apptio

**Cause**: Apptio Sync hasn't run yet or service labels missing

**Timeline**:
```
T+0:   Service merged to main
T+5m:  Apptio Sync runs (max 5 min poll interval)
T+7m:  Budgets created in Apptio
T+1h:  Cost data starts flowing from GCP

If not visible after 1 hour:
1. Check Apptio Sync pod logs:
   kubectl logs -f deployment/apptio-sync -n platform-system
2. Verify service has costProfile:
   grep -A5 "payment-processor:" kustomize/catalog/services.yaml
3. Check cost labels on pods:
   kubectl get pods -L cost.service,cost.environment
```

---

## 11. FAQ

### Q: Can I skip specifying a cost profile?
**A**: No. Every service must have `costProfile: profile-name`. This ensures consistent cost management.

### Q: What if my service doesn't match any profile?
**A**: Either:
1. Use the closest matching profile + overrides, or
2. Create a new profile (work with platform team)

### Q: Can I have environment-specific profiles?
**A**: Profiles are generic. Use `overrides` for environment-specific budget adjustments:
```yaml
cost:
  overrides:
    prod:
      budgetMultiplier: 1.5  # Prod costs 1.5× more
```

### Q: Who should be the cost owner?
**A**: Typically the tech lead or engineering manager responsible for resource optimization.

### Q: When do cost changes take effect?
**A**: 
- Profile update → effective at next Apptio Sync (5 min max)
- Service cost update → effective at next Apptio Sync (5 min max)
- Budget increase → takes effect immediately in Apptio

### Q: Can multiple services share a cost owner?
**A**: Yes, but cost owner receives alerts for ALL their services. Consider creating a team email alias (e.g., `payments-team-leads@company.com`) for group ownership.

---

## 12. File Reference

### Services Catalog
- **File**: `kustomize/catalog/services.yaml`
- **What**: Service definitions with minimal cost config
- **Change Frequency**: On service onboarding/updates
- **Validation**: CI/CD schema + cost validation

### Cost Profiles
- **File**: `kustomize/catalog/cost-profiles.yaml`
- **What**: Reusable cost policy templates
- **Change Frequency**: Rarely (affects all services using profile)
- **Validation**: CI/CD profile schema validation

### Kustomize Overlays
- **Files**: `kustomize/overlays/{env}/kustomization.yaml`
- **What**: Injected cost labels into pods
- **Auto-Generated**: Yes (from expanded cost config)

### Apptio Sync Service
- **Location**: `services/apptio-sync/`
- **Purpose**: Syncs cost profiles to Apptio budgets/alerts
- **Frequency**: Every 5 minutes (configurable)
- **Status**: ConfigMap `apptio-sync-state` tracks last sync

---

## 13. Summary

**Cost management via profiles**:

1. **Define reusable profiles** (cost-profiles.yaml) - 6 templates cover 90% of use cases
2. **Reference by name** in services - one line per service
3. **Specify allocation** - only costCenter, businessUnit, costOwner
4. **Calculate at validation** - budgets auto-calculated from profile + size
5. **Expand variables** - teams channels, email substituted per service
6. **Sync to Apptio** - budgets and alerts created automatically
7. **Monitor in real-time** - cost tracking begins at deployment

**Result**: 
- 83% less YAML in service catalog
- Consistent cost policies organization-wide
- Self-service at scale for development teams
- Central cost governance for platform team

---

**Document Version**: 1.0
**Created**: 2025-11-15
**Status**: ACTIVE
