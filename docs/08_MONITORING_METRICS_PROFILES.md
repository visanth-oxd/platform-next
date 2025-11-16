# Monitoring Metrics Profiles - Complete Architecture

**Status**: ACTIVE - Design & Architecture

**Document Type**: Architecture + Technical Specification

**Audience**: Platform engineers, SRE teams, development teams, observability teams

**Date**: 2025-11-16

---

## Executive Summary

**Monitoring metrics are not an afterthought**—they are integrated into the platform using the **same profile-based pattern as cost management**.

Just as services reference `costProfile: standard-api-cost`, they will reference monitoring profiles:

```yaml
services:
  - name: payment-service
    archetype: api
    size: large
    
    # Cost configuration (existing)
    costProfile: standard-api-cost
    cost: {...}
    
    # MONITORING CONFIGURATION (NEW)
    monitoringProfile: api-observability
    monitoring:
      prometheus: true
      dynatrace: true
      overrides:
        prod:
          sloAvailability: 99.99
          sloLatencyP95ms: 200
```

**Key Principles**:
- ✅ **Templates over Repetition** - Reusable monitoring profiles for similar service types
- ✅ **Prometheus + Dynatrace** - Support both monitoring stacks simultaneously
- ✅ **As Code** - Metrics, alerts, and SLOs defined in version-controlled YAML
- ✅ **Size-Aware** - Automatic scaling of resource thresholds based on service size
- ✅ **Environment-Specific** - Different SLOs and alert thresholds for prod vs dev
- ✅ **Composable** - Mix and match base profiles with custom metrics
- ✅ **Zero Boilerplate** - Services specify only essential monitoring allocation parameters

---

## 1. The Problem

### Current State (Without Profiles)

Each service needs custom monitoring configuration:

```yaml
# BEFORE: Repetitive, lengthy, error-prone
services:
  - name: payment-service
    monitoring:
      prometheus:
        enabled: true
        serviceMonitor:
          scrapeInterval: 30s
          scrapeTimeout: 10s
          endpoints:
            - port: metrics
              path: /metrics
        recordingRules:
          - name: http:requests:rate5m
            expr: sum(rate(http_requests_total{service="payment-service"}[5m])) by (method, status)
          - name: http:errors:rate5m
            expr: sum(rate(http_requests_total{service="payment-service",status=~"5.."}[5m]))
          - name: http:latency:p95
            expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="payment-service"}[5m])) by (le))
        alertRules:
          - alert: HighErrorRate
            expr: service:http_errors:rate5m{service="payment-service"} > 0.05
            for: 5m
            annotations:
              summary: "High error rate for payment-service"
          - alert: HighLatency
            expr: service:http_latency:p95{service="payment-service"} > 0.5
            for: 5m
            annotations:
              summary: "High latency for payment-service"
      
      dynatrace:
        enabled: true
        applicationName: payment-service
        monitoredTechnologies: [java, http]
        requestAttributes:
          - name: service
            source:
              serviceTag: payment-service
          - name: costCenter
            source:
              kubernetesLabel: cost.costCenter
        requestNaming:
          pattern: "{RequestPath} [{RequestMethod}]"
        alertRules:
          - name: ErrorRateAnomaly
            enabled: true
            condition: "Comparison(GreaterThan, 0.05)"
            targets: ["SERVICE"]
          - name: DatabaseLatency
            enabled: true
            condition: "Comparison(GreaterThan, 500ms)"
            targets: ["DB"]
```

**Problems**:
- ❌ 50+ lines per service
- ❌ Duplicate Prometheus recording rules across services
- ❌ Duplicate Dynatrace application definitions
- ❌ Easy to introduce inconsistencies
- ❌ Catalog YAML becomes unmaintainable at scale
- ❌ No governance or standardization

### Solution: Monitoring Profiles

```yaml
# AFTER: Minimal specification, maximum clarity
services:
  - name: payment-service
    archetype: api
    size: large
    
    monitoringProfile: api-observability    # Use this template
    monitoring:
      prometheus: true
      dynatrace: true
      overrides:
        prod:
          sloAvailability: 99.99
          sloLatencyP95ms: 200
```

**Benefits**:
- ✅ 4 lines of monitoring config instead of 50+
- ✅ Consistency across 100+ services
- ✅ Profiles define best practices
- ✅ Easy to update all services by modifying profile
- ✅ Environment-specific SLOs via overrides
- ✅ Completely declarative

---

## 2. Monitoring Profiles Architecture

### 2.1 Core Components

```
Service Definition (services.yaml)
    ↓
    ├─ References: monitoringProfile: "api-observability"
    ├─ Specifies: size: "large" (for resource thresholds)
    ├─ Specifies: archetype: "api" (for metric type)
    └─ Provides: environment overrides (SLO adjustments)
    
         ↓
    
Monitoring Profile (monitoring-profiles.yaml)
    ├─ Prometheus configuration
    │  ├─ ServiceMonitor template
    │  ├─ Recording rules
    │  ├─ Alert rules
    │  └─ Metric collection intervals
    │
    ├─ Dynatrace configuration
    │  ├─ Application definition
    │  ├─ Monitored technologies
    │  ├─ Request attributes
    │  ├─ Alert rules
    │  └─ Custom metrics
    │
    ├─ SLO definitions
    │  ├─ Availability targets (99.9%, 99.99%)
    │  ├─ Latency targets (p50, p95, p99)
    │  ├─ Error rate targets
    │  └─ Custom business SLIs
    │
    └─ Environment overrides
       ├─ prod: stricter SLOs
       ├─ pre-stable: standard SLOs
       └─ int-stable: relaxed SLOs
    
         ↓
    
Expansion Engine (at validation time)
    ├─ Load profile configuration
    ├─ Calculate thresholds: base × size-multiplier × env-factor
    ├─ Substitute variables: {service}, {team}, {environment}
    ├─ Apply environment overrides
    └─ Generate complete monitoring config
    
         ↓
    
Generated Manifests
    ├─ Prometheus resources
    │  ├─ ServiceMonitor (tells Prometheus where to scrape)
    │  ├─ PrometheusRule (recording + alerting rules)
    │  └─ Grafana dashboard ConfigMap
    │
    └─ Dynatrace resources
       ├─ Dynatrace application definition
       ├─ Request attributes mapping
       └─ Custom metric definitions
    
         ↓
    
Deployment
    ├─ Prometheus scrapes service metrics (every 30s)
    ├─ Dynatrace OneAgent auto-instruments services
    ├─ Both systems collect in parallel
    └─ Alerts fire when thresholds crossed
```

