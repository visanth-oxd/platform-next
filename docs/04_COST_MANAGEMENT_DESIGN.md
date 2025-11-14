# Cost Management & FinOps - Detailed Design

## Executive Summary

This document describes how granular cost management is integrated into the Platform-Next system to provide visibility, optimization, and governance of Kubernetes infrastructure costs.

**Key Points**:
- Per-service cost tracking
- Real-time cost visibility in Backstage
- Budget alerts and governance
- Cost optimization recommendations
- Chargeback to teams
- Integration with catalog and T-shirt sizing

---

## 1. Why Cost Management in Platform?

### The Problem

**Current State** (Without Cost Management):
- ❌ No visibility into per-service costs
- ❌ Over-provisioned resources (wasteful)
- ❌ No budget accountability
- ❌ Can't optimize without data
- ❌ Surprise cloud bills
- ❌ No cost attribution to teams

**Business Impact**:
- Estimated 30-40% waste in K8s resources
- $50K-$100K/month wasted on over-provisioning
- Teams don't know their infrastructure costs
- No incentive to optimize

### The Solution

**Integrated FinOps Platform**:
- ✅ Real-time cost per service, per environment, per team
- ✅ Budget limits and alerts
- ✅ Cost optimization recommendations
- ✅ Chargeback reporting
- ✅ Right-sizing suggestions based on actual usage
- ✅ Cost trends and forecasting

**Expected Savings**: 20-30% reduction in infrastructure costs ($15K-$30K/month)

---

## 2. Cost Management Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Cost Data Collection Layer                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Kubernetes Clusters                                        │
│    ↓                                                        │
│  Prometheus (metrics)                                       │
│    ↓                                                        │
│  OpenCost / Kubecost (cost calculation)                    │
│    ↓                                                        │
│  Cost Database (PostgreSQL/TimescaleDB)                     │
│                                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Cost Analytics Layer                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cost Aggregation Service                                   │
│    • Per-service costs                                      │
│    • Per-team costs                                         │
│    • Per-environment costs                                  │
│    • Per-region costs                                       │
│    • Time-series analysis                                   │
│                                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Cost Presentation Layer                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Backstage Cost Plugin                                      │
│    • Cost widget on service pages                           │
│    • Cost trends and forecasts                              │
│    • Budget alerts                                          │
│    • Optimization suggestions                               │
│                                                             │
│  Cost Dashboard                                             │
│    • Team-level view                                        │
│    • Service comparison                                     │
│    • Environment breakdown                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Cost Tracking Implementation

### Label Strategy for Cost Attribution

**All resources labeled with cost dimensions**:

```yaml
# Applied via Kustomize (automatically)
commonLabels:
  # Service identification
  app: payment-service
  app.kubernetes.io/name: payment-service
  
  # Cost dimensions
  cost.team: payments-team
  cost.service: payment-service
  cost.environment: prod
  cost.region: euw1
  cost.archetype: api
  cost.size: large
  cost.business-unit: retail-banking
  cost.cost-center: CC-12345
```

**How Labels Get Applied**:

1. **In Kustomize Generation Script**:
```bash
# scripts/generate-kz-v3.sh

# Load service metadata
SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" catalog/services.yaml)
TEAM=$(echo "$SERVICE_DATA" | yq eval '.team' -)
SIZE=$(echo "$SERVICE_DATA" | yq eval '.size' -)
ARCHETYPE=$(echo "$SERVICE_DATA" | yq eval '.archetype' -)

# Load team metadata (NEW)
TEAM_DATA=$(yq eval ".teams[] | select(.name == \"$TEAM\")" catalog/teams.yaml)
BUSINESS_UNIT=$(echo "$TEAM_DATA" | yq eval '.businessUnit' -)
COST_CENTER=$(echo "$TEAM_DATA" | yq eval '.costCenter' -)

# Add to kustomization.yaml
cat >> "$TMP_DIR/kustomization.yaml" <<EOF
commonLabels:
  app: $SERVICE
  env: $ENV
  region: $REGION
  cost.team: $TEAM
  cost.service: $SERVICE
  cost.environment: $ENV
  cost.region: $REGION
  cost.archetype: $ARCHETYPE
  cost.size: $SIZE
  cost.business-unit: $BUSINESS_UNIT
  cost.cost-center: $COST_CENTER
EOF
```

2. **In Catalog (Extended)**:

```yaml
# catalog/services.yaml
services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    team: payments-team
    
    # Cost metadata (NEW)
    cost:
      businessUnit: retail-banking
      costCenter: CC-12345
      budgetMonthly: 5000  # $5K/month budget
      alertThreshold: 0.8  # Alert at 80%
```

3. **In Team Catalog (NEW)**:

```yaml
# catalog/teams.yaml
teams:
  - name: payments-team
    displayName: Payments Team
    email: payments-team@company.com
    teams: "#team-payments"
    
    # Cost allocation
    businessUnit: retail-banking
    costCenter: CC-12345
    department: Engineering
    budgetMonthly: 50000  # $50K/month total team budget
    
    # Team services
    services:
      - payment-service
      - payment-processor
      - fraud-detection
```

