# Metrics as Code with Profiles: Unified Design

**Status**: COMPREHENSIVE DESIGN - Combining Metrics as Code with Monitoring Profiles

**Document Type**: Architecture + Implementation Guide

**Audience**: Platform engineers, SRE teams, observability teams

**Date**: 2025-11-16

---

## Executive Summary

This document explains the differences between **Custom Metrics as Code** (Doc 05) and **Monitoring Metrics Profiles** (Doc 08), and shows how to **unify them** into a single, powerful system that leverages both approaches.

**Key Insight**: 
- **Profiles** = Base templates (standard observability patterns)
- **Custom Metrics** = Composable additions (service-specific metrics)
- **Together** = Flexible, reusable, maintainable monitoring system

**Focus**: Dynatrace as the primary monitoring tool, with Prometheus for metrics collection.

---

## 1. Understanding the Two Approaches

### 1.1 Document 05: Custom Metrics as Code

**Philosophy**: Separate repository for metrics definitions

**Key Characteristics**:
- ✅ Metrics defined in separate `metrics-catalog` repository
- ✅ Referenced via Git URLs or OCI registry
- ✅ Versioned independently from platform-next
- ✅ Owned by observability team
- ✅ Highly composable (mix and match)
- ✅ Focus on Prometheus (ServiceMonitor, PrometheusRule)

**Structure**:
```
metrics-catalog/
├── profiles/
│   ├── golden-signals/
│   ├── business-metrics/
│   └── sre-sli/
├── archetypes/
│   ├── api/
│   └── listener/
└── services/
    ├── payment-service/
    └── account-service/
```

**Use Case**: When you want to:
- Decouple metrics from platform config
- Version metrics independently
- Share metrics across multiple platforms
- Have observability team own metrics lifecycle

---

### 1.2 Document 08: Monitoring Metrics Profiles

**Philosophy**: Integrated profiles within platform-next

**Key Characteristics**:
- ✅ Profiles defined in `monitoring-profiles.yaml` (in platform-next)
- ✅ Integrated with service catalog
- ✅ Template-based with variable substitution
- ✅ Supports both Prometheus and Dynatrace
- ✅ Size-aware (scales thresholds by service size)
- ✅ Environment-specific overrides

**Structure**:
```
platform-next/
├── kustomize/
│   ├── catalog/
│   │   └── services.yaml (references monitoringProfile)
│   └── monitoring-profiles.yaml (profile definitions)
└── generated/
    └── {service}/{env}/{region}/
        └── monitoring/
            ├── service-monitor.yaml
            ├── prometheus-rules.yaml
            └── dynatrace-app-config.yaml
```

**Use Case**: When you want to:
- Keep everything in one repository
- Tight integration with service catalog
- Automatic threshold scaling
- Profile-based standardization

---

## 2. The Unified Approach

### 2.1 Best of Both Worlds

**Combined Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│ Service Definition (services.yaml)                          │
├─────────────────────────────────────────────────────────────┤
│ monitoringProfile: api-observability  # Base profile        │
│ monitoring:                                                  │
│   customMetrics:                                            │
│     - payment-transactions                                  │
│     - fraud-check-latency                                   │
│   metricsRepository:                                        │
│     url: https://github.com/company/metrics-catalog        │
│     ref: v1.2.0                                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Profile Expansion Engine                                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Load base profile (from monitoring-profiles.yaml)        │
│ 2. Load custom metrics (from metrics-catalog repo)          │
│ 3. Merge: Base + Custom                                     │
│ 4. Substitute variables: {SERVICE}, {TEAM}, etc.           │
│ 5. Scale thresholds by size                                 │
│ 6. Apply environment overrides                               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Generated Monitoring Resources                              │
├─────────────────────────────────────────────────────────────┤
│ • ServiceMonitor (Prometheus)                               │
│ • PrometheusRule (recording + alerts)                       │
│ • Dynatrace ConfigMap (app definition + custom metrics)      │
│ • Grafana Dashboard ConfigMap                               │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 How They Work Together

**Base Profile** (from `monitoring-profiles.yaml`):
- Provides standard observability patterns
- Defines Dynatrace application structure
- Sets up Prometheus scraping
- Configures standard alert rules
- Defines SLO baselines

**Custom Metrics** (from `metrics-catalog`):
- Adds service-specific business metrics
- Extends Dynatrace custom metrics
- Adds custom Prometheus recording rules
- Provides service-specific dashboards

**Result**: 
- Standard observability (from profile) + Custom business metrics (from catalog)
- All merged and deployed together

---

## 3. Kustomize Folder Structure

### 3.1 Complete Structure