### 2.2 Size-Based Thresholds

Services are sized (small, medium, large, xlarge, xxlarge) and monitoring thresholds scale:

```
Size Multiplier for Resource Thresholds:
├─ small:    0.5×  (half of base)
├─ medium:   1.0×  (base thresholds)
├─ large:    1.5×  (50% higher thresholds)
├─ xlarge:   2.0×  (2× base thresholds)
└─ xxlarge:  2.5×  (2.5× base thresholds)

Example: api-observability profile with "large" service
├─ Memory threshold: 512MB (base) × 1.5 = 768MB
├─ CPU threshold: 500m (base) × 1.5 = 750m
├─ Error rate threshold: 5% (base) × 1.0 = 5% (not scaled)
└─ Latency p95: 500ms (base) × 1.0 = 500ms (not scaled)
```

---

## 3. Monitoring Profiles Catalog

### 3.1 Available Profiles

```yaml
monitoringProfiles:
  
  # REST APIs - most common
  api-observability:
    description: "REST API monitoring (Prometheus + Dynatrace)"
    applicableArchetypes: [api]
    
  # Batch jobs - job-specific metrics
  batch-job-observability:
    description: "Batch job monitoring (success rate, duration)"
    applicableArchetypes: [job]
    
  # Event consumers - queue-based metrics
  event-listener-observability:
    description: "Event listener monitoring (lag, processing rate)"
    applicableArchetypes: [listener]
    
  # Background schedulers - cron-based
  scheduler-observability:
    description: "Scheduled job monitoring (schedule adherence)"
    applicableArchetypes: [scheduler]
    
  # Streaming services - connection + throughput
  streaming-observability:
    description: "Streaming service monitoring"
    applicableArchetypes: [streaming]
    
  # Database services - query performance
  database-observability:
    description: "Database service monitoring"
    applicableArchetypes: [database]
```

---

## 4. Complete Profile Example: API Observability

### 4.1 Profile Definition

