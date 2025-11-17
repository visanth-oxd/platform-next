# Monitoring Components - Kustomize Structure

This directory contains monitoring resources that are integrated with the profile-based monitoring system.

## Structure

```
monitoring/
├── profiles/                    # Profile-based monitoring resources
│   ├── api-observability/      # API service monitoring profile
│   │   ├── kustomization.yaml
│   │   ├── service-monitor-base.yaml
│   │   ├── prometheus-rules-base.yaml
│   │   └── dynatrace-app-base.yaml
│   │
│   ├── batch-job-observability/
│   └── listener-observability/
│
└── dynatrace/                   # Dynatrace-specific resources
    ├── request-attributes-base.yaml
    ├── alert-rules-base.yaml
    └── custom-metrics-template.yaml
```

## How It Works

### 1. Base Profiles

Profiles define standard observability patterns:
- **Dynatrace** configuration (primary monitoring tool)
- **Prometheus** configuration (for metrics collection)
- Standard alert rules
- Standard request attributes

### 2. Custom Metrics

Custom metrics are defined in:
- **Service definition** (`catalog/services.yaml`) - inline custom metrics
- **Metrics catalog repository** - service-specific custom metrics

### 3. Generation Process

1. Load base profile from `monitoring-profiles.yaml`
2. Load custom metrics (from service config or metrics-catalog repo)
3. Merge: Base profile + Custom metrics
4. Substitute variables: `{SERVICE}`, `{ENVIRONMENT}`, etc.
5. Generate final monitoring resources

### 4. Generated Resources

For each service/environment/region:
- `service-monitor.yaml` - Prometheus scraping config
- `prometheus-rules.yaml` - Recording and alert rules
- `dynatrace-app-config.yaml` - Dynatrace application definition (merged: base + custom)

## Example Usage

### Service Definition

```yaml
# catalog/services.yaml
services:
  - name: payment-processor
    monitoringProfile: api-observability
    monitoring:
      dynatrace: true
      prometheus: true
      customMetrics:
        repository:
          url: https://github.com/company/metrics-catalog
          ref: v1.2.0
        profiles:
          - payment-business-metrics
        metrics:
          - name: payment_transactions_total
            type: counter
            dynatrace:
              enabled: true
```

### Generated Output

```yaml
# generated/payment-processor/prod/euw1/monitoring/dynatrace-app-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-processor-dynatrace-config
data:
  application.json: |
    {
      "metadata": {
        "name": "payment-processor",
        "environment": "prod"
      },
      "monitoring": {
        "technologies": ["java", "http", "databases"],
        "requestAttributes": [...]
      },
      "customMetrics": [
        {
          "name": "payment_transactions_total",
          "type": "counter",
          ...
        }
      ],
      "alertRules": [
        {
          "name": "ErrorRateAnomaly",
          ...
        },
        {
          "name": "PaymentSuccessRateLow",
          ...
        }
      ]
    }
```

## Dynatrace as Primary Tool

Dynatrace is configured as the **primary monitoring tool**:
- ✅ Full APM (Application Performance Monitoring)
- ✅ Distributed tracing
- ✅ Real-user monitoring
- ✅ Custom metrics support
- ✅ Anomaly detection
- ✅ Service dependency mapping

Prometheus is used as **secondary** for:
- Metrics collection (scraping)
- Recording rules (pre-computed aggregations)
- Alert rules (can forward to Dynatrace)

## Integration with Metrics Catalog

Custom metrics from `metrics-catalog` repository are:
1. Fetched during manifest generation
2. Merged with base profile
3. Added to Dynatrace ConfigMap
4. Synced to Dynatrace via Dynatrace Sync Controller

## See Also

- `docs/13_METRICS_AS_CODE_WITH_PROFILES.md` - Complete design document
- `docs/08_MONITORING_METRICS_PROFILES.md` - Monitoring profiles documentation
- `docs/05_CUSTOM_METRICS_AS_CODE.md` - Custom metrics as code documentation

