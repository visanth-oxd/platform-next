# Dynatrace Monitoring Design: Profiles + Custom Metrics as Code

**Status**: COMPREHENSIVE DESIGN - Dynatrace-Focused Monitoring

**Document Type**: Architecture + Implementation Guide

**Audience**: Platform engineers, SRE teams, observability teams

**Date**: 2025-11-16

---

## Executive Summary

This document describes the **Dynatrace-focused monitoring system** that combines **monitoring profiles** (base templates) with **custom metrics as code** (from a separate repository), enabling the observability team to configure service-specific metrics independently.

**Key Principles**:
- ✅ **Dynatrace Primary** - Dynatrace OneAgent is the primary monitoring tool
- ✅ **Profile-Based** - Base monitoring patterns via reusable profiles
- ✅ **Custom Metrics as Code** - Service-specific metrics in separate `metrics-catalog` repository
- ✅ **Observability Team Ownership** - Observability team can add custom metrics without touching platform config
- ✅ **Composable** - Mix base profiles with custom metrics
- ✅ **No Prometheus/Grafana** - Pure Dynatrace solution (Prometheus optional if needed)

**Business Context**:
- Business Unit: `core-banking`
- Owner: `owner@company.com`
- Cost Center: `COR-B`

---

## ⚠️ Important: Prometheus is NOT Required

**Question**: Do we need Prometheus for metrics data collection?

**Answer**: **NO, Prometheus is NOT required.**

### How Metrics Collection Works

1. **Dynatrace OneAgent** (DaemonSet) auto-instruments your Java application
2. **OneAgent collects metrics directly** from the application:
   - HTTP requests/responses
   - Database queries
   - Error rates
   - Latency (p50, p95, p99)
   - Custom application metrics (from your code)
3. **OneAgent sends metrics directly to Dynatrace SaaS** - no intermediate storage needed
4. **Dynatrace SaaS** stores, analyzes, and alerts on all metrics

### What About Custom Metrics?

- **Custom metrics** (like `payment_transactions_total`, `payment_success_rate`) are collected by OneAgent
- Your application code exposes these metrics (via Dynatrace SDK or standard formats)
- OneAgent automatically discovers and collects them
- **No Prometheus scraping needed**

### When Would You Need Prometheus?

Prometheus is **optional** and only useful for:
- ✅ Long-term metric storage (if Dynatrace retention limits are a concern)
- ✅ Custom PromQL queries (if you prefer PromQL over Dynatrace query language)
- ✅ Integration with tools that expect Prometheus metrics format
- ✅ Cost-effective metric storage for historical data

**But for core monitoring, alerting, and metrics collection - Dynatrace OneAgent handles everything.**

---

## 1. Architecture Overview

### 1.1 Two-Repository Model

```
┌─────────────────────────────────────────────────────────────┐
│ Repository 1: platform-next (Platform Team)                 │
├─────────────────────────────────────────────────────────────┤
│ • Service catalog (services.yaml)                            │
│ • Monitoring profiles (monitoring-profiles.yaml)             │
│ • Kustomize bases, components, overlays                     │
│ • Manifest generation                                        │
│ • References custom metrics from metrics-catalog            │
└────────────┬────────────────────────────────────────────────┘
             │
             │ References (Git URL or OCI)
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Repository 2: metrics-catalog (Observability Team)           │
├─────────────────────────────────────────────────────────────┤
│ • Service-specific custom metrics                            │
│ • Custom Dynatrace metrics definitions                       │
│ • Custom alert rules                                         │
│ • Custom dashboards                                          │
│ • Versioned independently                                    │
└─────────────────────────────────────────────────────────────┘
```

---

### 1.2 Complete Flow