```
platform-next/
├── kustomize/
│   ├── catalog/
│   │   ├── services.yaml                    # Service definitions
│   │   └── monitoring-profiles.yaml         # Base monitoring profiles
│   │
│   ├── monitoring/                          # NEW: Monitoring components
│   │   ├── profiles/                        # Profile-based resources
│   │   │   ├── api-observability/
│   │   │   │   ├── service-monitor-base.yaml
│   │   │   │   ├── prometheus-rules-base.yaml
│   │   │   │   ├── dynatrace-app-base.yaml
│   │   │   │   └── kustomization.yaml
│   │   │   │
│   │   │   ├── batch-job-observability/
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── listener-observability/
│   │   │       └── ...
│   │   │
│   │   ├── custom-metrics/                  # Custom metrics integration
│   │   │   ├── payment-service/
│   │   │   │   ├── payment-metrics.yaml      # Custom business metrics
│   │   │   │   ├── dynatrace-custom.yaml    # Dynatrace custom metrics
│   │   │   │   └── kustomization.yaml
│   │   │   │
│   │   │   └── account-service/
│   │   │       └── ...
│   │   │
│   │   └── dynatrace/                       # Dynatrace-specific resources
│   │       ├── request-attributes-base.yaml  # Standard request attributes
│   │       ├── alert-rules-base.yaml        # Standard alert rules
│   │       └── custom-metrics-template.yaml # Custom metrics template
│   │
│   └── components/                          # Existing components
│       ├── ingress/
│       ├── hpa/
│       └── ...
│
└── generated/
    └── {service}/{env}/{region}/
        └── monitoring/
            ├── service-monitor.yaml         # Merged: base + custom
            ├── prometheus-rules.yaml        # Merged: base + custom
            └── dynatrace-app-config.yaml    # Merged: base + custom
```

---

## 4. Implementation Examples

### 4.1 Base Profile Definition

**File**: `kustomize/catalog/monitoring-profiles.yaml`

```yaml
monitoringProfiles:
  api-observability:
    description: "REST API monitoring with Dynatrace as primary"
    
    # ================================================
    # DYNATRACE CONFIGURATION (PRIMARY)
    # ================================================
    dynatrace:
      enabled: true
      primary: true  # Dynatrace is primary monitoring tool
      
      application:
        monitoredTechnologies:
          - java
          - http
          - databases
          - kubernetes
        
        requestNaming: "{RequestPath} [{RequestMethod}]"
        
        # Standard request attributes (from K8s labels)
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
          - name: "region"
            source:
              kubernetesLabel: "cost.region"
        
        # Standard custom metrics (can be extended)
        customMetrics:
          - name: "http_requests_total"
            type: "counter"
            description: "Total HTTP requests"
            unit: "count"
          - name: "http_request_duration_seconds"
            type: "histogram"
            description: "HTTP request duration"
            unit: "seconds"
          - name: "http_errors_total"
            type: "counter"
            description: "Total HTTP errors"
            unit: "count"
      
      # Standard alert rules
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
        
        - name: "DatabaseSlowQueries"
          enabled: true
          condition: "SlowDatabaseQueries(200ms)"
          targets: ["DATABASE"]
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
    
    # ================================================
    # PROMETHEUS CONFIGURATION (SECONDARY)
    # ================================================
    prometheus:
      enabled: true
      primary: false  # Prometheus is secondary (for metrics collection)
      
      serviceMonitor:
        scrapeInterval: 30s
        path: /metrics
        port: http
      
      recordingRules:
        - name: "http:requests:rate5m"
          expr: |
            sum(rate(http_requests_total{service="{SERVICE}"}[5m]))
            by (method, status)
        
        - name: "http:errors:rate5m"
          expr: |
            sum(rate(http_errors_total{service="{SERVICE}"}[5m]))
        
        - name: "http:latency:p95"
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="{SERVICE}"}[5m]))
              by (le)
            )
      
      alertRules:
        - name: "HighErrorRate"
          expr: "http:errors:rate5m{service=\"{SERVICE}\"} > {ERROR_RATE_THRESHOLD}"
          for: 5m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
        
        - name: "HighLatency"
          expr: "http:latency:p95{service=\"{SERVICE}\"} > {LATENCY_P95_THRESHOLD}"
          for: 5m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
    
    # ================================================
    # SLO DEFINITIONS
    # ================================================
    slos:
      availability:
        baselineInt: 99.0
        baselinePre: 99.5
        baselineProd: 99.9
      
      latency:
        p95Baseline: 500  # milliseconds
        p99Baseline: 1000
      
      errorRate:
        baselineInt: 5.0
        baselinePre: 1.0
        baselineProd: 0.1
    
    # ================================================
    # ENVIRONMENT OVERRIDES
    # ================================================
    environmentOverrides:
      prod:
        slos:
          availability: 99.99
          latency:
            p95Baseline: 200
          errorRate: 0.05
        
        alertRules:
          - name: "HighErrorRate"
            expr: "http:errors:rate5m{service=\"{SERVICE}\"} > 0.0005"
```

