# Manifest Generation and Cost Data Flow

**Status**: TECHNICAL SPECIFICATION

**Scope**: How Kustomize generates manifests with cost labels, and how Apptio receives cost data via two separate channels:
1. **Budget setup** from catalog (synchronous)
2. **Actual cost data** from GCP billing (asynchronous)

---

## Executive Summary

Cost tracking happens through **two independent channels**:

```
Channel 1: BUDGET SETUP (Synchronous)
├─ Catalog (services.yaml + cost-profiles.yaml)
├─ Apptio Sync Service reads catalog every 5 minutes
├─ Creates/updates budgets in Apptio
└─ Result: Budget limits + alert rules ready before first cost

Channel 2: ACTUAL COSTS (Asynchronous)
├─ Service deployed to GCP with cost labels
├─ GCP billing exports daily (captures labels)
├─ Apptio ingests GCP billing export
├─ Calculates actual costs per service/team/cost-center
└─ Tracks against budgets, fires alerts
```

---

## 1. Service Definition → Manifest Generation Pipeline

### 1.1 Input: Service Definition

**File**: `kustomize/catalog/services.yaml`

```yaml
services:
  - name: payment-processor
    type: api
    image: gcr.io/my-project/payment-processor:latest
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # Behavior & size
    profile: public-api
    size: large
    
    # Cost configuration
    costProfile: standard-api-cost
    cost:
      costCenter: "CC-12345"
      businessUnit: "retail-banking"
      costOwner: "alice.johnson@company.com"
      
      overrides:
        environment:
          prod:
            budgetMultiplier: 1.5
    
    # Resource spec
    resources:
      defaults:
        cpu: "500m"
        memory: "1Gi"
      overrides:
        prod:
          cpu: "1000m"
          memory: "2Gi"
    
    hpa:
      enabled: true
      minReplicas:
        defaults: 2
        overrides:
          prod: 4
      maxReplicas:
        defaults: 6
        overrides:
          prod: 10
```

### 1.2 Process: Kustomize Generation

**Harness Pipeline Step**:

```bash
#!/bin/bash
# scripts/generate-kz.sh

SERVICE=$1          # payment-processor
ENVIRONMENT=$2      # prod
REGION=$3           # euw1

echo "Generating Kustomize manifests..."

# 1. Load service and profile definitions
service_def=$(yq eval ".services[] | select(.name==\"$SERVICE\")" kustomize/catalog/services.yaml)
cost_profile=$(yq eval ".costProfiles.standard-api-cost" kustomize/catalog/cost-profiles.yaml)

# 2. Expand cost configuration (calculate budgets, substitute variables)
expanded_cost=$(python scripts/expand-cost-config.py \
  --service "$SERVICE" \
  --environment "$ENVIRONMENT" \
  --profile "standard-api-cost")

# 3. Extract cost labels for injection
SERVICE_NAME=$(echo "$service_def" | yq eval '.name' -)
COST_CENTER=$(echo "$expanded_cost" | yq eval '.allocation.costCenter' -)
BUSINESS_UNIT=$(echo "$expanded_cost" | yq eval '.allocation.businessUnit' -)
COST_OWNER=$(echo "$expanded_cost" | yq eval '.allocation.costOwner' -)
MONTHLY_BUDGET=$(echo "$expanded_cost" | yq eval ".budgets.$ENVIRONMENT.monthly" -)

# 4. Generate Kustomize structure
mkdir -p "kustomize/generated/$SERVICE/$ENVIRONMENT/$REGION"

# 5. Create base kustomization.yaml with cost labels
cat > "kustomize/generated/$SERVICE/$ENVIRONMENT/$REGION/kustomization.yaml" << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# Base manifests for this service/env/region
resources:
  - base-deployment.yaml
  - base-service.yaml

# Cost labels applied to all resources
commonLabels:
  app: payment-processor
  version: v1
  
  # COST LABELS (injected from catalog)
  cost.service: payment-processor
  cost.team: payments-team
  cost.environment: prod
  cost.region: euw1
  cost.costCenter: CC-12345
  cost.businessUnit: retail-banking
  cost.owner: alice.johnson@company.com
  cost.budget: "9000"           # $9000/month (calculated)
  cost.cluster: gke-prod-euw1

# Patch resource requests/limits
patches:
  - target:
      kind: Deployment
      name: payment-processor
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources
        value:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"

# Service-specific configurations
configMapGenerator:
  - name: payment-processor-config
    literals:
      - SERVICE_NAME=payment-processor
      - COST_CENTER=CC-12345
      - ENVIRONMENT=prod
EOF

echo "✅ Generated manifest for $SERVICE in $ENVIRONMENT/$REGION"
```

