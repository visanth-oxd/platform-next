# Apptio Sync Alternatives: Beyond Cloud Functions

**Date**: 2025-11-15

**Context**: Current design uses Cloud Functions for Apptio sync. This document provides a second option and implementation details via Kustomize.

---

## Current Approach (Cloud Functions)

```
Service Catalog (Git) → Cloud Function (Event-driven) → Apptio API → Budgets Created
```

**Pros**:
- Minimal custom code
- Event-driven (triggers on catalog changes)
- Serverless (no operational overhead)
- Fast sync (seconds to minutes)

**Cons**:
- External dependency (GCP Cloud Functions)
- Cannot use in all cloud environments
- Requires GCP IAM configuration
- Cold start latency
- Requires separate monitoring setup

---

## Alternative Approach: Kubernetes Native Service (Option 2)

Instead of Cloud Functions, run a **dedicated Kubernetes service** within your platform cluster that continuously syncs the service catalog to Apptio.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    platform-next (Git)                      │
│                   ┌──────────────────┐                       │
│                   │  services.yaml   │ (Cost config)         │
│                   └────────┬─────────┘                       │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ Git Poll / Webhook
                             ↓
                ┌──────────────────────────────┐
                │  Apptio Sync Service (Pod)   │ ← In-cluster
                │  ┌──────────────────────┐    │
                │  │ Config Watch         │    │
                │  │ • Poll Git every 5min│    │
                │  │ • Parse YAML         │    │
                │  │ • Validate config    │    │
                │  │ • Compare with DB    │    │
                │  │ • Detect changes     │    │
                │  └──────────────────────┘    │
                │  ┌──────────────────────┐    │
                │  │ Sync Logic           │    │
                │  │ • Create budgets     │    │
                │  │ • Update budgets     │    │
                │  │ • Configure alerts   │    │
                │  │ • Set thresholds     │    │
                │  │ • Manage cost centers│    │
                │  └──────────────────────┘    │
                │  ┌──────────────────────┐    │
                │  │ State Management     │    │
                │  │ • Last sync time     │    │
                │  │ • Sync status        │    │
                │  │ • Error tracking     │    │
                │  │ • Retry logic        │    │
                │  └──────────────────────┘    │
                └──────────────┬───────────────┘
                               │
                               │ REST API (HTTPS)
                               ↓
                        ┌──────────────┐
                        │   Apptio     │
                        │   API        │
                        └──────────────┘
```

### Benefits

1. **No Cloud Functions** - Pure Kubernetes workload
2. **Multi-cloud compatible** - Works in any Kubernetes cluster (AWS, Azure, on-prem, etc.)
3. **Better observability** - Logs in standard container logs, metrics via Prometheus
4. **Easier testing** - Deploy locally, test in staging
5. **Full control** - Own the sync logic, can customize easily
6. **No cold-start** - Always running, consistent performance
7. **Retry mechanism** - Built-in exponential backoff
8. **State tracking** - Can store last-sync-time in ConfigMap or persistent volume

### Disadvantages vs Cloud Functions

- Slightly higher operational overhead (basic monitoring needed)
- Continuous resource usage (though minimal - can use Deployment with 1 replica)
- Requires service account with Git + Apptio API access

---

## Implementation: Kustomize Configuration

### 1. Deploy Apptio Sync Service

```yaml
# kustomize/components/apptio-sync/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: apptio-sync
  namespace: platform-system
spec:
  selector:
    app: apptio-sync
  ports:
    - port: 8080
      targetPort: 8080
      name: http
    - port: 9090
      targetPort: 9090
      name: prometheus
```

```yaml
# kustomize/components/apptio-sync/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apptio-sync
  namespace: platform-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apptio-sync
  template:
    metadata:
      labels:
        app: apptio-sync
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: apptio-sync
      containers:
      - name: apptio-sync
        image: platform-next:apptio-sync-v1
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: prometheus
        env:
        - name: GIT_REPO_URL
          value: "https://github.com/your-org/platform-next.git"
        - name: GIT_BRANCH
          value: "main"
        - name: GIT_POLL_INTERVAL_SECONDS
          value: "300"  # 5 minutes
        - name: CATALOG_PATH
          value: "kustomize/catalog/services.yaml"
        - name: APPTIO_API_URL
          value: "https://your-apptio-instance.apptio.com/api"
        - name: APPTIO_API_KEY
          valueFrom:
            secretKeyRef:
              name: apptio-credentials
              key: api-key
        - name: SYNC_STATE_CONFIGMAP
          value: "apptio-sync-state"
        - name: LOG_LEVEL
          value: "INFO"
        - name: ENABLE_PROMETHEUS
          value: "true"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### 2. Service Account & RBAC