---

### 4.2 Service Definition with Custom Metrics

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
        
        # Service-specific custom metrics
        profiles:
          - payment-business-metrics  # Business metrics profile
          - payment-fraud-metrics      # Fraud detection metrics
        
        # Service-specific custom metrics (direct)
        metrics:
          - name: payment_transactions_total
            type: counter
            description: "Total payment transactions processed"
            dynatrace:
              enabled: true
              unit: "count"
              aggregation: "sum"
          
          - name: payment_success_rate
            type: gauge
            description: "Payment success rate percentage"
            dynatrace:
              enabled: true
              unit: "percent"
              aggregation: "avg"
          
          - name: fraud_check_latency
            type: histogram
            description: "Fraud check latency in milliseconds"
            dynatrace:
              enabled: true
              unit: "milliseconds"
              aggregation: "p95"
      
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

---

### 4.3 Custom Metrics from Metrics Catalog

**File**: `metrics-catalog/services/payment-processor/payment-business-metrics.yaml`

```yaml
# Custom business metrics for payment-processor service
# This file is in the metrics-catalog repository

apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-business-metrics
  labels:
    metrics.type: business
    metrics.service: payment-processor
data:
  # Prometheus recording rules for business metrics
  prometheus-rules.yaml: |
    apiVersion: monitoring.coreos.com/v1
    kind: PrometheusRule
    metadata:
      name: payment-business-metrics
    spec:
      groups:
        - name: payment_business_metrics
          interval: 30s
          rules:
            - record: payment:transactions:rate5m
              expr: |
                sum(rate(payment_transactions_total{service="payment-processor"}[5m]))
                by (status, payment_method)
            
            - record: payment:success_rate:5m
              expr: |
                sum(rate(payment_transactions_total{service="payment-processor",status="success"}[5m]))
                /
                sum(rate(payment_transactions_total{service="payment-processor"}[5m]))
            
            - record: payment:fraud_check_latency:p95
              expr: |
                histogram_quantile(0.95,
                  sum(rate(fraud_check_latency_bucket{service="payment-processor"}[5m]))
                  by (le)
                )
  
  # Dynatrace custom metrics definition
  dynatrace-custom-metrics.json: |
    {
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
      ],
      "alertRules": [
        {
          "name": "PaymentSuccessRateLow",
          "enabled": true,
          "condition": "payment_success_rate < 95.0",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payment-processor", "pagerduty"]
        },
        {
          "name": "FraudCheckLatencyHigh",
          "enabled": true,
          "condition": "fraud_check_latency > 500",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
        },
        {
          "name": "ChargebackRateHigh",
          "enabled": true,
          "condition": "chargeback_count / payment_transactions_total > 0.01",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor"]
        }
      ]
    }
```

---

### 4.4 Profile Component in Kustomize

**File**: `kustomize/monitoring/profiles/api-observability/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Base resources for API observability profile
resources:
  - service-monitor-base.yaml
  - prometheus-rules-base.yaml
  - dynatrace-app-base.yaml

# Common labels
commonLabels:
  monitoring.profile: api-observability
  monitoring.tool: dynatrace

# Namespace (will be overridden by service-specific kustomization)
namespace: default
```

**File**: `kustomize/monitoring/profiles/api-observability/dynatrace-app-base.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dynatrace-app-base
  labels:
    monitoring.profile: api-observability
    monitoring.tool: dynatrace
data:
  application.json: |
    {
      "metadata": {
        "name": "{SERVICE}",
        "environment": "{ENVIRONMENT}",
        "team": "{TEAM}",
        "costCenter": "{COST_CENTER}"
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
          "notificationChannels": ["teams-{SERVICE}"]
        },
        {
          "name": "HighLatencyAnomaly",
          "enabled": true,
          "condition": "Anomaly(ResponseTime)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-{SERVICE}"]
        },
        {
          "name": "ServiceCrash",
          "enabled": true,
          "condition": "CrashDetection",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-{SERVICE}", "pagerduty-oncall"]
        }
      ],
      "customMetrics": []
    }
```

---

### 4.5 Custom Metrics Component

**File**: `kustomize/monitoring/custom-metrics/payment-processor/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Custom metrics from metrics-catalog repository
resources:
  # Fetch from metrics-catalog repo (Git URL)
  - https://github.com/company/metrics-catalog/services/payment-processor/payment-business-metrics.yaml?ref=v1.2.0
  - https://github.com/company/metrics-catalog/services/payment-processor/payment-fraud-metrics.yaml?ref=v1.2.0

# Or if using OCI registry:
# resources:
#   - oci://gcr.io/my-project/metrics/payment-business-metrics:v1.2.0

commonLabels:
  metrics.service: payment-processor
  metrics.type: custom
```