### 1.3 Output: Generated Manifest Files

**Generated Path**: `kustomize/generated/payment-processor/prod/euw1/`

#### File: `kustomization.yaml` (created by script above)

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - base-deployment.yaml
  - base-service.yaml

commonLabels:
  app: payment-processor
  version: v1
  cost.service: payment-processor
  cost.team: payments-team
  cost.environment: prod
  cost.region: euw1
  cost.costCenter: CC-12345
  cost.businessUnit: retail-banking
  cost.owner: alice.johnson@company.com
  cost.budget: "9000"
  cost.cluster: gke-prod-euw1

patches:
  - target:
      kind: Deployment
      name: payment-processor
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources
        value:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
```

#### File: `base-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-processor
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
spec:
  replicas: 4  # prod override
  selector:
    matchLabels:
      app: payment-processor
  template:
    metadata:
      labels:
        app: payment-processor
        # Cost labels will be injected here by Kustomize
    spec:
      serviceAccountName: payment-processor
      containers:
      - name: payment-processor
        image: gcr.io/my-project/payment-processor:2025-11-15-abc123
        ports:
        - containerPort: 8080
        env:
        - name: ENVIRONMENT
          value: prod
        - name: COST_CENTER
          valueFrom:
            configMapKeyRef:
              name: payment-processor-config
              key: COST_CENTER
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

#### File: `base-service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: payment-processor
  namespace: prod-payment-processor-euw1-stable
spec:
  type: ClusterIP
  selector:
    app: payment-processor
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
```

---

## 2. Kustomize Build Output (Final Manifest)

### 2.1 Build Command

**Harness Pipeline**:

```bash
# Generate final manifest by building kustomization
kustomize build kustomize/generated/payment-processor/prod/euw1 \
  > /tmp/payment-processor-prod-euw1-final.yaml
```

### 2.2 Final Built Manifest

After Kustomize processes the kustomization.yaml, the output is:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-processor-config-abc123
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
    version: v1
    cost.service: payment-processor
    cost.team: payments-team
    cost.environment: prod
    cost.region: euw1
    cost.costCenter: CC-12345
    cost.businessUnit: retail-banking
    cost.owner: alice.johnson@company.com
    cost.budget: "9000"
    cost.cluster: gke-prod-euw1
data:
  SERVICE_NAME: payment-processor
  COST_CENTER: CC-12345
  ENVIRONMENT: prod

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-processor
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
    version: v1
    cost.service: payment-processor          # ⭐ COST LABEL
    cost.team: payments-team                 # ⭐ COST LABEL
    cost.environment: prod                   # ⭐ COST LABEL
    cost.region: euw1                        # ⭐ COST LABEL
    cost.costCenter: CC-12345                # ⭐ COST LABEL
    cost.businessUnit: retail-banking        # ⭐ COST LABEL
    cost.owner: alice.johnson@company.com    # ⭐ COST LABEL
    cost.budget: "9000"                      # ⭐ COST LABEL
    cost.cluster: gke-prod-euw1              # ⭐ COST LABEL
spec:
  replicas: 4
  selector:
    matchLabels:
      app: payment-processor
  template:
    metadata:
      labels:
        app: payment-processor
        version: v1
        cost.service: payment-processor      # ⭐ POD LABELS
        cost.team: payments-team
        cost.environment: prod
        cost.region: euw1
        cost.costCenter: CC-12345
        cost.businessUnit: retail-banking
        cost.owner: alice.johnson@company.com
        cost.budget: "9000"
        cost.cluster: gke-prod-euw1
    spec:
      serviceAccountName: payment-processor
      containers:
      - name: payment-processor
        image: gcr.io/my-project/payment-processor:2025-11-15-abc123
        ports:
        - containerPort: 8080
        env:
        - name: ENVIRONMENT
          value: prod
        - name: COST_CENTER
          valueFrom:
            configMapKeyRef:
              name: payment-processor-config-abc123
              key: COST_CENTER
        resources:
          requests:
            cpu: "1000m"      # ⭐ From prod override
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: payment-processor
  namespace: prod-payment-processor-euw1-stable
  labels:
    app: payment-processor
    version: v1
    cost.service: payment-processor          # ⭐ COST LABEL
    cost.team: payments-team
    cost.environment: prod
    cost.costCenter: CC-12345
    cost.businessUnit: retail-banking
    cost.owner: alice.johnson@company.com
    cost.budget: "9000"
    cost.cluster: gke-prod-euw1
spec:
  type: ClusterIP
  selector:
    app: payment-processor
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
```