```yaml
# kustomize/catalog/monitoring-profiles.yaml

monitoringProfiles:
  
  api-observability:
    description: "REST API with RED metrics + business SLOs"
    
    # ================================================
    # PROMETHEUS CONFIGURATION
    # ================================================
    prometheus:
      enabled: true
      
      # ServiceMonitor - tells Prometheus where to scrape
      serviceMonitor:
        scrapeInterval: 30s
        scrapeTimeout: 10s
        path: /metrics
        port: http
      
      # Recording Rules - pre-compute common aggregations
      recordingRules:
        # RED Metrics (Request Rate, Error rate, Duration)
        
        - name: "http:requests:rate5m"
          expr: |
            sum(rate(http_requests_total{service="{SERVICE}"}[5m]))
            by (method, status)
          labels:
            team: "{TEAM}"
            environment: "{ENVIRONMENT}"
        
        - name: "http:errors:rate5m"
          expr: |
            sum(rate(http_requests_total{service="{SERVICE}",status=~"5.."}[5m]))
          labels:
            team: "{TEAM}"
        
        - name: "http:error_ratio:rate5m"
          expr: |
            (sum(rate(http_requests_total{service="{SERVICE}",status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{service="{SERVICE}"}[5m]))) * 100
        
        - name: "http:latency:p50"
          expr: |
            histogram_quantile(0.50,
              sum(rate(http_request_duration_seconds_bucket{service="{SERVICE}"}[5m]))
              by (le)
            )
        
        - name: "http:latency:p95"
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="{SERVICE}"}[5m]))
              by (le)
            )
        
        - name: "http:latency:p99"
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{service="{SERVICE}"}[5m]))
              by (le)
            )
      
      # Alert Rules - define when to alert
      alertRules:
        
        # SLO: Error Rate (5% for dev, 1% for prod, 0.1% for critical)
        - name: "HighErrorRate"
          expr: |
            http:error_ratio:rate5m{service="{SERVICE}"} > {ERROR_RATE_THRESHOLD}
          for: 5m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
          description: |
            Error rate is {{ $value }}% (threshold: {ERROR_RATE_THRESHOLD}%)
        
        # SLO: High Latency (p95)
        - name: "HighLatency"
          expr: |
            http:latency:p95{service="{SERVICE}"} > {LATENCY_THRESHOLD_SECONDS}
          for: 10m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
          description: |
            P95 latency is {{ $value }}s (threshold: {LATENCY_THRESHOLD_SECONDS}s)
        
        # SLO: Service Unavailable (no requests)
        - name: "ServiceDown"
          expr: |
            http:requests:rate5m{service="{SERVICE}"} == 0
          for: 2m
          severity: critical
          channels:
            teams: ["#team-{SERVICE}", "#platform-sre"]
            pagerduty: true
          description: |
            Service {SERVICE} has no incoming requests (possible outage)
        
        # Resource Utilization
        - name: "HighMemoryUsage"
          expr: |
            container_memory_usage_bytes{pod=~"{SERVICE}.*"} / {MEMORY_THRESHOLD_BYTES} > 0.85
          for: 5m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
          description: |
            Memory usage is {{ $value | humanizePercentage }} (threshold: 85%)
        
        - name: "HighCpuUsage"
          expr: |
            rate(container_cpu_usage_seconds_total{pod=~"{SERVICE}.*"}[5m]) / {CPU_THRESHOLD_CORES} > 0.80
          for: 5m
          severity: warning
          channels:
            teams: ["#team-{SERVICE}"]
          description: |
            CPU usage is {{ $value | humanizePercentage }} (threshold: 80%)
    
    # ================================================
    # DYNATRACE CONFIGURATION
    # ================================================
    dynatrace:
      enabled: true
      
      # Application definition
      application:
        monitoredTechnologies:
          - java
          - http
          - databases
        
        # Request naming pattern
        requestNaming: "{RequestPath} [{RequestMethod}]"
        
        # Capture request attributes from Kubernetes
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
        
        # Custom metrics - business metrics
        customMetrics: []  # Service-specific
      
      # Dynatrace Alert Rules
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
          condition: "SlowQueries(200ms)"
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
    # SLO DEFINITIONS
    # ================================================
    slos:
      # Availability SLO (uptime)
      availability:
        baselineInt: 99.0      # Dev environment
        baselinePre: 99.5      # Pre-prod
        baselineProd: 99.9     # Production
        measurement:
          method: "errorBudget"
          errorBudget: 43.2    # minutes per month
      
      # Latency SLO (response time)
      latency:
        p50Baseline: 100       # milliseconds
        p95Baseline: 500       # milliseconds
        p99Baseline: 1000      # milliseconds
        measurement:
          method: "percentile"
      
      # Error Rate SLO
      errorRate:
        baselineInt: 5.0       # 5% errors OK in dev
        baselinePre: 1.0       # 1% errors OK in pre
        baselineProd: 0.1      # 0.1% errors OK in prod
      
      # Custom business SLOs (empty by default, per-service)
      custom: []
    
    # ================================================
    # RESOURCE THRESHOLDS (scaled by service size)
    # ================================================
    resourceThresholds:
      memory:
        base: 512              # MB (for medium service)
        scaled: true           # Scale by size multiplier
        warningPercent: 85
        criticalPercent: 95
      
      cpu:
        base: 500              # millicores (for medium service)
        scaled: true
        warningPercent: 80
        criticalPercent: 90
      
      disk:
        base: 10               # GB
        scaled: false          # Don't scale disk
        warningPercent: 85
        criticalPercent: 95
    
    # ================================================
    # ENVIRONMENT OVERRIDES
    # ================================================
    environmentOverrides:
      
      int-stable:
        # Dev environment: relaxed thresholds
        alertRules:
          - name: "HighErrorRate"
            expr: "http:error_ratio:rate5m{service=\"{SERVICE}\"} > 5.0"
          - name: "HighLatency"
            expr: "http:latency:p95{service=\"{SERVICE}\"} > 2.0"
        
        slos:
          availability: 99.0
          errorRate: 5.0
        
        resourceThresholds:
          memory:
            warningPercent: 90     # More lenient in dev
          cpu:
            warningPercent: 85
      
      pre-stable:
        # Pre-prod: standard thresholds (from profile base)
        # No overrides needed
      
      prod:
        # Production: strict thresholds
        alertRules:
          - name: "HighErrorRate"
            expr: "http:error_ratio:rate5m{service=\"{SERVICE}\"} > 0.1"
          - name: "HighLatency"
            expr: "http:latency:p95{service=\"{SERVICE}\"} > {LATENCY_P95_PROD_MS}ms"
        
        slos:
          availability: 99.9      # (or higher via override)
          errorRate: 0.1
        
        resourceThresholds:
          memory:
            warningPercent: 80     # Stricter in prod
          cpu:
            warningPercent: 75
```

### 4.2 Other Profile Examples

**Batch Job Profile:**

```yaml
  batch-job-observability:
    description: "Batch job monitoring (success rate, execution time)"
    
    prometheus:
      serviceMonitor:
        scrapeInterval: 60s     # Less frequent for batch jobs
        path: /metrics
      
      recordingRules:
        - name: "job:success_rate:1h"
          expr: |
            sum(rate(batch_job_success_total{job="{SERVICE}"}[1h]))
            /
            sum(rate(batch_job_total{job="{SERVICE}"}[1h]))
        
        - name: "job:execution_time:p95"
          expr: |
            histogram_quantile(0.95,
              sum(rate(batch_job_duration_seconds_bucket{job="{SERVICE}"}[1h]))
              by (le)
            )
      
      alertRules:
        - name: "BatchJobFailureRate"
          expr: "job:success_rate:1h{job=\"{SERVICE}\"} < 0.99"
          for: 10m
          severity: warning
        
        - name: "BatchJobTakingTooLong"
          expr: "job:execution_time:p95{job=\"{SERVICE}\"} > {DURATION_THRESHOLD_SECONDS}"
          for: 1h
          severity: warning
    
    slos:
      jobSuccess: 99.0          # 99% jobs must succeed
      executionTime: 3600       # seconds (1 hour max)
```

**Event Listener Profile:**

```yaml
  event-listener-observability:
    description: "Event listener monitoring (lag, throughput)"
    
    prometheus:
      recordingRules:
        - name: "listener:lag:current"
          expr: |
            kafka_consumer_lag_sum{consumer_group="{SERVICE}"}
        
        - name: "listener:throughput:rate5m"
          expr: |
            sum(rate(listener_messages_processed_total{listener="{SERVICE}"}[5m]))
        
        - name: "listener:error_rate:5m"
          expr: |
            sum(rate(listener_message_errors_total{listener="{SERVICE}"}[5m]))
      
      alertRules:
        - name: "HighConsumerLag"
          expr: "listener:lag:current{listener=\"{SERVICE}\"} > {LAG_THRESHOLD_MESSAGES}"
          for: 5m
          severity: warning
        
        - name: "ProcessingTooSlow"
          expr: "listener:throughput:rate5m{listener=\"{SERVICE}\"} < {THROUGHPUT_THRESHOLD}"
          for: 10m
          severity: warning
    
    slos:
      maxConsumerLag: 10000      # messages
      minThroughput: 100         # messages/second
```

