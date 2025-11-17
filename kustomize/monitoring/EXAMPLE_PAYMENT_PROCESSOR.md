# Example: Payment Processor Service with Dynatrace Monitoring

**Service**: `payment-processor`  
**Business Unit**: `core-banking`  
**Owner**: `sre@company.com`  
**Cost Center**: `CORE-B`  
**Monitoring Profile**: `api-observability`  
**Custom Metrics**: `payment-business-metrics` (from metrics-catalog)

---

## 1. Service Catalog Entry

**File**: `kustomize/catalog/services.yaml`

```yaml
services:
  - name: payment-processor
    archetype: api
    size: large
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # Cost configuration
    costProfile: standard-api-cost
    cost:
      costCenter: "CORE-B"
      businessUnit: "core-banking"
      costOwner: "sre@company.com"
    
    # Monitoring configuration
    monitoringProfile: api-observability  # Base profile from platform-next
    
    monitoring:
      # Enable Dynatrace (primary and only monitoring tool)
      dynatrace: true
      
      # Custom metrics from metrics-catalog repository
      customMetrics:
        repository:
          url: https://github.com/company/metrics-catalog
          ref: v1.2.0  # Pin to specific version
        
        # Service-specific custom metrics profiles
        profiles:
          - payment-business-metrics  # Business metrics profile
          - payment-fraud-metrics      # Fraud detection metrics
      
      # Environment-specific overrides
      overrides:
        prod:
          sloAvailability: 99.99
          sloLatencyP95ms: 200
          sloErrorRate: 0.05
          
          # Additional Dynatrace alert rules for prod
          dynatrace:
            alertRules:
              - name: "PaymentSuccessRateLow"
                enabled: true
                condition: "payment_success_rate < 95.0"
                targets: ["SERVICE"]
                severity: critical
                channels:
                  teams: ["#team-payment-processor"]
                  pagerduty: true
                  email: ["sre@company.com"]
```

---

## 2. Base Monitoring Profile

**File**: `kustomize/catalog/monitoring-profiles.yaml`

```yaml
monitoringProfiles:
  api-observability:
    description: "REST API monitoring with Dynatrace OneAgent"
    
    dynatrace:
      enabled: true
      primary: true
      
      application:
        monitoredTechnologies:
          - java
          - http
          - databases
          - kubernetes
        
        requestNaming: "{RequestPath} [{RequestMethod}]"
        
        requestAttributes:
          - name: "service"
            source:
              kubernetesLabel: "app"
          - name: "team"
            source:
              kubernetesLabel: "cost.team"
          - name: "environment"
            source:
              kubernetesLabel: "cost.environment"
          - name: "costCenter"
            source:
              kubernetesLabel: "cost.costCenter"
          - name: "businessUnit"
            source:
              kubernetesLabel: "cost.businessUnit"
          - name: "region"
            source:
              kubernetesLabel: "cost.region"
      
      alertRules:
        - name: "ErrorRateAnomaly"
          enabled: true
          condition: "Anomaly(ErrorRate)"
          targets: ["SERVICE"]
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
        
        - name: "HighLatencyAnomaly"
          enabled: true
          condition: "Anomaly(ResponseTime)"
          targets: ["SERVICE"]
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
        
        - name: "ServiceCrash"
          enabled: true
          condition: "CrashDetection"
          targets: ["SERVICE"]
          severity: critical
          channels:
            teams: ["#team-{SERVICE}", "#platform-sre"]
            pagerduty: true
            email: ["sre@company.com"]
    
    slos:
      availability:
        baselineInt: 99.0
        baselinePre: 99.5
        baselineProd: 99.9
      
      latency:
        p95Baseline: 500
        p99Baseline: 1000
      
      errorRate:
        baselineInt: 5.0
        baselinePre: 1.0
        baselineProd: 0.1
```

---

## 3. Custom Metrics in Metrics Catalog

