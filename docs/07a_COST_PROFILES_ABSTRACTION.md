# Cost Profiles: Abstraction Pattern for Scale

**Status**: SOLUTION - Implementing Cost Config Abstraction

**Problem**: Embedding full cost configuration in every service entry makes `catalog/services.yaml` bloated with repetitive cost rules (100s of services × ~40 lines of cost config each).

**Solution**: Apply the same abstraction pattern used for resource profiles, shapes, and archetypes to cost management.

---

## Executive Summary

**Instead of embedding cost configuration per service:**
```yaml
services:
  - name: payment-service
    cost:
      budgets:
        int-stable: 800
        pre-stable: 2000
        prod: 5000
      alerts:
        - threshold: 80
          channels: [...]
        - threshold: 100
          channels: [...]
      # ... 30 more lines per service
```

**Use cost profiles (one per service, referenced by name):**
```yaml
services:
  - name: payment-service
    profile: public-api
    size: large
    costProfile: standard-api-cost  # NEW: Just a reference
    cost:
      costCenter: "CC-12345"
      costOwner: "alice@company.com"
```

**Cost profile defines the template** (reusable across similar services):
```yaml
costProfiles:
  standard-api-cost:
    description: "Standard REST API cost allocation"
    budgets:
      int-stable: { monthly: 800, scaling: 1.0 }
      pre-stable: { monthly: 2000, scaling: 2.5 }
      prod: { monthly: 5000, scaling: 6.25 }
    alerts:
      - threshold: 80
        severity: warning
        channels:
          teams: ["#team-{service}"]
          frequency: daily
      - threshold: 100
        severity: critical
        channels:
          teams: ["#team-{service}", "#platform-leadership"]
          email: ["{costOwner}@company.com"]
          frequency: immediate
```

---

## 1. Cost Profile Architecture

### 1.1 Core Concept

Cost profiles are **reusable templates** that define:
- Budget scaling rules (based on service size)
- Alert thresholds and channels
- Notification patterns
- Optimization defaults

Services reference a cost profile and only specify:
- Which profile to use
- Cost center (accounting reference)
- Cost owner (person responsible)
- Any environment-specific overrides

### 1.2 File Structure

```
kustomize/catalog/
├── services.yaml                 # Services (lightweight references)
├── cost-profiles.yaml            # NEW: Cost templates (reusable)
├── profiles.yaml                 # Behavior profiles (existing)
├── sizes.yaml                    # Resource sizes (existing)
└── COST_PROFILES_CATALOG.md      # This documentation
```

---

## 2. Cost Profiles: The Catalog

### 2.1 cost-profiles.yaml