```
Developer → Backstage Form
  ↓
Catalog Entry (services.yaml)
  ├─ monitoringProfile: domain-api (base)
  └─ customMetrics: {repository: metrics-catalog}
  ↓
CI/CD: Profile Expansion
  ├─ Load base profile (from monitoring-profiles.yaml)
  ├─ Fetch custom metrics (from metrics-catalog repo)
  └─ Merge: Base + Custom
  ↓
Manifest Generation
  ├─ Generate Dynatrace ConfigMap (merged)
  └─ Include in kustomization.yaml
  ↓
Deployment
  ├─ Dynatrace ConfigMap deployed
  └─ Dynatrace Sync Controller syncs to Dynatrace SaaS
  ↓
Runtime
  ├─ Dynatrace OneAgent auto-instruments application
  ├─ Custom metrics collected
  └─ Alerts fire based on rules
```

---

## 2. Monitoring Profiles (Base Templates)

### 2.1 Profile Definition

**File**: `kustomize/catalog/monitoring-profiles.yaml`

```yaml
monitoringProfiles:
  domain-api:
    description: "REST API monitoring with Dynatrace OneAgent"
    
    # ================================================
    # DYNATRACE CONFIGURATION (PRIMARY)
    # ================================================
    dynatrace:
      enabled: true
      primary: true
      
      # Application definition
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
          - name: "businessUnit"
            source:
              kubernetesLabel: "cost.businessUnit"
          - name: "region"
            source:
              kubernetesLabel: "cost.region"
          - name: "archetype"
            source:
              kubernetesLabel: "archetype"
          - name: "size"
            source:
              kubernetesLabel: "size"
      
      # Standard alert rules (base)
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
            email: ["owner@company.com"]
      
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
            condition: "ErrorRate > 0.0005"
            severity: critical
```

---

### 2.2 Other Profile Examples

**Batch Job Profile**:

```yaml
  batch-job-observability:
    description: "Batch job monitoring with Dynatrace"
    
    dynatrace:
      enabled: true
      primary: true
      
      application:
        monitoredTechnologies:
          - java
          - kubernetes
        
        requestAttributes:
          - name: "service"
            source:
              kubernetesLabel: "app"
          - name: "jobType"
            source:
              kubernetesLabel: "job.type"
      
      alertRules:
        - name: "JobFailure"
          enabled: true
          condition: "JobStatus == 'FAILED'"
          targets: ["JOB"]
          severity: critical
      
      customMetrics:
        - name: "job_success_rate"
          type: "gauge"
          description: "Job success rate"
          unit: "percent"
```

**Listener Profile**:

```yaml
  listener-observability:
    description: "Event listener monitoring with Dynatrace"
    
    dynatrace:
      enabled: true
      primary: true
      
      application:
        monitoredTechnologies:
          - java
          - kafka
          - kubernetes
        
        requestAttributes:
          - name: "service"
            source:
              kubernetesLabel: "app"
          - name: "topic"
            source:
              kubernetesLabel: "kafka.topic"
      
      alertRules:
        - name: "ConsumerLagHigh"
          enabled: true
          condition: "ConsumerLag > 1000"
          targets: ["KAFKA"]
          severity: warning
```

---

## 3. Service Definition with Custom Metrics

### 3.1 Service Catalog Entry

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
      costCenter: "COR-B"
      businessUnit: "core-banking"
      costOwner: "owner@company.com"
    
    # ================================================
    # MONITORING CONFIGURATION
    # ================================================
    monitoringProfile: domain-api  # Base profile
    
    monitoring:
      # Enable Dynatrace (primary)
      dynatrace: true
      
      # Custom metrics from metrics-catalog repository
      customMetrics:
        repository:
          url: https://github.com/company/metrics-catalog
          ref: v1.2.0  # Pin to version
        
        # Service-specific custom metrics profiles
        profiles:
          - payment-business-metrics  # Business metrics profile
          - payment-fraud-metrics      # Fraud detection metrics
        
        # Inline custom metrics (optional, can also be in metrics-catalog)
        metrics:
          - name: payment_transactions_total
            type: counter
            description: "Total payment transactions processed"
            dynatrace:
              enabled: true
              unit: "count"
              aggregation: "sum"
              dimensions: ["status", "payment_method", "environment"]
      
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
                  email: ["owner@company.com"]
