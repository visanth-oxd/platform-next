# Platform-Next: Monitoring & Metrics for Cost Integration

**Document Type**: Operational Monitoring & Observability Guide

**Audience**: Platform engineers, SRE team, FinOps practitioners

**Status**: ACTIVE - 2025-11-15

---

## Executive Summary

The cost integration system requires comprehensive monitoring to track:
- **System Health**: Is the cost tracking pipeline working?
- **Data Quality**: Are cost labels injected correctly? Are costs flowing to Apptio?
- **Enforcement**: Is cost config validation preventing bypasses?
- **User Impact**: Are teams responding to cost alerts? Are budgets being respected?
- **Business Outcomes**: Is the system delivering cost control and optimization?

This document defines metrics, dashboards, alerts, and SLOs for the Platform-Next cost integration.

---

## 1. Monitoring Layers

### Layer 1: Infrastructure Metrics (Prometheus)
Monitor the systems delivering cost tracking:
- Cloud Function (budget-sync) execution success/failure
- Apptio API response times and errors
- GCP Billing export frequency and latency
- Manifest generation with cost labels

### Layer 2: Data Quality Metrics (Custom)
Monitor cost data correctness:
- Cost labels present in deployed resources
- Cost labels correctly formatted
- Cost config matches deployed manifests
- Budget configurations in Apptio match catalog

### Layer 3: Enforcement Metrics (GitHub Actions + CI/CD)
Monitor cost config validation:
- % of PRs with valid cost config
- % of PRs rejected due to invalid cost fields
- Cost center validation success rate
- Budget amount validation success rate

### Layer 4: User Response Metrics (Apptio + Slack APIs)
Monitor team behavior:
- Alert acknowledgment rate (% teams respond to alerts)
- Time-to-respond after alert fires
- Cost optimization actions taken
- Budget variance (planned vs actual)

### Layer 5: Business Outcome Metrics (Financial)
Monitor cost management impact:
- Total costs by service/team
- Cost vs budget variance
- Month-over-month cost trends
- Cost savings from optimization

---

## 2. Prometheus Metrics (Infrastructure Level)

### 2.1 Cloud Function: Budget Sync

```prometheus
# Histogram: Time to sync catalog to Apptio
budget_sync_duration_seconds{status="success"}
budget_sync_duration_seconds{status="failure"}
  Summary:
  - Min: 5s (simple catalog with few services)
  - P50: 15s (typical)
  - P95: 45s (loaded catalog)
  - Max: 120s (timeout - investigate)

# Counter: Number of successful syncs
budget_sync_total{status="success"}
  Alert if: No syncs in last 6 hours (sync job broken)

# Counter: Number of failed syncs
budget_sync_total{status="failure"}
  Alert if: > 10% failure rate in last 1 hour

# Gauge: Services synced in last run
budget_sync_services_count{environment="int-stable"}
budget_sync_services_count{environment="pre-stable"}
budget_sync_services_count{environment="prod"}
  Alert if: Count drops 20% (service deletions or sync issues)

# Gauge: Last sync timestamp
budget_sync_last_timestamp
  Alert if: timestamp_now - budget_sync_last_timestamp > 6 hours

# Counter: Budget creation success
budget_creation_total{status="success"}
budget_creation_total{status="failure"}
  Alert if: Failure rate > 5%

# Histogram: Apptio API response time
apptio_api_request_duration_seconds{endpoint="/budgets", method="POST"}
apptio_api_request_duration_seconds{endpoint="/alerts", method="POST"}
  Alert if: P95 > 30 seconds
```

### 2.2 Manifest Generation: Cost Label Injection

```prometheus
# Counter: Manifest generation attempts
manifest_generation_total{status="success"}
manifest_generation_total{status="failure"}
manifest_generation_total{status="skipped"}

# Counter: Cost config validation failures
manifest_cost_config_missing_total
  Label missing by type: cost.service, cost.team, cost.costCenter, cost.businessUnit

# Histogram: Labels injected per manifest
manifest_cost_labels_injected{count_bucket="[1,5]", "[5,10]", "[10,∞)"}
  Alert if: Any manifest < 7 expected labels

# Gauge: Manifests with complete cost config
manifests_with_complete_cost_config_ratio
  Alert if: < 99.5% (should be 100%)

# Counter: Label format violations
manifest_cost_label_format_invalid_total
  Example: cost.costCenter=INVALID (not CC-XXXXX format)

# Histogram: Manifest generation duration
manifest_generation_duration_seconds
  Alert if: P95 > 30 seconds (blocking CI)
```

### 2.3 GCP Billing Export: Cost Data Flow