```yaml
# kustomize/components/apptio-sync/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: apptio-sync
  namespace: platform-system
```

```yaml
# kustomize/components/apptio-sync/role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: apptio-sync
  namespace: platform-system
rules:
# Read ConfigMap for sync state
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["apptio-sync-state"]
  verbs: ["get", "update"]
# Read secrets for credentials
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["apptio-credentials", "github-credentials"]
  verbs: ["get"]
```

```yaml
# kustomize/components/apptio-sync/rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: apptio-sync
  namespace: platform-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: apptio-sync
subjects:
- kind: ServiceAccount
  name: apptio-sync
  namespace: platform-system
```

### 3. Secrets for Credentials

```yaml
# kustomize/components/apptio-sync/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: apptio-credentials
  namespace: platform-system
type: Opaque
stringData:
  api-key: "YOUR_APPTIO_API_KEY"
  api-secret: "YOUR_APPTIO_SECRET"
---
apiVersion: v1
kind: Secret
metadata:
  name: github-credentials
  namespace: platform-system
type: Opaque
stringData:
  token: "YOUR_GITHUB_TOKEN"
```

### 4. State Storage ConfigMap

```yaml
# kustomize/components/apptio-sync/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: apptio-sync-state
  namespace: platform-system
data:
  last_sync_time: "2025-01-01T00:00:00Z"
  last_sync_status: "success"
  synced_services_count: "0"
  catalog_version: ""
```

### 5. Monitoring (Prometheus)

```yaml
# kustomize/monitoring/apptio-sync-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: apptio-sync
  namespace: monitoring
spec:
  groups:
  - name: apptio-sync
    interval: 30s
    rules:
    - alert: ApptioSyncFailure
      expr: increase(apptio_sync_failures_total[5m]) > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Apptio sync failed"
        description: "Apptio sync service failed to sync catalog"

    - alert: ApptioSyncDelayed
      expr: (time() - apptio_sync_last_success_timestamp) > 900
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Apptio sync delayed"
        description: "Last successful sync was {{ $value | humanizeDuration }} ago"

    - alert: ApptioApiError
      expr: rate(apptio_api_errors_total[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Apptio API errors"
        description: "Apptio API error rate: {{ $value | humanizePercentage }}"
```

### 6. Kustomize Component Definition

```yaml
# kustomize/components/apptio-sync/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
- service.yaml
- deployment.yaml
- serviceaccount.yaml
- role.yaml
- rolebinding.yaml
- secrets.yaml
- configmap.yaml

commonLabels:
  component: apptio-sync
  managed-by: kustomize

commonAnnotations:
  component.description: "Kubernetes-native Apptio budget sync service"
  component.version: "v1"
```

### 7. Overlay for Environment

```yaml
# kustomize/overlays/apptio-sync/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: platform-system

bases:
- ../../components/apptio-sync

patchesStrategicMerge:
- deployment-patch.yaml

namePrefix: apptio-sync-
nameSuffix: -prod
```

```yaml
# kustomize/overlays/apptio-sync/deployment-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apptio-sync
spec:
  replicas: 2  # High availability
  template:
    spec:
      containers:
      - name: apptio-sync
        env:
        - name: LOG_LEVEL
          value: "WARN"
        - name: GIT_POLL_INTERVAL_SECONDS
          value: "600"  # 10 minutes in prod
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - apptio-sync
              topologyKey: kubernetes.io/hostname
```

---

## Cost Configuration in Catalog (Kustomize Integration)

### 1. Service Catalog with Cost Config