**File**: `metrics-catalog/services/payment-processor/payment-business-metrics.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-business-metrics
  labels:
    metrics.type: business
    metrics.service: payment-processor
    metrics.owner: observability-team
data:
  dynatrace-custom-metrics.json: |
    {
      "customMetrics": [
        {
          "name": "payment_transactions_total",
          "type": "counter",
          "description": "Total payment transactions processed",
          "unit": "count",
          "aggregation": "sum",
          "dimensions": ["status", "payment_method", "environment"],
          "source": "application"
        },
        {
          "name": "payment_success_rate",
          "type": "gauge",
          "description": "Payment success rate percentage",
          "unit": "percent",
          "aggregation": "avg",
          "dimensions": ["payment_method", "environment"],
          "source": "application"
        },
        {
          "name": "fraud_check_latency",
          "type": "histogram",
          "description": "Fraud check latency in milliseconds",
          "unit": "milliseconds",
          "aggregation": "p95",
          "dimensions": ["environment"],
          "source": "application"
        },
        {
          "name": "chargeback_count",
          "type": "counter",
          "description": "Total chargebacks",
          "unit": "count",
          "aggregation": "sum",
          "dimensions": ["reason", "environment"],
          "source": "application"
        },
        {
          "name": "payment_amount_total",
          "type": "counter",
          "description": "Total payment amount processed",
          "unit": "currency",
          "aggregation": "sum",
          "dimensions": ["currency", "environment"],
          "source": "application"
        }
      ],
      "alertRules": [
        {
          "name": "PaymentSuccessRateLow",
          "enabled": true,
          "condition": "payment_success_rate < 95.0",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": {
            "teams": ["#team-payment-processor"],
            "pagerduty": true,
            "email": ["sre@company.com"]
          },
          "description": "Payment success rate dropped below 95%"
        },
        {
          "name": "FraudCheckLatencyHigh",
          "enabled": true,
          "condition": "fraud_check_latency > 500",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": {
            "teams": ["#team-payment-processor"],
            "email": ["sre@company.com"]
          },
          "description": "Fraud check latency exceeds 500ms"
        },
        {
          "name": "ChargebackRateHigh",
          "enabled": true,
          "condition": "chargeback_count / payment_transactions_total > 0.01",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": {
            "teams": ["#team-payment-processor"],
            "email": ["sre@company.com"]
          },
          "description": "Chargeback rate exceeds 1%"
        }
      ],
      "dashboards": [
        {
          "name": "payment-processor-business-metrics",
          "description": "Business metrics dashboard for payment-processor",
          "panels": [
            {
              "title": "Payment Transactions",
              "metric": "payment_transactions_total",
              "type": "line"
            },
            {
              "title": "Success Rate",
              "metric": "payment_success_rate",
              "type": "gauge"
            },
            {
              "title": "Fraud Check Latency",
              "metric": "fraud_check_latency",
              "type": "histogram"
            }
          ]
        }
      ]
    }
```

---

## 4. Generated Dynatrace ConfigMap