### 2.3 What Cost Labels Are Injected

| Label | Source | Value | Purpose |
|-------|--------|-------|---------|
| `cost.service` | Service name | payment-processor | Identify service |
| `cost.team` | Service metadata | payments-team | Allocate to team |
| `cost.environment` | Current env | prod | Track by environment |
| `cost.region` | Region config | euw1 | Regional cost breakdown |
| `cost.costCenter` | Cost profile | CC-12345 | Finance chargeback |
| `cost.businessUnit` | Cost profile | retail-banking | Business unit allocation |
| `cost.owner` | Cost profile | alice.johnson@company.com | Cost owner |
| `cost.budget` | Calculated | 9000 | Expected monthly spend |
| `cost.cluster` | Deployment target | gke-prod-euw1 | Cluster allocation |

---

## 3. Pod Deployment with Cost Labels

### 3.1 Deployment to GKE

**Harness Pipeline Step**:

```bash
#!/bin/bash
# Deploy manifest to cluster

MANIFEST_FILE="/tmp/payment-processor-prod-euw1-final.yaml"
CLUSTER="gke-prod-euw1"
NAMESPACE="prod-payment-processor-euw1-stable"

echo "Deploying to $CLUSTER..."

kubectl apply -f "$MANIFEST_FILE" \
  --cluster="$CLUSTER" \
  --namespace="$NAMESPACE"

# Verify pods are running with cost labels
kubectl get pods -n "$NAMESPACE" \
  -L cost.service,cost.environment,cost.costCenter,cost.owner
```

### 3.2 Pods Running with Cost Labels

```bash
$ kubectl get pods -n prod-payment-processor-euw1-stable \
    -L cost.service,cost.environment,cost.costCenter,cost.owner

NAME                                READY STATUS  COST.SERVICE         COST.ENVIRONMENT COST.COSTCENTER COST.OWNER
payment-processor-5d4f8c7b9-abc12   1/1   Running payment-processor   prod              CC-12345        alice.johnson@company.com
payment-processor-5d4f8c7b9-def45   1/1   Running payment-processor   prod              CC-12345        alice.johnson@company.com
payment-processor-5d4f8c7b9-ghi78   1/1   Running payment-processor   prod              CC-12345        alice.johnson@company.com
payment-processor-5d4f8c7b9-jkl01   1/1   Running payment-processor   prod              CC-12345        alice.johnson@company.com
```

### 3.3 Verify Cost Label Propagation

```bash
# Inspect pod labels
kubectl get pod payment-processor-5d4f8c7b9-abc12 \
  -n prod-payment-processor-euw1-stable \
  -o yaml | grep "cost\."

# Output:
# cost.budget: "9000"
# cost.businessUnit: retail-banking
# cost.cluster: gke-prod-euw1
# cost.costCenter: CC-12345
# cost.environment: prod
# cost.owner: alice.johnson@company.com
# cost.region: euw1
# cost.service: payment-processor
# cost.team: payments-team
```

---

## 4. Two-Channel Cost Data Flow

### 4.1 Channel 1: Budget Setup (Synchronous)

**What Apptio Gets**: Budget definitions + alert rules

```
Service Definition (catalog/services.yaml)
    ↓
Apptio Sync Service (every 5 minutes)
    ├─ Load: payment-processor from catalog
    ├─ Load: standard-api-cost profile
    ├─ Calculate: $9000 budget for prod (3000 × 1.67 × 2.0)
    ├─ Expand: alerts with variable substitution
    └─ Call Apptio API:
        POST /api/v3/budgets
        {
          "name": "payment-processor-prod",
          "description": "Payment Processor - Production",
          "amount": 9000,
          "currency": "USD",
          "period": "MONTHLY",
          "startDate": "2025-11-01",
          "costCenter": "CC-12345",
          "filters": {
            "labels": {
              "cost.service": "payment-processor",
              "cost.environment": "prod"
            }
          }
        }
        
        POST /api/v3/alert-rules
        {
          "budget_id": "budget-payment-processor-prod",
          "alerts": [
            {
              "name": "warning-70",
              "threshold": 70,
              "severity": "warning",
              "channels": {
                "teams": ["#team-payment-processor", "#platform-finops"],
                "email": ["alice.johnson@company.com"]
              }
            },
            {
              "name": "critical-85",
              "threshold": 85,
              "severity": "critical",
              "channels": {
                "teams": ["#team-payment-processor", "#platform-leadership"],
                "email": ["alice.johnson@company.com"],
                "pagerduty": "on-call-engineering"
              }
            }
          ]
        }
```