```yaml
costProfiles:
  
  # Standard profile for REST APIs (most services)
  standard-api-cost:
    description: "REST API with standard cost management"
    
    # Budget scaling: base × size multiplier = monthly budget
    budgets:
      int-stable:
        base: 500
        scaling: 1.0      # 1× = $500/month for medium size
      pre-stable:
        base: 1500
        scaling: 1.33     # 1.33× = $2000/month for medium
      prod:
        base: 3000
        scaling: 1.67     # 1.67× = $5000/month for medium
    
    # Alert thresholds (same for all environments)
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
            - "#platform-leadership"
          email:
            - "{costOwner}@company.com"
            - "finance-operations@company.com"
          pagerduty: "on-call-engineering"
          frequency: immediate
    
    # Optimization preferences
    optimization:
      enableAutoScaling: true
      allowSpotInstances: false
      allowRightSizing: true
  
  # Premium: High-traffic services requiring tighter monitoring
  premium-api-cost:
    description: "High-traffic API with enhanced cost control"
    
    budgets:
      int-stable:
        base: 800
        scaling: 1.0      # Start higher for premium services
      pre-stable:
        base: 2500
        scaling: 1.4
      prod:
        base: 6000
        scaling: 1.67
    
    alerts:
      - name: "warning-70"
        threshold: 70     # Earlier warning for premium
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
            - "{teamLead}@company.com"
            - "finance-operations@company.com"
          pagerduty: "on-call-engineering"
          frequency: immediate
      
      - name: "spike-detection"
        threshold: 110    # Detect unusual spikes
        severity: warning
        channels:
          teams:
            - "#platform-finops"
          frequency: once
    
    optimization:
      enableAutoScaling: true
      allowSpotInstances: false
      allowRightSizing: true
  
  # Batch: One-off or periodic batch jobs
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
      enableAutoScaling: false    # Batch jobs don't auto-scale
      allowSpotInstances: true    # Can use cheaper instances
      allowRightSizing: false
  
  # Internal: Low-visibility internal tools
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

## 3. Size-Adjusted Budgets

### 3.1 How Sizing Multipliers Work

Cost profiles use **budget scaling factors** based on service size:

```
Size Multiplier Scale:
├─ small:    0.3× (1/3 of base)
├─ medium:   1.0× (1× base) 
├─ large:    2.0× (2× base)
├─ xlarge:   3.5× (3.5× base)
└─ xxlarge:  6.0× (6× base)
```

**Example: standard-api-cost profile**

Base budget for prod = $3000

Actual monthly budget by service size:
- Small service (0.3×): $900/month
- Medium service (1.0×): $3000/month
- Large service (2.0×): $6000/month
- XLarge service (3.5×): $10,500/month

### 3.2 Profile + Size Resolution

```python
def calculate_budget(service_size, profile_budgets, environment):
    """
    Resolve service cost budget at onboarding time
    """
    size_multipliers = {
        'small': 0.3,
        'medium': 1.0,
        'large': 2.0,
        'xlarge': 3.5,
        'xxlarge': 6.0
    }
    
    base_budget = profile_budgets[environment].base
    multiplier = size_multipliers[service_size]
    
    monthly_budget = base_budget * multiplier
    
    # Round to nearest $50
    return round(monthly_budget / 50) * 50
```

**Example Resolution**:
```yaml
Service: payment-processor
Profile: standard-api-cost
Size: large

Calculation:
├─ Int-Stable: base=$500 × 2.0 = $1000
├─ Pre-Stable: base=$1500 × 2.0 = $3000
└─ Prod:       base=$3000 × 2.0 = $6000
```

---

## 4. Simplified Service Definition

### 4.1 Service Entry with Cost Profile

```yaml
services:
  - name: payment-processor
    type: api
    image: <GAR_IMAGE>
    
    # Existing fields (unchanged)
    profile: public-api
    size: large
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # NEW: Cost profile reference
    costProfile: standard-api-cost
    
    # NEW: Cost allocation (minimal, required)
    cost:
      # These are the ONLY required cost fields
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice.johnson@company.com"
      
      # OPTIONAL: Environment-specific overrides
      # If a service's expected cost differs significantly from profile
      overrides:
        prod:
          budgetMultiplier: 1.5  # Scale profile budget by 1.5×
```

### 4.2 What's NOT in Services Anymore

Services no longer need to define:
- ❌ Budget amounts (calculated from profile + size)
- ❌ Alert thresholds (defined in profile)
- ❌ Alert channels (defined in profile with dynamic substitution)
- ❌ Optimization preferences (defined in profile)
- ❌ Apptio labels (auto-generated)

---

## 5. Variable Substitution in Profiles

### 5.1 Dynamic Channel Resolution

Profiles use **template variables** that get substituted per service:

```yaml
costProfiles:
  standard-api-cost:
    alerts:
      - threshold: 80
        channels:
          teams:
            - "#team-{service}"        # Substituted: #team-payment-processor
          email:
            - "{costOwner}@company.com" # Substituted: alice.johnson@company.com
            - "finance-operations@company.com"
```

**Resolution at sync time**:
```
Service: payment-processor
Cost Owner: alice.johnson@company.com

Profile variables:
  {service} → payment-processor
  {costOwner} → alice.johnson@company.com
  {teamLead} → [resolved from service metadata]