---

## 5. Service Definition with Monitoring Profiles

### 5.1 Minimal Service Specification

```yaml
# kustomize/catalog/services.yaml

services:
  
  # Example 1: REST API
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # Cost profile (existing)
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice@company.com"
    
    # MONITORING PROFILE (NEW)
    monitoringProfile: api-observability
    monitoring:
      prometheus: true           # Enable Prometheus
      dynatrace: true            # Enable Dynatrace
      
      # Environment-specific SLO adjustments
      overrides:
        prod:
          sloAvailability: 99.99        # Even stricter than profile default
          sloErrorRate: 0.05            # 0.05% errors OK
          sloLatencyP95ms: 200          # p95 must be < 200ms
        int-stable:
          sloAvailability: 99.0         # Relaxed for dev
          resourceThresholdWarning: 90  # 90% instead of 80%
  
  # Example 2: Batch Job
  - name: data-export
    archetype: job
    profile: batch-job
    size: medium
    enabledIn: [int-stable, pre-stable, prod]
    
    costProfile: batch-job-cost
    cost: {...}
    
    monitoringProfile: batch-job-observability
    monitoring:
      prometheus: true
      dynatrace: false           # Dynatrace not needed for batch
      overrides:
        prod:
          jobSuccessRateSLO: 99.5
  
  # Example 3: Event Listener
  - name: order-processor
    archetype: listener
    profile: event-consumer
    size: xlarge
    enabledIn: [int-stable, pre-stable, prod]
    
    costProfile: standard-api-cost
    cost: {...}
    
    monitoringProfile: event-listener-observability
    monitoring:
      prometheus: true
      dynatrace: true
      overrides:
        prod:
          maxConsumerLag: 5000         # Tighter lag threshold
          minThroughputThreshold: 1000 # Higher throughput expected
```

### 5.2 What Gets Calculated

At validation time, the expansion engine calculates:

```
Profile: api-observability
Size: large (multiplier 1.5)
Environment: prod

↓

Calculated thresholds:
├─ Memory base: 512MB × 1.5 = 768MB
├─ CPU base: 500m × 1.5 = 750m
├─ Latency p95: 500ms (not scaled)
├─ Error rate: 0.1% (from prod override)
├─ Availability SLO: 99.99% (from prod override)
└─ Resource warning: 80% (from prod override)

Variable substitution:
├─ {SERVICE} → payment-service
├─ {TEAM} → payments-team
├─ {ENVIRONMENT} → prod
└─ {ERROR_RATE_THRESHOLD} → 0.1
```

---

## 6. Integration Architecture

### 6.1 Manifest Generation Flow

```
┌──────────────────────────────────────────────┐
│ Service Definition (services.yaml)            │
├──────────────────────────────────────────────┤
│ - name: payment-service                       │
│ - monitoringProfile: api-observability        │
│ - size: large                                 │
│ - monitoring:                                 │
│     prometheus: true                          │
│     dynatrace: true                           │
│     overrides:                                │
│       prod:                                   │
│         sloAvailability: 99.99                │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Monitoring Profiles Catalog                  │
├──────────────────────────────────────────────┤
│ api-observability:                            │
│   prometheus: {...recording rules, alerts}    │
│   dynatrace: {...app def, custom metrics}     │
│   slos: {...availability, latency targets}    │
│   environmentOverrides: {...prod-specific}    │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Expansion Engine (CI/CD)                      │
├──────────────────────────────────────────────┤
│ 1. Load monitoring profile                    │
│ 2. Apply size multipliers (1.5×)              │
│ 3. Apply environment overrides (prod)         │
│ 4. Substitute variables ({SERVICE}, {TEAM})   │
│ 5. Generate complete monitoring config        │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Generated Manifests (Git - Versioned)         │
├──────────────────────────────────────────────┤
│ - ServiceMonitor (payment-service)            │
│ - PrometheusRule (recording rules)            │
│ - PrometheusRule (alert rules)                │
│ - Dynatrace app definition                    │
│ - Grafana dashboard ConfigMap                 │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Harness Deployment                           │
├──────────────────────────────────────────────┤
│ Deploy to Kubernetes:                         │
│ - ServiceMonitor → Prometheus operator        │
│ - PrometheusRule → Prometheus operator        │
│ - Dynatrace config → OneAgent DaemonSet       │
│ - Grafana dashboard → ConfigMap               │
└────────────┬─────────────────────────────────┘
             ↓
┌──────────────────────────────────────────────┐
│ Monitoring Begins                            │
├──────────────────────────────────────────────┤
│ Prometheus:                                   │
│ - Scrapes /metrics every 30s                  │
│ - Stores time-series data                     │
│ - Evaluates alert rules every 30s             │
│ - Fires alerts when threshold crossed         │
│                                               │
│ Dynatrace:                                    │
│ - OneAgent instruments all calls              │
│ - Captures distributed traces                 │
│ - Sends to Dynatrace SaaS                     │
│ - Evaluates anomaly detection                 │
│ - Fires alerts when anomalies detected        │
└──────────────────────────────────────────────┘
```

### 6.2 Prometheus + Dynatrace Coexistence

Both monitoring systems work in parallel:

```
Service (payment-service)
    │
    ├─ Prometheus Agent (sidecar or embedded)
    │   └─ Exposes metrics on :9090/metrics (or custom port)
    │       ├─ http_requests_total (counter)
    │       ├─ http_request_duration_seconds (histogram)
    │       ├─ http_requests_in_flight (gauge)
    │       └─ custom_payment_success_total (custom)
    │
    ├─ Dynatrace OneAgent (DaemonSet)
    │   └─ Auto-instruments Java/HTTP/DB
    │       ├─ Captures all HTTP requests
    │       ├─ Traces distributed calls
    │       ├─ Monitors database queries
    │       └─ Detects anomalies
    │
    └─ Application Logs
        └─ Structured logging (JSON)
            └─ Correlated with traces

Both metrics flow to their respective backends:
├─ Prometheus → Time-series database (local or external)
│   └─ Queryable via PromQL
│   └─ Used for alerting (PrometheusRule)
│   └─ Grafana dashboards
│
└─ Dynatrace → Dynatrace SaaS
    └─ Real-user monitoring
    └─ Application performance monitoring
    └─ Full-stack observability
    └─ Anomaly detection engine
```