```prometheus
# Gauge: Hours since last billing export
gcp_billing_export_latency_hours
  Alert if: > 24 hours (costs not flowing)

# Counter: Billing export records processed
gcp_billing_export_records_total
  Track per environment: int-stable, pre-stable, prod

# Gauge: Cost data freshness by service
gcp_billing_cost_data_age_hours{service="payment-service"}
  Alert if: > 48 hours (stale data in Apptio)

# Counter: Billing records with cost labels
gcp_billing_labeled_records_total{label_present="true"}
gcp_billing_labeled_records_total{label_present="false"}
  Alert if: > 0.5% unlabeled (label injection failure)

# Histogram: Cost calculation variance
gcp_billing_cost_variance_percent{service="payment-service"}
  Compare estimated (from budget) vs actual
  Alert if: > 20% variance (budget estimation issue)
```

### 2.4 Apptio Integration: Budget Tracking

```prometheus
# Gauge: Budget spend percentage by service
apptio_budget_spend_percent{service="payment-service", environment="prod"}
  Values: 0-150% (0% unused, 100% at limit, 150% overrun)

# Gauge: Days remaining until month-end
apptio_budget_days_remaining{service="payment-service", environment="prod"}

# Counter: Budget alerts fired
apptio_budget_alerts_fired_total{service="payment-service", threshold="50"}
apptio_budget_alerts_fired_total{service="payment-service", threshold="80"}
apptio_budget_alerts_fired_total{service="payment-service", threshold="100"}

# Gauge: Alert delivery success
apptio_alert_delivery_success_ratio{channel="teams", severity="warning"}
apptio_alert_delivery_success_ratio{channel="email", severity="critical"}
  Alert if: < 95% (notification system failing)

# Counter: Services exceeding budget
services_over_budget_total{environment="prod"}
  Alert if: > 5% of services (widespread cost control issue)

# Gauge: Average days until budget overrun
apptio_budget_days_to_overrun{environment="prod"}
  Alert if: < 7 days remaining for 50%+ of services (cost spike)
```

---

## 3. Data Quality Metrics (Custom Implementation)

### 3.1 Cost Label Injection Verification

Create a daily validation job that runs queries like:

```bash
#!/bin/bash
# scripts/verify-cost-labels.sh

# Get all Kubernetes resources in production
kubectl get pods,services,deployments \
  --all-namespaces \
  -o json \
  -l cost.service \
  -l cost.team \
  -l cost.costCenter \
  > resources.json

# Check for missing labels
PODS_WITHOUT_SERVICE_LABEL=$(kubectl get pods -A -o json | \
  jq -r '.items[] | select(.metadata.labels["cost.service"] == null) | .metadata.name' | \
  wc -l)

echo "pods_missing_cost_service_label{count=\"$PODS_WITHOUT_SERVICE_LABEL\"}" \
  >> /var/lib/prometheus/node_exporter/textfile_collector/cost_labels.prom

DEPLOYMENT_COUNT=$(kubectl get deployments -A --no-headers | wc -l)
echo "deployments_total{count=\"$DEPLOYMENT_COUNT\"}" \
  >> /var/lib/prometheus/node_exporter/textfile_collector/cost_labels.prom
```

### 3.2 Cost Label Correctness

```python
# scripts/validate-cost-labels.py

from kubernetes import client, config
from prometheus_client import Counter, Gauge
import json

invalid_label_counter = Counter(
    'cost_label_invalid_total',
    'Invalid cost labels found',
    ['label_type', 'reason']
)

label_format_gauge = Gauge(
    'cost_labels_format_valid_ratio',
    'Ratio of correctly formatted cost labels',
    ['label_type']
)

def validate_cost_center_format(label_value):
    """Validate CC-XXXXX format"""
    import re
    return bool(re.match(r'^CC-\d{5}$', label_value))

def validate_budget_format(label_value):
    """Validate numeric budget"""
    try:
        float(label_value)
        return True
    except:
        return False

def check_pod_labels(pod):
    """Check all cost labels on a pod"""
    labels = pod.metadata.labels or {}
    
    # Required labels
    required = [
        'cost.service',
        'cost.team', 
        'cost.environment',
        'cost.costCenter',
        'cost.businessUnit'
    ]
    
    for label_key in required:
        if label_key not in labels:
            invalid_label_counter.labels(
                label_type=label_key,
                reason='missing'
            ).inc()
            return False
    
    # Format validation
    if not validate_cost_center_format(labels.get('cost.costCenter')):
        invalid_label_counter.labels(
            label_type='cost.costCenter',
            reason='invalid_format'
        ).inc()
        return False
    
    return True

# Run validation on all pods
config.load_incluster_config()
v1 = client.CoreV1Api()

all_pods = v1.list_pod_for_all_namespaces()
valid_count = sum(1 for pod in all_pods.items if check_pod_labels(pod))
total_count = len(all_pods.items)

label_format_gauge.labels(label_type='all').set(valid_count / total_count if total_count > 0 else 0)
```

### 3.3 Cost Configuration Consistency Check