---

### 4.6 Enhanced Manifest Generation Script

**File**: `scripts/generate-kz.sh` (enhanced section)

```bash
#!/usr/bin/env bash

SERVICE=$1
ENV=$2
REGION=$3

# ... existing catalog loading ...

# ================================================
# LOAD MONITORING CONFIGURATION
# ================================================
MONITORING_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.monitoringProfile // ""' -)
MONITORING_CONFIG=$(echo "$SERVICE_DATA" | yq eval '.monitoring // {}' -)

if [[ -n "$MONITORING_PROFILE" ]]; then
  # Load base profile
  PROFILE_CONFIG=$(yq eval ".monitoringProfiles.$MONITORING_PROFILE" kustomize/catalog/monitoring-profiles.yaml)
  
  # Load custom metrics config
  CUSTOM_METRICS_REPO=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.repository.url // ""' -)
  CUSTOM_METRICS_REF=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.repository.ref // "main"' -)
  CUSTOM_METRICS_PROFILES=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.profiles[]' - 2>/dev/null | tr '\n' ' ')
  
  # ================================================
  # GENERATE MONITORING RESOURCES
  # ================================================
  MONITORING_DIR="tmp/$SERVICE/$ENV/$REGION/monitoring"
  mkdir -p "$MONITORING_DIR"
  
  # 1. Generate ServiceMonitor (Prometheus)
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.prometheus.enabled // false' -) == "true" ]]; then
    generate_service_monitor "$PROFILE_CONFIG" "$SERVICE" > "$MONITORING_DIR/service-monitor.yaml"
  fi
  
  # 2. Generate PrometheusRule (recording + alerts)
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.prometheus.enabled // false' -) == "true" ]]; then
    generate_prometheus_rules "$PROFILE_CONFIG" "$SERVICE" "$ENV" > "$MONITORING_DIR/prometheus-rules.yaml"
  fi
  
  # 3. Generate Dynatrace ConfigMap (PRIMARY)
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.enabled // false' -) == "true" ]]; then
    # Merge base profile + custom metrics
    DYNATRACE_CONFIG=$(merge_dynatrace_config "$PROFILE_CONFIG" "$MONITORING_CONFIG" "$SERVICE" "$ENV")
    echo "$DYNATRACE_CONFIG" > "$MONITORING_DIR/dynatrace-app-config.yaml"
  fi
fi

# ================================================
# ADD MONITORING TO KUSTOMIZATION
# ================================================
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

# Monitoring resources
resources:
  - ./monitoring/service-monitor.yaml
  - ./monitoring/prometheus-rules.yaml
  - ./monitoring/dynatrace-app-config.yaml

# Custom metrics from metrics-catalog (if specified)
EOF

# Add custom metrics resources
if [[ -n "$CUSTOM_METRICS_REPO" ]]; then
  for PROFILE in $CUSTOM_METRICS_PROFILES; do
    echo "  - ${CUSTOM_METRICS_REPO}/profiles/${PROFILE}?ref=${CUSTOM_METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
  done
  
  # Add service-specific custom metrics
  echo "  - ${CUSTOM_METRICS_REPO}/services/${SERVICE}?ref=${CUSTOM_METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
fi

# Helper function to merge Dynatrace config
merge_dynatrace_config() {
  local PROFILE_CONFIG=$1
  local MONITORING_CONFIG=$2
  local SERVICE=$3
  local ENV=$4
  
  # Load base Dynatrace config from profile
  BASE_CONFIG=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.application' -)
  
  # Load custom metrics from service config
  CUSTOM_METRICS=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.metrics[]' -)
  
  # Merge custom metrics into base config
  MERGED_CONFIG=$(echo "$BASE_CONFIG" | yq eval ".customMetrics += $CUSTOM_METRICS" -)
  
  # Substitute variables
  MERGED_CONFIG=$(echo "$MERGED_CONFIG" | sed "s/{SERVICE}/$SERVICE/g")
  MERGED_CONFIG=$(echo "$MERGED_CONFIG" | sed "s/{ENVIRONMENT}/$ENV/g")
  
  # Generate ConfigMap
  cat <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${SERVICE}-dynatrace-config
  namespace: ${ENV}-${SERVICE}-${REGION}-stable
  labels:
    app: ${SERVICE}
    monitoring.profile: ${MONITORING_PROFILE}
    monitoring.tool: dynatrace
data:
  application.json: |
$(echo "$MERGED_CONFIG" | jq . | sed 's/^/    /')
EOF
}
```

---

## 5. Generated Output Example

