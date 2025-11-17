# Example: Payment Processor Service with Custom Metrics

This example shows how a service uses the unified monitoring approach with profiles and custom metrics.

## Service Definition

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
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice.johnson@company.com"
    
    # ================================================
    # MONITORING CONFIGURATION
    # ================================================
    monitoringProfile: api-observability  # Base profile
    
    monitoring:
      # Enable monitoring tools
      prometheus: true
      dynatrace: true
      
      # Custom metrics from metrics-catalog repository
      customMetrics:
        repository:
          url: https://github.com/company/metrics-catalog
          ref: v1.2.0
        
        # Service-specific custom metrics profiles
        profiles:
          - payment-business-metrics  # Business metrics profile
          - payment-fraud-metrics      # Fraud detection metrics
        
        # Inline custom metrics (can also be in metrics-catalog)
        metrics:
          - name: payment_transactions_total
            type: counter
            description: "Total payment transactions processed"
            dynatrace:
              enabled: true
              unit: "count"
              aggregation: "sum"
              dimensions: ["status", "payment_method", "environment"]
          
          - name: payment_success_rate
            type: gauge
            description: "Payment success rate percentage"
            dynatrace:
              enabled: true
              unit: "percent"
              aggregation: "avg"
              dimensions: ["payment_method", "environment"]
      
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
```

## Generated Kustomization

**File**: `generated/payment-processor/prod/euw1/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  # Platform-next base resources
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/prod
  - ../../../../kustomize/regions/euw1
  - ./namespace.yaml

  # Monitoring profile resources
  - ../../../../kustomize/monitoring/profiles/api-observability
  
  # Custom metrics from metrics-catalog (Git URL)
  - https://github.com/company/metrics-catalog/profiles/payment-business-metrics?ref=v1.2.0
  - https://github.com/company/metrics-catalog/profiles/payment-fraud-metrics?ref=v1.2.0
  - https://github.com/company/metrics-catalog/services/payment-processor?ref=v1.2.0

components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa
  - ../../../../kustomize/components/pdb

namespace: prod-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: prod
  region: euw1
  cost.service: payment-processor
  cost.costCenter: CC-12345
  cost.budget: "6000"
  monitoring.profile: api-observability
  monitoring.tool: dynatrace
  monitoring.primary: "true"

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

# Patches to customize monitoring resources
patches:
  # Replace service name in ServiceMonitor
  - target:
      kind: ServiceMonitor
    patch: |-
      - op: replace
        path: /spec/selector/matchLabels/app
        value: payment-processor
      - op: replace
        path: /metadata/name
        value: payment-processor-monitor
  
  # Replace service name in PrometheusRule
  - target:
      kind: PrometheusRule
    patch: |-
      - op: replace
        path: /metadata/name
        value: payment-processor-prometheus-rules
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          sum(rate(http_requests_total{service="payment-processor"}[5m]))
          by (method, status)
  
  # Replace variables in Dynatrace ConfigMap
  - target:
      kind: ConfigMap
      name: dynatrace-app-base
    patch: |-
      - op: replace
        path: /metadata/name
        value: payment-processor-dynatrace-config
      - op: replace
        path: /data/application.json
        value: |
          {
            "metadata": {
              "name": "payment-processor",
              "environment": "prod",
              "team": "payments-team",
              "costCenter": "CC-12345"
            },
            "monitoring": {
              "technologies": ["java", "http", "databases", "kubernetes"],
              "requestAttributes": [...]
            },
            "customMetrics": [
              {
                "name": "payment_transactions_total",
                "type": "counter",
                "description": "Total payment transactions processed",
                "unit": "count",
                "aggregation": "sum",
                "dimensions": ["status", "payment_method", "environment"]
              },
              {
                "name": "payment_success_rate",
                "type": "gauge",
                "description": "Payment success rate percentage",
                "unit": "percent",
                "aggregation": "avg",
                "dimensions": ["payment_method", "environment"]
              }
            ],
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
                "name": "PaymentSuccessRateLow",
                "enabled": true,
                "condition": "payment_success_rate < 95.0",
                "targets": ["SERVICE"],
                "severity": "critical",
                "notificationChannels": ["teams-payment-processor", "pagerduty-oncall"]
              }
            ]
          }
```

## Generated Dynatrace ConfigMap

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
    cost.costCenter: CC-12345
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "prod",
        "team": "payments-team",
        "costCenter": "CC-12345"
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
          "notificationChannels": ["teams-payment-processor", "pagerduty-oncall"]
        },
        {
          "name": "PaymentSuccessRateLow",
          "enabled": true,
          "condition": "payment_success_rate < 95.0",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payment-processor", "pagerduty-oncall"]
        },
        {
          "name": "FraudCheckLatencyHigh",
          "enabled": true,
          "condition": "fraud_check_latency > 500",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
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
          "dimensions": ["status", "payment_method", "environment"]
        },
        {
          "name": "payment_success_rate",
          "type": "gauge",
          "description": "Payment success rate percentage",
          "unit": "percent",
          "aggregation": "avg",
          "dimensions": ["payment_method", "environment"]
        },
        {
          "name": "fraud_check_latency",
          "type": "histogram",
          "description": "Fraud check latency in milliseconds",
          "unit": "milliseconds",
          "aggregation": "p95",
          "dimensions": ["environment"]
        },
        {
          "name": "chargeback_count",
          "type": "counter",
          "description": "Total chargebacks",
          "unit": "count",
          "aggregation": "sum",
          "dimensions": ["reason", "environment"]
        }
      ]
    }
```

## How It Works

1. **Base Profile** (`api-observability`) provides:
   - Dynatrace application structure
   - Standard request attributes
   - Standard alert rules (ErrorRateAnomaly, HighLatencyAnomaly, etc.)
   - Prometheus ServiceMonitor and PrometheusRule

2. **Custom Metrics** (from metrics-catalog) add:
   - Business metrics (payment_transactions_total, payment_success_rate)
   - Custom alert rules (PaymentSuccessRateLow, FraudCheckLatencyHigh)
   - Additional dimensions for analysis

3. **Merged Result**:
   - All base monitoring (from profile)
   - All custom metrics (from catalog)
   - All alert rules (base + custom)
   - Service-specific configuration

4. **Deployment**:
   - Dynatrace ConfigMap → Dynatrace Sync Controller → Dynatrace SaaS
   - ServiceMonitor → Prometheus Operator → Prometheus
   - PrometheusRule → Prometheus → AlertManager

## Benefits

- ✅ **Standard observability** from profiles
- ✅ **Custom business metrics** from metrics-catalog
- ✅ **Dynatrace primary** - Full APM and custom metrics
- ✅ **Prometheus secondary** - Metrics collection
- ✅ **Composable** - Mix and match profiles + custom metrics
- ✅ **Maintainable** - Profiles in platform-next, custom metrics in catalog

