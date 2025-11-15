# Custom Metrics as Code - Design & Implementation

## Executive Summary

This document describes how **custom application metrics, SLIs/SLOs, and observability configurations are defined as code** in a separate repository and composably applied to services in Platform-Next.

**Key Principles**:
- 📦 **Metrics as Code** - Version-controlled metric definitions
- 🔄 **Separate Repository** - Decouple metrics from config
- 🎯 **Composable** - Apply per service, per environment
- 🏗️ **Kustomize-Native** - Integrate with existing architecture
- 🔌 **Pluggable** - Easy to add new metrics without changing services

---

## 1. Why Separate Metrics Repository?

### The Problem

**If metrics are in platform-next repo**:
- ❌ Couples observability changes to config changes
- ❌ Different teams own metrics (observability team) vs config (platform team)
- ❌ Metrics evolve faster than infrastructure config
- ❌ Hard to reuse metrics across services
- ❌ Pollutes config repo with observability code

**Solution**: Separate `metrics-catalog` repository

### Benefits

| Benefit | Impact |
|---------|--------|
| **Separation of Concerns** | Observability team owns metrics repo |
| **Independent Evolution** | Update metrics without touching config |
| **Reusability** | Share metric definitions across services |
| **Versioning** | Pin to specific metric versions |
| **Testing** | Test metrics independently |
| **Composition** | Services reference metrics like components |

---

## 2. Architecture Overview

### Two-Repository Model

```
┌──────────────────────────────────────────────────────────────┐
│ Repo 1: platform-next (Config Management)                    │
├──────────────────────────────────────────────────────────────┤
│  • Service catalog                                            │
│  • Archetypes, components, overlays                          │
│  • Manifest generation                                        │
│  • References metrics from metrics-catalog                   │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 │ References (Git URL or OCI)
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Repo 2: metrics-catalog (Observability as Code)              │
├──────────────────────────────────────────────────────────────┤
│  • Metric definitions (ServiceMonitor, PrometheusRule)       │
│  • SLI/SLO definitions                                        │
│  • Grafana dashboards as code                                │
│  • Alert rules                                                │
│  • Metric profiles (golden signals, business metrics)        │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Metrics Catalog Repository Structure

### Directory Layout

```
metrics-catalog/
├── README.md
│
├── profiles/                    # Pre-defined metric bundles
│   ├── golden-signals/         # RED metrics (Rate, Errors, Duration)
│   │   ├── service-monitor.yaml
│   │   ├── recording-rules.yaml
│   │   ├── alert-rules.yaml
│   │   └── kustomization.yaml
│   │
│   ├── business-metrics/       # Business-specific metrics
│   │   ├── payment-metrics.yaml
│   │   ├── account-metrics.yaml
│   │   └── kustomization.yaml
│   │
│   ├── sre-sli/                # SLI/SLO tracking
│   │   ├── availability-sli.yaml
│   │   ├── latency-sli.yaml
│   │   └── kustomization.yaml
│   │
│   └── cost-metrics/           # Cost-related metrics
│       ├── resource-usage.yaml
│       └── kustomization.yaml
│
├── archetypes/                  # Metrics per archetype
│   ├── api/
│   │   ├── http-metrics.yaml        # HTTP request metrics
│   │   ├── grpc-metrics.yaml        # gRPC metrics
│   │   ├── latency-alerts.yaml      # Latency SLO alerts
│   │   └── kustomization.yaml
│   │
│   ├── listener/
│   │   ├── queue-metrics.yaml       # Queue depth, processing rate
│   │   ├── consumer-lag.yaml        # Consumer lag alerts
│   │   └── kustomization.yaml
│   │
│   └── job/
│       ├── job-metrics.yaml         # Job success/failure rate
│       └── kustomization.yaml
│
├── services/                    # Service-specific custom metrics
│   ├── payment-service/
│   │   ├── payment-success-rate.yaml
│   │   ├── fraud-detection-latency.yaml
│   │   ├── chargeback-count.yaml
│   │   └── kustomization.yaml
│   │
│   └── account-service/
│       ├── account-creation-rate.yaml
│       └── kustomization.yaml
│
├── dashboards/                  # Grafana dashboards as code
│   ├── api-service-dashboard.json
│   ├── listener-dashboard.json
│   └── team-overview-dashboard.json
│
└── environments/                # Environment-specific overrides
    ├── prod/
    │   ├── stricter-slos.yaml       # Tighter SLOs for prod
    │   └── kustomization.yaml
    └── int-stable/
        ├── relaxed-slos.yaml        # Looser SLOs for dev
        └── kustomization.yaml