---

## 4. Cost Collection Tool: OpenCost

### Why OpenCost?

**Alternatives Considered**:
| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **OpenCost** | Free, K8s-native, accurate | Limited UI | ✅ **Selected** |
| **Kubecost** | Rich UI, alerts | Expensive ($500+/mo) | ❌ Too costly |
| **CloudHealth** | Multi-cloud | Not K8s-native | ❌ Wrong fit |
| **Custom** | Full control | Development cost | ❌ Reinvent wheel |

**Decision**: OpenCost (open-source, accurate, integrates well)

### OpenCost Deployment

**Install in Each Cluster**:

```bash
# Install OpenCost via Helm
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.exporter.defaultClusterId=prod-euw1 \
  --set opencost.prometheus.external.enabled=true \
  --set opencost.prometheus.external.url=http://prometheus:9090
```

**What OpenCost Provides**:
- Per-pod cost calculation
- CPU, memory, storage, network costs
- Label-based cost aggregation
- Prometheus metrics exposure
- API for querying costs

**API Example**:
```bash
# Get cost for payment-service in prod
curl -G http://opencost:9003/allocation/compute \
  --data-urlencode 'window=7d' \
  --data-urlencode 'aggregate=label:cost.service' \
  --data-urlencode 'filter=label[cost.service]:payment-service,label[cost.environment]:prod'

# Response:
{
  "payment-service": {
    "cpuCost": 120.50,
    "memoryCost": 85.30,
    "gpuCost": 0,
    "pvCost": 25.00,
    "networkCost": 12.50,
    "totalCost": 243.30
  }
}
```

---

## 5. Cost Database & Aggregation

### Cost Data Pipeline

```
Kubernetes Metrics (cAdvisor)
         ↓
Prometheus (scrapes metrics every 1m)
         ↓
OpenCost (calculates costs)
         ↓
Cost Aggregation Service (our microservice)
         ↓
TimescaleDB (time-series cost data)
         ↓
Cost API (REST API for queries)
         ↓
Backstage Cost Plugin (UI)
```

### Cost Aggregation Service

**Purpose**: Collect, aggregate, and serve cost data

**Technology**: Python (FastAPI) or Go

**Responsibilities**:
- Poll OpenCost API every 15 minutes
- Aggregate costs by service, team, environment
- Store in TimescaleDB (time-series optimized)
- Calculate trends and forecasts
- Detect anomalies and budget breaches
- Expose REST API for cost queries

**Database Schema**:

```sql
-- TimescaleDB tables

CREATE TABLE service_costs (
  time TIMESTAMPTZ NOT NULL,
  service_name VARCHAR(100) NOT NULL,
  environment VARCHAR(50) NOT NULL,
  region VARCHAR(50) NOT NULL,
  team VARCHAR(100) NOT NULL,
  archetype VARCHAR(50) NOT NULL,
  size VARCHAR(20) NOT NULL,
  business_unit VARCHAR(100),
  cost_center VARCHAR(50),
  
  -- Cost breakdown
  cpu_cost DECIMAL(10,2),
  memory_cost DECIMAL(10,2),
  storage_cost DECIMAL(10,2),
  network_cost DECIMAL(10,2),
  total_cost DECIMAL(10,2),
  
  -- Resource usage
  cpu_cores DECIMAL(10,4),
  memory_gb DECIMAL(10,4),
  
  PRIMARY KEY (time, service_name, environment, region)
);

-- Create hypertable for time-series optimization
SELECT create_hypertable('service_costs', 'time');

-- Create indexes
CREATE INDEX idx_service_costs_service ON service_costs(service_name, time DESC);
CREATE INDEX idx_service_costs_team ON service_costs(team, time DESC);
CREATE INDEX idx_service_costs_env ON service_costs(environment, time DESC);

-- Materialized view for daily aggregates
CREATE MATERIALIZED VIEW service_costs_daily
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', time) AS day,
  service_name,
  environment,
  team,
  SUM(total_cost) as daily_cost,
  AVG(cpu_cores) as avg_cpu,
  AVG(memory_gb) as avg_memory
FROM service_costs
GROUP BY day, service_name, environment, team;

-- Budget tracking table
CREATE TABLE service_budgets (
  service_name VARCHAR(100) PRIMARY KEY,
  monthly_budget DECIMAL(10,2) NOT NULL,
  alert_threshold DECIMAL(3,2) DEFAULT 0.8,
  team VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost alerts table
CREATE TABLE cost_alerts (
  id SERIAL PRIMARY KEY,
  service_name VARCHAR(100),
  alert_type VARCHAR(50),  -- budget_breach, anomaly, optimization
  severity VARCHAR(20),    -- info, warning, critical
  message TEXT,
  current_cost DECIMAL(10,2),
  threshold_cost DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  notified BOOLEAN DEFAULT FALSE
);
```

---

## 6. Cost API Service

**Endpoints**:

```yaml
GET /api/v1/costs/service/{serviceName}
  Description: Get cost for specific service
  Query Params:
    - window: 7d, 30d, 90d (default: 7d)
    - environment: int-stable, pre-stable, prod (optional)
    - region: euw1, euw2 (optional)
  Response:
    {
      "service": "payment-service",
      "totalCost": 243.30,
      "breakdown": {
        "cpu": 120.50,
        "memory": 85.30,
        "storage": 25.00,
        "network": 12.50
      },
      "environments": {
        "int-stable": 15.20,
        "pre-stable": 28.10,
        "prod": 200.00
      },
      "trend": "+5.2%",  # vs previous period
      "forecast": 250.00,  # projected for next period
      "budget": {
        "monthly": 5000.00,
        "used": 243.30,
        "remaining": 4756.70,
        "percentUsed": 4.87,
        "status": "healthy"
      }
    }

GET /api/v1/costs/team/{teamName}
  Description: Get total cost for team (all services)
  Response:
    {
      "team": "payments-team",
      "totalCost": 8543.50,
      "serviceCount": 8,
      "services": [
        {"name": "payment-service", "cost": 243.30},
        {"name": "fraud-detection", "cost": 512.80},
        ...
      ],
      "budget": {
        "monthly": 50000.00,
        "used": 8543.50,
        "percentUsed": 17.09
      }
    }

GET /api/v1/costs/trends/{serviceName}
  Description: Get cost trends over time
  Response:
    {
      "service": "payment-service",
      "period": "30d",
      "dataPoints": [
        {"date": "2025-10-10", "cost": 230.50},
        {"date": "2025-10-11", "cost": 235.20},
        ...
      ],
      "trend": "increasing",
      "trendPercent": 8.5,
      "anomalies": []
    }

POST /api/v1/costs/recommendations/{serviceName}
  Description: Get cost optimization recommendations
  Response:
    {
      "service": "payment-service",
      "currentSize": "large",
      "currentMonthlyCost": 243.30,
      "recommendations": [
        {
          "type": "right-size",
          "suggestion": "Reduce to medium size",
          "reasoning": "CPU usage < 40% for last 7 days",
          "potentialSavings": 121.65,  # 50% savings
          "confidence": 0.85,
          "impact": "low"  # low/medium/high
        }
      ]
    }

GET /api/v1/costs/alerts
  Description: Get active cost alerts
  Response:
    {
      "alerts": [
        {
          "id": 123,
          "service": "fraud-detection",
          "type": "budget_breach",
          "severity": "warning",
          "message": "Service exceeded 80% of monthly budget",
          "currentCost": 4200.00,
          "budgetLimit": 5000.00,
          "percentUsed": 84.0
        }
      ]
    }
```

---

## 7. Integration with Catalog

### Extended Service Catalog with Cost Config

```yaml
# catalog/services.yaml (extended)
services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    environments: [int, pre, prod]
    team: payments-team
    
    # ================================================
    # COST CONFIGURATION (NEW)
    # ================================================
    cost:
      # Budget limits
      budgetMonthly: 5000  # $5,000/month budget
      alertThreshold: 0.8  # Alert at 80% of budget
      
      # Cost center allocation
      costCenter: CC-12345
      businessUnit: retail-banking
      
      # Optimization settings
      autoOptimize: true   # Allow auto-scaling down
      minSize: medium      # Don't go below medium
      
      # Chargeback
      chargebackEnabled: true
      chargebackRate: 1.2  # 20% markup for platform overhead
```

### Extended Size Definitions with Cost

```yaml
# catalog/sizes.yaml (extended)
sizes:
  small:
    cpu: 100m
    memory: 256Mi
    scaling:
      min: 1
      max: 3
    
    # ================================================
    # COST METADATA (NEW)
    # ================================================
    cost:
      hourlyCost: 0.015    # $0.015/hour
      monthlyCost: 10.80   # $10.80/month
      breakdown:
        cpu: 0.008         # $0.008/hour for CPU
        memory: 0.005      # $0.005/hour for memory
        overhead: 0.002    # $0.002/hour for platform
  
  medium:
    cpu: 250m
    memory: 512Mi
    scaling:
      min: 2
      max: 6
    cost:
      hourlyCost: 0.035    # $0.035/hour
      monthlyCost: 25.20   # $25.20/month
      breakdown:
        cpu: 0.018
        memory: 0.012
        overhead: 0.005
  
  large:
    cpu: 500m
    memory: 1Gi
    scaling:
      min: 3
      max: 10
    cost:
      hourlyCost: 0.070    # $0.070/hour
      monthlyCost: 50.40   # $50.40/month
      breakdown:
        cpu: 0.040
        memory: 0.023
        overhead: 0.007
  
  xlarge:
    cpu: 1000m
    memory: 2Gi
    scaling:
      min: 4
      max: 15
    cost:
      hourlyCost: 0.140    # $0.140/hour
      monthlyCost: 100.80  # $100.80/month
      breakdown:
        cpu: 0.080
        memory: 0.045
        overhead: 0.015
```

**Usage**: When developer selects "large", they see: "Estimated cost: ~$50/month"

---

## 8. Backstage Cost Plugin

### Cost Widget on Service Page