**File**: `generated/payment-processor/prod/euw1/monitoring/dynatrace-app-config.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-processor-dynatrace-config
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
    monitoring.profile: api-observability
    monitoring.tool: dynatrace
    monitoring.primary: "true"
    cost.service: payment-processor
    cost.costCenter: CORE-B
    cost.businessUnit: core-banking
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "prod",
        "team": "sre@company.com",
        "costCenter": "CORE-B",
        "businessUnit": "core-banking"
      },
      "monitoring": {
        "technologies": ["java", "http", "databases", "kubernetes"],
        "requestNaming": "{RequestPath} [{RequestMethod}]",
        "requestAttributes": [
          {
            "name": "service",
            "source": {
              "kubernetesLabel": "app"
            }
          },
          {
            "name": "team",
            "source": {
              "kubernetesLabel": "cost.team"
            }
          },
          {
            "name": "environment",
            "source": {
              "kubernetesLabel": "cost.environment"
            }
          },
          {
            "name": "costCenter",
            "source": {
              "kubernetesLabel": "cost.costCenter"
            }
          },
          {
            "name": "businessUnit",
            "source": {
              "kubernetesLabel": "cost.businessUnit"
            }
          },
          {
            "name": "region",
            "source": {
              "kubernetesLabel": "cost.region"
            }
          }
        ]
      },
      "alertRules": [
        {
          "name": "ErrorRateAnomaly",
          "enabled": true,
          "condition": "Anomaly(ErrorRate)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
        },
        {
          "name": "HighLatencyAnomaly",
          "enabled": true,
          "condition": "Anomaly(ResponseTime)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
        },
        {
          "name": "ServiceCrash",
          "enabled": true,
          "condition": "CrashDetection",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payment-processor", "pagerduty-oncall", "sre@company.com"]
        },
        {
          "name": "PaymentSuccessRateLow",
          "enabled": true,
          "condition": "payment_success_rate < 95.0",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payment-processor", "pagerduty-oncall", "sre@company.com"],
          "description": "Payment success rate dropped below 95%"
        },
        {
          "name": "FraudCheckLatencyHigh",
          "enabled": true,
          "condition": "fraud_check_latency > 500",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor", "sre@company.com"],
          "description": "Fraud check latency exceeds 500ms"
        },
        {
          "name": "ChargebackRateHigh",
          "enabled": true,
          "condition": "chargeback_count / payment_transactions_total > 0.01",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor", "sre@company.com"],
          "description": "Chargeback rate exceeds 1%"
        }
      ],
      "customMetrics": [
        {
          "name": "http_requests_total",
          "type": "counter",
          "description": "Total HTTP requests",
          "unit": "count"
        },
        {
          "name": "http_request_duration_seconds",
          "type": "histogram",
          "description": "HTTP request duration",
          "unit": "seconds"
        },
        {
          "name": "http_errors_total",
          "type": "counter",
          "description": "Total HTTP errors",
          "unit": "count"
        },
        {
          "name": "payment_transactions_total",
          "type": "counter",
          "description": "Total payment transactions processed",
          "unit": "count",
          "aggregation": "sum",
          "dimensions": ["status", "payment_method", "environment"],
          "source": "application"
        },
        {
          "name": "payment_success_rate",
          "type": "gauge",
          "description": "Payment success rate percentage",
          "unit": "percent",
          "aggregation": "avg",
          "dimensions": ["payment_method", "environment"],
          "source": "application"
        },
        {
          "name": "fraud_check_latency",
          "type": "histogram",
          "description": "Fraud check latency in milliseconds",
          "unit": "milliseconds",
          "aggregation": "p95",
          "dimensions": ["environment"],
          "source": "application"
        },
        {
          "name": "chargeback_count",
          "type": "counter",
          "description": "Total chargebacks",
          "unit": "count",
          "aggregation": "sum",
          "dimensions": ["reason", "environment"],
          "source": "application"
        },
        {
          "name": "payment_amount_total",
          "type": "counter",
          "description": "Total payment amount processed",
          "unit": "currency",
          "aggregation": "sum",
          "dimensions": ["currency", "environment"],
          "source": "application"
        }
      ]
    }
```

---

## 5. Generated Kustomization

**File**: `generated/payment-processor/prod/euw1/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/prod
  - ../../../../kustomize/regions/euw1
  - ./namespace.yaml
  - ./monitoring/dynatrace-app-config.yaml

components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa
  - ../../../../kustomize/components/circuit-breaker

namespace: prod-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: prod
  region: euw1
  archetype: api
  size: large
  cost.service: payment-processor
  cost.costCenter: CORE-B
  cost.businessUnit: core-banking
  cost.team: sre@company.com
  cost.environment: prod
  cost.region: euw1
  monitoring.profile: api-observability
  monitoring.tool: dynatrace
  monitoring.primary: "true"

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG  # Replaced by Harness

patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "2000m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "4Gi"
  
  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 3
      - op: replace
        path: /spec/maxReplicas
        value: 10
```

---

## 6. Deployment Flow

### Step 1: Developer Onboards Service
- Fills Backstage form with:
  - Service name: `payment-processor`
  - Monitoring profile: `api-observability`
  - Custom metrics: `payment-business-metrics`
  - Business unit: `core-banking`
  - Cost center: `CORE-B`
  - Owner: `sre@company.com`