```

---

## 4. Custom Metrics in Metrics Catalog

### 4.1 Metrics Catalog Structure

```
metrics-catalog/
├── services/
│   ├── payment-processor/
│   │   ├── payment-business-metrics.yaml
│   │   ├── payment-fraud-metrics.yaml
│   │   └── kustomization.yaml
│   │
│   └── account-service/
│       └── account-metrics.yaml
│
└── profiles/
    ├── payment-business-metrics/
    │   └── metrics.yaml
    └── payment-fraud-metrics/
        └── metrics.yaml
```

---

### 4.2 Custom Metrics Definition

**File**: `metrics-catalog/services/payment-processor/payment-business-metrics.yaml`

```yaml
# Custom business metrics for payment-processor service
# Owned by observability team
# Versioned independently from platform-next

apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-business-metrics
  labels:
    metrics.type: business
    metrics.service: payment-processor
    metrics.owner: observability-team
data:
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
            "email": ["owner@company.com"]
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
            "email": ["owner@company.com"]
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
            "email": ["owner@company.com"]
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

## 5. Kustomize Folder Structure

### 5.1 Complete Structure

```
kustomize/
├── catalog/
│   ├── services.yaml                    # Service definitions
│   └── monitoring-profiles.yaml         # Base monitoring profiles
│
├── monitoring/                          # Monitoring components
│   ├── profiles/                        # Profile-based resources
│   │   ├── domain-api/
│   │   │   ├── kustomization.yaml
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

### 5.2 Profile Component

**File**: `kustomize/monitoring/profiles/domain-api/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - dynatrace-app-base.yaml

commonLabels:
  monitoring.profile: domain-api
  monitoring.tool: dynatrace
  monitoring.primary: "true"

namespace: default
```

**File**: `kustomize/monitoring/profiles/domain-api/dynatrace-app-base.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dynatrace-app-base
  labels:
    monitoring.profile: domain-api
    monitoring.tool: dynatrace
    monitoring.primary: "true"
data:
  application.json: |
    {
      "metadata": {
        "name": "{SERVICE}",
        "environment": "{ENVIRONMENT}",
        "team": "{TEAM}",
        "costCenter": "{COST_CENTER}",
        "businessUnit": "{BUSINESS_UNIT}"
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
          "notificationChannels": ["teams-{SERVICE}", "owner@company.com"]
        }
      ],
      "customMetrics": []
    }