**Location**: Service page → "Cost" tab

**UI Design**:

```
┌──────────────────────────────────────────────────────────────┐
│ payment-service                                    Cost Tab  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Current Month Cost                          Budget Status    │
│ ┌─────────────────────────┐  ┌──────────────────────────┐   │
│ │                         │  │ Budget: $5,000/month     │   │
│ │   $243.30               │  │ Used: $243.30 (4.87%)    │   │
│ │                         │  │ Remaining: $4,756.70     │   │
│ │   ↑ 5.2% vs last month  │  │                          │   │
│ │                         │  │ [████░░░░░░░░░░░░░] 5%   │   │
│ └─────────────────────────┘  │ Status: ✅ Healthy       │   │
│                               └──────────────────────────┘   │
│                                                               │
│ Cost Breakdown by Environment                                │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Environment   │ Cost     │ % of Total │ Trend          │  │
│ ├───────────────┼──────────┼────────────┼────────────────┤  │
│ │ prod (euw1)   │ $200.00  │ 82.2%      │ ↑ +3%          │  │
│ │ pre-stable    │ $ 28.10  │ 11.5%      │ → stable       │  │
│ │ int-stable    │ $ 15.20  │  6.3%      │ ↓ -2%          │  │
│ └───────────────┴──────────┴────────────┴────────────────┘  │
│                                                               │
│ Cost Breakdown by Resource                                   │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Resource │ Cost     │ Usage              │ Efficiency   │  │
│ ├──────────┼──────────┼────────────────────┼──────────────┤  │
│ │ CPU      │ $120.50  │ 1.5 cores avg      │ 75% util ✅  │  │
│ │ Memory   │ $ 85.30  │ 3.2 GB avg         │ 65% util ⚠️  │  │
│ │ Storage  │ $ 25.00  │ 50 GB              │ 80% util ✅  │  │
│ │ Network  │ $ 12.50  │ 120 GB egress      │ N/A          │  │
│ └──────────┴──────────┴────────────────────┴──────────────┘  │
│                                                               │
│ 💡 Optimization Recommendations                              │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 1. Right-size memory: large → medium                     │  │
│ │    Savings: ~$40/month (Memory usage consistently < 50%) │  │
│ │    Confidence: High (85%)                                 │  │
│ │    Impact: Low                                            │  │
│ │    [Apply Recommendation] [Dismiss]                       │  │
│ │                                                           │  │
│ │ 2. Enable HPA for cost optimization                       │  │
│ │    Savings: ~$30/month (Scale down during off-peak)      │  │
│ │    Confidence: Medium (70%)                               │  │
│ │    Impact: Low                                            │  │
│ │    [Apply Recommendation] [Dismiss]                       │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ Cost Trend (Last 30 Days)                                    │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ $300 │                                                   │  │
│ │      │                                                   │  │
│ │ $250 │                              ●──●                 │  │
│ │      │                         ●──●                      │  │
│ │ $200 │                    ●──●                           │  │
│ │      │               ●──●                                │  │
│ │ $150 │          ●──●                                     │  │
│ │      │     ●──●                                          │  │
│ │ $100 │ ●──●                                              │  │
│ │      └───────────────────────────────────────────────────│  │
│ │       Oct 10    Oct 17    Oct 24    Oct 31    Nov 7      │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ [Download Report] [Set Budget Alert] [View Team Costs]       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Cost Optimization Engine

### Automatic Right-Sizing Recommendations

**Algorithm**:

```python
# cost-optimizer/recommender.py

def analyze_service(service_name: str, window_days: int = 7):
    """Analyze service usage and recommend optimizations"""
    
    # Get actual resource usage
    metrics = get_prometheus_metrics(service_name, window_days)
    
    cpu_p95 = percentile(metrics['cpu_usage'], 95)
    memory_p95 = percentile(metrics['memory_usage'], 95)
    
    # Get current size
    current_size = get_service_size(service_name)
    current_cost = SIZE_COSTS[current_size]['monthlyCost']
    
    # Calculate efficiency
    cpu_efficiency = cpu_p95 / SIZE_CONFIGS[current_size]['cpu']
    memory_efficiency = memory_p95 / SIZE_CONFIGS[current_size]['memory']
    
    recommendations = []
    
    # Recommendation 1: Right-size down
    if cpu_efficiency < 0.5 and memory_efficiency < 0.5:
        smaller_size = get_next_smaller_size(current_size)
        savings = current_cost - SIZE_COSTS[smaller_size]['monthlyCost']
        
        recommendations.append({
            "type": "right-size-down",
            "from": current_size,
            "to": smaller_size,
            "reasoning": f"CPU usage {cpu_efficiency*100:.1f}%, Memory {memory_efficiency*100:.1f}%",
            "savings": savings,
            "confidence": calculate_confidence(metrics),
            "impact": "low"  # Low risk since usage is low
        })
    
    # Recommendation 2: Right-size up
    if cpu_efficiency > 0.85 or memory_efficiency > 0.85:
        larger_size = get_next_larger_size(current_size)
        additional_cost = SIZE_COSTS[larger_size]['monthlyCost'] - current_cost
        
        recommendations.append({
            "type": "right-size-up",
            "from": current_size,
            "to": larger_size,
            "reasoning": f"High utilization: CPU {cpu_efficiency*100:.1f}%, Memory {memory_efficiency*100:.1f}%",
            "additionalCost": additional_cost,
            "confidence": calculate_confidence(metrics),
            "impact": "medium"  # Medium risk, performance improvement
        })
    
    # Recommendation 3: Enable HPA for cost savings
    if not has_hpa(service_name):
        # Calculate potential savings from scaling down during off-peak
        off_peak_hours = 12  # hours per day
        potential_savings = current_cost * 0.3  # 30% savings estimate
        
        recommendations.append({
            "type": "enable-hpa",
            "reasoning": "Scale down during off-peak hours (12h/day)",
            "savings": potential_savings,
            "confidence": 0.7,
            "impact": "low"
        })
    
    # Recommendation 4: Spot instances (if applicable)
    if current_size in ['large', 'xlarge'] and environment == 'dev':
        savings = current_cost * 0.6  # 60% savings on spot
        
        recommendations.append({
            "type": "use-spot-instances",
            "reasoning": "Dev environment suitable for spot instances",
            "savings": savings,
            "confidence": 0.9,
            "impact": "medium"  # May have interruptions
        })
    
    return recommendations