### Step 2: Catalog Entry Created
- PR created in `platform-next` repo
- `services.yaml` updated with service definition
- References `metrics-catalog` repo for custom metrics

### Step 3: CI/CD Profile Expansion
- Loads base profile: `api-observability`
- Fetches custom metrics from `metrics-catalog` v1.2.0
- Merges base + custom metrics
- Substitutes variables:
  - `{SERVICE}` → `payment-processor`
  - `{ENVIRONMENT}` → `prod`
  - `{COST_CENTER}` → `CORE-B`
  - `{BUSINESS_UNIT}` → `core-banking`
  - `{TEAM}` → `sre@company.com`

### Step 4: Manifest Generation
- Generates unified Dynatrace ConfigMap
- Includes in `kustomization.yaml`
- Commits to `generated/` directory

### Step 5: Deployment
- Harness fetches manifests from Git
- Deploys to Kubernetes cluster
- ConfigMap created in namespace: `prod-payment-processor-euw1-stable`
- Pod deployed with cost labels

### Step 6: Dynatrace Sync
- Dynatrace Sync Controller detects ConfigMap
- Syncs to Dynatrace SaaS:
  - Application definition created
  - Alert rules configured
  - Custom metrics registered

### Step 7: Runtime Monitoring
- Dynatrace OneAgent (DaemonSet) auto-instruments Java app
- Collects standard metrics (HTTP, DB, errors, latency)
- Collects custom metrics (payment_transactions_total, etc.)
- Sends to Dynatrace SaaS
- Alerts fire based on rules

---

## 7. Observability Team Adds New Metric (Later)

### Scenario: Add revenue metric

**Step 1**: Create new metric in `metrics-catalog`

```yaml
# metrics-catalog/services/payment-processor/payment-revenue-metrics.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-revenue-metrics
data:
  dynatrace-custom-metrics.json: |
    {
      "customMetrics": [
        {
          "name": "revenue_total",
          "type": "counter",
          "description": "Total revenue processed",
          "unit": "currency",
          "aggregation": "sum",
          "dimensions": ["currency", "environment"]
        }
      ]
    }
```

**Step 2**: Commit and tag

```bash
cd metrics-catalog
git add services/payment-processor/payment-revenue-metrics.yaml
git commit -m "feat: Add revenue metrics for payment-processor"
git tag v1.3.0
git push origin main --tags
```

**Step 3**: Update service definition (optional)

```yaml
# catalog/services.yaml
services:
  - name: payment-processor
    monitoring:
      customMetrics:
        repository:
          ref: v1.3.0  # Update version
        profiles:
          - payment-business-metrics
          - payment-revenue-metrics  # NEW
```

**Step 4**: CI/CD regenerates manifests
- Fetches `metrics-catalog` v1.3.0
- Merges new revenue metric
- Regenerates Dynatrace ConfigMap

**Step 5**: Deploy
- Harness deploys updated ConfigMap
- Dynatrace Sync Controller syncs
- New metric available in Dynatrace

**Key Point**: Observability team can add metrics **without touching platform-next** (if using existing profile) or with minimal change (updating ref version).

---

## 8. Summary

✅ **Base Profile** (`api-observability`) provides:
- Standard Dynatrace application structure
- Standard alert rules (ErrorRateAnomaly, HighLatencyAnomaly, ServiceCrash)
- Standard request attributes (service, team, costCenter, businessUnit, region)

✅ **Custom Metrics** (`payment-business-metrics`) adds:
- Business-specific metrics (payment_transactions_total, payment_success_rate, etc.)
- Business-specific alert rules (PaymentSuccessRateLow, FraudCheckLatencyHigh, etc.)
- Custom dashboards

✅ **Merged Result**:
- Single Dynatrace ConfigMap with base + custom
- All alert rules active
- All custom metrics registered
- Business context (CORE-B, core-banking, sre@company.com) included

✅ **Observability Team**:
- Can add metrics independently
- Versioned separately
- No need to touch platform-next (if using existing profile)

✅ **Pure Dynatrace Solution**:
- No Prometheus/Grafana required
- Dynatrace OneAgent handles all instrumentation
- All monitoring in one place

