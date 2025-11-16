# Cost Management: Budget Creation vs Cost Tracking

**Status**: CORRECTED CLARIFICATION DOCUMENT

**Date**: 2025-11-16 (Updated)

---

## Executive Summary

This document clarifies when **budget creation** and **cost tracking** happen in the Platform-Next cost management system.

**CORRECTED Key Point**: Apptio sync (budget creation) is triggered when deployment is successful, not when the catalog is merged. This ensures budgets are created only when services are actually deployed, and cost tracking can start immediately.

---

## The Question

**User Question**: "In the draw.io design diagram there is a trigger apptio sync when the catalog is merged. But unless the deployment happens from harness there is no service. So how does budgets, cost metrics work if the service is not deployed?"

**Answer**: This is an excellent observation! The distinction is:

- **Budgets** = Planned/Allocated targets (created early, before deployment)
- **Cost Tracking** = Actual spending (only happens after deployment)

---

## Corrected Flow: Budget Creation on Deployment

### Phase 1: Manifest Generation (Planning Phase)

**When**: Catalog merged to `main` branch

**What Happens**:
1. CI/CD pipeline triggered
2. Profile expansion calculates budgets
3. Manifests generated with cost labels
4. Manifests committed to Git

**Status**: 
- ✅ Manifests ready with cost labels
- ✅ Budgets calculated (but not yet in Apptio)
- ⚠️ **Service not deployed yet**

### Phase 2: Budget Creation (Deployment Phase)

**When**: Deployment successful (Harness pipeline completes)

**What Happens**:
1. Harness deploys service with cost labels
2. Pods running with cost labels
3. **Apptio Sync Service is triggered** (webhook from Harness or polling)
4. Reads service definition from catalog
5. Expands cost profile to calculate budgets
6. Creates budgets in Apptio:
   - `payment-processor-int-stable`: $1,000/month
   - `payment-processor-pre-stable`: $3,000/month
   - `payment-processor-prod`: $6,000/month
7. Configures alert rules (80%, 100% thresholds)
8. Sets up notification channels
9. Enables cost tracking

**Status**: 
- ✅ Budgets created in Apptio
- ✅ Alert rules configured
- ✅ **Service deployed with labels**
- ✅ **Cost tracking can start immediately**

---

### Phase 3: Cost Tracking (Runtime Phase)

**When**: After deployment (next day when GCP exports billing)

**What Happens**:
1. Pods already running with cost labels (from Phase 2):
   ```yaml
   labels:
     cost.service: payment-processor
     cost.costCenter: CC-12345
     cost.budget: "6000"
   ```

2. Pods start running with these labels

3. **GCP Billing Export** (daily):
   - GCP automatically includes labels in billing data
   - Exports: `cost.service=payment-processor`, `cost.costCenter=CC-12345`
   - Daily aggregates per resource

4. **Apptio Ingestion**:
   - Apptio reads labeled costs from GCP
   - Allocates costs to: `payment-processor-prod` budget
   - Compares: **Actual costs vs Planned budget**

5. **Cost Tracking Active**:
   - Day 1: Pods running → $0 (just deployed)
   - Day 2: GCP exports → $50 (first day of costs)
   - Day 3: Apptio ingests → $50 tracked
   - Day 4+: Daily tracking continues

6. **Alerts Fire** (when thresholds reached):
   - 80% of budget ($4,800) → Warning alert
   - 100% of budget ($6,000) → Critical alert

**Status**:
- ✅ Actual costs being tracked
- ✅ Budget vs actual comparison active
- ✅ Alerts monitoring thresholds

---

## Timeline Example (CORRECTED)

### T+0: Catalog Merged

```
Developer merges PR to main
  ↓
CI/CD generates manifests with cost labels
  ↓
Manifests committed to Git
  ↓
Status: Manifests ready, service not deployed yet
```

### T+1: Service Deployed

```
Developer triggers Harness pipeline
  ↓
Harness deploys service with cost labels
  ↓
Pods running with labels:
  - cost.service: payment-processor
  - cost.costCenter: CC-12345
  - cost.budget: "6000"
  ↓
Deployment successful → Apptio Sync triggered
  ↓
Creates budgets in Apptio:
  - payment-processor-int-stable: $1,000/month
  - payment-processor-prod: $6,000/month

Apptio Dashboard Shows:
  Service: payment-processor-prod
  Budget: $6,000/month
  Actual: $0 (just deployed, no costs yet)
  % Used: 0%
  Status: ✅ Budget created, cost tracking enabled
```

### T+2: First Cost Data (Next Day)

```
GCP Daily Export (runs at midnight)
  ↓
Exports labeled costs:
  - payment-processor-prod: $200 (Day 1)
  ↓
Apptio Ingestion (runs at 2 AM)
  ↓
Apptio Dashboard Shows:
  Service: payment-processor-prod
  Budget: $6,000/month
  Actual: $200 (Day 1)
  % Used: 3.3%
  Status: ✅ Tracking active
```

### T+30: Monthly Tracking

```
Apptio Dashboard Shows:
  Service: payment-processor-prod
  Budget: $6,000/month
  Actual: $5,400 (month-to-date)
  % Used: 90%
  Status: ⚠️ Approaching budget limit
  Alert: 80% threshold reached (sent to team)
```

---

## Why This Design Makes Sense (CORRECTED)

### 1. **Budgets Created When Service is Deployed**

Benefits of creating budgets on deployment:
- ✅ Budgets only exist for deployed services
- ✅ No empty budgets for services that are never deployed
- ✅ Cost tracking can start immediately (pods are running)
- ✅ Budgets and actual costs appear together
- ✅ Cleaner Apptio dashboard (no "waiting" budgets)