```

---

## 6. Manifest Generation Script

### 6.1 Enhanced Generation Script

**File**: `scripts/generate-kz.sh` (monitoring section)

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
  
  # Get service metadata
  TEAM=$(echo "$SERVICE_DATA" | yq eval '.cost.costOwner // "owner@company.com"' -)
  COST_CENTER=$(echo "$SERVICE_DATA" | yq eval '.cost.costCenter // "COR-B"' -)
  BUSINESS_UNIT=$(echo "$SERVICE_DATA" | yq eval '.cost.businessUnit // "core-banking"' -)
  
  # ================================================
  # GENERATE DYNATRACE CONFIGMAP
  # ================================================
  MONITORING_DIR="tmp/$SERVICE/$ENV/$REGION/monitoring"
  mkdir -p "$MONITORING_DIR"
  
  if [[ $(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.enabled // false' -) == "true" ]]; then
    # Merge base profile + custom metrics
    DYNATRACE_CONFIG=$(merge_dynatrace_config \
      "$PROFILE_CONFIG" \
      "$MONITORING_CONFIG" \
      "$SERVICE" \
      "$ENV" \
      "$TEAM" \
      "$COST_CENTER" \
      "$BUSINESS_UNIT" \
      "$CUSTOM_METRICS_REPO" \
      "$CUSTOM_METRICS_REF" \
      "$CUSTOM_METRICS_PROFILES"
    )
    echo "$DYNATRACE_CONFIG" > "$MONITORING_DIR/dynatrace-app-config.yaml"
  fi
fi

# ================================================
# ADD MONITORING TO KUSTOMIZATION
# ================================================
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

# Monitoring resources
resources:
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

# ================================================
# HELPER FUNCTION: MERGE DYNATRACE CONFIG
# ================================================
merge_dynatrace_config() {
  local PROFILE_CONFIG=$1
  local MONITORING_CONFIG=$2
  local SERVICE=$3
  local ENV=$4
  local TEAM=$5
  local COST_CENTER=$6
  local BUSINESS_UNIT=$7
  local CUSTOM_METRICS_REPO=$8
  local CUSTOM_METRICS_REF=$9
  shift 9
  local CUSTOM_METRICS_PROFILES="$@"
  
  # Load base Dynatrace config from profile
  BASE_APP_CONFIG=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.application' -)
  BASE_ALERT_RULES=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.alertRules[]' -)
  BASE_CUSTOM_METRICS=$(echo "$PROFILE_CONFIG" | yq eval '.dynatrace.customMetrics[]' -)
  
  # Initialize merged config
  MERGED_CUSTOM_METRICS="$BASE_CUSTOM_METRICS"
  MERGED_ALERT_RULES="$BASE_ALERT_RULES"
  
  # Fetch custom metrics from metrics-catalog repo (if specified)
  if [[ -n "$CUSTOM_METRICS_REPO" ]]; then
    # Clone metrics-catalog repo temporarily
    TEMP_METRICS_DIR=$(mktemp -d)
    git clone --depth 1 --branch "$CUSTOM_METRICS_REF" "$CUSTOM_METRICS_REPO" "$TEMP_METRICS_DIR" 2>/dev/null || true
    
    # Load custom metrics from service-specific directory
    if [[ -d "$TEMP_METRICS_DIR/services/$SERVICE" ]]; then
      for METRICS_FILE in "$TEMP_METRICS_DIR/services/$SERVICE"/*.yaml; do
        if [[ -f "$METRICS_FILE" ]]; then
          # Extract custom metrics from ConfigMap
          CUSTOM_METRICS_JSON=$(yq eval '.data."dynatrace-custom-metrics.json"' "$METRICS_FILE" 2>/dev/null || echo "")
          if [[ -n "$CUSTOM_METRICS_JSON" ]]; then
            # Parse and merge custom metrics
            CUSTOM_METRICS_FROM_FILE=$(echo "$CUSTOM_METRICS_JSON" | jq -r '.customMetrics[]' 2>/dev/null || echo "")
            CUSTOM_ALERT_RULES_FROM_FILE=$(echo "$CUSTOM_METRICS_JSON" | jq -r '.alertRules[]' 2>/dev/null || echo "")
            
            # Merge custom metrics
            if [[ -n "$CUSTOM_METRICS_FROM_FILE" ]]; then
              MERGED_CUSTOM_METRICS=$(echo -e "$MERGED_CUSTOM_METRICS\n$CUSTOM_METRICS_FROM_FILE")
            fi
            
            # Merge alert rules
            if [[ -n "$CUSTOM_ALERT_RULES_FROM_FILE" ]]; then
              MERGED_ALERT_RULES=$(echo -e "$MERGED_ALERT_RULES\n$CUSTOM_ALERT_RULES_FROM_FILE")
            fi
          fi
        fi
      done
    fi
    
    # Load custom metrics from profiles
    for PROFILE in $CUSTOM_METRICS_PROFILES; do
      if [[ -d "$TEMP_METRICS_DIR/profiles/$PROFILE" ]]; then
        for METRICS_FILE in "$TEMP_METRICS_DIR/profiles/$PROFILE"/*.yaml; do
          if [[ -f "$METRICS_FILE" ]]; then
            CUSTOM_METRICS_JSON=$(yq eval '.data."dynatrace-custom-metrics.json"' "$METRICS_FILE" 2>/dev/null || echo "")
            if [[ -n "$CUSTOM_METRICS_JSON" ]]; then
              CUSTOM_METRICS_FROM_FILE=$(echo "$CUSTOM_METRICS_JSON" | jq -r '.customMetrics[]' 2>/dev/null || echo "")
              if [[ -n "$CUSTOM_METRICS_FROM_FILE" ]]; then
                MERGED_CUSTOM_METRICS=$(echo -e "$MERGED_CUSTOM_METRICS\n$CUSTOM_METRICS_FROM_FILE")
              fi
            fi
          fi
        done
      fi
    fi
    
    rm -rf "$TEMP_METRICS_DIR"
  fi
  
  # Load inline custom metrics from service config
  INLINE_METRICS=$(echo "$MONITORING_CONFIG" | yq eval '.customMetrics.metrics[]' - 2>/dev/null || echo "")
  if [[ -n "$INLINE_METRICS" ]]; then
    MERGED_CUSTOM_METRICS=$(echo -e "$MERGED_CUSTOM_METRICS\n$INLINE_METRICS")
  fi
  
  # Build final JSON structure
  FINAL_CUSTOM_METRICS_JSON=$(echo "$MERGED_CUSTOM_METRICS" | jq -s . 2>/dev/null || echo "[]")
  FINAL_ALERT_RULES_JSON=$(echo "$MERGED_ALERT_RULES" | jq -s . 2>/dev/null || echo "[]")
  
  # Substitute variables in base config
  MERGED_APP_CONFIG=$(echo "$BASE_APP_CONFIG" | sed "s/{SERVICE}/$SERVICE/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{ENVIRONMENT}/$ENV/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{TEAM}/$TEAM/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{COST_CENTER}/$COST_CENTER/g")
  MERGED_APP_CONFIG=$(echo "$MERGED_APP_CONFIG" | sed "s/{BUSINESS_UNIT}/$BUSINESS_UNIT/g")
  
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
    cost.service: ${SERVICE}
    cost.costCenter: ${COST_CENTER}
    cost.businessUnit: ${BUSINESS_UNIT}
data:
  application.json: |
    {
      "metadata": {
        "name": "${SERVICE}",
        "environment": "${ENV}",
        "team": "${TEAM}",
        "costCenter": "${COST_CENTER}",
        "businessUnit": "${BUSINESS_UNIT}"
      },
      "monitoring": $(echo "$MERGED_APP_CONFIG" | jq '.monitoring' 2>/dev/null || echo "{}"),
      "alertRules": ${FINAL_ALERT_RULES_JSON},
      "customMetrics": ${FINAL_CUSTOM_METRICS_JSON}
    }
EOF
}
```