```

---

## 10. Budget Alerts & Governance

### Alert System

**Alert Types**:

1. **Budget Threshold Alert**
   - Trigger: Service cost > 80% of monthly budget
   - Severity: Warning
   - Action: Notify team in Teams
   - Example: "⚠️ payment-service used 85% of monthly budget ($4,250 / $5,000)"

2. **Budget Exceeded Alert**
   - Trigger: Service cost > 100% of monthly budget
   - Severity: Critical
   - Action: Notify team + platform team
   - Example: "🚨 payment-service exceeded monthly budget! ($5,500 / $5,000)"

3. **Anomaly Alert**
   - Trigger: Cost spike > 50% vs previous week
   - Severity: Warning
   - Action: Notify team
   - Example: "⚠️ payment-service cost increased 65% this week"

4. **Optimization Alert**
   - Trigger: Service running > 7 days with low utilization
   - Severity: Info
   - Action: Send recommendation
   - Example: "💡 payment-service can be right-sized to save $120/month"

**Alert Delivery**:

```yaml
# Via Teams webhook
POST https://company.webhook.office.com/webhooks/...
{
  "@type": "MessageCard",
  "@context": "http://schema.org/extensions",
  "summary": "Cost Alert: payment-service",
  "themeColor": "FFA500",
  "title": "⚠️ Budget Alert",
  "sections": [{
    "activityTitle": "payment-service exceeded 80% of budget",
    "facts": [
      {"name": "Service", "value": "payment-service"},
      {"name": "Current Cost", "value": "$4,250"},
      {"name": "Budget", "value": "$5,000"},
      {"name": "% Used", "value": "85%"},
      {"name": "Remaining", "value": "$750"}
    ],
    "text": "Consider right-sizing or optimizing resources."
  }],
  "potentialAction": [
    {
      "@type": "OpenUri",
      "name": "View in Backstage",
      "targets": [{
        "os": "default",
        "uri": "https://backstage.company.com/catalog/payment-service"
      }]
    }
  ]
}
```

---

## 11. Cost Optimization Workflow

### Auto-Optimization (Optional)

**When Enabled** (`cost.autoOptimize: true`):

```
Cost Optimizer runs daily
  ↓
Analyzes last 7 days of usage
  ↓
Identifies over-provisioned services
  ↓
Calculates confidence score
  ↓
If confidence > 85% AND impact = low:
  1. Create PR to update catalog
     (change size: large → medium)
  2. Send Teams notification
  3. Wait 24 hours for veto
  4. If no veto, auto-merge PR
  5. CI regenerates manifests
  6. Next deployment uses new size
```

**Manual Optimization**:

```
Backstage shows recommendation
  ↓
Developer clicks "Apply Recommendation"
  ↓
Opens modal:
  ┌────────────────────────────────────────┐
  │ Apply Optimization?                    │
  ├────────────────────────────────────────┤
  │ Change: large → medium                 │
  │ Savings: ~$120/month                   │
  │ Impact: Low                            │
  │                                        │
  │ This will:                             │
  │ 1. Update catalog                      │
  │ 2. Regenerate manifests                │
  │ 3. Apply on next deployment            │
  │                                        │
  │ [Cancel] [Apply to Int Only] [Apply]  │
  └────────────────────────────────────────┘
  ↓
Creates PR with size change
  ↓
Developer reviews and merges
  ↓