```

---

## 4. Metric Definition Examples

### Profile: Golden Signals (RED Metrics)

**File**: `metrics-catalog/profiles/golden-signals/service-monitor.yaml`

```yaml
# ServiceMonitor - Tells Prometheus where to scrape
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-golden-signals
  labels:
    metrics.profile: golden-signals
spec:
  selector:
    matchLabels:
      app: app  # Will be replaced by actual service name
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
```

**File**: `metrics-catalog/profiles/golden-signals/recording-rules.yaml`

```yaml
# PrometheusRule - Recording rules (pre-compute aggregations)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: app-golden-signals-recording
  labels:
    metrics.profile: golden-signals
spec:
  groups:
    - name: golden_signals_recording
      interval: 30s
      rules:
        # Request Rate (requests per second)
        - record: service:http_requests:rate5m
          expr: |
            sum(rate(http_requests_total{service="APP_NAME"}[5m]))
            by (service, environment, method, status_code)
        
        # Error Rate (errors per second)
        - record: service:http_errors:rate5m
          expr: |
            sum(rate(http_requests_total{service="APP_NAME",status_code=~"5.."}[5m]))
            by (service, environment)
        
        # Error Ratio (errors / total requests)
        - record: service:http_error_ratio:rate5m
          expr: |
            sum(rate(http_requests_total{service="APP_NAME",status_code=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{service="APP_NAME"}[5m]))
        
        # Request Duration (p50, p95, p99)
        - record: service:http_request_duration_seconds:p50
          expr: |
            histogram_quantile(0.50,
              sum(rate(http_request_duration_seconds_bucket{service="APP_NAME"}[5m]))
              by (service, environment, le)
            )
        
        - record: service:http_request_duration_seconds:p95
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="APP_NAME"}[5m]))
              by (service, environment, le)
            )
        
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{service="APP_NAME"}[5m]))
              by (service, environment, le)
            )
```

**File**: `metrics-catalog/profiles/golden-signals/alert-rules.yaml`

```yaml
# PrometheusRule - Alerting rules
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: app-golden-signals-alerts
  labels:
    metrics.profile: golden-signals
spec:
  groups:
    - name: golden_signals_alerts
      interval: 30s
      rules:
        # High Error Rate Alert
        - alert: HighErrorRate
          expr: |
            service:http_error_ratio:rate5m{service="APP_NAME"} > 0.05
          for: 5m
          labels:
            severity: warning
            service: APP_NAME
            team: TEAM_NAME
          annotations:
            summary: "High error rate for {{ $labels.service }}"
            description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
            runbook_url: "https://runbooks.company.com/high-error-rate"
        
        # High Latency Alert (p95 > 500ms)
        - alert: HighLatency
          expr: |
            service:http_request_duration_seconds:p95{service="APP_NAME"} > 0.5
          for: 5m
          labels:
            severity: warning
            service: APP_NAME
            team: TEAM_NAME
          annotations:
            summary: "High latency for {{ $labels.service }}"
            description: "P95 latency is {{ $value }}s (threshold: 0.5s)"
        
        # Low Request Rate Alert (service down?)
        - alert: LowRequestRate
          expr: |
            service:http_requests:rate5m{service="APP_NAME"} < 1
          for: 10m
          labels:
            severity: critical
            service: APP_NAME
            team: TEAM_NAME
          annotations:
            summary: "Low request rate for {{ $labels.service }} - possible outage"
            description: "Request rate is {{ $value }} req/s (threshold: 1 req/s)"
```

**File**: `metrics-catalog/profiles/golden-signals/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - service-monitor.yaml
  - recording-rules.yaml
  - alert-rules.yaml

# These will be patched by consumer to replace APP_NAME and TEAM_NAME
```

---

### Service-Specific Custom Metrics

**File**: `metrics-catalog/services/payment-service/payment-success-rate.yaml`

```yaml
# Custom business metric for payment service
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-business-metrics
  labels:
    metrics.type: business
    metrics.service: payment-service