```python
# scripts/validate-catalog-consistency.py

"""
Verify that catalog cost config matches:
1. What's in Apptio budgets
2. What labels are in deployed manifests
3. What's configured in alerts
"""

import requests
import yaml
import json

# 1. Load catalog
with open('catalog/services.yaml') as f:
    catalog = yaml.safe_load(f)

# 2. Query Apptio budgets
apptio_budgets = requests.get(
    'https://apptio.company.com/api/budgets',
    headers={'Authorization': f'Bearer {APPTIO_TOKEN}'}
).json()

# 3. For each service in catalog
mismatches = []
for service in catalog['services']:
    service_name = service['metadata']['name']
    
    # Check each environment
    for env in ['int-stable', 'pre-stable', 'prod']:
        catalog_budget = service['cost']['budgets'][env]['monthly']
        
        # Find corresponding Apptio budget
        apptio_budget = next(
            (b for b in apptio_budgets if b['service'] == service_name and b['environment'] == env),
            None
        )
        
        if not apptio_budget:
            mismatches.append({
                'service': service_name,
                'environment': env,
                'issue': 'Budget not created in Apptio',
                'catalog_budget': catalog_budget
            })
        elif apptio_budget['amount'] != catalog_budget:
            mismatches.append({
                'service': service_name,
                'environment': env,
                'issue': 'Budget mismatch',
                'catalog_budget': catalog_budget,
                'apptio_budget': apptio_budget['amount']
            })

# 4. Check alerts
for service in catalog['services']:
    if 'alerts' not in service['cost']:
        mismatches.append({
            'service': service['metadata']['name'],
            'issue': 'No alerts configured'
        })

# 5. Export metrics
consistency_score = (len(catalog['services']) - len(mismatches)) / len(catalog['services']) * 100
print(f"cost_config_consistency_ratio {consistency_score}")

if mismatches:
    print(f"cost_config_inconsistencies_total {len(mismatches)}")
    for mismatch in mismatches:
        print(f"# Mismatch: {json.dumps(mismatch)}")
```

---

## 4. Enforcement Metrics (CI/CD Level)

### 4.1 GitHub Actions: Cost Config Validation

```yaml
# .github/workflows/validate-cost-metrics.yml

name: Cost Configuration Validation

on:
  pull_request:
    paths:
      - 'catalog/services.yaml'

jobs:
  cost-validation:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate Cost Config
        run: |
          # Count services
          TOTAL_SERVICES=$(grep -c "^  - name:" catalog/services.yaml || true)
          
          # Count services with cost config
          SERVICES_WITH_COST=$(grep -A 20 "^  - name:" catalog/services.yaml | \
            grep -B 20 "cost:" | grep "^  - name:" | wc -l)
          
          # Count services with complete cost fields
          COMPLETE_COST_CONFIG=0
          while IFS= read -r service; do
            if grep -q "enabled: true" <<< "$service" && \
               grep -q "budgets:" <<< "$service" && \
               grep -q "alerts:" <<< "$service"; then
              ((COMPLETE_COST_CONFIG++))
            fi
          done < <(sed -n '/^  - name:/,/^  - name:/p' catalog/services.yaml)
          
          echo "total_services=$TOTAL_SERVICES" >> $GITHUB_ENV
          echo "services_with_cost=$SERVICES_WITH_COST" >> $GITHUB_ENV
          echo "complete_cost_config=$COMPLETE_COST_CONFIG" >> $GITHUB_ENV
      
      - name: Post Metrics to Prometheus
        run: |
          curl -X POST http://prometheus-pushgateway:9091/metrics/job/cost_validation/instance/${{ github.run_id }} \
            --data-binary @- <<EOF
          # HELP cost_config_validation_total Total services validated
          # TYPE cost_config_validation_total gauge
          cost_config_validation_total{status="total"} ${{ env.total_services }}
          cost_config_validation_total{status="with_cost"} ${{ env.services_with_cost }}
          cost_config_validation_total{status="complete"} ${{ env.complete_cost_config }}
          EOF
      
      - name: Check Enforcement
        run: |
          if [ "${{ env.complete_cost_config }}" != "${{ env.total_services }}" ]; then
            echo "❌ NOT ALL SERVICES HAVE COMPLETE COST CONFIG"
            echo "Missing cost config: $(({{ env.total_services }} - {{ env.complete_cost_config }}))"
            exit 1
          fi
          echo "✅ All services have complete cost configuration"
```

### 4.2 Cost Validation Success Metrics

```prometheus
# Metrics to track validation effectiveness

# Counter: PRs with valid cost config
github_pr_cost_validation_total{status="valid"}
github_pr_cost_validation_total{status="invalid"}

# Counter: Specific validation failures
cost_validation_failures_total{reason="missing_budgets"}
cost_validation_failures_total{reason="invalid_cost_center"}
cost_validation_failures_total{reason="budget_out_of_range"}
cost_validation_failures_total{reason="invalid_alert_threshold"}

# Gauge: Validation coverage
github_pr_validation_coverage_ratio
  = (valid PRs) / (total PRs with cost changes)
  Alert if: < 100% (validation not being enforced)

# Histogram: Cost validation execution time
cost_validation_duration_seconds
  Alert if: P95 > 60 seconds (blocking CI pipeline)
```

