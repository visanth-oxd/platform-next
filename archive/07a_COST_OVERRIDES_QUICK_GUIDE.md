# Cost Overrides Quick Reference

**Three-Level Override System** - Customize cost configuration at service, environment, or service+environment level.

---

## Overview

```
Profile (cost-profiles.yaml)
├── Budget: $3000 prod, 80% alert threshold
├── environmentOverrides (if defined)
│   └── Prod: Different alerts, alert channels
└── Service references it: costProfile: "standard-api-cost"
    └── Service-level override (applies to all environments)
    │   └── budgetMultiplier: 1.5
    └── Service+Environment override (most specific)
        └── prod: budgetMultiplier: 2.0, different alerts
```

---

## 1. Service-Level Override (All Environments)

Apply override across all environments for a specific service.

```yaml
- name: payment-processor
  costProfile: standard-api-cost
  cost:
    costCenter: "CC-12345"
    businessUnit: "retail-banking"
    costOwner: "alice@company.com"
    
    overrides:
      service:
        budgetMultiplier: 1.5  # All envs: $1500, $4500, $9000
        # OR/AND custom alerts for all environments:
        alerts:
          - name: "warning-70"
            threshold: 70
            channels: [...]
```

**Use when**: Service characteristics apply across all environments (e.g., payment processor always needs stricter controls).

---

## 2. Environment-Level Override (Profile-Wide)

Override profile settings for all services in a specific environment.

```yaml
# kustomize/catalog/cost-profiles.yaml

costProfiles:
  standard-api-cost:
    budgets: { ... }
    alerts: [ ... ]  # Default
    
    # Override for all services using this profile in prod
    environmentOverrides:
      prod:
        alerts:
          - name: "warning-70"
            threshold: 70
            channels:
              teams: ["#team-{service}", "#platform-finops"]
        optimization:
          enableAutoScaling: true
```

**Use when**: Environment-wide policies (e.g., prod always needs stricter alerts than int).

---

## 3. Service + Environment Override (Most Specific)

Override for a specific service in a specific environment. Highest precedence.

```yaml
- name: payment-processor
  costProfile: standard-api-cost
  cost:
    costCenter: "CC-12345"
    businessUnit: "retail-banking"
    costOwner: "alice@company.com"
    
    overrides:
      environment:
        prod:
          budgetMultiplier: 2.0       # Only prod: $12000
          alerts:
            - name: "warning-70"
              threshold: 70
            - name: "critical-85"
              threshold: 85
        
        int-stable:
          budgetMultiplier: 0.5       # Only int: $1500
          alerts:
            - name: "critical-100"
              threshold: 100
```

**Use when**: One-off exceptions or environment-specific tuning for a single service.

---

## Precedence Order

```
┌─────────────────────────────────────────────────────────────┐
│ Resolution Order (Most → Least Specific)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. Service + Environment Override ⭐ (WINS)                 │
│    cost.overrides.environment.prod                          │
│                                                              │
│    ↓ (used if #1 not defined)                               │
│                                                              │
│ 2. Service-Level Override                                   │
│    cost.overrides.service                                   │
│                                                              │
│    ↓ (used if #1 and #2 not defined)                        │
│                                                              │
│ 3. Profile Environment Override                             │
│    costProfile.environmentOverrides.prod                    │
│                                                              │
│    ↓ (used if #1, #2, #3 not defined)                       │
│                                                              │
│ 4. Profile Default                                          │
│    costProfile.budgets, costProfile.alerts                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Example Resolution**:
```yaml
# Profile default: $3000 prod, 80% alert
standard-api-cost:
  budgets:
    prod:
      base: 3000
      scaling: 1.67  # For medium
  alerts:
    - threshold: 80

# Profile env override: Stricter prod alerts
environmentOverrides:
  prod:
    alerts:
      - threshold: 70  # Override 1: prod gets 70% warning

# Service-level override: Affects all envs
cost:
  overrides:
    service:
      budgetMultiplier: 1.5  # Override 2: $6000 prod (3000 × 2.0 size × 1.5)

# Service+env override: WINS
cost:
  overrides:
    environment:
      prod:
        budgetMultiplier: 2.0  # Override 3: $12000 prod (3000 × 2.0 × 2.0)
        alerts:
          - threshold: 85     # Override 3: 85% alert (not 70%)

# FINAL RESULT:
# Budget: $12000 (service+env multiplier applied)
# Alert: 85% threshold (service+env alert used)
```

---

## Real-World Scenarios

### Scenario 1: Unexpected Production Traffic Spike

```yaml
- name: payment-processor
  size: large
  costProfile: standard-api-cost  # Base: $6000/prod
  cost:
    costCenter: "CC-12345"
    costOwner: "alice@company.com"
    
    overrides:
      environment:
        prod:
          budgetMultiplier: 1.5  # Increase to $9000 for higher load
          alerts:
            - threshold: 70  # Alert earlier
            - threshold: 100
```

**Why**: Service hit 90% of budget more frequently than expected.

---

### Scenario 2: Cost Center Changes by Environment

```yaml
# cost-profiles.yaml
standard-api-cost:
  budgets: { ... }
  
  environmentOverrides:
    int-stable:
      allocation:
        costCenter: "CC-SHARED-INT"  # All int-stable shared
    
    prod:
      allocation:
        costCenter: null  # Use service's costCenter