Optimization applied
```

---

## 12. Chargeback & Reporting

### Team-Level Chargeback

**Monthly Chargeback Report**:

```yaml
# Generated monthly via Cost API
Report:
  Team: payments-team
  Period: 2025-11
  Total Cost: $8,543.50
  Budget: $50,000.00
  Status: Under budget (17% used)
  
  Services:
    - payment-service:
        Cost: $243.30
        Environments:
          prod: $200.00 (82%)
          pre: $28.10 (12%)
          int: $15.20 (6%)
        Size: large
        Recommendation: Consider medium size
    
    - fraud-detection:
        Cost: $512.80
        Environments:
          prod: $480.00 (94%)
          pre: $32.80 (6%)
        Size: xlarge
        Recommendation: None (well-utilized)
    
    # ... 6 more services
  
  Savings Opportunities:
    - Right-size payment-service: $120/month
    - Enable HPA on 3 services: $200/month
    Total Potential Savings: $320/month (3.7% of team budget)
```

**Delivery**:
- Email to team lead (monthly)
- Teams channel post (monthly summary)
- Backstage dashboard (real-time)
- Executive report (quarterly)

---

## 13. Integration with Harness

### Cost Tracking in Deployments

**Add to Harness Pipeline**:

```yaml
# In pipeline template
execution:
  steps:
    # After successful deployment
    - step:
        type: Http
        name: Record Deployment Cost
        identifier: record_cost
        spec:
          url: https://cost-api.company.com/api/v1/costs/deployments
          method: POST
          headers:
            - key: Content-Type
              value: application/json
          body: |
            {
              "service": "{{SERVICE_NAME}}",
              "environment": "<+pipeline.variables.targetEnvironment>",
              "region": "<+pipeline.variables.targetRegion>",
              "imageTag": "<+pipeline.variables.imageTag>",
              "size": "{{SIZE}}",
              "timestamp": "<+pipeline.startTs>",
              "deploymentId": "<+pipeline.executionId>"
            }
        timeout: 30s
```

**Deployment Cost Tracking**:
- Record every deployment
- Track deployment frequency
- Calculate cost of deployments (CI/CD overhead)
- Attribute to service cost

---

## 14. Cost Dashboard (Team View)

**Location**: Backstage → Cost Dashboard (custom page)

**Features**:

```
┌──────────────────────────────────────────────────────────────┐
│ Cost Dashboard - payments-team                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Team Overview                                                │
│ ┌────────────────┬────────────────┬────────────────────┐     │
│ │ This Month     │ Last Month     │ Trend              │     │
│ ├────────────────┼────────────────┼────────────────────┤     │
│ │ $8,543.50      │ $8,102.30      │ ↑ +5.4%            │     │
│ └────────────────┴────────────────┴────────────────────┘     │
│                                                               │
│ Budget: $50,000/month    [████░░░░░░░░░░░░░] 17%            │
│                                                               │
│ Top 5 Services by Cost                                       │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Service            │ Cost     │ % of Team │ Trend       │  │
│ ├────────────────────┼──────────┼───────────┼─────────────┤  │
│ │ fraud-detection    │ $512.80  │ 6.0%      │ → stable    │  │
│ │ payment-gateway    │ $420.50  │ 4.9%      │ ↑ +8%       │  │
│ │ payment-service    │ $243.30  │ 2.8%      │ ↑ +5%       │  │
│ │ settlement-service │ $198.40  │ 2.3%      │ ↓ -3%       │  │
│ │ reconciliation     │ $165.20  │ 1.9%      │ → stable    │  │
│ └────────────────────┴──────────┴───────────┴─────────────┘  │
│                                                               │
│ Cost by Environment                                          │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ prod: $7,200 (84%)                                        │  │
│ │ pre: $950 (11%)                                           │  │
│ │ int: $393.50 (5%)                                         │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ 💰 Total Savings Opportunities: $1,240/month (14.5%)         │
│                                                               │
│ [Download Report] [Budget Settings] [Optimization Queue]     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 15. Catalog Updates for Cost

### Service Onboarding Form (Updated)

**Backstage Template - Add Cost Fields**:

```yaml
# backstage/templates/kubernetes-service.yaml (excerpt)

parameters:
  - title: Cost & Budget Configuration
    properties:
      monthlyBudget:
        title: Monthly Budget (USD)
        type: number
        description: Maximum monthly cost for this service
        default: 1000
        minimum: 100
        maximum: 50000
        ui:help: 'Estimated cost based on size will be shown'
      
      costCenter:
        title: Cost Center
        type: string
        description: Cost center for chargeback
        ui:field: EntityPicker
        ui:options:
          catalogFilter:
            kind: CostCenter
      
      estimatedCost:
        title: Estimated Monthly Cost (Calculated)
        type: string
        description: Estimated cost based on selected size
        ui:field: ReadOnlyField
        ui:value: ${{ parameters.size == 'small' && '$10.80' || parameters.size == 'medium' && '$25.20' || parameters.size == 'large' && '$50.40' || '$100.80' }}
        ui:help: 'This is base cost. Actual cost depends on replicas and usage.'
```

**UI Shows Real-Time Cost Estimate**:

```
┌──────────────────────────────────────────────────────────┐
│ Cost & Budget Configuration                              │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ Selected Size: Large                                      │
│                                                           │
│ 💰 Estimated Monthly Cost:                               │
│                                                           │
│   Base: $50.40/month (single replica)                    │
│   With HPA (2-10 replicas): $100 - $500/month            │
│   Prod environment (3-10 replicas): $150 - $500/month    │
│                                                           │
│ 📊 Cost Breakdown:                                        │
│   • CPU (500m): $28.80/month                             │
│   • Memory (1Gi): $16.56/month                           │
│   • Platform overhead: $5.04/month                        │
│                                                           │
│ Monthly Budget Limit:                                     │
│ [$1000_______________]                                    │
│                                                           │
│ ✅ Estimated cost ($100-$500) is within budget            │
│                                                           │
│ Cost Center:                                              │
│ [CC-12345 - Retail Banking ▼]                            │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 16. Cost Labels in Generated Manifests

### Automatic Label Injection

**In Generated kustomization.yaml**:

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml

commonLabels:
  # Functional labels
  app: payment-service
  env: prod
  region: euw1
  archetype: api
  
  # ================================================
  # COST LABELS (NEW)
  # ================================================
  cost.team: payments-team
  cost.service: payment-service
  cost.environment: prod
  cost.region: euw1
  cost.archetype: api
  cost.size: large
  cost.business-unit: retail-banking
  cost.cost-center: CC-12345
  cost.budget-monthly: "5000"
  cost.estimated-monthly: "200"

# ================================================
# COST ANNOTATIONS (NEW)
# ================================================
commonAnnotations:
  cost.optimization.enabled: "true"
  cost.alert.threshold: "0.8"
  cost.chargeback.rate: "1.2"
  cost.created-at: "2025-11-09T10:00:00Z"
  cost.created-by: "user@company.com"
```

**Why Labels?**
- ✅ Prometheus can aggregate by labels
- ✅ OpenCost uses labels for cost allocation
- ✅ Kubernetes API can filter by labels
- ✅ Enables multi-dimensional cost analysis

---

## 17. Cost Forecasting

### Predictive Cost Model

**ML-Based Forecasting**:

```python
# cost-forecasting/predictor.py

from prophet import Prophet  # Facebook's time-series forecasting
import pandas as pd

def forecast_service_cost(service_name: str, forecast_days: int = 30):
    """Forecast future costs using historical data"""
    
    # Get historical data (last 90 days)
    historical_costs = get_cost_history(service_name, days=90)
    
    # Prepare data for Prophet
    df = pd.DataFrame(historical_costs)
    df = df.rename(columns={'date': 'ds', 'cost': 'y'})
    
    # Train model
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,  # Weekly patterns (weekday vs weekend)
        daily_seasonality=True    # Daily patterns (business hours)
    )
    model.fit(df)
    
    # Make forecast
    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)
    
    # Extract predictions
    predicted_cost = forecast.tail(forecast_days)['yhat'].sum()
    lower_bound = forecast.tail(forecast_days)['yhat_lower'].sum()
    upper_bound = forecast.tail(forecast_days)['yhat_upper'].sum()
    
    return {
        "service": service_name,
        "forecastDays": forecast_days,
        "predictedCost": round(predicted_cost, 2),
        "lowerBound": round(lower_bound, 2),
        "upperBound": round(upper_bound, 2),
        "confidence": 0.85
    }
```

**Usage in Backstage**:

```
Service Page → Cost Tab → Forecast Section

Next 30 Days Forecast:
  Predicted: $250 (±$30)
  Current Trend: $243/month
  Budget Impact: 5% of monthly budget
  Status: ✅ Within budget
```

---

## 18. Integration Points

### Cost Data Flow

```
┌────────────────────────────────────────────────────────────┐
│ 1. Kubernetes Clusters                                     │
│    • Pods with cost labels                                 │
│    • Metrics exposed to Prometheus                         │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 2. OpenCost                                                │
│    • Scrapes Prometheus metrics                            │
│    • Calculates costs using cloud pricing API             │
│    • Aggregates by cost labels                             │
│    • Exposes cost API                                      │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Cost Aggregation Service                                │
│    • Polls OpenCost API every 15 min                       │
│    • Stores in TimescaleDB                                 │
│    • Calculates trends and forecasts                       │
│    • Detects anomalies                                     │
│    • Generates alerts                                      │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Cost API                                                │
│    • REST endpoints for cost queries                       │
│    • Used by Backstage plugin                              │
│    • Used by cost dashboard                                │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 5. Backstage Cost Plugin                                   │
│    • Displays costs on service pages                       │
│    • Shows recommendations                                 │
│    • Budget tracking                                       │
└────────────────────────────────────────────────────────────┘
```

---

## 19. Implementation Details

### OpenCost Configuration

**values.yaml**:

```yaml
opencost:
  # Prometheus configuration
  prometheus:
    external:
      enabled: true
      url: http://prometheus-server.monitoring:9090
  
  # Cloud provider pricing
  cloudProviderApiKey: ${GCP_API_KEY}
  
  # Cost model configuration
  customPricing:
    enabled: true
    costModel:
      CPU: 0.031611  # $/core/hour (GCP n1-standard)
      spotCPU: 0.01   # $/core/hour (spot instances)
      RAM: 0.004237  # $/GB/hour
      spotRAM: 0.001  # $/GB/hour
      storage: 0.00005  # $/GB/hour (standard PD)
      zonal_pd: 0.00005
      regional_pd: 0.0001
      network: 0.01  # $/GB egress
  
  # UI configuration
  ui:
    enabled: true
    ingress:
      enabled: true
      hosts:
        - opencost.company.com
  
  # Metrics export
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        prometheus: kube-prometheus
```