---

## 7. Prometheus Configuration (Detailed)

### 7.1 Generated ServiceMonitor

```yaml
# generated/payment-service/prod/euw1/monitoring/service-monitor.yaml

apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: payment-service-monitor
  namespace: payment-service
  labels:
    app: payment-service
    monitoring.profile: api-observability
spec:
  selector:
    matchLabels:
      app: payment-service
  
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
      
      # Relabel to add service metadata
      relabelings:
        - sourceLabels: [__meta_kubernetes_pod_label_app]
          targetLabel: service
        - sourceLabels: [__meta_kubernetes_pod_label_cost_team]
          targetLabel: team
        - sourceLabels: [__meta_kubernetes_pod_label_cost_environment]
          targetLabel: environment
        - sourceLabels: [__meta_kubernetes_pod_label_cost_costCenter]
          targetLabel: costCenter
```

### 7.2 Generated PrometheusRule (Recording Rules)

```yaml
# generated/payment-service/prod/euw1/monitoring/prometheus-rules-recording.yaml

apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-recording-rules
  namespace: payment-service
  labels:
    app: payment-service
    monitoring.profile: api-observability
    prometheus: kube-prometheus
spec:
  groups:
    - name: payment_service_recording
      interval: 30s
      
      rules:
        # Request Rate
        - record: payment:http_requests:rate5m
          expr: |
            sum(rate(http_requests_total{service="payment-service"}[5m]))
            by (method, status)
          labels:
            team: payments-team
            environment: prod
        
        # Error Rate
        - record: payment:http_errors:rate5m
          expr: |
            sum(rate(http_requests_total{service="payment-service",status=~"5.."}[5m]))
        
        # Error Ratio (%)
        - record: payment:http_error_ratio:rate5m
          expr: |
            (sum(rate(http_requests_total{service="payment-service",status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total{service="payment-service"}[5m]))) * 100
        
        # Latency Percentiles
        - record: payment:http_latency:p50
          expr: |
            histogram_quantile(0.50,
              sum(rate(http_request_duration_seconds_bucket{service="payment-service"}[5m]))
              by (le)
            )
        
        - record: payment:http_latency:p95
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="payment-service"}[5m]))
              by (le)
            )
        
        - record: payment:http_latency:p99
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{service="payment-service"}[5m]))
              by (le)
            )
```

### 7.3 Generated PrometheusRule (Alert Rules)

```yaml
# generated/payment-service/prod/euw1/monitoring/prometheus-rules-alerts.yaml

apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: payment-service-alert-rules
  namespace: payment-service
  labels:
    app: payment-service
    monitoring.profile: api-observability
    prometheus: kube-prometheus
    severity: warning
spec:
  groups:
    - name: payment_service_alerts
      interval: 30s
      
      rules:
        
        # Alert 1: High Error Rate (SLO violation)
        - alert: PaymentServiceHighErrorRate
          expr: |
            payment:http_error_ratio:rate5m > 0.05
          for: 5m
          labels:
            severity: warning
            service: payment-service
            team: payments-team
            environment: prod
            slo: "error-rate"
          annotations:
            summary: "High error rate for payment-service"
            description: "Error rate is {{ $value }}% (threshold: 0.05%)"
            runbook_url: "https://runbooks.company.com/payment-service/high-error-rate"
            impact: "Customers experiencing payment failures"
            action: "Check error logs, verify payment gateway connectivity"
        
        # Alert 2: High Latency (SLO violation)
        - alert: PaymentServiceHighLatency
          expr: |
            payment:http_latency:p95 > 0.2
          for: 10m
          labels:
            severity: warning
            service: payment-service
            team: payments-team
            environment: prod
            slo: "latency-p95"
          annotations:
            summary: "High p95 latency for payment-service"
            description: "P95 latency is {{ $value }}s (threshold: 0.2s)"
            runbook_url: "https://runbooks.company.com/payment-service/high-latency"
            action: "Check database queries, review service logs for bottlenecks"
        
        # Alert 3: Service Down
        - alert: PaymentServiceDown
          expr: |
            payment:http_requests:rate5m == 0
          for: 2m
          labels:
            severity: critical
            service: payment-service
            team: payments-team
            environment: prod
          annotations:
            summary: "Payment service is down (no requests)"
            description: "No incoming requests detected for 2 minutes"
            runbook_url: "https://runbooks.company.com/payment-service/service-down"
            action: "Check service status, verify dependencies"
        
        # Alert 4: High Memory Usage
        - alert: PaymentServiceHighMemory
          expr: |
            (container_memory_usage_bytes{pod=~"payment-service.*"} / 768000000) > 0.85
          for: 5m
          labels:
            severity: warning
            service: payment-service
            team: payments-team
            resource: memory
          annotations:
            summary: "High memory usage for payment-service"
            description: "Memory at {{ $value | humanizePercentage }} (threshold: 85%)"
            action: "Check for memory leaks, consider pod upgrade"
        
        # Alert 5: High CPU Usage
        - alert: PaymentServiceHighCpu
          expr: |
            (rate(container_cpu_usage_seconds_total{pod=~"payment-service.*"}[5m]) / 0.750) > 0.80
          for: 5m
          labels:
            severity: warning
            service: payment-service
            team: payments-team
            resource: cpu
          annotations:
            summary: "High CPU usage for payment-service"
            description: "CPU at {{ $value | humanizePercentage }} (threshold: 80%)"
            action: "Investigate slow queries, check for CPU spikes"
```

---

## 8. Dynatrace Configuration (Detailed)