**Timeline**:
- T+0m: Service merged to main
- T+5m: Apptio Sync runs, creates budget in Apptio
- T+10m: Budgets visible in Apptio UI
- Ready for cost tracking

### 4.2 Channel 2: Actual Costs (Asynchronous)

**What Apptio Gets**: Real cost data from GCP

```
Pods Running (with cost labels)
    ↓ (consume CPU, memory, network, storage)
    ↓
GCP Billing (captures resource usage)
    ↓
GCP Daily Export (captures labels)
    ├─ time_usec: 1731705600000000
    ├─ project_id: my-project
    ├─ labels:
    │   ├─ cost.service: payment-processor
    │   ├─ cost.environment: prod
    │   ├─ cost.costCenter: CC-12345
    │   ├─ cost.owner: alice.johnson@company.com
    │   └─ resource.labels.pod_name: payment-processor-5d4f8c7b9-abc12
    ├─ metrics:
    │   ├─ compute.googleapis.com/cpu_cores_used: 0.85
    │   ├─ compute.googleapis.com/memory_mb_used: 1500
    │   ├─ compute.googleapis.com/network_in_gbs: 2.3
    │   └─ compute.googleapis.com/network_out_gbs: 5.1
    └─ cost: $247.50 (daily for this pod + pod's portion of shared)
    
    ↓ (exported to GCS)
    ↓
BigQuery (gs://my-project-billing-export/...)
    ├─ Table: projects.my-project.compute_usage.gce_instance
    ├─ daily_cost_aggregate:
    │   ├─ service: payment-processor
    │   ├─ environment: prod
    │   ├─ region: euw1
    │   ├─ cost_center: CC-12345
    │   ├─ daily_cost_usd: 990.00
    │   └─ date: 2025-11-15
    
    ↓ (Apptio ingests)
    ↓
Apptio Analytics
    ├─ Aggregates by cost.service + cost.environment
    ├─ Sums daily costs
    ├─ Calculates MTD total: $14,850 (as of Nov 15)
    ├─ Compares to budget: $9,000
    ├─ Calculates overage: $5,850 (65% over budget!)
    └─ Fires alerts:
        ├─ Alert 1: warning-70 fires
        │   → Teams: #team-payment-processor, #platform-finops
        │   → Email: alice.johnson@company.com
        ├─ Alert 2: critical-85 fires
        │   → Teams: #team-payment-processor, #platform-leadership
        │   → Email: alice.johnson@company.com
        │   → PagerDuty: on-call-engineering incident created
```

**Timeline**:
- T+0h: Pod deployed with cost labels
- T+24h: GCP exports daily billing with labels
- T+48h: BigQuery ingests data
- T+72h: Apptio calculates costs and compares to budgets
- T+72h+: Alerts fire if thresholds crossed

---

## 5. Apptio API Integration Details

### 5.1 Budget Creation Request (from Catalog)

```python
# services/apptio-sync/sync_service.py

import requests
from datetime import datetime

class ApptioSync:
    def sync_service_to_apptio(self, service_name, environment):
        """
        Sync service cost configuration from catalog to Apptio.
        Called for each service in catalog every 5 minutes.
        """
        
        # 1. Load service definition
        service = self.load_service(service_name)
        profile = self.load_cost_profile(service['costProfile'])
        
        # 2. Expand cost configuration
        expanded_cost = self.expand_cost_config(
            service=service,
            profile=profile,
            environment=environment
        )
        
        # 3. Calculate budget
        monthly_budget = expanded_cost['budgets'][environment]['monthly']
        
        # 4. Create budget in Apptio
        budget_request = {
            "name": f"{service_name}-{environment}",
            "description": f"{service_name.replace('-', ' ').title()} - {environment}",
            "amount": monthly_budget,
            "currency": "USD",
            "period": "MONTHLY",
            "startDate": datetime.now().strftime("%Y-%m-01"),
            "costCenter": service['cost']['costCenter'],
            "alerts": expanded_cost['alerts'],
            "filters": {
                "labels": {
                    "cost.service": service_name,
                    "cost.environment": environment
                }
            }
        }
        
        # 5. POST to Apptio
        response = requests.post(
            f"{self.apptio_url}/api/v3/budgets",
            json=budget_request,
            headers={"Authorization": f"Bearer {self.apptio_token}"}
        )
        
        if response.status_code == 201:
            budget_id = response.json()['id']
            print(f"✅ Created budget {service_name}-{environment}: ${monthly_budget}/month")
            self.store_sync_state(service_name, environment, budget_id)
        else:
            print(f"❌ Failed to create budget: {response.text}")
            raise Exception(f"Apptio API error: {response.status_code}")
```