```

**Why**: Test environment costs are consolidated; prod charges by service owner.

---

### Scenario 3: Gradual Size Migration with Cost Validation

```yaml
- name: user-service
  size: large           # Upgraded from medium
  costProfile: standard-api-cost
  cost:
    costCenter: "CC-12346"
    costOwner: "bob@company.com"
    
    overrides:
      environment:
        int-stable:
          budgetMultiplier: 0.5      # Test with half budget
        pre-stable:
          budgetMultiplier: 1.0      # Pre validates cost
        # Prod uses full calculation (no override)
```

**Why**: Validate cost impact before full rollout.

---

### Scenario 4: Mission-Critical Service Gets Tighter Control

```yaml
- name: fraud-detection
  size: large
  costProfile: standard-api-cost
  cost:
    costCenter: "CC-20001"
    costOwner: "carlos@company.com"
    
    overrides:
      service:
        # Stricter alerts across ALL environments
        alerts:
          - name: "warning-70"
            threshold: 70
            channels:
              teams: ["#team-fraud-detection", "#platform-finops"]
      
      environment:
        prod:
          # Even stricter in production
          budgetMultiplier: 1.2
          alerts:
            - name: "warning-60"
              threshold: 60
              channels:
                teams: ["#team-fraud-detection", "#platform-finops"]
                frequency: immediate
            - name: "critical-85"
              threshold: 85
              channels:
                teams: ["#team-fraud-detection", "#platform-leadership"]
                pagerduty: "on-call-engineering"
```

**Why**: Fraud detection is critical; failure costs more than overspending.

---

## Common Override Patterns

### Pattern A: Scale by Service Size

```yaml
cost:
  overrides:
    service:
      budgetMultiplier: 1.5  # Service is larger than typical
```

### Pattern B: Environment-Specific Budgets

```yaml
cost:
  overrides:
    environment:
      int-stable:
        budgetMultiplier: 0.5    # Dev is cheap
      pre-stable:
        budgetMultiplier: 1.0    # Pre mirrors expected
      prod:
        budgetMultiplier: 1.5    # Prod has safety margin
```

### Pattern C: Alert Customization Only (No Budget Change)

```yaml
cost:
  overrides:
    service:
      alerts:
        - name: "warning-70"
          threshold: 70
          channels: [...]
      # (budgetMultiplier not specified = use profile)
```

### Pattern D: Nested Customization (Service + Env)

```yaml
cost:
  overrides:
    service:
      budgetMultiplier: 1.2  # +20% everywhere
    
    environment:
      prod:
        budgetMultiplier: 1.5  # Prod gets additional 50%
        # Total prod multiplier: 1.2 × 1.5 = 1.8×
```

---

## Validation & Testing

### View Expanded Configuration

```bash
# See final config after all overrides applied
python scripts/expand-cost-config.py \
  --services kustomize/catalog/services.yaml \
  --profiles kustomize/catalog/cost-profiles.yaml \
  --service payment-processor \
  --environment prod \
  --output /tmp/expanded.yaml

cat /tmp/expanded.yaml | grep -A20 "budgets:"
```

### Check Override Precedence

```bash
# Trace which overrides were applied
python scripts/expand-cost-config.py \
  --services kustomize/catalog/services.yaml \
  --profiles kustomize/catalog/cost-profiles.yaml \
  --service payment-processor \
  --debug

# Output:
# 1. Profile default: $3000
# 2. Profile env override: alert threshold 70%
# 3. Service-level override: budgetMultiplier 1.5 → $4500
# 4. Service+env override: budgetMultiplier 2.0 → $6000 (FINAL)
```

---

## FAQ

**Q: Can I override just budgets without changing alerts?**
```yaml
overrides:
  service:
    budgetMultiplier: 1.5  # Only this, alerts stay from profile
```

**Q: Can I override just alerts without changing budgets?**
```yaml
overrides:
  service:
    alerts: [...]  # Only this, budgets calculated normally
```

**Q: What if I set conflicting service-level and service+env overrides?**
Service+env wins (highest precedence).

**Q: Can I use overrides to change cost center?**
Yes, via profile environmentOverrides:
```yaml
environmentOverrides:
  prod:
    allocation:
      costCenter: "CC-PROD-ONLY"
```

**Q: Do overrides affect profile changes?**
No. Profile changes only affect services without explicit overrides.

---

## Summary

| Override Type | Scope | Priority | Use Case |
|---------------|-------|----------|----------|
| Profile default | All services in profile | Lowest | Baseline rules |
| Profile environment | All services in profile + env | Low | Org-wide env policies |
| Service-level | Single service, all envs | High | Service-wide customization |
| Service + Environment | Single service + env | HIGHEST ⭐ | One-off exceptions |

**Rule of thumb**: 
- Use **profile environmentOverrides** for org-wide rules
- Use **service-level** for service characteristics
- Use **service+env** for exceptions and fine-tuning

---

**Full Documentation**: See [07_COST_MANAGEMENT_WITH_PROFILES.md](./07_COST_MANAGEMENT_WITH_PROFILES.md) sections 3.4-3.8