---

## 5. User Response Metrics (Behavioral Level)

### 5.1 Alert Response Tracking

Create a Cloud Function that monitors alert acknowledgments:

```python
# cost-metrics/src/cloud-functions/alert-monitoring/main.py

from slack_sdk import WebClient
from datetime import datetime, timedelta
import json
import firebase_admin
from firebase_admin import firestore

slack = WebClient(token=SLACK_BOT_TOKEN)
db = firestore.client()

def track_alert_response(request):
    """
    Monitor Teams/Slack alert channels for response threads
    Calculate: time-to-respond, acknowledge rate, resolution rate
    """
    
    event = request.get_json()
    
    if event['type'] == 'event_callback':
        event_data = event['event']
        
        # Alert message posted
        if event_data['type'] == 'message' and 'cost' in event_data.get('text', ''):
            alert_time = datetime.fromtimestamp(float(event_data['ts']))
            channel = event_data['channel']
            message_ts = event_data['ts']
            
            # Store alert event
            db.collection('alerts').document(message_ts).set({
                'channel': channel,
                'alert_time': alert_time,
                'service': extract_service_from_message(event_data['text']),
                'threshold': extract_threshold_from_message(event_data['text']),
                'severity': extract_severity_from_message(event_data['text']),
                'thread_replies': 0,
                'acknowledged': False,
                'acknowledged_time': None,
                'resolved': False,
                'resolved_time': None
            })
        
        # Thread reply (acknowledgment/action)
        elif event_data.get('thread_ts'):
            thread_ts = event_data['thread_ts']
            reply_time = datetime.fromtimestamp(float(event_data['ts']))
            
            # Update alert document
            alert_doc = db.collection('alerts').document(thread_ts).get()
            if alert_doc.exists():
                alert_data = alert_doc.to_dict()
                
                # Check if first response (acknowledgment)
                if alert_data['thread_replies'] == 0:
                    response_time = (reply_time - alert_data['alert_time']).total_seconds()
                    
                    db.collection('alerts').document(thread_ts).update({
                        'acknowledged': True,
                        'acknowledged_time': reply_time,
                        'time_to_response_seconds': response_time
                    })
                
                # Check if resolved (keywords in message)
                if any(kw in event_data['text'].lower() for kw in ['resolved', 'fixed', 'optimized']):
                    db.collection('alerts').document(thread_ts).update({
                        'resolved': True,
                        'resolved_time': reply_time
                    })
                
                db.collection('alerts').document(thread_ts).update({
                    'thread_replies': firestore.Increment(1)
                })

def get_alert_metrics():
    """
    Query alerts from last 30 days and calculate metrics
    """
    past_30_days = datetime.now() - timedelta(days=30)
    
    alerts = db.collection('alerts')\
        .where('alert_time', '>=', past_30_days)\
        .stream()
    
    metrics = {
        'total_alerts': 0,
        'acknowledged': 0,
        'resolved': 0,
        'avg_time_to_response': 0,
        'avg_time_to_resolution': 0,
        'by_severity': {}
    }
    
    response_times = []
    resolution_times = []
    
    for alert in alerts:
        data = alert.to_dict()
        metrics['total_alerts'] += 1
        
        severity = data['severity']
        if severity not in metrics['by_severity']:
            metrics['by_severity'][severity] = {
                'total': 0,
                'acknowledged': 0,
                'acknowledged_ratio': 0
            }
        metrics['by_severity'][severity]['total'] += 1
        
        if data['acknowledged']:
            metrics['acknowledged'] += 1
            metrics['by_severity'][severity]['acknowledged'] += 1
            response_times.append(data['time_to_response_seconds'])
        
        if data['resolved']:
            metrics['resolved'] += 1
            resolution_times.append(
                (data['resolved_time'] - data['alert_time']).total_seconds()
            )
    
    # Calculate ratios
    if metrics['total_alerts'] > 0:
        metrics['acknowledged_ratio'] = metrics['acknowledged'] / metrics['total_alerts']
        metrics['resolved_ratio'] = metrics['resolved'] / metrics['total_alerts']
    
    if response_times:
        metrics['avg_time_to_response'] = sum(response_times) / len(response_times)
    
    if resolution_times:
        metrics['avg_time_to_resolution'] = sum(resolution_times) / len(resolution_times)
    
    # Calculate per-severity
    for severity in metrics['by_severity']:
        data = metrics['by_severity'][severity]
        if data['total'] > 0:
            data['acknowledged_ratio'] = data['acknowledged'] / data['total']
    
    return metrics
```

### 5.2 Alert Response SLOs