### 5.2 Cost Data Query (from GCP Billing)

```python
# services/apptio-sync/cost_ingestion.py

from google.cloud import bigquery

class ApptioIngest:
    def ingest_gcp_costs(self):
        """
        Query GCP billing data with cost labels.
        Aggregate by service, environment, cost center.
        """
        
        client = bigquery.Client()
        
        query = """
        SELECT
            labels.value as service_name,
            EXTRACT(DATE FROM usage_time) as date,
            SUM(cost) as daily_cost_usd,
            STRING_AGG(DISTINCT labels.value) as cost_center
        FROM
            `my-project.billing_export.gce_instance_daily_*`
        WHERE
            _TABLE_SUFFIX = FORMAT_DATE('%Y%m%d', CURRENT_DATE() - 1)
            AND labels.key = 'cost.service'
        GROUP BY
            labels.value,
            EXTRACT(DATE FROM usage_time),
            labels.value  -- cost center
        ORDER BY
            daily_cost_usd DESC
        """
        
        results = client.query(query).result()
        
        # 2. Push aggregated costs to Apptio
        for row in results:
            service = row['service_name']
            date = row['date']
            cost = row['daily_cost_usd']
            
            # Match against budget
            budget = self.get_budget(service)
            mtd_cost = self.calculate_mtd_cost(service, date)
            budget_pct = (mtd_cost / budget['amount']) * 100
            
            # Update Apptio with actual costs
            self.update_cost_in_apptio(
                service=service,
                date=date,
                actual_cost=cost,
                mtd_cost=mtd_cost,
                budget_percentage=budget_pct
            )
            
            # Fire alerts if thresholds crossed
            self.check_and_fire_alerts(
                service=service,
                budget_percentage=budget_pct,
                alerts=budget['alerts']
            )
```

---