```yaml
# kustomize/catalog/services.yaml
apiVersion: platform.internal/v1
kind: ServiceCatalog
metadata:
  name: platform-services
spec:
  services:
  
  # Example: Payment Service
  - name: payment-service
    team: fintech-platform
    archetype: api-service
    profile: standard
    size: medium
    
    # ========== COST CONFIGURATION ==========
    costManagement:
      enabled: true
      owner: john.smith@company.com
      businessUnit: "Finance Systems"
      
      # Cost Center for Chargeback
      costCenter:
        code: "CC-FIN-001"
        name: "Finance Platform Cost Center"
      
      # Per-Environment Budgets
      budgets:
        int-stable:
          monthly: 5000    # $5,000/month
          currency: USD
          alert:
            thresholds:
              - percentage: 50
                channels: ["slack:#fintech-alerts"]
              - percentage: 80
                channels: ["slack:#fintech-alerts", "email:team@company.com"]
              - percentage: 100
                channels: ["slack:#fintech-alerts", "email:team@company.com", "pagerduty:fintech-oncall"]
        
        pre-stable:
          monthly: 7500
          currency: USD
          alert:
            thresholds:
              - percentage: 75
                channels: ["slack:#fintech-alerts"]
              - percentage: 100
                channels: ["slack:#fintech-alerts", "email:team@company.com"]
        
        prod:
          monthly: 25000
          currency: USD
          alert:
            thresholds:
              - percentage: 50
                channels: ["slack:#fintech-alerts"]
              - percentage: 75
                channels: ["slack:#fintech-alerts", "email:team@company.com"]
              - percentage: 90
                channels: ["slack:#fintech-alerts", "email:team@company.com", "pagerduty:fintech-oncall"]
              - percentage: 100
                channels: ["slack:#fintech-alerts", "email:team@company.com", "pagerduty:fintech-oncall"]
      
      # Tags for Cost Allocation
      tags:
        product: "payment-processing"
        department: "engineering"
        environment-specific: true
      
      # Optimization Config
      optimization:
        rightSizing:
          enabled: true
          recommendations: true
        reservedInstances:
          enabled: true
          commitmentLevel: "1-year"
        commitmentDiscounts:
          enabled: true
    
    # ========== MANIFEST GENERATION ==========
    # When manifests are generated, these become labels:
    # cost.service: payment-service
    # cost.team: fintech-platform
    # cost.owner: john.smith@company.com
    # cost.costCenter: CC-FIN-001
    # cost.businessUnit: Finance Systems
    # cost.budget.prod: "25000"
    # cost.product: payment-processing
```

### 2. Kustomize Post-Processing Script

```bash
#!/bin/bash
# scripts/inject-cost-labels.sh
# Generates Kustomize labels from catalog cost configuration

set -e

SERVICES_YAML="${1:-kustomize/catalog/services.yaml}"
OUTPUT_DIR="${2:-kustomize/components/cost-labels}"

mkdir -p "$OUTPUT_DIR"

# Parse YAML and generate kustomization for each service
python3 << 'EOF'
import yaml
import sys
import os
from pathlib import Path

with open('$SERVICES_YAML') as f:
    catalog = yaml.safe_load(f)

for service in catalog['spec']['services']:
    service_name = service['name']
    team = service.get('team', 'unknown')
    cost_mgmt = service.get('costManagement', {})
    
    if not cost_mgmt.get('enabled'):
        continue
    
    cost_center_code = cost_mgmt.get('costCenter', {}).get('code', '')
    owner = cost_mgmt.get('owner', '')
    business_unit = cost_mgmt.get('businessUnit', '')
    
    # Generate commonLabels section
    kustomize_config = {
        'apiVersion': 'kustomize.config.k8s.io/v1beta1',
        'kind': 'Kustomization',
        'commonLabels': {
            'cost.service': service_name,
            'cost.team': team,
            'cost.costCenter': cost_center_code,
            'cost.businessUnit': business_unit,
            'cost.owner': owner,
        }
    }
    
    # Add per-environment budget labels
    budgets = cost_mgmt.get('budgets', {})
    for env, budget_config in budgets.items():
        monthly = budget_config.get('monthly', 0)
        kustomize_config['commonLabels'][f'cost.budget.{env}'] = str(monthly)
    
    # Write kustomization file
    output_file = Path(f"$OUTPUT_DIR/{service_name}-cost-labels.yaml")
    with open(output_file, 'w') as f:
        yaml.dump(kustomize_config, f)
    
    print(f"Generated: {output_file}")

EOF
```

### 3. Include Cost Labels in Service Kustomization

```yaml
# kustomize/archetype/api-service/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
- base-deployment.yaml
- base-service.yaml

# Include cost labels from catalog
patchesStrategicMerge:
- ../../components/cost-labels/${SERVICE_NAME}-cost-labels.yaml

# Merge with other labels
commonLabels:
  platform.managed: "true"
  archetype: api-service
  component: application
```