```prometheus
# Metrics exported from the above Cloud Function

# Gauge: Alert acknowledgment rate (%)
alert_acknowledgment_ratio{severity="warning"}
alert_acknowledgment_ratio{severity="critical"}
  SLO: warning >= 80%, critical >= 95%

# Histogram: Time to acknowledge alert
alert_time_to_response_seconds{severity="warning"}
alert_time_to_response_seconds{severity="critical"}
  SLO: warning p95 < 4 hours, critical p95 < 30 minutes

# Gauge: Alert resolution rate (%)
alert_resolution_ratio{service="payment-service"}
  SLO: >= 80%

# Histogram: Time to resolve
alert_time_to_resolution_seconds{service="payment-service"}
  Track how long before team fixes the issue
  Baseline: Varies by service, establish first month
```

---

## 6. Business Outcome Metrics (Financial Level)

### 6.1 Cost vs Budget Tracking

```python
# scripts/cost-vs-budget-metrics.py

"""
Monthly financial metrics exported from Apptio
"""

import requests
from datetime import datetime

apptio = ApptioClient(token=APPTIO_TOKEN)

# Get all services with budgets
services = apptio.list_services()

metrics = {}

for service in services:
    for environment in ['int-stable', 'pre-stable', 'prod']:
        
        # Budget from catalog
        budget = service['cost']['budgets'][environment]['monthly']
        
        # Actual spend from Apptio
        spend = apptio.get_mtd_spend(
            service=service['name'],
            environment=environment
        )
        
        # Days into month
        today = datetime.now()
        days_into_month = today.day
        days_in_month = (datetime(today.year, today.month + 1, 1) - 
                         datetime(today.year, today.month, 1)).days
        
        # Projected month-end
        daily_rate = spend / days_into_month if days_into_month > 0 else 0
        projected_total = daily_rate * days_in_month
        
        # Variance
        variance_pct = ((projected_total - budget) / budget * 100) if budget > 0 else 0
        
        key = f"{service['name']}-{environment}"
        metrics[key] = {
            'budget': budget,
            'spend': spend,
            'projected_total': projected_total,
            'variance_pct': variance_pct,
            'days_into_month': days_into_month,
            'daily_rate': daily_rate
        }

# Export Prometheus metrics
for key, data in metrics.items():
    service, env = key.split('-', 1)
    print(f'cost_budget_monthly{{service="{service}", environment="{env}"}} {data["budget"]}')
    print(f'cost_spend_mtd{{service="{service}", environment="{env}"}} {data["spend"]}')
    print(f'cost_projected_monthly{{service="{service}", environment="{env}"}} {data["projected_total"]}')
    print(f'cost_variance_percent{{service="{service}", environment="{env}"}} {data["variance_pct"]}')
    print(f'cost_daily_rate{{service="{service}", environment="{env}"}} {data["daily_rate"]}')
```

### 6.2 Cost Optimization Impact

```prometheus
# Gauge: Total monthly infrastructure costs
infrastructure_cost_total{environment="prod"}
  Alert if: > budget for entire prod (sum of all services)

# Gauge: Cost savings from optimization
cost_savings_monthly{optimization_type="right_sizing"}
cost_savings_monthly{optimization_type="spot_instances"}
cost_savings_monthly{optimization_type="reserved_instances"}

# Gauge: Cost trend year-over-year
cost_trend_yoy_percent{service="payment-service"}
  Target: < 5% growth annually (with optimization)
  Alert if: > 15% growth (runaway costs)

# Gauge: Cost per unit of business
cost_per_transaction{service="payment-service"}
cost_per_login{service="identity-service"}
  Track: Cost efficiency improving

# Histogram: Cost distribution by team
cost_by_team_percent{team="payments-team"}
cost_by_team_percent{team="identity-team"}
  Alert if: Any team > 40% of infrastructure budget (concentration risk)
```

---

## 7. Grafana Dashboards

### 7.1 Dashboard: Cost System Health

```json
{
  "dashboard": {
    "title": "Platform-Next: Cost Integration Health",
    "panels": [
      {
        "title": "Budget Sync Status",
        "targets": [
          {
            "expr": "rate(budget_sync_total{status='success'}[1h])",
            "legendFormat": "Successful Syncs/Hour"
          },
          {
            "expr": "rate(budget_sync_total{status='failure'}[1h])",
            "legendFormat": "Failed Syncs/Hour"
          }
        ],
        "alert": "SyncFailureRate"
      },
      {
        "title": "Cost Label Injection Rate",
        "targets": [
          {
            "expr": "manifests_with_complete_cost_config_ratio",
            "legendFormat": "{{ environment }}"
          }
        ],
        "alert": "LabelInjectionRate < 99.5%"
      },
      {
        "title": "GCP Billing Data Freshness",
        "targets": [
          {
            "expr": "gcp_billing_cost_data_age_hours",
            "legendFormat": "{{ service }}"
          }
        ],
        "alert": "DataFreshness > 48h"
      },
      {
        "title": "Apptio Budget-Catalog Consistency",
        "targets": [
          {
            "expr": "cost_config_consistency_ratio",
            "legendFormat": "Consistency Score %"
          }
        ]
      },
      {
        "title": "Cost Validation Success Rate",
        "targets": [
          {
            "expr": "rate(github_pr_cost_validation_total{status='valid'}[24h]) / rate(github_pr_cost_validation_total[24h])",
            "legendFormat": "Valid PRs %"
          }
        ],
        "alert": "ValidationCoverage < 100%"
      }
    ]
  }
}
```