### 8.1 Application Definition

Dynatrace application definitions are stored as ConfigMap and synced via custom controller:

```yaml
# generated/payment-service/prod/euw1/monitoring/dynatrace-app-config.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-service-dynatrace-config
  namespace: payment-service
  labels:
    app: payment-service
    monitoring.profile: api-observability
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-service",
        "environment": "prod",
        "team": "payments-team",
        "costCenter": "CC-12345"
      },
      
      "monitoring": {
        "technologies": [
          "java",
          "http",
          "databases"
        ],
        
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
          "notificationChannels": ["teams-payments-team"]
        },
        {
          "name": "LatencyAnomaly",
          "enabled": true,
          "condition": "Anomaly(ResponseTime)",
          "targets": ["SERVICE"],
          "severity": "warning",
          "notificationChannels": ["teams-payments-team"]
        },
        {
          "name": "DatabaseSlowQueries",
          "enabled": true,
          "condition": "SlowDatabaseQueries(200ms)",
          "targets": ["DATABASE"],
          "severity": "warning",
          "notificationChannels": ["teams-payments-team"]
        },
        {
          "name": "ServiceCrash",
          "enabled": true,
          "condition": "CrashDetection",
          "targets": ["SERVICE"],
          "severity": "critical",
          "notificationChannels": ["teams-payments-team", "pagerduty-oncall"]
        }
      ],
      
      "customMetrics": [
        {
          "name": "payment_transactions_total",
          "type": "counter",
          "description": "Total payment transactions processed"
        },
        {
          "name": "payment_success_rate",
          "type": "gauge",
          "description": "Payment success rate percentage"
        },
        {
          "name": "fraud_check_latency",
          "type": "histogram",
          "description": "Fraud check latency in milliseconds"
        }
      ]
    }
```

### 8.2 Dynatrace Sync Controller

A custom Kubernetes controller syncs monitoring-profiles to Dynatrace:

```python
# services/dynatrace-sync/sync.py

#!/usr/bin/env python3
"""
Dynatrace Sync Controller - Syncs monitoring profiles to Dynatrace
"""

import json
import os
from kubernetes import client, config, watch
from dynatrace import Dynatrace

def sync_monitoring_config():
    """
    Watch ServiceMonitor and PrometheusRule changes,
    Sync corresponding Dynatrace application definitions
    """
    
    # Load Kubernetes config
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    
    # Dynatrace client
    dt = Dynatrace(
        environment_id=os.getenv('DYNATRACE_ENV_ID'),
        api_token=os.getenv('DYNATRACE_API_TOKEN')
    )
    
    # Watch for ConfigMap changes (monitoring config)
    w = watch.Watch()
    
    for event in w.stream(
        v1.list_namespaced_config_map,
        namespace="",
        label_selector="monitoring.profile",
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
                result = dt.create_or_update_application(
                    name=f"{service_name}-{environment}",
                    configuration=app_config
                )
                
                print(f"✅ Synced {service_name} to Dynatrace")
                
                # Update ConfigMap with sync status
                cm.metadata.labels = cm.metadata.labels or {}
                cm.metadata.labels['dynatrace.sync.status'] = 'synced'
                cm.metadata.labels['dynatrace.sync.timestamp'] = str(datetime.now())
                
                v1.patch_namespaced_config_map(
                    name, namespace, cm
                )
            
            except Exception as e:
                print(f"❌ Failed to sync {service_name}: {str(e)}")
                cm.metadata.labels['dynatrace.sync.status'] = 'failed'
                v1.patch_namespaced_config_map(name, namespace, cm)

if __name__ == '__main__':
    sync_monitoring_config()
```

---

## 9. Generated Grafana Dashboard

### 9.1 Dashboard as Code

```yaml
# generated/payment-service/prod/euw1/monitoring/grafana-dashboard.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-service-dashboard
  namespace: payment-service
  labels:
    grafana_dashboard: "1"
data:
  payment-service-dashboard.json: |
    {
      "dashboard": {
        "title": "Payment Service - Production",
        "tags": ["payment-service", "prod", "api"],
        "timezone": "UTC",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "payment:http_requests:rate5m"
              }
            ],
            "type": "graph"
          },
          {
            "title": "Error Rate",
            "targets": [
              {
                "expr": "payment:http_error_ratio:rate5m"
              }
            ],
            "type": "graph",
            "alert": {
              "conditions": [
                {
                  "evaluator": { "params": [0.05], "type": "gt" }
                }
              ]
            }
          },
          {
            "title": "Latency (p50, p95, p99)",
            "targets": [
              {
                "expr": "payment:http_latency:p50",
                "legendFormat": "p50"
              },
              {
                "expr": "payment:http_latency:p95",
                "legendFormat": "p95"
              },
              {
                "expr": "payment:http_latency:p99",
                "legendFormat": "p99"
              }
            ],
            "type": "graph"
          },
          {
            "title": "Memory Usage",
            "targets": [
              {
                "expr": "container_memory_usage_bytes{pod=~\"payment-service.*\"} / 768000000"
              }
            ],
            "type": "gauge",
            "thresholds": "0,0.85,0.95"
          }
        ]
      }
    }
```

---

## 10. Validation & CI/CD

### 10.1 Schema Validation

```yaml
# kustomize/schemas/monitoring-profile-schema.yaml

type: object
properties:
  monitoringProfile:
    type: string
    enum:
      - api-observability
      - batch-job-observability
      - event-listener-observability
      - scheduler-observability
      - streaming-observability
      - database-observability
  
  monitoring:
    type: object
    required: [prometheus, dynatrace]
    properties:
      prometheus:
        type: boolean
      dynatrace:
        type: boolean
      overrides:
        type: object
        properties:
          int-stable:
            $ref: "#/definitions/environmentOverrides"
          pre-stable:
            $ref: "#/definitions/environmentOverrides"
          prod:
            $ref: "#/definitions/environmentOverrides"

definitions:
  environmentOverrides:
    type: object
    properties:
      sloAvailability:
        type: number
        minimum: 99.0
        maximum: 99.99
      sloErrorRate:
        type: number
        minimum: 0.01
        maximum: 10.0
      sloLatencyP95ms:
        type: number
        minimum: 50
        maximum: 5000
```