Resolved alert:
  channels:
    teams:
      - "#team-payment-processor"
    email:
      - "alice.johnson@company.com"
      - "finance-operations@company.com"
```

### 5.2 Supported Variables

```yaml
{service}              # Service name (e.g., payment-processor)
{costCenter}           # Cost center (e.g., CC-12345)
{costOwner}            # Cost owner email
{teamLead}             # Team lead (from service metadata)
{environment}          # Current environment (int-stable, pre-stable, prod)
{businessUnit}         # Business unit (retail-banking, etc.)
```

---

## 6. Cost Profile Application Workflow

### 6.1 Complete Data Flow

```
┌──────────────────────────────────────────────────────────┐
│ STEP 1: Service Definition in Catalog                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ services.yaml:                                           │
│   - name: payment-processor                              │
│     profile: public-api                                  │
│     size: large                  ← Size multiplier       │
│     costProfile: standard-api-cost ← Profile reference  │
│     cost:                                                │
│       costCenter: "CC-12345"     ← Only these 3 fields  │
│       businessUnit: "retail-banking"                     │
│       costOwner: "alice@company.com"                     │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ STEP 2: Expand Service (At Validation Time)             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ Load:                                                    │
│  • Service definition                                    │
│  • Profile: standard-api-cost                            │
│  • Size multipliers: large = 2.0                         │
│                                                          │
│ Calculate budgets:                                       │
│  • Int-Stable: $500 × 2.0 = $1000                       │
│  • Pre-Stable: $1500 × 2.0 = $3000                      │
│  • Prod: $3000 × 2.0 = $6000                            │
│                                                          │
│ Substitute variables:                                    │
│  • {service} → payment-processor                         │
│  • {costOwner} → alice@company.com                       │
│  • {costCenter} → CC-12345                               │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ STEP 3: Generated Full Cost Config (In-Memory)          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ cost:                                                    │
│   enabled: true                                          │
│   allocation:                                            │
│     costCenter: "CC-12345"                               │
│     businessUnit: "retail-banking"                       │
│     costOwner: "alice@company.com"                       │
│   budgets:                                               │
│     int-stable: { monthly: 1000 }                        │
│     pre-stable: { monthly: 3000 }                        │
│     prod: { monthly: 6000 }                              │
│   alerts:                                                │
│     - threshold: 80                                      │
│       channels:                                          │
│         teams: ["#team-payment-processor"]   ← Expanded │
│         email: ["alice@company.com"]                     │
│     - threshold: 100                                     │
│       channels:                                          │
│         teams: ["#team-payment-processor",               │
│                 "#platform-leadership"]                  │
│         email: ["alice@company.com", ...]               │
│         pagerduty: "on-call-engineering"                │
│   optimization:                                          │
│     enableAutoScaling: true                              │
│     allowSpotInstances: false                            │
│     allowRightSizing: true                               │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ STEP 4: Validation (Same as Before)                     │
├──────────────────────────────────────────────────────────┤
│  ✅ Schema validation                                    │
│  ✅ Budget amounts in valid ranges                       │
│  ✅ Cost center exists                                   │
│  ✅ Notification channels valid                          │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ STEP 5: Sync to Apptio (Same as Before)                 │
├──────────────────────────────────────────────────────────┤
│  • Create budgets for all environments                   │
│  • Configure alert rules with resolved channels          │
│  • Store sync metadata                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Implementation: Schema Update