### 5.1 Generated Dynatrace ConfigMap

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

---

## 6. Key Differences Summary

| Aspect | Doc 05: Metrics as Code | Doc 08: Monitoring Profiles | Unified Approach |
|--------|------------------------|----------------------------|------------------|
| **Location** | Separate `metrics-catalog` repo | In `platform-next` repo | Both: Profiles in platform-next, custom metrics in catalog |
| **Ownership** | Observability team | Platform team | Shared: Platform owns profiles, Observability owns custom metrics |
| **Versioning** | Independent versioning | Tied to platform-next | Both: Profiles versioned with platform, custom metrics independently |
| **Composability** | Highly composable | Template-based | Best of both: Templates + composable |
| **Dynatrace** | Limited support | Full support | Full Dynatrace support (primary tool) |
| **Prometheus** | Primary focus | Secondary | Secondary (for metrics collection) |
| **Custom Metrics** | Strong support | Limited | Strong support via metrics-catalog |
| **Integration** | External reference | Integrated | Unified: Profiles + external custom metrics |

---

## 7. How They Work Together

### 7.1 Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Service Definition (services.yaml)                          │
├─────────────────────────────────────────────────────────────┤
│ monitoringProfile: api-observability                        │
│ monitoring:                                                  │
│   customMetrics:                                            │
│     repository:                                             │
│       url: https://github.com/company/metrics-catalog      │
│       ref: v1.2.0                                           │
│     profiles: [payment-business-metrics]                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Profile Expansion Engine                                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Load base profile (monitoring-profiles.yaml)             │
│    → Dynatrace app structure                                │
│    → Standard alert rules                                   │
│    → Standard request attributes                            │
│                                                              │
│ 2. Fetch custom metrics (metrics-catalog repo)              │
│    → Payment business metrics                               │
│    → Custom Dynatrace metrics                               │
│    → Custom alert rules                                     │
│                                                              │
│ 3. Merge configurations                                     │
│    → Base Dynatrace config                                  │
│    + Custom metrics                                         │
│    + Custom alert rules                                     │
│                                                              │
│ 4. Substitute variables                                     │
│    → {SERVICE} → payment-processor                           │
│    → {ENVIRONMENT} → prod                                    │
│    → {TEAM} → payments-team                                  │
│                                                              │
│ 5. Apply environment overrides                              │
│    → Prod SLOs: 99.99% availability                         │
│    → Prod latency: 200ms p95                                │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Generated Monitoring Resources                              │
├─────────────────────────────────────────────────────────────┤
│ • Dynatrace ConfigMap (merged: base + custom)              │
│   - Application definition                                   │
│   - Request attributes                                       │
│   - Custom metrics (from catalog)                           │
│   - Alert rules (base + custom)                             │
│                                                              │
│ • ServiceMonitor (Prometheus)                                │
│   - Scraping configuration                                   │
│                                                              │
│ • PrometheusRule (recording + alerts)                        │
│   - Recording rules (base + custom)                         │
│   - Alert rules (base + custom)                             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Deployment                                                  │
├─────────────────────────────────────────────────────────────┤
│ • Dynatrace ConfigMap → Dynatrace Sync Controller           │
│   → Creates/updates Dynatrace application                   │
│   → Configures custom metrics                               │
│   → Sets up alert rules                                     │
│                                                              │
│ • ServiceMonitor → Prometheus Operator                      │
│   → Prometheus starts scraping                              │
│                                                              │
│ • PrometheusRule → Prometheus                                │
│   → Recording rules active                                  │
│   → Alert rules armed                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Implementation in Kustomize Folder

### 8.1 Complete Folder Structure

```
kustomize/
├── catalog/
│   ├── services.yaml                    # Service definitions
│   └── monitoring-profiles.yaml         # Base monitoring profiles
│
├── monitoring/                          # NEW: Monitoring components
│   ├── profiles/                        # Profile-based resources
│   │   ├── api-observability/
│   │   │   ├── kustomization.yaml
│   │   │   ├── service-monitor-base.yaml
│   │   │   ├── prometheus-rules-base.yaml
│   │   │   └── dynatrace-app-base.yaml
│   │   │
│   │   ├── batch-job-observability/
│   │   │   └── ...
│   │   │
│   │   └── listener-observability/
│   │       └── ...
│   │
│   └── dynatrace/                       # Dynatrace-specific
│       ├── request-attributes-base.yaml
│       └── alert-rules-base.yaml
│
└── components/                         # Existing components
    ├── ingress/
    ├── hpa/
    └── ...
```

---

### 8.2 Example: API Observability Profile Component

**File**: `kustomize/monitoring/profiles/api-observability/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - service-monitor-base.yaml
  - prometheus-rules-base.yaml
  - dynatrace-app-base.yaml

commonLabels:
  monitoring.profile: api-observability
  monitoring.tool: dynatrace
  monitoring.primary: "true"
```