### Cost Aggregation Service Deployment

**Kubernetes Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-aggregator
  namespace: platform-services
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cost-aggregator
  template:
    metadata:
      labels:
        app: cost-aggregator
    spec:
      containers:
        - name: aggregator
          image: gcr.io/company/cost-aggregator:v1.0.0
          env:
            - name: OPENCOST_API_URL
              value: "http://opencost:9003"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cost-db-credentials
                  key: connection-string
            - name: POLL_INTERVAL_SECONDS
              value: "900"  # 15 minutes
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 200m
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: cost-api
  namespace: platform-services
spec:
  selector:
    app: cost-aggregator
  ports:
    - port: 8080
      targetPort: 8080
      name: http
```

---

## 20. Cost Governance Policies

### Budget Enforcement

**Policy 1: Budget Approval Required**

```rego
# policies/cost-budget.rego
package cost_governance

deny[msg] {
    input.service.cost.budgetMonthly > 10000
    not input.approvals.finance_approved
    msg := sprintf("Services with budget > $10K require finance approval. Budget: $%v", [input.service.cost.budgetMonthly])
}

deny[msg] {
    input.service.size == "xlarge"
    input.service.cost.budgetMonthly < 500
    msg := "X-Large services require minimum $500/month budget"
}
```

**Policy 2: Cost Center Required**

```rego
package cost_governance

deny[msg] {
    input.service.cost.costCenter == ""
    input.service.environments contains "prod"
    msg := "Production services must have a cost center assigned"
}
```

**Policy 3: Prevent Over-Provisioning**

```rego
package cost_governance

warn[msg] {
    input.service.size == "xlarge"
    input.service.archetype == "job"
    msg := "Warning: Jobs typically don't need xlarge size. Consider large or medium."
}

deny[msg] {
    count(input.service.environments) == 1
    input.service.environments[0] == "int"
    input.service.size == "xlarge"
    msg := "Int-only services cannot use xlarge size"
}
```

---

## 21. Benefits of Integrated Cost Management

### Visibility

| Before | After |
|--------|-------|
| ❌ No idea what services cost | ✅ Real-time cost per service |
| ❌ Quarterly cloud bills (surprise!) | ✅ Daily cost tracking |
| ❌ Can't attribute costs to teams | ✅ Full chargeback capability |
| ❌ No way to optimize | ✅ AI-powered recommendations |

### Optimization

| Capability | Impact | Annual Savings |
|------------|--------|----------------|
| **Right-Sizing** | 20-30% cost reduction | $200K-$300K |
| **HPA Optimization** | 15-20% savings | $150K-$200K |
| **Spot Instances** | 40-60% for dev/test | $100K-$150K |
| **Storage Optimization** | 10-15% savings | $50K-$75K |

**Total Potential**: $500K-$725K annual savings

### Accountability

- Teams see their costs → Incentive to optimize
- Budget limits prevent runaway costs
- Chargeback enables cost attribution
- Finance has visibility into infrastructure spend

---

## 22. Roadmap Integration

### Phase 1: Foundation (Weeks 1-4)
- [ ] Deploy OpenCost to all clusters
- [ ] Setup Cost Aggregation Service
- [ ] Create TimescaleDB instance
- [ ] Build Cost API endpoints

### Phase 2: Backstage Integration (Weeks 5-8)
- [ ] Develop Backstage Cost Plugin
- [ ] Add cost widget to service pages
- [ ] Integrate with team dashboard
- [ ] Test with pilot services

### Phase 3: Optimization (Weeks 9-12)
- [ ] Build recommendation engine
- [ ] Implement anomaly detection
- [ ] Create forecasting models
- [ ] Enable auto-optimization (opt-in)

### Phase 4: Governance (Weeks 13-16)
- [ ] Budget enforcement policies
- [ ] Chargeback reporting
- [ ] Executive dashboards
- [ ] Integration with finance systems

---

## Summary

### Cost Management as Competitive Advantage

**The Vision**:
> _"Every developer knows exactly how much their service costs, gets intelligent recommendations to optimize, and has full accountability within team budgets."_

**The Impact**:
- 💰 **$500K-$700K annual savings** from optimization
- 📊 **100% cost visibility** (no surprises)
- 🎯 **Budget accountability** (teams own costs)
- 🤖 **AI-powered optimization** (continuous improvement)
- 🏆 **FinOps maturity** (industry best practices)

**Integration Points**:
```
Catalog (budgets) → Kustomize (labels) → K8s (metrics) → OpenCost (calculation)
  → Cost API → Backstage (visibility) → Teams (alerts) → Optimization
```

**This transforms Platform-Next from a deployment platform to a complete Platform Product with built-in cost intelligence!** 💡