### 2. **Cost Tracking Requires Running Resources**

Actual costs only exist when:
- Pods are running (consuming CPU, memory)
- Resources are provisioned (storage, network)
- Services are active (network egress, API calls)

**No deployment = No resources = No costs = No budget needed**

### 3. **Deployment Success Triggers Budget Creation**

Benefits of triggering on deployment:
- ✅ Budgets created when service is actually running
- ✅ Immediate cost tracking (pods already have labels)
- ✅ No delay between budget creation and cost tracking
- ✅ Alert rules configured when service is active
- ✅ Dashboard shows budget and actual costs together

### 4. **Seamless Integration**

When deployment is successful:
- Service deployed with cost labels → Immediate cost tracking
- Apptio sync triggered → Budgets created
- GCP billing exports labels → Costs appear in Apptio
- Budget vs actual comparison → Starts immediately
- Alert rules active → Monitoring from day 1

---

## Updated Architecture Flow (CORRECTED)

### Planning Phase (Before Deployment)

```
Developer → Backstage Form
  ↓
Catalog PR Created
  ↓
CI/CD: Profile Expansion
  - Calculates budgets: $1K, $3K, $6K
  - Generates cost labels
  ↓
Catalog Merged
  ↓
Manifests Generated (with cost labels)
  ↓
Status: Ready for deployment
  (No budgets in Apptio yet)
```

### Deployment Phase

```
Harness Pipeline Triggered
  ↓
Fetches Manifests (with cost labels)
  ↓
Deploys to Kubernetes
  ↓
Pods Running with Labels
  ↓
Deployment Successful
  ↓
Apptio Sync Triggered (webhook/polling)
  ↓
Creates BUDGETS in Apptio
  - Budget: $6,000/month
  - Actual: $0 (just deployed)
  - Status: Cost tracking enabled
```

### Runtime Phase (After Deployment)

```
Pods Running with Cost Labels
  ↓
GCP Billing Export (daily, starting next day)
  - Includes cost labels
  - Exports: $200/day
  ↓
Apptio Ingestion
  - Reads labeled costs
  - Allocates to budget
  ↓
Cost Tracking Active
  - Budget: $6,000/month
  - Actual: $200/day
  - Comparison: 3.3% used
  - Alerts: Monitoring thresholds
```

---

## Diagram Updates

The architecture diagram has been updated to clarify:

1. **Apptio Sync Tasks**: Now labeled as "Phase 1: Budget Setup" with note: "⚠️ No actual costs yet (service not deployed)"

2. **GCP Billing**: Now labeled as "Phase 2: Cost Tracking" with note: "✅ Only works when pods are running with labels"

3. **Cost Timeline**: Added timeline showing:
   - T+0: Budget creation (catalog merged)
   - T+1: Service deployed
   - T+2+: Ongoing cost tracking

4. **Arrow Labels**: Updated to clarify:
   - "Creates BUDGETS only (No costs until deployed)"
   - "Ingest ACTUAL Costs (After deployment)"
   - "Cost Tracking Starts (Pods with labels)"

5. **Data Flow Summary**: Split into three phases:
   - 📋 PLANNING PHASE (Before Deployment)
   - 🚀 DEPLOYMENT PHASE
   - 💰 RUNTIME PHASE (After Deployment)

---

## Common Questions

### Q: Why create budgets before deployment?

**A**: Budgets are planning tools. Creating them early enables:
- Finance review and approval
- Governance validation
- Team visibility into planned spending
- Alert rules ready when deployment happens

### Q: What if service is never deployed?

**A**: Budgets remain in Apptio with $0 actual costs. This is fine - it shows:
- Planned but not deployed services
- Budget allocated but not used
- Can be cleaned up later if service is cancelled

### Q: What if service is deployed but no costs appear?

**A**: This could indicate:
- Pods not running (check deployment status)
- Labels missing (check manifests)
- GCP billing export delay (check export schedule)
- Apptio ingestion delay (check sync schedule)

### Q: Can budgets be updated after creation?

**A**: Yes! If service configuration changes:
- Update catalog (change cost profile or size)
- CI/CD recalculates budgets
- Apptio Sync updates budgets in Apptio
- Actual costs continue tracking against new budget

---

## Summary (CORRECTED)

**The Corrected Logic**:

1. ✅ **Manifest Generation** (when catalog merged):
   - CI/CD generates manifests with cost labels
   - Budgets calculated but not yet in Apptio
   - Service ready for deployment

2. ✅ **Budget Creation** (when deployment successful):
   - Harness deploys service with cost labels
   - Pods running with labels
   - Apptio Sync triggered → Creates budgets in Apptio
   - Cost tracking enabled immediately

3. ✅ **Cost Tracking** (after deployment):
   - Pods running with cost labels
   - GCP billing exports labeled costs (daily)
   - Apptio ingests and compares vs budget
   - Alerts fire at thresholds

**The Corrected Flow**:
- Catalog merged → Manifests generated (with cost labels)
- Service deployed → Budgets created in Apptio
- Cost tracking → Starts immediately (pods running)
- Ongoing → Budget vs actual comparison

**Why This is Better**:
- ✅ No empty budgets for services that are never deployed
- ✅ Budgets created when service is actually running
- ✅ Cost tracking starts immediately (no delay)
- ✅ Cleaner Apptio dashboard
- ✅ More logical flow: Deploy → Budget → Track

This design ensures budgets are created only when services are deployed, and cost tracking starts immediately!

---

**Document Status**: ✅ Complete Clarification