spec:
  groups:
    - name: payment_business_metrics
      interval: 30s
      rules:
        # Payment Success Rate
        - record: payment:success_rate:5m
          expr: |
            sum(rate(payment_transactions_total{status="success"}[5m]))
            /
            sum(rate(payment_transactions_total[5m]))
        
        # Payment Volume by Method
        - record: payment:volume_by_method:5m
          expr: |
            sum(rate(payment_transactions_total[5m]))
            by (payment_method)
        
        # Average Transaction Value
        - record: payment:avg_transaction_value:5m
          expr: |
            sum(rate(payment_transaction_value_sum[5m]))
            /
            sum(rate(payment_transactions_total[5m]))
        
        # Fraud Detection Rate
        - record: payment:fraud_detected_rate:5m
          expr: |
            sum(rate(fraud_checks_total{result="flagged"}[5m]))
            /
            sum(rate(fraud_checks_total[5m]))
        
        # Business SLI: Payment Success (99.9%)
        - alert: PaymentSuccessRateBelowSLO
          expr: |
            payment:success_rate:5m < 0.999
          for: 5m
          labels:
            severity: critical
            service: payment-service
            team: payments-team
            slo: payment-success
          annotations:
            summary: "Payment success rate below SLO"
            description: "Success rate is {{ $value | humanizePercentage }} (SLO: 99.9%)"
            impact: "Customers experiencing payment failures"
            action: "Check payment gateway, database connectivity"
```

---

## 5. Integration with Platform-Next

### Method 1: Kustomize Remote Bases (Recommended)

**In platform-next catalog**:

```yaml
# catalog/services.yaml
services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    
    # ================================================
    # METRICS CONFIGURATION (NEW)
    # ================================================
    metrics:
      # Metric profiles to apply (from metrics-catalog repo)
      profiles:
        - golden-signals        # Standard RED metrics
        - business-metrics      # Custom business metrics
        - sre-sli              # SLI/SLO tracking
      
      # Service-specific custom metrics
      custom:
        - payment-service      # From metrics-catalog/services/payment-service/
      
      # Environment-specific overrides
      overrides:
        prod:
          slo:
            availability: 99.99  # Stricter SLO for prod
            latencyP95: 200      # 200ms p95 in prod
        int-stable:
          slo:
            availability: 99.0   # Relaxed for dev
            latencyP95: 1000     # 1s acceptable in dev
      
      # Metric repository reference
      repository:
        url: https://github.com/company/metrics-catalog
        ref: v1.2.0  # Pin to version
```

**In generated kustomization.yaml**:

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  # Platform-next resources
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/prod
  - ../../../../kustomize/regions/euw1
  
  # ================================================
  # METRICS FROM REMOTE REPO (NEW)
  # ================================================
  # Kustomize can fetch from Git URLs
  - https://github.com/company/metrics-catalog/profiles/golden-signals?ref=v1.2.0
  - https://github.com/company/metrics-catalog/profiles/business-metrics?ref=v1.2.0
  - https://github.com/company/metrics-catalog/profiles/sre-sli?ref=v1.2.0
  - https://github.com/company/metrics-catalog/services/payment-service?ref=v1.2.0

components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa

# ================================================
# PATCHES - Customize metrics for this service
# ================================================
patches:
  # Replace APP_NAME placeholder with actual service name
  - target:
      kind: ServiceMonitor
    patch: |-
      - op: replace
        path: /spec/selector/matchLabels/app
        value: payment-service
  
  - target:
      kind: PrometheusRule
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          sum(rate(http_requests_total{service="payment-service"}[5m]))
          by (service, environment, method, status_code)
  
  # Apply prod-specific SLO thresholds
  - target:
      kind: PrometheusRule
      name: app-golden-signals-alerts
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          service:http_error_ratio:rate5m{service="payment-service"} > 0.0001
      - op: replace
        path: /spec/groups/0/rules/0/labels/slo
        value: "99.99"
      - op: replace
        path: /spec/groups/0/rules/1/expr
        value: |
          service:http_request_duration_seconds:p95{service="payment-service"} > 0.2
```

**How It Works**:
1. Kustomize fetches metrics from GitHub at specified version
2. Applies metrics to service
3. Patches replace placeholders (APP_NAME → payment-service)
4. Environment-specific SLO thresholds applied
5. Final manifest includes all metrics

---

### Method 2: OCI Registry (Advanced)

**Publish metrics to OCI registry**:

```bash
# In metrics-catalog repo CI/CD
cd metrics-catalog/profiles/golden-signals

# Package as OCI artifact
tar czf golden-signals.tar.gz *.yaml

# Push to OCI registry (GCP Artifact Registry)
crane push golden-signals.tar.gz \
  gcr.io/my-project/metrics/golden-signals:v1.2.0
```

**Reference in kustomization.yaml**:

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml
resources:
  # Pull metrics from OCI registry
  - oci://gcr.io/my-project/metrics/golden-signals:v1.2.0
  - oci://gcr.io/my-project/metrics/business-metrics:v1.2.0
  - oci://gcr.io/my-project/metrics/payment-service:v1.2.0