### 7.1 services.yaml Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "services": {
      "type": "array",
      "items": {
        "properties": {
          "costProfile": {
            "type": "string",
            "description": "Reference to a cost profile from cost-profiles.yaml",
            "examples": ["standard-api-cost", "premium-api-cost", "batch-job-cost"]
          },
          "cost": {
            "type": "object",
            "required": ["costCenter", "businessUnit", "costOwner"],
            "properties": {
              "costCenter": {
                "type": "string",
                "pattern": "^CC-[0-9]{5}$"
              },
              "businessUnit": {
                "type": "string",
                "enum": ["retail-banking", "wealth-management", "corporate-banking", "technology", "operations"]
              },
              "costOwner": {
                "type": "string",
                "format": "email"
              },
              "overrides": {
                "type": "object",
                "description": "Environment-specific budget overrides",
                "properties": {
                  "int-stable": { "type": "object", "properties": { "budgetMultiplier": { "type": "number" } } },
                  "pre-stable": { "type": "object", "properties": { "budgetMultiplier": { "type": "number" } } },
                  "prod": { "type": "object", "properties": { "budgetMultiplier": { "type": "number" } } }
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

### 7.2 cost-profiles.yaml Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "costProfiles": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["description", "budgets", "alerts", "optimization"],
        "properties": {
          "description": {
            "type": "string"
          },
          "budgets": {
            "type": "object",
            "required": ["int-stable", "pre-stable", "prod"],
            "properties": {
              "int-stable": {
                "type": "object",
                "required": ["base", "scaling"],
                "properties": {
                  "base": { "type": "number", "minimum": 0 },
                  "scaling": { "type": "number", "minimum": 0.1 }
                }
              },
              "pre-stable": {
                "type": "object",
                "required": ["base", "scaling"],
                "properties": {
                  "base": { "type": "number", "minimum": 0 },
                  "scaling": { "type": "number", "minimum": 0.1 }
                }
              },
              "prod": {
                "type": "object",
                "required": ["base", "scaling"],
                "properties": {
                  "base": { "type": "number", "minimum": 0 },
                  "scaling": { "type": "number", "minimum": 0.1 }
                }
              }
            }
          },
          "alerts": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["threshold", "severity", "channels"]
            }
          },
          "optimization": {
            "type": "object",
            "properties": {
              "enableAutoScaling": { "type": "boolean" },
              "allowSpotInstances": { "type": "boolean" },
              "allowRightSizing": { "type": "boolean" }
            }
          }
        }
      }
    }
  }
}
```

---

## 8. Example Catalog Comparison

### Before (Full Cost Config)

```yaml
services:
  - name: payment-processor
    profile: public-api
    size: large
    cost:
      enabled: true
      allocation:
        costCenter: "CC-12345"
        businessUnit: "retail-banking"
        costOwner: "alice@company.com"
      budgets:
        int-stable:
          monthly: 1000
          currency: USD
        pre-stable:
          monthly: 3000
          currency: USD
        prod:
          monthly: 6000
          currency: USD
      alerts:
        - name: "warning-80"
          type: "budget"
          threshold: 80
          severity: "warning"
          channels:
            teams:
              - "#team-payment-processor"
            email:
              - "alice@company.com"
            frequency: "daily"
        - name: "critical-100"
          type: "budget"
          threshold: 100
          severity: "critical"
          channels:
            teams:
              - "#team-payment-processor"
              - "#platform-leadership"
            email:
              - "alice@company.com"
              - "finance-operations@company.com"
            pagerduty: "on-call-engineering"
            frequency: "immediate"
      optimization:
        enableAutoScaling: true
        allowSpotInstances: false
        allowRightSizing: true
      apptioLabels:
        serviceCode: "payment-processor"
        applicationId: "app-12345"
        businessService: "payments-platform"
```

### After (Profile-Based)

```yaml
services:
  - name: payment-processor
    profile: public-api
    size: large
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice@company.com"
```

**46 lines → 8 lines** (83% reduction)

For 100 services:
- Before: 4,600 lines of cost config
- After: 800 lines of cost config + 1 shared profile file (100 lines)
- **Savings: 3,700 lines**

---

## 9. Implementation Script: Profile Expansion

### 9.1 expand-cost-config.py

```python
#!/usr/bin/env python3
"""
Expand service cost configuration from profile reference to full config.
Runs during validation (before Apptio sync).
"""

import yaml
import re
from pathlib import Path

