# Metrics Approaches: Comparison & Unified Solution

**Status**: COMPARISON DOCUMENT

**Date**: 2025-11-16

---

## Executive Summary

This document clearly explains the differences between **Custom Metrics as Code** (Doc 05) and **Monitoring Metrics Profiles** (Doc 08), and shows how they work together in the unified approach.

---

## Side-by-Side Comparison

| Aspect | Doc 05: Custom Metrics as Code | Doc 08: Monitoring Profiles | Unified Approach |
|--------|--------------------------------|----------------------------|------------------|
| **Repository** | Separate `metrics-catalog` repo | In `platform-next` repo | **Both**: Profiles in platform-next, custom metrics in catalog |
| **Ownership** | Observability team | Platform team | **Shared**: Platform owns profiles, Observability owns custom metrics |
| **Versioning** | Independent (v1.0.0, v1.1.0) | Tied to platform-next | **Both**: Profiles versioned with platform, custom metrics independently |
| **Structure** | Profiles, archetypes, services | Profile definitions in YAML | **Combined**: Profile components + external custom metrics |
| **Dynatrace Support** | ❌ Limited | ✅ Full support | ✅ **Full support (PRIMARY)** |
| **Prometheus Support** | ✅ Primary focus | ✅ Secondary | ✅ **Secondary (for collection)** |
| **Custom Metrics** | ✅ Strong (separate repo) | ⚠️ Limited (inline only) | ✅ **Strong (via metrics-catalog)** |
| **Composability** | ✅ High (mix and match) | ⚠️ Medium (template-based) | ✅ **High (profiles + custom)** |
| **Integration** | ⚠️ External reference | ✅ Integrated | ✅ **Unified integration** |
| **Use Case** | Service-specific metrics | Standard observability | **Both**: Standard + custom |

---

## Key Differences Explained

### 1. Repository Location

**Doc 05 (Metrics as Code)**:
- Metrics in separate `metrics-catalog` repository
- Owned by observability team
- Versioned independently
- Referenced via Git URLs or OCI registry

**Doc 08 (Monitoring Profiles)**:
- Profiles in `platform-next` repository
- Owned by platform team
- Versioned with platform
- Integrated with service catalog

**Unified**:
- **Profiles** in platform-next (standard patterns)
- **Custom metrics** in metrics-catalog (service-specific)
- Best of both worlds

---

### 2. Dynatrace Support

**Doc 05 (Metrics as Code)**:
- Focus on Prometheus
- Limited Dynatrace support
- Primarily ServiceMonitor and PrometheusRule

**Doc 08 (Monitoring Profiles)**:
- Full Dynatrace support
- Dynatrace ConfigMap generation
- Request attributes, custom metrics, alert rules

**Unified**:
- **Dynatrace is PRIMARY** monitoring tool
- Full Dynatrace application definition
- Custom metrics in Dynatrace
- Prometheus for metrics collection only

---

### 3. Custom Metrics

**Doc 05 (Metrics as Code)**:
- Strong support for custom metrics
- Service-specific metrics in separate repo
- Highly composable

**Doc 08 (Monitoring Profiles)**:
- Limited custom metrics support
- Mostly inline in service definition
- Template-based

**Unified**:
- **Base metrics** from profiles (standard)
- **Custom metrics** from metrics-catalog (service-specific)
- **Merged** into single Dynatrace ConfigMap

---

### 4. Composability

**Doc 05 (Metrics as Code)**:
- Highly composable
- Mix and match profiles
- Service-specific additions

**Doc 08 (Monitoring Profiles)**:
- Template-based
- Less composable
- Environment overrides

**Unified**:
- **Profiles** provide base templates
- **Custom metrics** compose on top
- **High composability** maintained

---

## Unified Architecture

### How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│ Service Definition (services.yaml)                          │
├─────────────────────────────────────────────────────────────┤
│ monitoringProfile: api-observability  ← From Doc 08         │
│ monitoring:                                                  │
│   customMetrics:                                            │
│     repository:                                             │
│       url: metrics-catalog  ← From Doc 05                  │
│     profiles: [payment-business-metrics]                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Profile Expansion Engine                                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Load base profile (monitoring-profiles.yaml)            │
│    → Dynatrace app structure                               │
│    → Standard alert rules                                   │
│    → Standard request attributes                            │
│                                                              │
│ 2. Fetch custom metrics (metrics-catalog repo)             │
│    → Payment business metrics                               │
│    → Custom Dynatrace metrics                               │
│    → Custom alert rules                                     │
│                                                              │
│ 3. Merge: Base + Custom                                     │
│    → Dynatrace ConfigMap (merged)                          │
│    → Prometheus rules (merged)                              │
│                                                              │
│ 4. Substitute variables                                     │
│    → {SERVICE} → payment-processor                           │
│    → {ENVIRONMENT} → prod                                   │
│                                                              │
│ 5. Apply environment overrides                              │
│    → Prod SLOs: 99.99% availability                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Generated Monitoring Resources                              │
├─────────────────────────────────────────────────────────────┤
│ • Dynatrace ConfigMap (merged: base + custom)               │
│ • ServiceMonitor (Prometheus)                                │
│ • PrometheusRule (recording + alerts)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## When to Use What

### Use Profiles (Doc 08) For:
- ✅ Standard observability patterns
- ✅ Base Dynatrace configuration
- ✅ Standard alert rules
- ✅ Standard request attributes
- ✅ SLO definitions
- ✅ Environment-specific overrides

### Use Custom Metrics (Doc 05) For:
- ✅ Service-specific business metrics
- ✅ Custom Dynatrace metrics
- ✅ Service-specific alert rules
- ✅ Custom dashboards
- ✅ Metrics that evolve independently
- ✅ Metrics shared across multiple platforms

### Use Unified Approach For:
- ✅ **Everything** - Best of both worlds
- ✅ Standard observability (profiles) + Custom metrics (catalog)
- ✅ Dynatrace as primary monitoring tool
- ✅ Maximum flexibility and maintainability

---

## Example: Payment Processor Service

### Service Definition

```yaml
services:
  - name: payment-processor
    monitoringProfile: api-observability  # From Doc 08 (base profile)
    monitoring:
      dynatrace: true
      prometheus: true
      customMetrics:                       # From Doc 05 (custom metrics)
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

### What Gets Generated

1. **Base Profile** (from `monitoring-profiles.yaml`):
   - Dynatrace application structure
   - Standard request attributes
   - Standard alert rules (ErrorRateAnomaly, HighLatencyAnomaly)

2. **Custom Metrics** (from `metrics-catalog`):
   - `payment_transactions_total` (counter)
   - `payment_success_rate` (gauge)
   - `fraud_check_latency` (histogram)
   - Custom alert rules (PaymentSuccessRateLow)

3. **Merged Result**:
   - Single Dynatrace ConfigMap with:
     - Base application structure
     - Standard + custom metrics
     - Standard + custom alert rules
   - ServiceMonitor (Prometheus)
   - PrometheusRule (recording + alerts)

---

## Summary

**The Unified Approach**:
- ✅ **Profiles** (Doc 08) = Base templates in platform-next
- ✅ **Custom Metrics** (Doc 05) = Service-specific in metrics-catalog
- ✅ **Together** = Flexible, maintainable, composable monitoring
- ✅ **Dynatrace** = Primary monitoring tool (full support)
- ✅ **Prometheus** = Secondary (for metrics collection)

**Result**: Standard observability from profiles + Custom business metrics from catalog = Complete monitoring solution!

---

**Document Status**: ✅ Complete Comparison