```

**Benefits**:
- ✅ Versioned and immutable
- ✅ Faster than Git (no clone needed)
- ✅ Works offline (cached locally)
- ✅ Standard container registry

---

## 6. Generation Script Integration

**Update**: `scripts/generate-kz-v3.sh`

```bash
#!/usr/bin/env bash
# Extended to include metrics

SERVICE=$1
ENV=$2
REGION=$3

# ... existing catalog loading ...

# ================================================
# LOAD METRICS CONFIGURATION
# ================================================
METRICS_CONFIG=$(echo "$SERVICE_DATA" | yq eval '.metrics // {}' -)
METRICS_PROFILES=$(echo "$METRICS_CONFIG" | yq eval '.profiles[]' - 2>/dev/null | tr '\n' ' ')
CUSTOM_METRICS=$(echo "$METRICS_CONFIG" | yq eval '.custom[]' - 2>/dev/null | tr '\n' ' ')
METRICS_REPO=$(echo "$METRICS_CONFIG" | yq eval '.repository.url' -)
METRICS_REF=$(echo "$METRICS_CONFIG" | yq eval '.repository.ref // "main"' -)

# ... existing kustomization generation ...

# ================================================
# ADD METRICS RESOURCES
# ================================================
if [[ -n "$METRICS_PROFILES" ]] || [[ -n "$CUSTOM_METRICS" ]]; then
  echo "" >> "$TMP_DIR/kustomization.yaml"
  echo "# Metrics from metrics-catalog repository" >> "$TMP_DIR/kustomization.yaml"
  
  # Add metric profiles
  for PROFILE in $METRICS_PROFILES; do
    echo "  - ${METRICS_REPO}/profiles/${PROFILE}?ref=${METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
  done
  
  # Add service-specific custom metrics
  for CUSTOM in $CUSTOM_METRICS; do
    echo "  - ${METRICS_REPO}/services/${CUSTOM}?ref=${METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
  done
  
  # Add archetype-specific metrics
  if [[ -n "$ARCHETYPE" ]]; then
    echo "  - ${METRICS_REPO}/archetypes/${ARCHETYPE}?ref=${METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
  fi
fi

# ================================================
# ADD METRIC PATCHES (Replace placeholders)
# ================================================
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

# Patches to customize metrics for this service
patches:
  # Replace APP_NAME with actual service name
  - target:
      kind: ServiceMonitor
    patch: |-
      - op: replace
        path: /spec/selector/matchLabels/app
        value: $SERVICE
  
  - target:
      kind: PrometheusRule
    patch: |-
      - op: test
        path: /spec/groups/0/rules/0/expr
        value: /APP_NAME/
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          \$(echo "\$expr" | sed "s/APP_NAME/$SERVICE/g")
EOF

# ================================================
# ADD ENVIRONMENT-SPECIFIC SLO PATCHES
# ================================================
SLO_AVAILABILITY=$(echo "$METRICS_CONFIG" | yq eval ".overrides.$ENV.slo.availability // 99.9" -)
SLO_LATENCY=$(echo "$METRICS_CONFIG" | yq eval ".overrides.$ENV.slo.latencyP95 // 500" -)

cat >> "$TMP_DIR/kustomization.yaml" <<EOF
  
  # Environment-specific SLO thresholds
  - target:
      kind: PrometheusRule
      name: app-golden-signals-alerts
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/annotations/slo
        value: "$SLO_AVAILABILITY"
      - op: replace
        path: /spec/groups/0/rules/1/expr
        value: |
          service:http_request_duration_seconds:p95{service="$SERVICE"} > $(echo "scale=3; $SLO_LATENCY / 1000" | bc)
EOF
```

---

## 7. Service-Specific Custom Metrics Example

### Payment Service Custom Metrics

**File**: `metrics-catalog/services/payment-service/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - payment-success-rate.yaml
  - fraud-detection-latency.yaml
  - chargeback-metrics.yaml
  - gateway-health.yaml
```

**File**: `metrics-catalog/services/payment-service/payment-success-rate.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-business-slo
  labels:
    metrics.type: business-slo
    metrics.service: payment-service