### 7.2 Dashboard: Team Cost Management

```json
{
  "dashboard": {
    "title": "Platform-Next: Team Cost Management",
    "templating": {
      "list": [
        {
          "name": "team",
          "type": "query",
          "query": "label_values(apptio_budget_spend_percent, team)"
        }
      ]
    },
    "panels": [
      {
        "title": "Budget Burn-Down by Environment",
        "targets": [
          {
            "expr": "apptio_budget_spend_percent{team='$team'}",
            "legendFormat": "{{ environment }}"
          }
        ],
        "thresholds": [
          { "value": 80, "color": "yellow" },
          { "value": 100, "color": "red" }
        ]
      },
      {
        "title": "Days Until Budget Overrun",
        "targets": [
          {
            "expr": "apptio_budget_days_to_overrun{team='$team'}",
            "legendFormat": "{{ service }}"
          }
        ],
        "alert": "DaysToOverrun < 7"
      },
      {
        "title": "Alert Response Time",
        "targets": [
          {
            "expr": "alert_time_to_response_seconds{team='$team'}",
            "legendFormat": "{{ severity }}"
          }
        ]
      },
      {
        "title": "Alert Acknowledgment Rate",
        "targets": [
          {
            "expr": "alert_acknowledgment_ratio{team='$team'}",
            "legendFormat": "{{ severity }}"
          }
        ],
        "thresholds": [
          { "value": 80, "color": "green" },
          { "value": 80, "color": "red" }
        ]
      },
      {
        "title": "Cost vs Budget Variance",
        "targets": [
          {
            "expr": "cost_variance_percent{team='$team'}",
            "legendFormat": "{{ service }}"
          }
        ]
      },
      {
        "title": "Monthly Cost Trend",
        "targets": [
          {
            "expr": "cost_spend_mtd{team='$team'}",
            "legendFormat": "{{ service }}"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Dashboard: Finance & Optimization

```json
{
  "dashboard": {
    "title": "Platform-Next: Finance & Optimization",
    "panels": [
      {
        "title": "Total Infrastructure Costs",
        "targets": [
          {
            "expr": "sum(cost_spend_mtd)",
            "legendFormat": "Monthly Spend"
          },
          {
            "expr": "sum(cost_budget_monthly)",
            "legendFormat": "Total Budget"
          }
        ]
      },
      {
        "title": "Cost by Business Unit",
        "targets": [
          {
            "expr": "sum by (business_unit) (cost_spend_mtd)",
            "legendFormat": "{{ business_unit }}"
          }
        ],
        "type": "piechart"
      },
      {
        "title": "Cost by Cost Center",
        "targets": [
          {
            "expr": "sum by (cost_center) (cost_spend_mtd)",
            "legendFormat": "{{ cost_center }}"
          }
        ],
        "type": "piechart"
      },
      {
        "title": "Services Over Budget",
        "targets": [
          {
            "expr": "count(apptio_budget_spend_percent > 100)",
            "legendFormat": "Services"
          }
        ],
        "alert": "ServicesOverBudget > 5%"
      },
      {
        "title": "Cost Savings Realized",
        "targets": [
          {
            "expr": "sum(cost_savings_monthly)",
            "legendFormat": "Monthly Savings"
          }
        ]
      },
      {
        "title": "Cost per Unit of Business",
        "targets": [
          {
            "expr": "cost_per_transaction{service='payment-service'}",
            "legendFormat": "Cost per transaction"
          }
        ]
      },
      {
        "title": "Year-over-Year Cost Trend",
        "targets": [
          {
            "expr": "cost_trend_yoy_percent",
            "legendFormat": "{{ service }}"
          }
        ]
      }
    ]
  }
}
```

---

## 8. SLOs (Service Level Objectives)

### 8.1 System Health SLOs

```yaml
# slos/cost-system-health.yaml

apiVersion: monitoring.coreos.com/v1
kind: SLO

metadata:
  name: cost-integration-system-health