### 10.2 CI/CD Validation Script

```bash
#!/bin/bash
# scripts/validate-monitoring-profiles.sh

set -e

echo "🔍 Validating monitoring profiles..."

# 1. Validate YAML syntax
echo "  ✓ Checking YAML syntax..."
for file in kustomize/catalog/monitoring-profiles.yaml; do
    yq eval '.' "$file" > /dev/null || {
        echo "    ❌ Invalid YAML in $file"
        exit 1
    }
done

# 2. Validate PromQL expressions
echo "  ✓ Checking PromQL syntax..."
PROFILES=$(yq eval '.monitoringProfiles | keys | .[]' kustomize/catalog/monitoring-profiles.yaml)

for PROFILE in $PROFILES; do
    RULES=$(yq eval ".monitoringProfiles.$PROFILE.prometheus.alertRules" kustomize/catalog/monitoring-profiles.yaml)
    
    if [[ "$RULES" != "null" ]]; then
        echo "    Validating rules in $PROFILE..."
        
        # Check each PromQL expression
        COUNT=$(echo "$RULES" | yq eval 'length' -)
        for ((i=0; i<$COUNT; i++)); do
            EXPR=$(echo "$RULES" | yq eval ".[$i].expr" -)
            
            # Use promtool to validate
            echo "$EXPR" | promtool check metrics || {
                echo "    ❌ Invalid PromQL in $PROFILE, rule $i"
                exit 1
            }
        done
    fi
done

# 3. Validate profile references in services
echo "  ✓ Checking service profile references..."
SERVICES=$(yq eval '.services[] | select(.monitoringProfile) | .name' kustomize/catalog/services.yaml)

for SERVICE in $SERVICES; do
    PROFILE=$(yq eval ".services[] | select(.name == \"$SERVICE\") | .monitoringProfile" kustomize/catalog/services.yaml)
    
    # Check if profile exists
    EXISTS=$(yq eval ".monitoringProfiles | has(\"$PROFILE\")" kustomize/catalog/monitoring-profiles.yaml)
    
    if [[ "$EXISTS" != "true" ]]; then
        echo "    ❌ Service $SERVICE references non-existent profile: $PROFILE"
        exit 1
    fi
done

# 4. Validate environment overrides
echo "  ✓ Checking environment overrides..."
PROFILES=$(yq eval '.monitoringProfiles | keys | .[]' kustomize/catalog/monitoring-profiles.yaml)

for PROFILE in $PROFILES; do
    ENVS=$(yq eval ".monitoringProfiles.$PROFILE.environmentOverrides | keys | .[]" kustomize/catalog/monitoring-profiles.yaml 2>/dev/null || true)
    
    for ENV in $ENVS; do
        if [[ ! "$ENV" =~ ^(int-stable|pre-stable|prod)$ ]]; then
            echo "    ❌ Invalid environment '$ENV' in profile $PROFILE"
            echo "       Valid environments: int-stable, pre-stable, prod"
            exit 1
        fi
    done
done

echo "✅ All monitoring profiles validated successfully"
```

---

## 11. Onboarding Flow (With Monitoring)

### 11.1 Backstage Form (Updated)

```yaml
# backstage/templates/kubernetes-service.yaml (excerpt)

parameters:
  
  - title: Service Configuration
    properties:
      # ... existing fields (name, type, archetype, size) ...
  
  - title: Cost Configuration
    properties:
      # ... existing cost fields ...
  
  - title: Monitoring Configuration (NEW)
    properties:
      
      monitoringProfile:
        title: Monitoring Profile
        type: string
        description: Select monitoring template for your service
        enum:
          - api-observability
          - batch-job-observability
          - event-listener-observability
          - scheduler-observability
          - streaming-observability
        default: api-observability
        ui:widget: select
      
      enablePrometheus:
        title: Enable Prometheus
        type: boolean
        description: Collect metrics via Prometheus
        default: true
        ui:help: "Required for alerts and Grafana dashboards"
      
      enableDynatrace:
        title: Enable Dynatrace
        type: boolean
        description: Enable Dynatrace monitoring (optional, requires license)
        default: false
        ui:help: "Provides full-stack APM and real-user monitoring"
      
      prodSloAvailability:
        title: Production Availability SLO (%)
        type: number
        description: Target availability for production
        default: 99.9
        minimum: 99.0
        maximum: 99.99
        multipleOf: 0.01
        ui:help: "99.9 = 43 minutes downtime/month"
      
      prodLatencyP95Ms:
        title: Production Latency SLO (p95, ms)
        type: number
        description: Target p95 response time for production
        default: 500
        minimum: 50
        maximum: 5000
        ui:help: "Time to complete 95% of requests"
```

### 11.2 Generated Service Definition

When service is created via Backstage:

```yaml
# Added to kustomize/catalog/services.yaml
services:
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # Cost (existing)
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice@company.com"
    
    # Monitoring (NEW)
    monitoringProfile: api-observability
    monitoring:
      prometheus: true
      dynatrace: false  # Not enabled in this example
      overrides:
        prod:
          sloAvailability: 99.99
          sloLatencyP95ms: 200
```

---

## 12. Deployment Timeline