**File**: `kustomize/monitoring/profiles/api-observability/dynatrace-app-base.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dynatrace-app-base
  labels:
    monitoring.profile: api-observability
    monitoring.tool: dynatrace
data:
  application.json: |
    {
      "metadata": {
        "name": "{SERVICE}",
        "environment": "{ENVIRONMENT}",
        "team": "{TEAM}",
        "costCenter": "{COST_CENTER}"
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
          "notificationChannels": ["teams-{SERVICE}"]
        },
        {
          "name": "HighLatencyAnomaly",
          "enabled": true,
          "condition": "Anomaly(ResponseTime)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-{SERVICE}"]
        },
        {
          "name": "ServiceCrash",
          "enabled": true,
          "condition": "CrashDetection",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-{SERVICE}", "pagerduty-oncall"]
        }
      ],
      "customMetrics": []
    }
```

---

### 8.3 Example: ServiceMonitor Base

**File**: `kustomize/monitoring/profiles/api-observability/service-monitor-base.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-service-monitor
  labels:
    monitoring.profile: api-observability
spec:
  selector:
    matchLabels:
      app: app  # Will be replaced by service name
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
      relabelings:
        # Add service metadata as metric labels
        - sourceLabels: [__meta_kubernetes_pod_label_cost_service]
          targetLabel: service
        - sourceLabels: [__meta_kubernetes_pod_label_cost_team]
          targetLabel: team
        - sourceLabels: [__meta_kubernetes_pod_label_cost_environment]
          targetLabel: environment
        - sourceLabels: [__meta_kubernetes_pod_label_cost_costCenter]
          targetLabel: costCenter
```

---

### 8.4 Example: Prometheus Rules Base

**File**: `kustomize/monitoring/profiles/api-observability/prometheus-rules-base.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: app-prometheus-rules
  labels:
    monitoring.profile: api-observability
spec:
  groups:
    # Recording rules (pre-compute aggregations)
    - name: golden_signals_recording
      interval: 30s
      rules:
        - record: service:http_requests:rate5m
          expr: |
            sum(rate(http_requests_total{service="{SERVICE}"}[5m]))
            by (method, status)
        
        - record: service:http_errors:rate5m
          expr: |
            sum(rate(http_errors_total{service="{SERVICE}"}[5m]))
        
        - record: service:http_latency:p95
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="{SERVICE}"}[5m]))
              by (le)
            )
        
        - record: service:http_error_ratio:rate5m
          expr: |
            service:http_errors:rate5m{service="{SERVICE}"}
            /
            service:http_requests:rate5m{service="{SERVICE}"}
    
    # Alert rules
    - name: golden_signals_alerts
      rules:
        - alert: HighErrorRate
          expr: |
            service:http_error_ratio:rate5m{service="{SERVICE}"} > {ERROR_RATE_THRESHOLD}
          for: 5m
          labels:
            severity: warning
            service: "{SERVICE}"
          annotations:
            summary: "High error rate for {SERVICE}"
            description: "Error rate is {{ $value | humanizePercentage }} (threshold: {ERROR_RATE_THRESHOLD})"
        
        - alert: HighLatency
          expr: |
            service:http_latency:p95{service="{SERVICE}"} > {LATENCY_P95_THRESHOLD}
          for: 5m
          labels:
            severity: warning
            service: "{SERVICE}"
          annotations:
            summary: "High latency for {SERVICE}"
            description: "P95 latency is {{ $value | humanizeDuration }} (threshold: {LATENCY_P95_THRESHOLD})"
```

---

## 9. Enhanced Generation Script

### 9.1 Complete Script Section

**File**: `scripts/generate-kz.sh` (monitoring section)