### 4. Kustomization Build with Cost Labels

```bash
#!/bin/bash
# scripts/build-manifests.sh

SERVICE_NAME="payment-service"
ENVIRONMENT="prod"
REGION="euw1"

# Build manifests with cost labels
kustomize build \
  --enable-alpha-plugins \
  --reorder legacy \
  -o "manifests/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}/generated.yaml" \
  "kustomize/overlays/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}"

# Verify cost labels were injected
echo "Cost labels in generated manifests:"
grep "cost\." "manifests/${SERVICE_NAME}/${ENVIRONMENT}/${REGION}/generated.yaml" | head -20
```

### 5. Validation in CI/CD

```yaml
# .github/workflows/validate-cost-config.yml
name: Validate Cost Configuration

on:
  pull_request:
    paths:
      - 'kustomize/catalog/services.yaml'
      - '.github/workflows/validate-cost-config.yml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Validate cost config schema
      run: |
        python3 scripts/validate-cost-schema.py \
          --catalog kustomize/catalog/services.yaml \
          --schema scripts/cost-config-schema.json
    
    - name: Check budget amounts
      run: |
        python3 scripts/validate-budgets.py \
          --catalog kustomize/catalog/services.yaml \
          --min-budget 50 \
          --max-budget 50000
    
    - name: Verify cost centers exist
      run: |
        python3 scripts/validate-cost-centers.py \
          --catalog kustomize/catalog/services.yaml
    
    - name: Test cost label injection
      run: |
        python3 scripts/test-label-injection.py \
          --catalog kustomize/catalog/services.yaml
```

### 6. GitHub Action to Trigger Apptio Sync

```yaml
# .github/workflows/sync-apptio.yml
name: Sync Apptio Budgets

on:
  push:
    branches: [main]
    paths:
      - 'kustomize/catalog/services.yaml'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Trigger Apptio Sync
      run: |
        # Call the Apptio Sync service webhook
        curl -X POST \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer ${{ secrets.APPTIO_WEBHOOK_TOKEN }}" \
          -d '{"action": "sync", "source": "github"}' \
          https://apptio-sync.platform-system/webhook/sync
```

---

## Comparison: Cloud Functions vs Kubernetes Service

| Aspect | Cloud Functions | Kubernetes Service |
|--------|-----------------|-------------------|
| **Setup Complexity** | Simple (GCP UI) | Moderate (Kustomize configs) |
| **Cost** | Pay per invocation | Minimal pod resources (~$5-10/month) |
| **Multi-cloud** | GCP only | Any Kubernetes cluster |
| **Cold Start** | 1-2 seconds | Instant (always running) |
| **Sync Frequency** | Event-driven (seconds) | Configurable (5-10 min typical) |
| **Observability** | Cloud Function logs | Container logs + Prometheus |
| **Testing** | Harder (GCP environment) | Easier (local Kubernetes) |
| **Customization** | Limited (GCP constraints) | Full control |
| **Operational Overhead** | Minimal | Minimal (automated deployment) |
| **GitOps Alignment** | Separate infrastructure | Infrastructure as code (YAML) |

---

## Deployment Steps

### Step 1: Create Apptio Sync Service Code
```bash
mkdir -p services/apptio-sync
# Create Dockerfile, Python/Go/Node.js service code
```

### Step 2: Build and Push Docker Image
```bash
docker build -t your-registry/apptio-sync:v1 services/apptio-sync/
docker push your-registry/apptio-sync:v1
```

### Step 3: Apply Kustomize Overlay
```bash
kubectl apply -k kustomize/overlays/apptio-sync/
```

### Step 4: Verify Deployment
```bash
kubectl logs -f deployment/apptio-sync -n platform-system
kubectl port-forward svc/apptio-sync 8080:8080 -n platform-system
curl http://localhost:8080/healthz
```

### Step 5: Test Sync
```bash
# Trigger manual sync via webhook
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8080/webhook/sync
```

---

## Recommendation

**Use Kubernetes Native Service (Option 2) if**:
- You want cloud-agnostic solution
- You have multiple cloud environments
- You want better observability and testing
- You prefer GitOps-aligned infrastructure

**Use Cloud Functions (Current) if**:
- You're GCP-only
- You want minimal operational overhead
- Event-driven sync is important
- You're already using Cloud Functions extensively

---

**Next Step**: Implement the Kubernetes service or stick with Cloud Functions based on your requirements.