```
Day 1 - Service Creation
├─ 9:00 AM - Developer fills Backstage form
│   └─ Selects: monitoringProfile: api-observability
│   └─ Specifies: prometheus: true, dynatrace: false
│   └─ Sets SLOs: 99.9% availability, 500ms p95
│
├─ 9:15 AM - CI/CD Validation
│   └─ ✓ Monitoring profile exists
│   └─ ✓ PromQL syntax valid
│   └─ ✓ SLO values in valid range
│
└─ 9:20 AM - Merge to Main
   └─ Catalog updated with monitoring config

Day 1 - Manifest Generation
├─ 2:00 PM - Developer initiates first deployment
│
├─ 2:05 PM - CI generates Kubernetes manifests
│   ├─ Expands monitoring profile
│   ├─ Creates ServiceMonitor (Prometheus scrape config)
│   ├─ Creates PrometheusRule (recording + alert rules)
│   ├─ Creates Dynatrace app config
│   └─ Commits to generated/ directory (versioned)
│
└─ 2:08 PM - Manifests ready for deployment

Day 1 - Deployment to Production
├─ 2:10 PM - Harness deploys to GKE
│   ├─ ServiceMonitor deployed → Prometheus operator picks up
│   ├─ PrometheusRule deployed → Prometheus evaluates alerts
│   ├─ Dynatrace config deployed → OneAgent configured
│   └─ Grafana dashboard ConfigMap deployed
│
└─ 2:15 PM - Monitoring begins
   ├─ Prometheus scrapes /metrics every 30s
   ├─ Recording rules calculated every 30s
   ├─ Alerts armed and monitoring (threshold checks active)
   └─ Dynatrace OneAgent collecting traces

Days 2+ - Monitoring Active
├─ Prometheus metrics visible in Grafana (real-time)
├─ Dynatrace APM dashboard active
├─ Alerts fire when SLO thresholds crossed:
│  ├─ 80% error rate threshold → Warning to #team-payment-service
│  ├─ 95% resource utilization → Warning to team
│  └─ 0.1% error rate (critical) → Critical alert to team + PagerDuty
├─ SLO tracking begins
└─ Cost + Monitoring data available together for optimization
```

---

## 13. Advantages Over Non-Templated Approach

| Aspect | Without Profiles | With Profiles |
|--------|-----------------|---------------|
| **Lines per service** | 50-100 | 4-6 |
| **Consistency** | Manual (error-prone) | Guaranteed (templated) |
| **Profile changes** | Update 100 services | Update 1 profile |
| **SLO updates** | Manual per service | Environment override in profile |
| **New metric addition** | Add to 100 services | Add to profile (affects all) |
| **Validation** | Manual review | Automated schema + PromQL checks |
| **Onboarding time** | 30+ minutes | 2 minutes (Backstage form) |
| **Governance** | No standardization | Central standards |

---

## 14. Integration with Cost Profiles

Monitoring and Cost are complementary:

```
Service: payment-service
├─ Archetype: api
├─ Size: large
│
├─ Cost Profile (existing)
│  ├─ costProfile: standard-api-cost
│  ├─ Budgets calculated: size × base
│  └─ Alerts at 50%, 80%, 100% of budget
│
└─ Monitoring Profile (NEW)
   ├─ monitoringProfile: api-observability
   ├─ Resource thresholds: size × base
   ├─ SLO targets: 99.9% availability
   └─ Alerts on: high error rate, high latency, resource overuse

Together:
├─ Cost monitoring: "Is this service expensive?"
├─ Performance monitoring: "Is this service performing well?"
└─ Resource monitoring: "Is this service using resources efficiently?"

The platform tracks all three dimensions together.
```

---

## 15. Success Metrics

### Deployment Metrics
- ✅ 100% of services have monitoring profile (mandatory, like cost)
- ✅ 100% of services have ServiceMonitor deployed
- ✅ 100% of services have PrometheusRule deployed

### Observability Metrics
- ✅ Prometheus metrics visible in Grafana within 5 minutes of deployment
- ✅ Alert rules armed and evaluating within 5 minutes
- ✅ Dynatrace application traces visible within 10 minutes
- ✅ SLO dashboards available for each service

### Operations Metrics
- ✅ Alert firing accuracy (no false positives)
- ✅ MTTR improved (faster incident detection)
- ✅ Team adoption (% of teams using SLO dashboards)
- ✅ Incident correlation (% of incidents correlating Prometheus + Dynatrace data)

---

## 16. Summary

**Monitoring metrics are integrated into Platform-Next using the same profile-based pattern as cost management.**

| Component | Cost | Monitoring |
|-----------|------|-----------|
| **Definition** | costProfile | monitoringProfile |
| **Storage** | cost-profiles.yaml | monitoring-profiles.yaml |
| **Service Config** | `cost: {...}` | `monitoring: {...}` |
| **Templates** | 6 profiles | 6 profiles |
| **Scale Factor** | Budget multiplier | Resource threshold multiplier |
| **Overrides** | Per-service, per-env | Per-service, per-env |
| **Platforms** | Apptio | Prometheus + Dynatrace |
| **Catalog Lines** | 4-6 lines | 4-6 lines |

**Key Benefits**:
- ✅ Services specify minimal monitoring configuration
- ✅ Profiles enforce standardization and best practices
- ✅ Both Prometheus and Dynatrace supported simultaneously
- ✅ Environment-specific SLOs and thresholds
- ✅ Size-aware resource monitoring
- ✅ Composable and extensible

---

**Document Status**: ✅ Architecture Complete

**Next Steps**:
1. Create monitoring-profiles.yaml in kustomize/catalog/
2. Update services.yaml schema to include monitoringProfile
3. Implement profile expansion engine in CI/CD
4. Create Dynatrace sync controller
5. Update Backstage template with monitoring section
6. Deploy and validate with pilot services

**Related Documents**:
- [07_ARCHITECTURE_COMPLETE_COST_INTEGRATION.md](./07_ARCHITECTURE_COMPLETE_COST_INTEGRATION.md) - Cost profile design (template for this doc)
- [07_COST_MANAGEMENT_WITH_PROFILES.md](./07_COST_MANAGEMENT_WITH_PROFILES.md) - Cost profile operation guide
- [05_CUSTOM_METRICS_AS_CODE.md](./05_CUSTOM_METRICS_AS_CODE.md) - Metrics as code approach (complementary)