```bash
# ================================================
# MONITORING RESOURCES GENERATION
# ================================================
generate_monitoring_resources() {
  local SERVICE=$1
  local ENV=$2
  local REGION=$3
  local MONITORING_DIR="tmp/$SERVICE/$ENV/$REGION/monitoring"
  mkdir -p "$MONITORING_DIR"
  
  # Load monitoring profile
  MONITORING_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.monitoringProfile // ""' -)
  if [[ -z "$MONITORING_PROFILE" ]]; then
    return 0  # No monitoring configured
  fi
  
  # Load profile configuration
  PROFILE_CONFIG=$(yq eval ".monitoringProfiles.$MONITORING_PROFILE" kustomize/catalog/monitoring-profiles.yaml)
  
  # Load custom metrics configuration
  MONITORING_CONFIG=$(echo "$SERVICE_DATA" | yq eval '.monitoring // {}' -)
  CUSTOM_METRICS_REPO=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.repository.url // ""' -)
  CUSTOM_METRICS_REF=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.repository.ref // "main"' -)
  
  # ================================================
  # GENERATE SERVICEMONITOR (Prometheus)
  # ================================================
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.prometheus.enabled // false' -) == "true" ]]; then
    generate_service_monitor "$PROFILE_CONFIG" "$SERVICE" > "$MONITORING_DIR/service-monitor.yaml"
  fi
  
  # ================================================
  # GENERATE PROMETHEUS RULES
  # ================================================
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.prometheus.enabled // false' -) == "true" ]]; then
    generate_prometheus_rules "$PROFILE_CONFIG" "$SERVICE" "$ENV" > "$MONITORING_DIR/prometheus-rules.yaml"
  fi
  
  # ================================================
  # GENERATE DYNATRACE CONFIGMAP (PRIMARY)
  # ================================================
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.enabled // false' -) == "true" ]]; then
    # Merge base profile + custom metrics
    DYNATRACE_CONFIG=$(merge_dynatrace_config \
      "$PROFILE_CONFIG" \
      "$MONITORING_CONFIG" \
      "$SERVICE" \
      "$ENV" \
      "$CUSTOM_METRICS_REPO" \
      "$CUSTOM_METRICS_REF"
    )
    echo "$DYNATRACE_CONFIG" > "$MONITORING_DIR/dynatrace-app-config.yaml"
  fi
}

# ================================================
# GENERATE SERVICEMONITOR
# ================================================
generate_service_monitor() {
  local PROFILE_CONFIG=$1
  local SERVICE=$2
  
  local SCRAPE_INTERVAL=$(echo "$PROFILE_CONFIG" | yq eval '.prometheus.serviceMonitor.scrapeInterval // "30s"' -)
  local PATH=$(echo "$PROFILE_CONFIG" | yq eval '.prometheus.serviceMonitor.path // "/metrics"' -)
  local PORT=$(echo "$PROFILE_CONFIG" | yq eval '.prometheus.serviceMonitor.port // "http"' -)
  
  cat <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ${SERVICE}-monitor
  namespace: ${ENV}-${SERVICE}-${REGION}-stable
  labels:
    app: ${SERVICE}
    monitoring.profile: ${MONITORING_PROFILE}
spec:
  selector:
    matchLabels:
      app: ${SERVICE}
  endpoints:
    - port: ${PORT}
      path: ${PATH}
      interval: ${SCRAPE_INTERVAL}
      scrapeTimeout: 10s
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_label_cost_service]
          targetLabel: service
        - sourceLabels: [__meta_kubernetes_pod_label_cost_team]
          targetLabel: team
        - sourceLabels: [__meta_kubernetes_pod_label_cost_environment]
          targetLabel: environment
        - sourceLabels: [__meta_kubernetes_pod_label_cost_costCenter]
          targetLabel: costCenter
EOF
}

# ================================================
# GENERATE PROMETHEUS RULES
# ================================================
generate_prometheus_rules() {
  local PROFILE_CONFIG=$1
  local SERVICE=$2
  local ENV=$3
  
  # Get thresholds from profile (with environment overrides)
  ERROR_RATE_THRESHOLD=$(get_error_rate_threshold "$PROFILE_CONFIG" "$ENV")
  LATENCY_THRESHOLD=$(get_latency_threshold "$PROFILE_CONFIG" "$ENV")
  
  # Load recording rules from profile
  RECORDING_RULES=$(echo "$PROFILE_CONFIG" | yq eval '.prometheus.recordingRules[]' -)
  ALERT_RULES=$(echo "$PROFILE_CONFIG" | yq eval '.prometheus.alertRules[]' -)
  
  cat <<EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ${SERVICE}-prometheus-rules
  namespace: ${ENV}-${SERVICE}-${REGION}-stable
  labels:
    app: ${SERVICE}
    monitoring.profile: ${MONITORING_PROFILE}
spec:
  groups:
    - name: ${SERVICE}_recording
      interval: 30s
      rules:
$(echo "$RECORDING_RULES" | yq eval - | sed "s/{SERVICE}/$SERVICE/g" | sed 's/^/        /')
    
    - name: ${SERVICE}_alerts
      rules:
$(echo "$ALERT_RULES" | yq eval - | sed "s/{SERVICE}/$SERVICE/g" | sed "s/{ERROR_RATE_THRESHOLD}/$ERROR_RATE_THRESHOLD/g" | sed "s/{LATENCY_P95_THRESHOLD}/$LATENCY_THRESHOLD/g" | sed 's/^/        /')
EOF
}

# ================================================
# MERGE DYNATRACE CONFIG
# ================================================
merge_dynatrace_config() {
  local PROFILE_CONFIG=$1
  local MONITORING_CONFIG=$2
  local SERVICE=$3
  local ENV=$4
  local CUSTOM_METRICS_REPO=$5
  local CUSTOM_METRICS_REF=$6
  
  # Load base Dynatrace config from profile
  BASE_APP_CONFIG=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.application' -)
  BASE_ALERT_RULES=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.alertRules[]' -)
  
  # Load custom metrics from service config
  CUSTOM_METRICS=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.metrics[]' - 2>/dev/null || echo "")
  
  # Fetch custom metrics from metrics-catalog repo (if specified)
  if [[ -n "$CUSTOM_METRICS_REPO" ]]; then
    # Clone metrics-catalog repo temporarily
    TEMP_METRICS_DIR=$(mktemp -d)
    git clone --depth 1 --branch "$CUSTOM_METRICS_REF" "$CUSTOM_METRICS_REPO" "$TEMP_METRICS_DIR" 2>/dev/null || true
    
    if [[ -d "$TEMP_METRICS_DIR/services/$SERVICE" ]]; then
      # Load custom metrics from metrics-catalog
      CUSTOM_METRICS_FROM_REPO=$(yq eval '.customMetrics[]' "$TEMP_METRICS_DIR/services/$SERVICE"/*.yaml 2>/dev/null || echo "")
      CUSTOM_ALERT_RULES_FROM_REPO=$(yq eval '.alertRules[]' "$TEMP_METRICS_DIR/services/$SERVICE"/*.yaml 2>/dev/null || echo "")
      
      # Merge with existing custom metrics
      CUSTOM_METRICS=$(echo -e "$CUSTOM_METRICS\n$CUSTOM_METRICS_FROM_REPO")
      BASE_ALERT_RULES=$(echo -e "$BASE_ALERT_RULES\n$CUSTOM_ALERT_RULES_FROM_REPO")
    fi
    
    rm -rf "$TEMP_METRICS_DIR"
  fi
  
  # Merge custom metrics into base config
  MERGED_APP_CONFIG=$(echo "$BASE_APP_CONFIG" | yq eval ".customMetrics = []" -)
  
  # Add custom metrics
  if [[ -n "$CUSTOM_METRICS" ]]; then
    while IFS= read -r metric; do
      MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | yq eval ".customMetrics += [$metric]" -)
    done <<< "$CUSTOM_METRICS"
  fi
  
  # Substitute variables
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{SERVICE}/$SERVICE/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{ENVIRONMENT}/$ENV/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{TEAM}/payments-team/g")  # Get from service config
  
  # Generate final ConfigMap
  cat <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${SERVICE}-dynatrace-config
  namespace: ${ENV}-${SERVICE}-${REGION}-stable
  labels:
    app: ${SERVICE}
    monitoring.profile: ${MONITORING_PROFILE}
    monitoring.tool: dynatrace
    monitoring.primary: "true"
data:
  application.json: |
$(echo "$MERGED_APP_CONFIG" | jq . | sed 's/^/    /')
  alert-rules.json: |
$(echo "$BASE_ALERT_RULES" | jq -s . | sed 's/^/    /')
EOF
}
```