class CostProfileExpander:
    def __init__(self, catalog_dir):
        self.catalog_dir = Path(catalog_dir)
        self.services = self._load_yaml('services.yaml')['services']
        self.profiles = self._load_yaml('cost-profiles.yaml')['costProfiles']
        self.sizes = self._load_yaml('sizes.yaml')['sizes']
    
    def _load_yaml(self, filename):
        with open(self.catalog_dir / filename) as f:
            return yaml.safe_load(f)
    
    def expand_all(self):
        """Expand all services with cost profile references."""
        for service in self.services:
            self._expand_service(service)
        return self.services
    
    def _expand_service(self, service):
        """Expand single service: load profile, calculate budgets, substitute variables."""
        
        # Get profile reference
        profile_name = service.get('costProfile')
        if not profile_name:
            raise ValueError(f"Service '{service['name']}' missing costProfile")
        
        profile = self.profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Profile '{profile_name}' not found")
        
        # Get size multiplier
        service_size = service.get('size', 'medium')
        size_multiplier = self.sizes[service_size]['cost_multiplier']
        
        # Extract cost allocation
        cost_config = service.get('cost', {})
        
        # Calculate budgets per environment
        budgets = {}
        for env in ['int-stable', 'pre-stable', 'prod']:
            base = profile['budgets'][env]['base']
            scaling = profile['budgets'][env]['scaling']
            multiplier = size_multiplier
            
            # Apply environment-specific override if present
            if 'overrides' in cost_config and env in cost_config['overrides']:
                multiplier *= cost_config['overrides'][env].get('budgetMultiplier', 1.0)
            
            monthly = base * scaling * multiplier
            # Round to nearest $50
            monthly = round(monthly / 50) * 50
            
            budgets[env] = {'monthly': monthly, 'currency': 'USD'}
        
        # Substitute variables in alert channels
        alerts = self._substitute_variables(
            profile['alerts'],
            service,
            cost_config
        )
        
        # Build complete cost config
        expanded_cost = {
            'enabled': True,
            'allocation': {
                'costCenter': cost_config['costCenter'],
                'businessUnit': cost_config['businessUnit'],
                'costOwner': cost_config['costOwner']
            },
            'budgets': budgets,
            'alerts': alerts,
            'optimization': profile['optimization'],
            'apptioLabels': {
                'serviceCode': service['name'],
                'applicationId': f"app-{service['name']}",
                'businessService': cost_config.get('businessService', service['name'])
            }
        }
        
        # Store expanded config
        service['cost'] = expanded_cost
    
    def _substitute_variables(self, alerts, service, cost_config):
        """Substitute template variables in alert channels."""
        
        variables = {
            '{service}': service['name'],
            '{costCenter}': cost_config['costCenter'],
            '{costOwner}': cost_config['costOwner'],
            '{businessUnit}': cost_config['businessUnit'],
        }
        
        expanded_alerts = []
        for alert in alerts:
            expanded_alert = alert.copy()
            
            if 'channels' in alert:
                channels = alert['channels'].copy()
                
                # Substitute Teams channels
                if 'teams' in channels:
                    channels['teams'] = [
                        self._substitute_text(ch, variables)
                        for ch in channels['teams']
                    ]
                
                # Substitute email channels
                if 'email' in channels:
                    channels['email'] = [
                        self._substitute_text(ch, variables)
                        for ch in channels['email']
                    ]
                
                expanded_alert['channels'] = channels
            
            expanded_alerts.append(expanded_alert)
        
        return expanded_alerts
    
    def _substitute_text(self, text, variables):
        """Substitute all variables in a string."""
        result = text
        for var, value in variables.items():
            result = result.replace(var, value)
        return result

if __name__ == '__main__':
    import sys
    
    catalog_dir = sys.argv[1] if len(sys.argv) > 1 else 'kustomize/catalog'
    
    expander = CostProfileExpander(catalog_dir)
    expanded_services = expander.expand_all()
    
    # Output expanded configuration (for validation/debugging)
    print(yaml.dump({'services': expanded_services}, default_flow_style=False))