spec:
  groups:
    - name: payment_business_slo
      interval: 30s
      rules:
        # Recording: Payment Success Rate
        - record: payment:transactions:success_rate:5m
          expr: |
            sum(rate(payment_transactions_total{status="success",service="payment-service"}[5m]))
            /
            sum(rate(payment_transactions_total{service="payment-service"}[5m]))
        
        # Recording: Payment Volume
        - record: payment:transactions:volume:5m
          expr: |
            sum(rate(payment_transactions_total{service="payment-service"}[5m]))
        
        # Recording: Average Transaction Value
        - record: payment:transactions:avg_value:5m
          expr: |
            sum(rate(payment_transaction_value_sum{service="payment-service"}[5m]))
            /
            sum(rate(payment_transactions_total{service="payment-service"}[5m]))
        
        # Alert: Payment Success Rate below SLO (99.9%)
        - alert: PaymentSuccessRateBelowSLO
          expr: |
            payment:transactions:success_rate:5m < 0.999
          for: 5m
          labels:
            severity: critical
            service: payment-service
            team: payments-team
            slo_type: business
            impact: revenue
          annotations:
            summary: "Payment success rate below SLO"
            description: "Success rate: {{ $value | humanizePercentage }}, SLO: 99.9%"
            impact: "Revenue loss, customer experience degradation"
            estimated_revenue_impact: "${{ $value * 10000 }}/hour"  # Custom calculation
            runbook_url: "https://runbooks.company.com/payment-success-rate"
            teams_channel: "#team-payments"
            escalation: "page-payments-oncall"
        
        # Alert: Abnormal Payment Volume
        - alert: AbnormalPaymentVolume
          expr: |
            abs(payment:transactions:volume:5m - payment:transactions:volume:5m offset 1w) 
            / payment:transactions:volume:5m offset 1w > 0.5
          for: 10m
          labels:
            severity: warning
            service: payment-service
            team: payments-team
          annotations:
            summary: "Payment volume anomaly detected"
            description: "Volume changed {{ $value | humanizePercentage }} vs last week"
```

---

## 8. Environment-Specific SLO Overrides

**File**: `metrics-catalog/environments/prod/stricter-slos.yaml`

```yaml
# Production has stricter SLOs
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

patches:
  # Tighter error rate threshold for prod
  - target:
      kind: PrometheusRule
      labelSelector: "metrics.profile=golden-signals"
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          service:http_error_ratio:rate5m > 0.001  # 0.1% (was 5%)
      - op: replace
        path: /spec/groups/0/rules/0/labels/slo
        value: "99.99"
  
  # Tighter latency threshold for prod
  - target:
      kind: PrometheusRule
      labelSelector: "metrics.profile=golden-signals"
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/1/expr
        value: |
          service:http_request_duration_seconds:p95 > 0.2  # 200ms (was 500ms)
```

**File**: `metrics-catalog/environments/int-stable/relaxed-slos.yaml`

```yaml
# Int-stable has relaxed SLOs
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

patches:
  # More lenient error rate for dev
  - target:
      kind: PrometheusRule
      labelSelector: "metrics.profile=golden-signals"
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          service:http_error_ratio:rate5m > 0.1  # 10% (relaxed)
      - op: replace
        path: /spec/groups/0/rules/0/for
        value: 15m  # Longer before alerting
```

---

## 9. Alertmanager Configuration

**Route alerts to Teams based on labels**:

**File**: `metrics-catalog/alertmanager/config.yaml`

```yaml
# Alertmanager configuration
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'service', 'environment']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  
  routes:
    # Critical alerts → Teams + PagerDuty
    - matchers:
        - severity = critical
      receiver: 'teams-critical-pagerduty'
      continue: false
    
    # Warning alerts → Teams only
    - matchers:
        - severity = warning
      receiver: 'teams-warning'
      continue: false
    
    # Info alerts → Teams (low priority)
    - matchers:
        - severity = info
      receiver: 'teams-info'
      continue: false
    
    # Business SLO alerts → Special routing
    - matchers:
        - slo_type = business
      receiver: 'teams-business-slo'
      continue: false

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'https://cost-api.company.com/api/v1/alerts/default'
  
  - name: 'teams-critical-pagerduty'
    webhook_configs:
      # Send to Cloud Function for Teams routing
      - url: 'https://europe-west1-my-project.cloudfunctions.net/alert-to-teams'
        send_resolved: true
        http_config:
          headers:
            X-Alert-Severity: critical
      
      # Send to PagerDuty
      - url: 'https://events.pagerduty.com/v2/enqueue'
        send_resolved: true
        http_config:
          headers:
            X-Routing-Key: $PAGERDUTY_INTEGRATION_KEY
  
  - name: 'teams-warning'
    webhook_configs:
      - url: 'https://europe-west1-my-project.cloudfunctions.net/alert-to-teams'
        send_resolved: true
        http_config:
          headers:
            X-Alert-Severity: warning
  
  - name: 'teams-business-slo'
    webhook_configs:
      - url: 'https://europe-west1-my-project.cloudfunctions.net/alert-to-teams'
        send_resolved: true
        http_config:
          headers:
            X-Alert-Severity: critical
            X-Alert-Type: business-slo