---

## 10. Summary

### 10.1 Key Differences

| Aspect | Doc 05 | Doc 08 | Unified |
|--------|--------|--------|---------|
| **Base Templates** | ❌ | ✅ Profiles | ✅ Profiles (in platform-next) |
| **Custom Metrics** | ✅ Separate repo | ❌ | ✅ Separate repo (metrics-catalog) |
| **Dynatrace** | ❌ Limited | ✅ Full | ✅ Full (primary) |
| **Composability** | ✅ High | ⚠️ Medium | ✅ High |
| **Integration** | ⚠️ External | ✅ Integrated | ✅ Unified |

### 10.2 Unified Approach Benefits

1. **Profiles** provide standard observability patterns (base templates)
2. **Custom Metrics** extend profiles with service-specific metrics
3. **Dynatrace** is primary monitoring tool (full support)
4. **Prometheus** is secondary (for metrics collection)
5. **Composable** - mix and match profiles + custom metrics
6. **Maintainable** - profiles in platform-next, custom metrics in catalog

### 10.3 Implementation Steps

1. ✅ Create `kustomize/monitoring/profiles/` structure
2. ✅ Define base profiles in `monitoring-profiles.yaml`
3. ✅ Create profile components (Dynatrace, Prometheus)
4. ✅ Enhance generation script to merge profiles + custom metrics
5. ✅ Support metrics-catalog repository references
6. ✅ Generate unified Dynatrace ConfigMap
7. ✅ Deploy via Kustomize

---

**Document Status**: ✅ Complete Unified Design

**Next Steps**: Implement the kustomize folder structure and enhanced generation script.