---

## 7. Generated Output Example

### 7.1 Generated Dynatrace ConfigMap

**File**: `generated/payment-processor/prod/euw1/monitoring/dynatrace-app-config.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-processor-dynatrace-config
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
    monitoring.profile: domain-api
    monitoring.tool: dynatrace
    monitoring.primary: "true"
    cost.service: payment-processor
    cost.costCenter: COR-B
    cost.businessUnit: core-banking
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "prod",
        "team": "owner@company.com",
        "costCenter": "COR-B",
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
          "notificationChannels": ["teams-payment-processor", "owner@company.com"]
        },
        {
          "name": "PaymentSuccessRateLow",
          "enabled": true,
          "condition": "payment_success_rate < 95.0",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payment-processor", "owner@company.com"],
          "description": "Payment success rate dropped below 95%"
        },
        {
          "name": "FraudCheckLatencyHigh",
          "enabled": true,
          "condition": "fraud_check_latency > 500",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payment-processor", "owner@company.com"],
          "description": "Fraud check latency exceeds 500ms"
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
        }
      ]
    }
```

---

## 8. Dynatrace Sync Controller

### 8.1 Controller Implementation

**File**: `services/dynatrace-sync/sync.py`

```python
#!/usr/bin/env python3
"""
Dynatrace Sync Controller - Syncs monitoring profiles to Dynatrace SaaS
Watches ConfigMaps with monitoring.tool=dynatrace label and syncs to Dynatrace
"""

import json
import os
import time
from datetime import datetime
from kubernetes import client, config, watch
from dynatrace import Dynatrace

def sync_to_dynatrace():
    """
    Watch ConfigMap changes and sync to Dynatrace SaaS
    """
    
    # Load Kubernetes config
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    
    # Dynatrace client
    dt = Dynatrace(
        environment_id=os.getenv('DYNATRACE_ENV_ID'),
        api_token=os.getenv('DYNATRACE_API_TOKEN')
    )
    
    # Watch for ConfigMap changes
    w = watch.Watch()
    
    for event in w.stream(
        v1.list_namespaced_config_map,
        namespace="",
        label_selector="monitoring.tool=dynatrace,monitoring.primary=true",
        timeout_seconds=None
    ):
        cm = event['object']
        action = event['type']
        
        if action in ['ADDED', 'MODIFIED']:
            namespace = cm.metadata.namespace
            name = cm.metadata.name
            
            # Extract app config from ConfigMap
            app_config_json = cm.data.get('application.json')
            if not app_config_json:
                continue
            
            app_config = json.loads(app_config_json)
            service_name = app_config['metadata']['name']
            environment = app_config['metadata']['environment']
            
            # Sync to Dynatrace
            try:
                # Create or update Dynatrace application
                result = dt.create_or_update_application(
                    name=f"{service_name}-{environment}",
                    configuration=app_config
                )
                
                # Update ConfigMap with sync status
                cm.metadata.labels['dynatrace.sync.status'] = 'synced'
                cm.metadata.labels['dynatrace.sync.timestamp'] = str(datetime.now())
                cm.metadata.labels['dynatrace.application.id'] = result.get('applicationId', '')
                
                v1.patch_namespaced_config_map(
                    name=name,
                    namespace=namespace,
                    body=cm
                )
                
                print(f"✅ Synced {service_name} to Dynatrace")
                
            except Exception as e:
                print(f"❌ Failed to sync {service_name}: {e}")
                
                # Update ConfigMap with error status
                cm.metadata.labels['dynatrace.sync.status'] = 'failed'
                cm.metadata.labels['dynatrace.sync.error'] = str(e)
                
                v1.patch_namespaced_config_map(
                    name=name,
                    namespace=namespace,
                    body=cm
                )

if __name__ == "__main__":
    sync_to_dynatrace()
```