```

---

## 10. Cloud Function: Alert to Teams

**File**: `cloud-functions/alert-to-teams/main.py`

```python
import functions_framework
import requests
import json
from google.cloud import bigquery

@functions_framework.http
def alert_to_teams(request):
    """
    Receives Prometheus alerts from Alertmanager
    Routes to appropriate Teams channels based on service config
    """
    
    alert_data = request.get_json()
    
    for alert in alert_data.get('alerts', []):
        service = alert['labels'].get('service')
        severity = alert['labels'].get('severity')
        team = alert['labels'].get('team')
        
        # Get Teams channel configuration from catalog
        bq_client = bigquery.Client()
        query = f"""
        SELECT
          s.teams as primary_channel,
          t.notifications.teams.secondary as secondary_channel,
          t.notifications.teams.critical as critical_channel
        FROM `cost_analytics.service_config` s
        JOIN `cost_analytics.team_config` t ON s.team = t.name
        WHERE s.service_name = '{service}'
        """
        
        result = list(bq_client.query(query).result())
        if not result:
            return {"status": "service not found"}, 404
        
        config = result[0]
        
        # Determine which channel(s) to notify
        teams_channels = [config.primary_channel]
        
        if severity == 'warning':
            teams_channels.append(config.secondary_channel)
        elif severity == 'critical':
            teams_channels.extend([config.secondary_channel, config.critical_channel])
        
        # Send to each channel
        for channel in teams_channels:
            webhook_url = get_teams_webhook_url(channel)
            send_alert_to_teams(webhook_url, alert)
    
    return {"status": "sent", "count": len(alert_data.get('alerts', []))}

def send_alert_to_teams(webhook_url, alert):
    """Format and send alert to Teams"""
    
    # Extract alert details
    labels = alert['labels']
    annotations = alert['annotations']
    
    # Color based on severity
    colors = {
        'info': '0078D4',
        'warning': 'FFA500',
        'critical': 'DC3545'
    }
    color = colors.get(labels.get('severity'), '0078D4')
    
    # Build Teams Adaptive Card
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color,
        "summary": annotations.get('summary', 'Alert'),
        "sections": [{
            "activityTitle": f"{'🚨' if labels.get('severity') == 'critical' else '⚠️'} {annotations.get('summary')}",
            "activitySubtitle": annotations.get('description'),
            "facts": [
                {"name": "Service", "value": labels.get('service')},
                {"name": "Environment", "value": labels.get('environment')},
                {"name": "Severity", "value": labels.get('severity', '').upper()},
                {"name": "Alert", "value": labels.get('alertname')},
            ],
            "text": annotations.get('action', '')
        }],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View in Grafana",
                "targets": [{
                    "os": "default",
                    "uri": f"https://grafana.company.com/d/{labels.get('service')}"
                }]
            },
            {
                "@type": "OpenUri",
                "name": "Runbook",
                "targets": [{
                    "os": "default",
                    "uri": annotations.get('runbook_url', 'https://runbooks.company.com')
                }]
            }
        ]
    }
    
    # Add business impact if present
    if 'estimated_revenue_impact' in annotations:
        card['sections'][0]['facts'].append({
            "name": "Revenue Impact",
            "value": annotations['estimated_revenue_impact']
        })
    
    response = requests.post(webhook_url, json=card)
    return response.status_code == 200