## 6. Complete End-to-End Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│ STEP 1: Service Catalog (Developer Input)                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ kustomize/catalog/services.yaml                                    │
│ - name: payment-processor                                          │
│   costProfile: standard-api-cost                                   │
│   cost:                                                            │
│     costCenter: CC-12345                                           │
│     costOwner: alice@company.com                                   │
│     overrides:                                                     │
│       environment:                                                 │
│         prod:                                                      │
│           budgetMultiplier: 1.5                                    │
│                                                                     │
│ kustomize/catalog/cost-profiles.yaml                               │
│ costProfiles:                                                      │
│   standard-api-cost:                                               │
│     budgets:                                                       │
│       prod: { base: 3000, scaling: 1.67 }                         │
│     alerts: [80%, 100%]                                           │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
        ┌───────────▼──────────────┐ ┌───────▼──────────────┐
        │ CHANNEL 1: BUDGET SETUP  │ │ CHANNEL 2: COST DATA │
        │ (Synchronous)            │ │ (Asynchronous)       │
        └──────────┬────────────────┘ └──────────┬──────────┘
                   │                              │
                   │                              │
    ┌──────────────▼──────────────┐              │
    │ APPTIO SYNC SERVICE         │              │
    │ (Every 5 minutes)           │              │
    │ ├─ Load catalog             │              │
    │ ├─ Expand cost config       │              │
    │ │  (calc budgets)           │              │
    │ └─ POST to Apptio API       │              │
    │    /api/v3/budgets          │              │
    └──────────────┬──────────────┘              │
                   │                              │
    ┌──────────────▼──────────────┐              │
    │ APPTIO BUDGETS CREATED      │              │
    │ ├─ Budget ID: xyz123        │              │
    │ ├─ Amount: $9000/month      │              │
    │ ├─ Alerts: [70%, 85%]       │              │
    │ └─ Status: Ready            │              │
    └──────────────────────────────┘              │
                   ▲                              │
                   │                              │
                   └──────────┬────────────────────┘
                              │
                              │
    ┌─────────────────────────▼─────────────────────────┐
    │ STEP 2: Kustomize Build (CI/CD Pipeline)         │
    ├─────────────────────────────────────────────────┤
    │ kustomize build kustomize/generated/... \       │
    │   > final-manifest.yaml                         │
    │                                                 │
    │ Injects cost labels into every resource:       │
    │ ├─ cost.service: payment-processor              │
    │ ├─ cost.environment: prod                       │
    │ ├─ cost.costCenter: CC-12345                    │
    │ ├─ cost.owner: alice@company.com                │
    │ └─ cost.budget: 9000                            │
    └──────────────┬──────────────────────────────────┘
                   │
    ┌──────────────▼──────────────┐
    │ STEP 3: Deploy to GKE       │
    ├──────────────────────────────┤
    │ kubectl apply -f final-manifest.yaml            │
    │                                                 │
    │ Pods created with cost labels:                  │
    │ ├─ payment-processor-abc12 (pod 1)             │
    │ ├─ payment-processor-def45 (pod 2)             │
    │ ├─ payment-processor-ghi78 (pod 3)             │
    │ └─ payment-processor-jkl01 (pod 4)             │
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │ STEP 4: Pods Running (24 hours)     │
    ├──────────────────────────────────────┤
    │ CPU: 0.85 cores avg × 4 pods        │
    │ Memory: 1500 MB avg × 4 pods        │
    │ Network: ~8 GB total                 │
    │ Storage: ...                         │
    └──────────────┬──────────────────────┘
                   │
                   │ (T+24h)
                   ▼
    ┌──────────────────────────────────────┐
    │ STEP 5: GCP Daily Billing Export     │
    ├──────────────────────────────────────┤
    │ Export to gs://...billing/2025-11-15│
    │                                      │
    │ File contains:                       │
    │ ├─ service: payment-processor        │
    │ ├─ environment: prod                 │
    │ ├─ cost_center: CC-12345             │
    │ ├─ owner: alice@company.com          │
    │ ├─ daily_cost: $990.00               │
    │ └─ resource_labels: [pod names, ...] │
    └──────────────┬──────────────────────┘
                   │
                   │ (T+48h)
                   ▼
    ┌──────────────────────────────────────┐
    │ STEP 6: BigQuery Ingests Data        │
    ├──────────────────────────────────────┤
    │ Query aggregates costs by:           │
    │ ├─ service                           │
    │ ├─ environment                       │
    │ ├─ cost_center                       │
    │ └─ date                              │
    │                                      │
    │ Result:                              │
    │ └─ MTD Cost: $14,850 (Nov 1-15)     │
    │    Budget: $9,000                    │
    │    Overage: 65%                      │
    └──────────────┬──────────────────────┘
                   │
                   │ (T+72h)
                   ▼
    ┌──────────────────────────────────────┐
    │ STEP 7: Apptio Alerts & Dashboard    │
    ├──────────────────────────────────────┤
    │ ✅ Alert 1 (70%): FIRED              │
    │    → #team-payment-processor         │
    │    → #platform-finops                │
    │    → alice@company.com               │
    │                                      │
    │ ✅ Alert 2 (85%): FIRED              │
    │    → #team-payment-processor         │
    │    → #platform-leadership            │
    │    → alice@company.com               │
    │    → PagerDuty incident created      │
    │                                      │
    │ Dashboard shows:                     │
    │ ├─ Service: payment-processor        │
    │ ├─ Budget: $9,000                    │
    │ ├─ Spent: $14,850 (65% over)         │
    │ ├─ Forecast: $29,700 (projected)     │
    │ └─ Status: ⚠️  OVER BUDGET            │
    └──────────────────────────────────────┘
```

---

## 7. Harness Pipeline Integration

### 7.1 Complete Harness Pipeline YAML

```yaml
# deploy-service.harness.yaml