```

### 9.2 Integration into CI/CD

```yaml
# .github/workflows/validate-cost-metrics.yml

jobs:
  validate-cost-config:
    steps:
      
      # 1. Expand profiles
      - name: Expand cost profiles
        run: |
          python scripts/expand-cost-config.py kustomize/catalog > /tmp/expanded-services.yaml
      
      # 2. Validate expanded config (existing validation)
      - name: Validate expanded configuration
        run: |
          python scripts/validate-catalog-schema.py \
            --catalog /tmp/expanded-services.yaml \
            --schema schema/services-schema.json
      
      # 3. Check budget ranges
      - name: Validate budget amounts
        run: |
          python scripts/validate-budget-ranges.py \
            --catalog /tmp/expanded-services.yaml
```

---

## 10. Managing Cost Profiles

### 10.1 Adding a New Profile

```yaml
# cost-profiles.yaml

costProfiles:
  # ... existing profiles ...
  
  # NEW: Custom profile for ML workloads
  ml-workload-cost:
    description: "Machine learning training/inference with variable costs"
    
    budgets:
      int-stable:
        base: 1000        # ML workloads are expensive even in test
        scaling: 0.8
      pre-stable:
        base: 3000
        scaling: 1.2
      prod:
        base: 8000        # Can scale significantly
        scaling: 2.0
    
    alerts:
      - name: "spike-detection"
        threshold: 50     # Alert early for cost spikes
        severity: warning
        channels:
          teams: ["#team-{service}", "#ml-ops"]
          frequency: immediate
      
      - name: "warning-80"
        threshold: 80
        severity: warning
        channels:
          teams: ["#team-{service}"]
          frequency: daily
      
      - name: "critical-100"
        threshold: 100
        severity: critical
        channels:
          teams: ["#team-{service}", "#platform-leadership"]
          email: ["{costOwner}@company.com"]
          frequency: immediate
    
    optimization:
      enableAutoScaling: true
      allowSpotInstances: true  # ML often tolerates interruptions
      allowRightSizing: true
```

### 10.2 Updating an Existing Profile

**Before**: Updating a profile affects ALL services using it (good for organization-wide changes)

**After**: Service gets automatic budget recalculation on next sync

```yaml
# Update standard-api-cost profile to be stricter
costProfiles:
  standard-api-cost:
    alerts:
      - name: "warning-75"        # Changed from 80 to 75
        threshold: 75
        # ... rest unchanged
```

All services using `standard-api-cost` now get warned at 75% (effective next sync).

---

## 11. Migration Path

### Phase 1: Deploy Cost Profile Infrastructure (Week 1)

- [x] Create `cost-profiles.yaml` with standard profiles
- [x] Update catalog schemas (services + profiles)
- [x] Implement `expand-cost-config.py`
- [x] Add expansion step to CI/CD validation

### Phase 2: Migrate Pilot Services (Week 2)

- Migrate 5 representative services to profile-based cost:
  - 1 public API (payment-service)
  - 1 internal API (user-service)
  - 1 batch job (data-export)
  - 1 high-traffic API (search-service)
  - 1 internal tool (metrics-exporter)

- Verify:
  - Expanded config matches original
  - Budgets calculated correctly
  - Apptio sync works with expanded config
  - Alerts fire as expected

### Phase 3: Mass Migration (Week 3)

- Migrate remaining services
- Run parallel validation (old vs expanded)
- Update documentation
- Train teams

### Phase 4: Deprecation (Week 4)

- Remove old inline cost config support
- Require all new services to use profiles
- Archive old patterns in documentation

---

## 12. Benefits of Cost Profile Abstraction

### Reduced Complexity

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Lines per service (cost) | 45 | 5 | 89% |
| Total catalog lines (100 services) | 4,600 | 800 | 83% |
| Cost profile files | 0 | 1 | N/A |
| Profile templates | 0 | 6 | N/A |

### Governance & Consistency

✅ **Centralized cost policies** - All cost rules in one place (cost-profiles.yaml)
✅ **Easy organization-wide changes** - Update profile once, affects all using services
✅ **Audit trail** - Profile changes tracked in git history
✅ **Compliance** - Enforce company cost policies via profiles

### Operational Efficiency

✅ **New services faster** - Reference a profile instead of defining cost from scratch
✅ **Fewer mistakes** - Variables substitute automatically (no manual typos)
✅ **Team independence** - Services don't need cost expertise (platform team manages profiles)
✅ **Self-service scale** - Developers can onboard services without cost knowledge

### Financial Control

✅ **Right-sized budgets** - Calculated from proven formulas (not guesses)
✅ **Consistent thresholds** - All similar services alert the same way
✅ **Flexible overrides** - Still allow per-service customization when needed
✅ **Clear ownership** - Cost owner specified per service (not inherited)

---

## 13. Example: Full Migration

### Before Profile Abstraction

```yaml
# kustomize/catalog/services.yaml (massive, 4600 lines for 100 services)