```

---

## 11. Metrics Catalog CI/CD

**File**: `metrics-catalog/.github/workflows/validate-and-publish.yml`

```yaml
name: Validate and Publish Metrics

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate PrometheusRule Syntax
        run: |
          # Use promtool to validate rules
          for file in $(find . -name "*-rules.yaml"); do
            promtool check rules $file
          done
      
      - name: Validate ServiceMonitor
        run: |
          # Validate against CRD schema
          kubectl apply --dry-run=client -f profiles/*/service-monitor.yaml
      
      - name: Lint PromQL Expressions
        run: |
          # Use promtool to lint expressions
          for file in $(find . -name "*-rules.yaml"); do
            yq eval '.spec.groups[].rules[].expr' $file | \
              promtool check metrics
          done
  
  publish:
    needs: validate
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Publish to OCI Registry
        run: |
          # Package each profile
          for profile in profiles/*; do
            name=$(basename $profile)
            tar czf ${name}.tar.gz -C $profile .
            
            # Push to GCP Artifact Registry
            crane push ${name}.tar.gz \
              gcr.io/my-project/metrics/${name}:${GITHUB_REF_NAME}
          done
      
      - name: Update Metrics Index
        run: |
          # Create index of available metrics
          ./scripts/generate-index.sh > metrics-index.yaml
          
          # Publish index
          gsutil cp metrics-index.yaml \
            gs://platform-next-artifacts/metrics/index.yaml
```

---

## 12. Usage in Backstage

### Service Onboarding Form (Updated)

```yaml
# backstage/templates/kubernetes-service.yaml (excerpt)

parameters:
  - title: Observability Configuration
    properties:
      metricProfiles:
        title: Metric Profiles
        type: array
        description: Select metric bundles to enable
        items:
          type: string
          enum:
            - golden-signals
            - business-metrics
            - sre-sli
            - cost-metrics
        default:
          - golden-signals
        uniqueItems: true
        ui:widget: checkboxes
      
      customMetrics:
        title: Custom Metrics (Optional)
        type: boolean
        description: Enable service-specific custom metrics?
        default: false
        ui:help: 'Only available for services with custom metric definitions'
      
      sloTargets:
        title: SLO Targets (Production)
        type: object
        description: Service Level Objective targets
        properties:
          availability:
            type: number
            title: Availability (%)
            default: 99.9
            minimum: 99.0
            maximum: 99.99
          latencyP95:
            type: number
            title: P95 Latency (ms)
            default: 500
            minimum: 100
            maximum: 5000
```

**Generated Service Definition**:

```yaml
# Backstage template creates this in catalog
services:
  - name: payment-service
    # ... standard config ...
    
    metrics:
      profiles:
        - golden-signals
        - business-metrics
      custom:
        - payment-service  # Service-specific metrics
      repository:
        url: https://github.com/company/metrics-catalog
        ref: v1.2.0
      overrides:
        prod:
          slo:
            availability: 99.9
            latencyP95: 500
```

---

## 13. Benefits of Metrics as Code

### Separation of Concerns

| Concern | Repository | Owner | Update Frequency |
|---------|-----------|-------|------------------|
| **Infrastructure Config** | platform-next | Platform team | Weekly |
| **Metrics Definitions** | metrics-catalog | Observability team | Daily |
| **Service Code** | app repos | App teams | Daily |

### Reusability

```
Golden Signals profile
  → Used by 80+ API services
  → Update once, affects all
  → Versioned (v1.0, v1.1, v1.2)
  → Services pin to version (stability)
```

### Flexibility

```
Service A: golden-signals + business-metrics + custom metrics
Service B: golden-signals only (simple)
Service C: golden-signals + sre-sli + custom metrics + third-party integrations
```

### Governance

```
Metrics catalog has:
  → Schema validation (CI)
  → PromQL linting
  → SLO templates (standardized)
  → Approval workflow (observability team reviews)
```

---

## 14. Complete Example: Payment Service

### In metrics-catalog Repo

```
metrics-catalog/
├── profiles/
│   └── golden-signals/
│       ├── service-monitor.yaml (scrape /metrics)
│       ├── recording-rules.yaml (RED metrics)
│       ├── alert-rules.yaml (error rate, latency)
│       └── kustomization.yaml
│
├── services/
│   └── payment-service/
│       ├── payment-success-rate.yaml (business SLO)
│       ├── fraud-detection.yaml (fraud rate tracking)
│       ├── gateway-health.yaml (payment gateway checks)
│       └── kustomization.yaml
│
└── environments/
    └── prod/
        └── stricter-slos.yaml (99.99% availability)
```

### In platform-next Repo

```yaml
# catalog/services.yaml
services:
  - name: payment-service
    archetype: api
    metrics:
      profiles: [golden-signals]
      custom: [payment-service]
      repository:
        url: https://github.com/company/metrics-catalog
        ref: v1.2.0
      overrides:
        prod:
          slo:
            availability: 99.99
```

### Generated Kustomization

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml
resources:
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/prod
  
  # Metrics from remote repo
  - https://github.com/company/metrics-catalog/profiles/golden-signals?ref=v1.2.0
  - https://github.com/company/metrics-catalog/services/payment-service?ref=v1.2.0
  - https://github.com/company/metrics-catalog/environments/prod?ref=v1.2.0

patches:
  # Replace APP_NAME → payment-service
  - target:
      kind: PrometheusRule
    patch: |-
      - op: replace
        path: /spec/groups/0/rules/0/expr
        value: |
          sum(rate(http_requests_total{service="payment-service"}[5m]))
```

### Final Manifests Include

```yaml
# ServiceMonitor for payment-service
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: payment-service
spec:
  selector:
    matchLabels:
      app: payment-service
  endpoints:
    - port: http
      path: /metrics

---
# PrometheusRule - Golden Signals
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-golden-signals
spec:
  groups:
    - name: payment_service_golden_signals
      rules:
        - alert: HighErrorRate
          expr: |
            service:http_error_ratio:rate5m{service="payment-service"} > 0.0001
          for: 5m
          labels:
            severity: critical
            slo: "99.99"

---
# PrometheusRule - Business Metrics
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-business-slo
spec:
  groups:
    - name: payment_business_slo
      rules:
        - alert: PaymentSuccessRateBelowSLO
          expr: |
            payment:transactions:success_rate:5m < 0.999
          for: 5m
          labels:
            severity: critical
            teams_channel: "#team-payments"
```

---

## 15. Advanced: Dynamic Metric Selection

### Intelligent Metric Selection Based on Archetype

**In generate-kz-v3.sh**:

```bash
# Auto-include archetype-specific metrics
if [[ "$ARCHETYPE" == "api" ]]; then
  METRICS_PROFILES="golden-signals sre-sli"
elif [[ "$ARCHETYPE" == "listener" ]]; then
  METRICS_PROFILES="queue-metrics consumer-lag-tracking"
elif [[ "$ARCHETYPE" == "job" ]]; then
  METRICS_PROFILES="job-completion-tracking batch-metrics"
fi

# Add to kustomization
for PROFILE in $METRICS_PROFILES; do
  echo "  - ${METRICS_REPO}/archetypes/${ARCHETYPE}?ref=${METRICS_REF}" >> "$TMP_DIR/kustomization.yaml"
done
```

**Archetype-Specific Metrics**:

```
api → HTTP metrics (request rate, latency, errors)
listener → Queue metrics (lag, processing rate, dead letters)
job → Job metrics (success rate, duration, failures)
scheduler → CronJob metrics (schedule adherence, job duration)
streaming → Connection metrics (active connections, message rate)
```

---

## 16. Summary & Integration

### How It All Works Together

```
┌─────────────────────────────────────────────────────────────┐
│ Developer onboards service in Backstage                     │
│   → Selects metric profiles (golden-signals)                │
│   → Sets SLO targets (99.9% availability, 500ms p95)        │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Catalog updated with metrics config                         │
│   metrics:                                                   │
│     profiles: [golden-signals]                               │
│     custom: [payment-service]                                │
│     repository: github.com/company/metrics-catalog           │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ CI generates manifests                                       │
│   → Fetches metrics from metrics-catalog repo (v1.2.0)      │
│   → Applies environment-specific SLO overrides               │
│   → Patches APP_NAME → payment-service                       │
│   → Commits ServiceMonitor + PrometheusRule to generated/   │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Harness deploys to Kubernetes                               │
│   → ServiceMonitor deployed (Prometheus starts scraping)    │
│   → PrometheusRule deployed (alerts active)                 │
│   → Metrics collected every 30s                              │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Alertmanager detects SLO breach                             │
│   → Routes to Cloud Function (alert-to-teams)               │
│   → Queries Teams channel config from catalog               │
│   → Sends to #team-payments, #platform-sre                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

✅ **Version Controlled** - Metrics in Git, immutable versions
✅ **Composable** - Mix and match metric profiles
✅ **Per-Service** - Custom metrics for specific services
✅ **Per-Environment** - Different SLOs for prod vs dev
✅ **Multi-Channel** - Teams + Email + PagerDuty
✅ **Configurable Thresholds** - Define your own alert levels
✅ **AI-Powered** - BigQuery ML for forecasting and anomaly detection
✅ **Zero Overhead** - GCP-native, fully managed

See complete design: [05_CUSTOM_METRICS_AS_CODE.md](file:///Users/visanth/Documents/copilot/platform-next/docs/05_CUSTOM_METRICS_AS_CODE.md)

**This enables teams to define custom business metrics, SLIs/SLOs, and alert rules as code, version them independently, and composably apply them per service and environment!** 📊🎯