spec:
  objectives:
    
    - name: budget-sync-success
      description: Budget sync completes successfully
      target: 99.5%
      window: 30d
      sli:
        ratio:
          good: rate(budget_sync_total{status="success"}[5m])
          total: rate(budget_sync_total[5m])
      alerting:
        rules:
          - severity: warning
            threshold: 95%
            duration: 1h
          - severity: critical
            threshold: 90%
            duration: 30m
    
    - name: cost-label-injection
      description: All manifests have complete cost labels
      target: 99.9%
      window: 7d
      sli:
        ratio:
          good: manifests_with_complete_cost_config_ratio
          total: manifest_generation_total{status="success"}
    
    - name: cost-data-freshness
      description: Cost data latency < 48 hours
      target: 98%
      window: 30d
      sli:
        threshold:
          value: gcp_billing_cost_data_age_hours <= 48
    
    - name: cost-config-validity
      description: 100% of cost configs are valid
      target: 100%
      window: 7d
      sli:
        ratio:
          good: github_pr_cost_validation_total{status="valid"}
          total: github_pr_cost_validation_total
```

### 8.2 User Experience SLOs

```yaml
apiVersion: monitoring.coreos.com/v1
kind: SLO

metadata:
  name: cost-management-ux

spec:
  objectives:
    
    - name: alert-acknowledgment-warning
      description: Teams acknowledge warning alerts
      target: 80%
      window: 30d
      sli:
        ratio:
          good: alert_acknowledgment_total{severity="warning", acknowledged=true}
          total: alert_acknowledgment_total{severity="warning"}
    
    - name: alert-acknowledgment-critical
      description: Teams acknowledge critical alerts immediately
      target: 95%
      window: 30d
      sli:
        ratio:
          good: alert_acknowledgment_total{severity="critical", acknowledged=true}
          total: alert_acknowledgment_total{severity="critical"}
    
    - name: alert-response-time-critical
      description: Critical alerts get response within 30 minutes
      target: 95%
      window: 30d
      sli:
        threshold:
          value: alert_time_to_response_seconds{severity="critical"} <= 1800
    
    - name: budget-accuracy
      description: Projected month-end costs within 10% of budget
      target: 80%
      window: 30d
      sli:
        threshold:
          value: abs(cost_variance_percent) <= 10
```

---

## 9. Alerting Rules

### 9.1 Critical Alerts (Immediate)

```yaml
# prometheus/alerts/cost-critical.yaml

groups:
  - name: cost-integration-critical
    rules:
      
      - alert: BudgetSyncFailure
        expr: rate(budget_sync_total{status="failure"}[1h]) > 0.05
        for: 15m
        annotations:
          severity: critical
          summary: "Budget sync to Apptio failing ({{ $value | humanizePercentage }})"
          dashboard: "https://grafana/d/cost-health"
      
      - alert: CostLabelInjectionFailure
        expr: manifests_with_complete_cost_config_ratio < 0.995
        for: 30m
        annotations:
          severity: critical
          summary: "Cost labels not injected in {{ $value | humanizePercentage }} of manifests"
          description: "This blocks deployment and cost tracking"
      
      - alert: CostDataFreshness
        expr: gcp_billing_cost_data_age_hours > 48
        for: 1h
        annotations:
          severity: critical
          summary: "Cost data is {{ $value }} hours old (should be < 48h)"
          description: "Costs not visible in Apptio"
      
      - alert: ApptioApiErrors
        expr: rate(apptio_api_request_total{status="error"}[1h]) > 0.01
        for: 15m
        annotations:
          severity: critical
          summary: "Apptio API error rate {{ $value | humanizePercentage }}"
          action: "Check Apptio status page"
```

### 9.2 Warning Alerts (1 hour)

```yaml
# prometheus/alerts/cost-warning.yaml

groups:
  - name: cost-integration-warning
    rules:
      
      - alert: HighServicesCostOverBudget
        expr: count(apptio_budget_spend_percent > 100) / count(apptio_budget_spend_percent) > 0.05
        for: 1h
        annotations:
          severity: warning
          summary: "> 5% of services exceeding budget"
          description: "{{ $value | humanizePercentage }} of services are over budget"
      
      - alert: LowAlertAcknowledgmentRate
        expr: alert_acknowledgment_ratio{severity="warning"} < 0.80
        for: 1h
        annotations:
          severity: warning
          summary: "Only {{ $value | humanizePercentage }} of warning alerts acknowledged"
          description: "Teams not responding to cost alerts"
      
      - alert: CostValidationFailure
        expr: rate(github_pr_cost_validation_total{status="invalid"}[24h]) > 0
        for: 1h
        annotations:
          severity: warning
          summary: "{{ $value }} PRs with invalid cost config in last 24h"
          action: "Review PR validation logs"
      
      - alert: SlowBudgetSync
        expr: budget_sync_duration_seconds{status="success"} > 60
        for: 5m
        annotations:
          severity: warning
          summary: "Budget sync took {{ $value }}s (should be < 30s)"
          description: "May indicate catalog load or API performance issues"