---

## 9. Complete Service Lifecycle with Monitoring

### 9.1 Step-by-Step Flow

**Step 1: Developer Onboards Service**

```yaml
# Backstage form filled:
Service Name: payment-processor
Monitoring Profile: domain-api
Custom Metrics: payment-business-metrics (from metrics-catalog)
```

**Step 2: Catalog Entry Created**

```yaml
# catalog/services.yaml
services:
  - name: payment-processor
    monitoringProfile: domain-api
    monitoring:
      dynatrace: true
      customMetrics:
        repository:
          url: https://github.com/company/metrics-catalog
          ref: v1.2.0
        profiles:
          - payment-business-metrics
```

**Step 3: CI/CD Profile Expansion**

```
1. Load base profile: domain-api
   → Dynatrace app structure
   → Standard alert rules
   → Standard request attributes

2. Fetch custom metrics: payment-business-metrics
   → Custom Dynatrace metrics
   → Custom alert rules

3. Merge: Base + Custom
   → Single Dynatrace ConfigMap

4. Substitute variables:
   → {SERVICE} → payment-processor
   → {ENVIRONMENT} → prod
   → {COST_CENTER} → COR-B
   → {BUSINESS_UNIT} → core-banking
```

**Step 4: Manifest Generation**

```
Generated: generated/payment-processor/prod/euw1/monitoring/dynatrace-app-config.yaml
  → Contains: Base profile + Custom metrics
  → Ready for deployment
```

**Step 5: Deployment**

```
Harness deploys service
  → Dynatrace ConfigMap deployed to cluster
  → Dynatrace Sync Controller detects ConfigMap
  → Syncs to Dynatrace SaaS
  → Application definition created/updated
```

**Step 6: Runtime Monitoring**

```
Dynatrace OneAgent (DaemonSet)
  → Auto-instruments Java application
  → Collects standard metrics (HTTP, DB, etc.)
  → Collects custom metrics (payment_transactions_total, etc.)
  → Sends to Dynatrace SaaS
  → Alerts fire based on rules
```