pipeline:
  name: Deploy Payment Processor
  projectIdentifier: myproject
  
  stages:
    
    - stage:
        name: Build & Validate
        type: CI
        spec:
          execution:
            steps:
              - step:
                  name: Checkout Code
                  type: RestCall
                  spec:
                    url: https://github.com/my-org/platform-next.git
              
              - step:
                  name: Validate Catalog
                  type: Run
                  spec:
                    container:
                      image: python:3.11
                    command: |
                      python scripts/validate-catalog-schema.py \
                        --catalog kustomize/catalog/services.yaml \
                        --profiles kustomize/catalog/cost-profiles.yaml
              
              - step:
                  name: Expand Cost Config
                  type: Run
                  spec:
                    container:
                      image: python:3.11
                    command: |
                      python scripts/expand-cost-config.py \
                        --services kustomize/catalog/services.yaml \
                        --profiles kustomize/catalog/cost-profiles.yaml \
                        --output /workspace/expanded-services.yaml
    
    - stage:
        name: Generate Manifests
        type: Custom
        spec:
          steps:
            - step:
                name: Build Kustomize Manifests
                type: Run
                spec:
                  container:
                    image: kustomize:latest
                  command: |
                    #!/bin/bash
                    SERVICE=payment-processor
                    
                    for ENV in int-stable pre-stable prod; do
                      for REGION in euw1 euw2; do
                        echo "Generating $SERVICE/$ENV/$REGION..."
                        
                        bash scripts/generate-kz.sh $SERVICE $ENV $REGION
                        
                        kustomize build kustomize/generated/$SERVICE/$ENV/$REGION \
                          > /workspace/manifests/$SERVICE-$ENV-$REGION.yaml
                        
                        echo "Generated $SERVICE-$ENV-$REGION.yaml ✅"
                      done
                    done
            
            - step:
                name: Validate Manifests
                type: Run
                spec:
                  container:
                    image: kubeconform:latest
                  command: |
                    find /workspace/manifests -name "*.yaml" \
                      -exec kubeconform --strict {} \;
            
            - step:
                name: Verify Cost Labels
                type: Run
                spec:
                  container:
                    image: yq:latest
                  command: |
                    # Verify cost labels in final manifests
                    for file in /workspace/manifests/payment-processor-*.yaml; do
                      echo "Checking cost labels in $file..."
                      
                      # Extract labels
                      yq eval '.metadata.labels | keys[] | select(startswith("cost."))' "$file" \
                        | sort
                      
                      if [ $? -eq 0 ]; then
                        echo "✅ Cost labels present in $file"
                      else
                        echo "❌ Missing cost labels in $file"
                        exit 1
                      fi
                    done
    
    - stage:
        name: Deploy to Environments
        type: Custom
        spec:
          steps:
            - step:
                name: Deploy to Int-Stable
                type: Run
                spec:
                  container:
                    image: kubectl:latest
                  command: |
                    # Deploy to int-stable (both regions)
                    for REGION in euw1 euw2; do
                      echo "Deploying to int-stable/$REGION..."
                      
                      kubectl apply -f /workspace/manifests/payment-processor-int-stable-$REGION.yaml \
                        --cluster=gke-int-euw1
                      
                      # Wait for rollout
                      kubectl rollout status deployment/payment-processor \
                        -n int-payment-processor-$REGION-stable \
                        --timeout=5m
                    done
            
            - step:
                name: Deploy to Pre-Stable
                type: Run
                spec:
                  container:
                    image: kubectl:latest
                  command: |
                    # Deploy to pre-stable (both regions)
                    for REGION in euw1 euw2; do
                      echo "Deploying to pre-stable/$REGION..."
                      
                      kubectl apply -f /workspace/manifests/payment-processor-pre-stable-$REGION.yaml \
                        --cluster=gke-pre-euw1
                      
                      kubectl rollout status deployment/payment-processor \
                        -n pre-payment-processor-$REGION-stable \
                        --timeout=5m
                    done
            
            - step:
                name: Deploy to Production
                type: Run
                spec:
                  container:
                    image: kubectl:latest
                  command: |
                    # Deploy to production (both regions, rolling update)
                    for REGION in euw1 euw2; do
                      echo "Deploying to prod/$REGION..."
                      
                      kubectl apply -f /workspace/manifests/payment-processor-prod-$REGION.yaml \
                        --cluster=gke-prod-$REGION
                      
                      # Monitor rollout (rolling update, max surge 25%)
                      kubectl rollout status deployment/payment-processor \
                        -n prod-payment-processor-$REGION-stable \
                        --timeout=10m
                    done
    
    - stage:
        name: Sync Cost Config to Apptio
        type: Custom
        spec:
          steps:
            - step:
                name: Trigger Apptio Sync
                type: RestCall
                spec:
                  url: https://apptio-sync.platform-system.svc.cluster.local:8080/api/sync
                  method: POST
                  requestBody: |
                    {
                      "service": "payment-processor",
                      "environments": ["int-stable", "pre-stable", "prod"],
                      "force": true
                    }
                  authorization:
                    type: ApiKey
                    spec:
                      key: <+secrets.getValue("apptio_api_key")>
            
            - step:
                name: Verify Budget Created
                type: Run
                spec:
                  container:
                    image: python:3.11-slim
                  command: |
                    # Wait for budget to be created in Apptio
                    timeout=60
                    while [ $timeout -gt 0 ]; do
                      budget=$(curl -s \
                        -H "Authorization: Bearer $APPTIO_TOKEN" \
                        "https://apptio.company.com/api/v3/budgets?filter=name:payment-processor-prod" \
                        | jq '.results[0]')
                      
                      if [ ! -z "$budget" ]; then
                        echo "✅ Budget created in Apptio"
                        echo "Budget ID: $(echo $budget | jq -r '.id')"
                        echo "Amount: $(echo $budget | jq -r '.amount')"
                        exit 0
                      fi
                      
                      sleep 5
                      ((timeout--))
                    done
                    
                    echo "❌ Budget not found in Apptio after 60s"
                    exit 1
    
    - stage:
        name: Post-Deployment Verification
        type: Custom
        spec:
          steps:
            - step:
                name: Verify Pod Cost Labels
                type: Run
                spec:
                  container:
                    image: kubectl:latest
                  command: |
                    # Verify pods have cost labels
                    echo "Checking pods in prod..."
                    
                    kubectl get pods -n prod-payment-processor-euw1-stable \
                      -l app=payment-processor \
                      -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.cost\.service}{"\t"}{.metadata.labels.cost\.budget}{"\n"}{end}'
                    
                    # Should show all pods with cost labels
            
            - step:
                name: Create Deployment Summary
                type: Run
                spec:
                  container:
                    image: alpine:latest
                  command: |
                    cat > /workspace/deployment-summary.txt << 'EOF'
                    # Deployment Summary: payment-processor
                    
                    ## Service Configuration
                    - Service: payment-processor
                    - Cost Profile: standard-api-cost
                    - Cost Center: CC-12345
                    - Cost Owner: alice.johnson@company.com
                    
                    ## Deployed Environments
                    - Int-Stable: 2 regions (euw1, euw2) ✅
                    - Pre-Stable: 2 regions (euw1, euw2) ✅
                    - Production: 2 regions (euw1, euw2) ✅
                    
                    ## Cost Budgets
                    - Int-Stable: $1,000/month
                    - Pre-Stable: $3,000/month
                    - Production: $9,000/month
                    
                    ## Alerts Configured
                    - Warning (70%): #team-payment-processor, #platform-finops
                    - Critical (85%): #team-payment-processor, #platform-leadership, PagerDuty
                    
                    ## Cost Labels Injected
                    All pods deployed with labels:
                    - cost.service: payment-processor
                    - cost.environment: prod (per environment)
                    - cost.costCenter: CC-12345
                    - cost.owner: alice.johnson@company.com
                    - cost.budget: 9000 (per environment)
                    
                    ## Timeline
                    - T+0h: Deployment complete
                    - T+24h: GCP billing exports costs with labels
                    - T+48h: Apptio ingests costs from BigQuery
                    - T+72h: Cost tracking active, alerts enabled
                    EOF
                    
                    cat /workspace/deployment-summary.txt
```

---

## 8. Summary: What Each System Sees

| System | Sees | Source | Timing |
|--------|------|--------|--------|
| **Kubernetes** | Pods with cost labels | Kustomize-generated manifest | Immediate |
| **GCP Billing** | Resource usage tagged with labels | Pod metrics with labels | Daily export |
| **BigQuery** | Aggregated costs by service/env/team | GCP billing export | 24-48h delay |
| **Apptio (Budgets)** | Budget definitions + alert rules | Catalog via Apptio Sync | 5 minutes |
| **Apptio (Costs)** | Actual costs matched to budgets | BigQuery ingestion | 48-72h delay |
| **Alerts** | Threshold breaches | Apptio comparing actual vs budget | 48-72h after spend |

---

**Document Version**: 1.0
**Created**: 2025-11-15
**Status**: ACTIVE