```

---

## 10. Implementation Checklist

### Phase 1: Infrastructure Metrics (Week 1-2)
- [ ] Deploy Prometheus with cost-related scrape configs
- [ ] Configure Prometheus Pushgateway for batch jobs
- [ ] Export Cloud Function metrics
- [ ] Export manifest generation metrics
- [ ] Export GCP Billing export metrics
- [ ] Test metric collection

### Phase 2: Data Quality Metrics (Week 3)
- [ ] Create label validation job (daily)
- [ ] Create cost config consistency check (daily)
- [ ] Create cost label format validation
- [ ] Integrate with Prometheus textfile collector
- [ ] Test validation accuracy

### Phase 3: Enforcement Metrics (Week 4)
- [ ] Update GitHub Actions workflow with metric collection
- [ ] Create validation metrics export
- [ ] Test PR validation tracking
- [ ] Verify metric accuracy

### Phase 4: User Response Metrics (Week 5)
- [ ] Deploy alert monitoring Cloud Function
- [ ] Integrate with Teams/Slack APIs
- [ ] Create alert tracking database (Firestore)
- [ ] Implement response time calculation
- [ ] Test alert acknowledgment tracking

### Phase 5: Business Metrics (Week 6)
- [ ] Create cost vs budget calculation job
- [ ] Create cost optimization tracking
- [ ] Integrate with Apptio APIs
- [ ] Export financial metrics
- [ ] Test accuracy against actual spend

### Phase 6: Dashboards & Alerts (Week 7)
- [ ] Create Grafana dashboards (3 main views)
- [ ] Create alerting rules
- [ ] Configure alert routing to Slack/PagerDuty
- [ ] Test dashboard functionality
- [ ] Set alert thresholds

### Phase 7: SLOs & Testing (Week 8)
- [ ] Define SLOs (system health + UX)
- [ ] Create SLO dashboard
- [ ] Test SLO calculation
- [ ] Document SLO meaning
- [ ] Train team on interpreting SLOs

---

## 11. Metrics Summary Table

| Metric Layer | Purpose | Example Metrics | Collection Interval |
|---|---|---|---|
| **Infrastructure** | System health | budget_sync_*, apptio_api_*, gcp_billing_* | 1 minute |
| **Data Quality** | Cost data correctness | manifests_with_cost_labels, cost_label_format_valid | 1 hour |
| **Enforcement** | Config validation | github_pr_cost_validation_*, cost_validation_failures_* | Per PR |
| **User Response** | Team behavior | alert_acknowledgment_ratio, alert_time_to_response | 1 hour |
| **Business Outcome** | Cost control | cost_spend_*, cost_variance_%, cost_savings_* | 1 day |

---

## 12. Integration with Existing Monitoring

### Prometheus Scrape Config

```yaml
# prometheus/prometheus.yml

global:
  scrape_interval: 1m
  evaluation_interval: 1m

scrape_configs:
  # Existing scrapes...
  
  - job_name: 'cost-integration'
    static_configs:
      - targets: ['cost-integration-exporter:9090']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'cost-integration'
  
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['prometheus-pushgateway:9091']
  
  - job_name: 'github-validation'
    static_configs:
      - targets: ['github-metrics-exporter:9090']
```

### Alert Manager Config

```yaml
# prometheus/alertmanager.yml

global:
  slack_api_url: ${SLACK_WEBHOOK_URL}

route:
  receiver: 'cost-team'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    - match:
        severity: critical
      receiver: 'cost-critical'
      repeat_interval: 5m
    
    - match:
        severity: warning
      receiver: 'cost-warnings'
      repeat_interval: 1h

receivers:
  - name: 'cost-critical'
    slack_configs:
      - channel: '#platform-critical'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
    pagerduty_configs:
      - service_key: ${PAGERDUTY_SERVICE_KEY}
  
  - name: 'cost-warnings'
    slack_configs:
      - channel: '#platform-finops'
        title: 'WARNING: {{ .GroupLabels.alertname }}'
  
  - name: 'cost-team'
    slack_configs:
      - channel: '#platform-cost-management'
```

---

## Summary

**Platform-Next now has comprehensive monitoring covering:**
- ✅ System health (sync, APIs, data flow)
- ✅ Data quality (label injection, consistency)
- ✅ Enforcement (validation, configuration)
- ✅ User response (alert acknowledgment, resolution)
- ✅ Business outcomes (cost vs budget, savings)

**With dashboards and alerts for:**
- ✅ Platform team (system health)
- ✅ Development teams (cost tracking, alerts)
- ✅ Finance team (cost allocation, trends)

**Measured by SLOs ensuring:**
- ✅ Cost integration system reliability (99.5%+)
- ✅ Cost data freshness (< 48 hours)
- ✅ User response effectiveness (80-95% acknowledgment)

---

**Status**: ✅ Complete Design

**Last Updated**: 2025-11-15

**Next Step**: Implement Phase 1 - Deploy Prometheus scrape configs and Cloud Function metrics