---

## 10. Observability Team Workflow

### 10.1 Adding Custom Metrics (Later)

**Scenario**: Observability team wants to add new custom metric for `payment-processor`

**Step 1: Create Custom Metric in Metrics Catalog**

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
      ],
      "alertRules": [
        {
          "name": "RevenueDrop",
          "enabled": true,
          "condition": "revenue_total < previous_day * 0.9",
          "targets": ["SERVICE"],
          "severity": "warning"
        }
      ]
    }
```

**Step 2: Commit and Tag**

```bash
cd metrics-catalog
git add services/payment-processor/payment-revenue-metrics.yaml
git commit -m "feat: Add revenue metrics for payment-processor"
git tag v1.3.0
git push origin main --tags
```

**Step 3: Update Service Definition (Optional)**

```yaml
# catalog/services.yaml
services:
  - name: payment-processor
    monitoring:
      customMetrics:
        repository:
          ref: v1.3.0  # Update to new version
        profiles:
          - payment-business-metrics
          - payment-revenue-metrics  # NEW
```

**Step 4: CI/CD Regenerates Manifests**

```
CI/CD detects catalog change
  → Fetches metrics-catalog v1.3.0
  → Merges new custom metrics
  → Regenerates Dynatrace ConfigMap
  → Commits to generated/
```

**Step 5: Deployment**

```
Harness deploys updated ConfigMap
  → Dynatrace Sync Controller syncs
  → New custom metrics available in Dynatrace
  → New alert rules active
```

**Key Point**: Observability team can add metrics **without touching platform-next repo** (if using existing profile reference) or with minimal change (updating ref version).

---

## 11. Prometheus/Grafana (Optional)

### 11.1 When You Might Need Prometheus

**Prometheus can be useful for**:
- ✅ Long-term metric storage (Dynatrace retention limits)
- ✅ Custom PromQL queries
- ✅ Integration with other tools
- ✅ Cost-effective metric storage

**But it's NOT required** for Dynatrace monitoring.

### 11.2 Optional Prometheus Setup

If you decide to add Prometheus later:

```yaml
# In monitoring profile
prometheus:
  enabled: false  # Set to true if needed
  primary: false
  purpose: "metric-collection-only"  # Not for alerting
  
  serviceMonitor:
    scrapeInterval: 30s
    path: /metrics
  
  # Prometheus only collects, doesn't alert
  # Alerts come from Dynatrace
```

**Note**: This is **optional** and can be added later without changing the core design.

---

## 12. Summary

### 12.1 Key Features

1. ✅ **Dynatrace Primary** - Full Dynatrace OneAgent monitoring
2. ✅ **Profile-Based** - Base templates in platform-next
3. ✅ **Custom Metrics as Code** - Service-specific metrics in metrics-catalog
4. ✅ **Observability Team Ownership** - Can add metrics independently
5. ✅ **Composable** - Mix profiles + custom metrics
6. ✅ **Business Context** - COR-B, core-banking, owner@company.com

### 12.2 Benefits

- ✅ **Separation of Concerns**: Platform team owns profiles, Observability team owns custom metrics
- ✅ **Independent Evolution**: Custom metrics can evolve without touching platform config
- ✅ **Versioning**: Pin to specific metric versions
- ✅ **Flexibility**: Add custom metrics later without service redeployment
- ✅ **Dynatrace-Focused**: Pure Dynatrace solution (no Prometheus required)

### 12.3 Implementation

1. ✅ Create `kustomize/monitoring/profiles/` structure
2. ✅ Define base profiles in `monitoring-profiles.yaml`
3. ✅ Create profile components (Dynatrace ConfigMap templates)
4. ✅ Enhance generation script to merge profiles + custom metrics
5. ✅ Support metrics-catalog repository references
6. ✅ Generate unified Dynatrace ConfigMap
7. ✅ Deploy Dynatrace Sync Controller
8. ✅ Deploy via Kustomize

---

**Document Status**: ✅ Complete Dynatrace-Focused Design