services:
  - name: payment-processor
    cost:
      enabled: true
      allocation: { costCenter: "CC-12345", ... }
      budgets:
        int-stable: { monthly: 1000 }
        pre-stable: { monthly: 3000 }
        prod: { monthly: 6000 }
      alerts:
        - threshold: 80
          channels:
            teams: ["#team-payment-processor"]
            email: ["alice@company.com"]
        - threshold: 100
          channels:
            teams: ["#team-payment-processor", "#platform-leadership"]
            email: ["alice@company.com"]
  
  - name: user-service
    cost:
      enabled: true
      allocation: { costCenter: "CC-12346", ... }
      budgets:
        int-stable: { monthly: 800 }
        pre-stable: { monthly: 2400 }
        prod: { monthly: 5000 }
      alerts:
        - threshold: 80
          channels:
            teams: ["#team-users"]
            email: ["bob@company.com"]
        - threshold: 100
          channels:
            teams: ["#team-users", "#platform-leadership"]
            email: ["bob@company.com"]
  
  # ... 98 more services with repetitive cost configs
```

### After Profile Abstraction

```yaml
# kustomize/catalog/services.yaml (lightweight, ~500 lines for 100 services)

services:
  - name: payment-processor
    profile: public-api
    size: large
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice@company.com"
  
  - name: user-service
    profile: public-api
    size: medium
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12346"
      businessUnit: "retail-banking"
      costOwner: "bob@company.com"
  
  # ... 98 more services with minimal cost config

---

# kustomize/catalog/cost-profiles.yaml (shared, 150 lines)

costProfiles:
  standard-api-cost:
    description: "REST API with standard cost management"
    budgets:
      int-stable: { base: 500, scaling: 1.0 }
      pre-stable: { base: 1500, scaling: 1.33 }
      prod: { base: 3000, scaling: 1.67 }
    alerts:
      - threshold: 80
        channels:
          teams: ["#team-{service}"]
          email: ["{costOwner}@company.com"]
      - threshold: 100
        channels:
          teams: ["#team-{service}", "#platform-leadership"]
          email: ["{costOwner}@company.com"]
    optimization:
      enableAutoScaling: true
      allowSpotInstances: false
      allowRightSizing: true
```

**Result**: Catalog maintainability improves dramatically while cost control is maintained.

---

## Summary

Cost profile abstraction applies the same battle-tested pattern used for resource profiles and shapes:

1. **Define reusable templates** (cost-profiles.yaml)
2. **Reference by name** in service definitions
3. **Calculate values** at validation time
4. **Substitute variables** per service
5. **Generate complete config** for Apptio sync

**Benefits**:
- 83% reduction in catalog lines
- Centralized cost policies
- Easier governance and compliance
- Self-service at scale
- Better financial control

---

**Document Version**: 1.0
**Created**: 2025-11-15
**Status**: READY FOR IMPLEMENTATION
