# Dynamic Harness Pipeline Approach - Design & Analysis

## Concept Overview

### The Idea

Instead of using the service catalog to directly deploy manifests:

**Use catalog to dynamically generate dedicated Harness CD pipelines**

```
Service Catalog (Single File)
         ↓
    UI Onboarding
         ↓
  Generate Harness Pipeline (via API)
         ↓
Per-Service Pipeline Created
         ↓
Deploy to Environments (with controls)
```

### Key Difference from Previous Approach

| Aspect | Previous (GitOps) | This (Harness Pipelines) |
|--------|-------------------|--------------------------|
| **Deployment Model** | Git push → Auto-sync | Pipeline execution (manual/scheduled) |
| **Catalog Storage** | Per-service files | Single catalog (or per-archetype) |
| **Scalability** | Parallel matrix jobs | Independent pipelines per service |
| **Approval** | GitHub PR review | Harness approval gates |
| **Control** | Git revert | Pipeline pause/resume |
| **RBAC** | GitHub CODEOWNERS | Harness RBAC per pipeline |

---

## Architecture Design

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Developer Uses Self-Service UI                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Developer Portal (Web UI)                                   │
│    ├─ Service Name: payment-service                          │
│    ├─ Archetype: api                                         │
│    ├─ Profile: public-api                                    │
│    ├─ Size: medium                                           │
│    └─ Environments: [int, pre, prod]                         │
│                                                              │
│         [Submit] ──────────────────┐                         │
└───────────────────────────────────┬┘                         │
                                    │                          │
                                    ▼                          │
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Backend Service Processes Request                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Onboarding API Service                                      │
│    1. Validate input (schema, permissions)                   │
│    2. Check if service already exists                        │
│    3. Load archetype template                                │
│    4. Load profile + size configuration                      │
│    5. Update catalog/services.yaml                           │
│    6. Commit to Git                                          │
│    7. Call Harness API to create pipeline                    │
│                                                              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Harness Pipeline Created                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Harness API Response                                        │
│    Pipeline ID: payment-service-cd                           │
│    Stages:                                                   │
│      - int-stable (auto-approve)                             │
│      - pre-stable (1-hour delay)                             │
│      - prod (manual approval)                                │
│                                                              │
│    Pipeline URL: https://harness.io/pipelines/payment-...    │
│                                                              │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: First Deployment Triggered                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Harness Pipeline Execution                                  │
│    Stage 1: int-stable                                       │
│      ├─ Fetch kustomize config from Git                     │
│      ├─ Generate manifests (kustomize build)                 │
│      ├─ Validate manifests                                   │
│      ├─ Deploy to int-stable cluster                         │
│      └─ Health check ✓                                       │
│                                                              │
│    Stage 2: pre-stable                                       │
│      ├─ Wait for approval (1-hour timeout)                   │
│      ├─ Deploy to pre-stable cluster                         │
│      └─ Health check ✓                                       │
│                                                              │
│    Stage 3: prod                                             │
│      ├─ Wait for manual approval                             │
│      ├─ Check change window                                  │
│      ├─ Deploy to prod cluster                               │
│      └─ Health check ✓                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Service Catalog Structure

**Option A: Single Catalog File** (Recommended)

```yaml
# kustomize/catalog/services.yaml
services:
  - name: account-service
    archetype: api
    profile: public-api
    size: medium
    environments: [int, pre, prod]
    team: platform-team-a
    slack: "#team-platform-a"
    pagerduty: pd-team-a
    
    # Harness-specific
    harness:
      pipelineId: account-service-cd  # Auto-generated
      createdAt: "2025-11-08T10:30:00Z"
      createdBy: user@company.com
  
  - name: payment-service
    archetype: api
    profile: public-api
    size: large
    environments: [int, pre, prod]
    team: payments-team
    harness:
      pipelineId: payment-service-cd
      createdAt: "2025-11-08T11:00:00Z"
```

**Option B: Per-Archetype Catalogs**

```
catalog/
├── api-services.yaml       # All API services
├── listener-services.yaml  # All listener services
├── job-services.yaml       # All batch jobs
└── scheduler-services.yaml # All scheduled tasks
```

**Recommendation**: Start with **Option A** (single file), split later if it grows > 500 services.

---

### 2. Self-Service UI

**Technology Stack**:
- Frontend: React + Material-UI / Next.js
- Backend: Node.js / Python (FastAPI)
- Database: PostgreSQL (for audit trail)
- Auth: SSO (Okta, Auth0)

**UI Screens**:

#### Screen 1: Service Onboarding

```
┌────────────────────────────────────────────────────────────┐
│  Create New Service                                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Basic Information                                         │
│  ────────────────────────────────────────────────────────  │
│                                                            │
│  Service Name:                                             │
│  [payment-service_____________________________]            │
│                                                            │
│  Team:                                                     │
│  [Payments Team ▼]                                         │
│                                                            │
│  Archetype:                                                │
│  ○ API (HTTP/REST services)                                │
│  ○ Listener (Event consumers)                              │
│  ○ Streaming (WebSocket/long-lived)                        │
│  ○ Scheduler (Periodic tasks)                              │
│  ○ Job (One-time batch)                                    │
│                                                            │
│  Profile (Behavior):                                       │
│  [Public API ▼]                                            │
│    - External exposure via Ingress                         │
│    - Retry policies, Circuit breaker                       │
│    - Mutual TLS, High availability                         │
│                                                            │
│  Resource Size:                                            │
│  ○ Small   (100m CPU, 256Mi RAM) - Low traffic             │
│  ● Medium  (250m CPU, 512Mi RAM) - Standard                │
│  ○ Large   (500m CPU, 1Gi RAM)   - High traffic            │
│  ○ X-Large (1000m CPU, 2Gi RAM)  - Very high               │
│                                                            │
│  Deployment Environments:                                  │
│  ☑ Integration (int-stable)                                │
│  ☑ Pre-Production (pre-stable)                             │
│  ☑ Production (prod)                                       │
│                                                            │
│  Regions:                                                  │
│  ☑ EU West 1 (euw1) - Primary                              │
│  ☑ EU West 2 (euw2) - DR                                   │
│                                                            │
│  ────────────────────────────────────────────────────────  │
│                                                            │
│  Ownership & Notifications                                 │
│  ────────────────────────────────────────────────────────  │
│                                                            │
│  Slack Channel:                                            │
│  [#team-payments_______________________________]           │
│                                                            │
│  PagerDuty Escalation:                                     │
│  [pd-payments-team ▼]                                      │
│                                                            │
│  Email Notifications:                                      │
│  [payments-team@company.com____________________]           │
│                                                            │
│  ────────────────────────────────────────────────────────  │
│                                                            │
│         [Cancel]  [Preview Config]  [Create Service]       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### Screen 2: Pipeline Creation Preview

```
┌────────────────────────────────────────────────────────────┐
│  Review & Create                                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  This will create:                                         │
│                                                            │
│  1. ✓ Add entry to service catalog                        │
│     → kustomize/catalog/services.yaml                      │
│                                                            │
│  2. ✓ Generate Harness CD pipeline                        │
│     → Pipeline: payment-service-cd                         │
│     → Stages: int-stable → pre-stable → prod               │
│                                                            │
│  3. ✓ Configure approval gates                            │
│     → int-stable: Auto-approve                             │
│     → pre-stable: 1-hour wait                              │
│     → prod: Manual approval (team + platform)              │
│                                                            │
│  4. ✓ Setup RBAC permissions                               │
│     → Payments Team: Execute, view, approve (non-prod)     │
│     → Platform Team: All permissions                       │
│                                                            │
│  Generated Configuration:                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ name: payment-service                                │ │
│  │ archetype: api                                       │ │
│  │ profile: public-api                                  │ │
│  │ size: medium                                         │ │
│  │ environments: [int, pre, prod]                       │ │
│  │ team: payments-team                                  │ │
│  │ ...                                                  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Pipeline YAML: [Download] [View in Harness]              │
│                                                            │
│  Estimated Time to Deploy:                                 │
│    • Pipeline creation: ~2 minutes                         │
│    • First deployment: ~5-10 minutes                       │
│                                                            │
│  ☐ Deploy to int-stable immediately after creation        │
│                                                            │
│         [Back]              [Confirm & Create]             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### Screen 3: Pipeline Dashboard

```
┌────────────────────────────────────────────────────────────┐
│  My Services                                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  [Search services...] [+ New Service]                      │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ payment-service                    [API] [Medium]    │ │
│  │ Last deployed: 2 hours ago by user@company.com       │ │
│  │                                                       │ │
│  │ Environments:                                         │ │
│  │   ✓ int-stable  (v1.2.3) - Healthy                   │ │
│  │   ✓ pre-stable  (v1.2.3) - Healthy                   │ │
│  │   ✓ prod        (v1.2.1) - Healthy                   │ │
│  │                                                       │ │
│  │ [View Pipeline] [Deploy] [Edit Config] [Logs]        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ account-service                    [API] [Large]     │ │
│  │ Last deployed: 1 day ago by teammate@company.com     │ │
│  │                                                       │ │
│  │ Environments:                                         │ │
│  │   ✓ int-stable  (v2.0.0) - Healthy                   │ │
│  │   ⚠ pre-stable  (v2.0.0) - Degraded (1/3 pods)       │ │
│  │   ✓ prod        (v1.9.5) - Healthy                   │ │
│  │                                                       │ │
│  │ [View Pipeline] [Deploy] [Edit Config] [Logs]        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

### 3. Harness Pipeline Template

**Harness Pipeline YAML Template**:

```yaml
# templates/harness-pipeline-template.yaml
pipeline:
  name: "{{SERVICE_NAME}}-cd"
  identifier: "{{SERVICE_NAME}}_cd"
  projectIdentifier: platform
  orgIdentifier: default
  
  tags:
    archetype: "{{ARCHETYPE}}"
    team: "{{TEAM}}"
    size: "{{SIZE}}"
  
  properties:
    ci:
      codebase:
        connectorRef: github_platform_next
        repoName: platform-next
        build:
          type: branch
          spec:
            branch: main
  
  stages:
    # Stage 1: Int-Stable
    - stage:
        name: Deploy to Int-Stable
        identifier: int_stable
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: "{{SERVICE_NAME}}"
            serviceDefinition:
              type: Kubernetes
              spec:
                variables: []
                manifests:
                  - manifest:
                      identifier: kustomize_manifests
                      type: Kustomize
                      spec:
                        store:
                          type: Github
                          spec:
                            connectorRef: github_platform_next
                            gitFetchType: Branch
                            branch: main
                            paths:
                              - kustomize/archetype/{{ARCHETYPE}}
                              - kustomize/envs/int-stable
                              - kustomize/regions/euw1
                        overlayConfiguration:
                          kustomizeYamlFolderPath: generated/{{SERVICE_NAME}}/int-stable/euw1
          
          environment:
            environmentRef: int_stable_euw1
            deployToAll: false
            infrastructureDefinitions:
              - identifier: int_stable_k8s
          
          execution:
            steps:
              - step:
                  type: K8sManifest
                  name: Fetch Manifests
                  identifier: fetch_manifests
                  spec:
                    skipDryRun: false
              
              - step:
                  type: ShellScript
                  name: Generate Kustomization
                  identifier: generate_kustomization
                  spec:
                    shell: Bash
                    source:
                      type: Inline
                      spec:
                        script: |
                          #!/bin/bash
                          ./scripts/generate-kz-v3.sh {{SERVICE_NAME}} int-stable euw1
              
              - step:
                  type: K8sApply
                  name: Deploy
                  identifier: deploy
                  spec:
                    filePaths:
                      - generated/{{SERVICE_NAME}}/int-stable/euw1
                    skipDryRun: false
                    skipSteadyStateCheck: false
              
              - step:
                  type: K8sRollingDeploy
                  name: Rolling Deploy
                  identifier: rolling_deploy
                  spec:
                    skipDryRun: false
              
              - step:
                  type: ShellScript
                  name: Health Check
                  identifier: health_check
                  spec:
                    shell: Bash
                    source:
                      type: Inline
                      spec:
                        script: |
                          #!/bin/bash
                          ./scripts/health-check.sh {{SERVICE_NAME}} int-stable euw1
            
            rollbackSteps:
              - step:
                  type: K8sRollingRollback
                  name: Rollback
                  identifier: rollback
        
        failureStrategies:
          - onFailure:
              errors:
                - AllErrors
              action:
                type: StageRollback
    
    # Stage 2: Pre-Stable (with delay)
    - stage:
        name: Deploy to Pre-Stable
        identifier: pre_stable
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            useFromStage:
              stage: int_stable
          environment:
            environmentRef: pre_stable_euw1
            infrastructureDefinitions:
              - identifier: pre_stable_k8s
          
          execution:
            steps:
              - step:
                  type: HarnessApproval
                  name: Auto-Approve After Delay
                  identifier: auto_approve_delay
                  spec:
                    approvalMessage: "Auto-approving after 1 hour bake time in int-stable"
                    includePipelineExecutionHistory: true
                    approvers:
                      userGroups:
                        - account.{{TEAM}}
                    minimumCount: 1
                    disallowPipelineExecutor: false
                    approverInputs: []
                  timeout: 1h
                  failureStrategies:
                    - onFailure:
                        errors:
                          - Timeout
                        action:
                          type: MarkAsSuccess  # Auto-approve on timeout
              
              # Same deploy steps as int-stable
              - step:
                  type: K8sRollingDeploy
                  name: Deploy
                  identifier: deploy
    
    # Stage 3: Production (manual approval)
    - stage:
        name: Deploy to Production
        identifier: prod
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            useFromStage:
              stage: int_stable
          environment:
            environmentRef: prod_euw1
            infrastructureDefinitions:
              - identifier: prod_k8s
          
          execution:
            steps:
              - step:
                  type: HarnessApproval
                  name: Production Approval
                  identifier: prod_approval
                  spec:
                    approvalMessage: |
                      Production deployment for {{SERVICE_NAME}}
                      
                      Changes:
                      - Version: <+pipeline.stages.int_stable.spec.artifacts.primary.tag>
                      - Size: {{SIZE}}
                      - Team: {{TEAM}}
                      
                      Approvers required: 2 (1 from team, 1 from platform)
                    
                    approvers:
                      userGroups:
                        - account.{{TEAM}}
                        - account.platform_team
                      minimumCount: 2
                      disallowPipelineExecutor: true
                    
                    approverInputs:
                      - name: change_ticket
                        type: String
                        label: "Change Ticket ID"
                        required: true
                      - name: rollback_plan
                        type: String
                        label: "Rollback Plan"
                        required: true
                  
                  timeout: 7d  # 1 week max
              
              - step:
                  type: ShellScript
                  name: Check Change Window
                  identifier: check_change_window
                  spec:
                    shell: Bash
                    source:
                      type: Inline
                      spec:
                        script: |
                          #!/bin/bash
                          # Check if current time is within allowed change window
                          ./scripts/check-change-window.sh prod
              
              # Deploy with canary
              - step:
                  type: K8sCanaryDeploy
                  name: Canary Deploy (10%)
                  identifier: canary_10
                  spec:
                    instanceSelection:
                      type: Count
                      spec:
                        count: 1
                    skipDryRun: false
              
              - step:
                  type: ShellScript
                  name: Smoke Test
                  identifier: smoke_test
                  spec:
                    shell: Bash
                    source:
                      type: Inline
                      spec:
                        script: |
                          ./scripts/smoke-test.sh {{SERVICE_NAME}} prod
              
              - step:
                  type: K8sCanaryDeploy
                  name: Canary Deploy (50%)
                  identifier: canary_50
                  spec:
                    instanceSelection:
                      type: Percentage
                      spec:
                        percentage: 50
              
              - step:
                  type: K8sCanaryDelete
                  name: Full Rollout
                  identifier: full_rollout
            
            rollbackSteps:
              - step:
                  type: K8sRollingRollback
                  name: Rollback
                  identifier: rollback
  
  # Triggers
  triggers:
    - trigger:
        name: On Catalog Update
        identifier: catalog_update
        enabled: true
        source:
          type: Webhook
          spec:
            type: Github
            spec:
              type: PullRequest
              spec:
                connectorRef: github_platform_next
                autoAbortPreviousExecutions: false
                payloadConditions:
                  - key: changedFiles
                    operator: Contains
                    value: "kustomize/catalog/services.yaml"
                  - key: <+trigger.payload.pull_request.merged>
                    operator: Equals
                    value: "true"
                actions:
                  - type: PullRequest
                headerConditions: []
                repoName: platform-next
                actions:
                  - Closed
        inputYaml: |
          identifier: {{SERVICE_NAME}}_cd
```

---

### 4. Backend Service (Pipeline Generator)

**API Endpoints**:

```typescript
// API Specification (OpenAPI)

POST /api/v1/services
  Description: Create new service and generate Harness pipeline
  Request:
    {
      "name": "payment-service",
      "archetype": "api",
      "profile": "public-api",
      "size": "medium",
      "environments": ["int", "pre", "prod"],
      "team": "payments-team",
      "slack": "#team-payments",
      "pagerduty": "pd-payments"
    }
  Response:
    {
      "serviceId": "payment-service",
      "catalogUpdated": true,
      "pipelineId": "payment-service-cd",
      "pipelineUrl": "https://harness.io/ng/account/abc/cd/orgs/default/projects/platform/pipelines/payment-service-cd",
      "status": "created"
    }

GET /api/v1/services/{serviceName}
  Description: Get service configuration and pipeline status
  
PUT /api/v1/services/{serviceName}
  Description: Update service configuration and pipeline

DELETE /api/v1/services/{serviceName}
  Description: Delete service and pipeline
```

**Implementation (Python FastAPI)**:

```python
# backend/api/services.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import yaml
import git
import requests

app = FastAPI()

class ServiceCreate(BaseModel):
    name: str
    archetype: str
    profile: str
    size: str
    environments: List[str]
    team: str
    slack: str
    pagerduty: str

class HarnessClient:
    def __init__(self, api_key: str, account_id: str):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = f"https://app.harness.io/gateway/ng/api"
    
    def create_pipeline(self, service_name: str, template_vars: dict) -> dict:
        """Create Harness pipeline from template"""
        
        # Load pipeline template
        with open('templates/harness-pipeline-template.yaml', 'r') as f:
            template = f.read()
        
        # Replace variables
        pipeline_yaml = template
        for key, value in template_vars.items():
            pipeline_yaml = pipeline_yaml.replace(f"{{{{{key}}}}}", str(value))
        
        # Create pipeline via Harness API
        url = f"{self.base_url}/pipelines"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/yaml"
        }
        
        response = requests.post(
            url,
            headers=headers,
            params={
                "accountIdentifier": self.account_id,
                "orgIdentifier": "default",
                "projectIdentifier": "platform"
            },
            data=pipeline_yaml
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create pipeline: {response.text}")
        
        return response.json()

@app.post("/api/v1/services")
async def create_service(service: ServiceCreate):
    try:
        # 1. Validate input
        if service.archetype not in ["api", "listener", "streaming", "scheduler", "job"]:
            raise HTTPException(400, "Invalid archetype")
        
        # 2. Load catalog
        repo = git.Repo('.')
        with open('kustomize/catalog/services.yaml', 'r') as f:
            catalog = yaml.safe_load(f)
        
        # 3. Check if service already exists
        existing = [s for s in catalog['services'] if s['name'] == service.name]
        if existing:
            raise HTTPException(409, f"Service {service.name} already exists")
        
        # 4. Add to catalog
        catalog['services'].append({
            "name": service.name,
            "archetype": service.archetype,
            "profile": service.profile,
            "size": service.size,
            "environments": service.environments,
            "team": service.team,
            "slack": service.slack,
            "pagerduty": service.pagerduty,
            "harness": {
                "pipelineId": f"{service.name}-cd",
                "createdAt": datetime.utcnow().isoformat() + "Z"
            }
        })
        
        # 5. Commit to Git
        with open('kustomize/catalog/services.yaml', 'w') as f:
            yaml.dump(catalog, f)
        
        repo.index.add(['kustomize/catalog/services.yaml'])
        repo.index.commit(f"Add service: {service.name}")
        repo.remote('origin').push()
        
        # 6. Create Harness pipeline
        harness = HarnessClient(
            api_key=os.getenv("HARNESS_API_KEY"),
            account_id=os.getenv("HARNESS_ACCOUNT_ID")
        )
        
        pipeline = harness.create_pipeline(
            service_name=service.name,
            template_vars={
                "SERVICE_NAME": service.name,
                "ARCHETYPE": service.archetype,
                "TEAM": service.team,
                "SIZE": service.size
            }
        )
        
        # 7. Return response
        return {
            "serviceId": service.name,
            "catalogUpdated": True,
            "pipelineId": pipeline['data']['identifier'],
            "pipelineUrl": f"https://harness.io/ng/account/{harness.account_id}/cd/orgs/default/projects/platform/pipelines/{pipeline['data']['identifier']}",
            "status": "created"
        }
    
    except Exception as e:
        raise HTTPException(500, str(e))
```

---

## Pros & Cons Analysis

### ✅ Pros

#### 1. **True Pipeline Isolation**
- Each service has dedicated pipeline
- No contention, no queuing
- Independent execution
- **Impact**: Unlimited scalability

#### 2. **Single Catalog File**
- Simpler to manage than 100+ files
- Easier to search/query
- Better for UI rendering
- No merge conflicts (UI updates, not manual edits)
- **Impact**: Better developer experience

#### 3. **Harness Native Features**
- Built-in approval workflows
- Canary deployments
- Blue-green deployments
- Pipeline templates
- RBAC at pipeline level
- **Impact**: Production-grade CD out of the box

#### 4. **Fine-Grained Control**
- Pause/resume per service
- Rollback per service
- Different approval rules per service
- Custom change windows per service
- **Impact**: Better production safety

#### 5. **Audit & Compliance**
- Harness tracks every deployment
- Who approved what, when
- Change ticket integration
- Compliance reporting
- **Impact**: Meets enterprise requirements

#### 6. **Team Autonomy**
- Teams own their pipelines
- Can customize stages (within template)
- Can trigger deployments
- Can view logs/metrics
- **Impact**: Developer empowerment

#### 7. **Easier Migration**
- Similar to current Helm-based Harness setup
- Teams already know Harness
- Reuse existing Harness infrastructure
- **Impact**: Lower learning curve

#### 8. **Progressive Delivery**
- Canary per service
- Traffic splitting
- Automated rollback on metrics
- **Impact**: Safer deployments

#### 9. **Cost Predictability**
- Pay per pipeline execution
- Clear cost per service
- Can set execution limits
- **Impact**: Better cost management

#### 10. **Integration Ecosystem**
- Harness integrates with PagerDuty, Slack, Jira
- ServiceNow change management
- Datadog/New Relic/Prometheus
- **Impact**: Better operational visibility

---

### ❌ Cons

#### 1. **Pipeline Sprawl**
- 100 services = 100 pipelines in Harness
- Harness UI can become cluttered
- Harder to get "all services" overview
- **Mitigation**: Use folders, tags, filters in Harness

#### 2. **Template Management Complexity**
- Need to version pipeline templates
- Updating templates requires updating 100 pipelines
- Risk of template drift
- **Mitigation**: Harness template library + update script

#### 3. **Harness API Rate Limits**
- Creating 100 pipelines at once may hit rate limits
- API throttling during bulk operations
- **Mitigation**: Rate-limit the onboarding API, batch operations

#### 4. **Cost**
- Harness pricing per pipeline execution
- 100 services × 3 envs × daily deploys = $$$
- More expensive than GitOps (ArgoCD is free)
- **Mitigation**: Set execution quotas, use free tier wisely

#### 5. **Pipeline Garbage Collection**
- Deleted services leave orphaned pipelines
- Need cleanup automation
- **Mitigation**: Implement pipeline cleanup job

#### 6. **Catalog Trigger Complexity**
- Catalog change must trigger specific pipeline creation
- Need webhook → API → Harness flow
- More moving parts than GitOps
- **Mitigation**: Robust error handling, retries

#### 7. **Harness Dependency**
- Locked into Harness platform
- Migration away from Harness is hard
- Vendor lock-in
- **Mitigation**: Keep kustomize layer portable

#### 8. **Pipeline Update Lag**
- Archetype/component changes don't auto-update pipelines
- Need to regenerate pipelines
- Risk of stale pipelines
- **Mitigation**: Pipeline update automation

#### 9. **Testing Complexity**
- Can't easily test pipeline changes locally
- Need Harness sandbox environment
- **Mitigation**: Harness git-sync for pipeline-as-code

#### 10. **Learning Curve for New Teams**
- Need to understand Harness concepts
- More complex than "git push"
- Documentation overhead
- **Mitigation**: Good onboarding docs, videos

---

## Comparison Matrix

| Aspect | Harness Per-Service Pipelines | GitOps (ArgoCD) | GitHub Actions Matrix |
|--------|-------------------------------|-----------------|----------------------|
| **Scalability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Moderate |
| **Catalog Management** | ⭐⭐⭐⭐⭐ Single file | ⭐⭐⭐ Per-service files | ⭐⭐⭐ Per-service files |
| **Approval Control** | ⭐⭐⭐⭐⭐ Native workflows | ⭐⭐⭐ PR-based | ⭐⭐⭐⭐ Actions + approvals |
| **Prod Safety** | ⭐⭐⭐⭐⭐ Multi-gate, canary | ⭐⭐⭐⭐ Sync waves | ⭐⭐⭐ Manual gates |
| **Cost** | ⭐⭐ Expensive | ⭐⭐⭐⭐⭐ Free | ⭐⭐⭐⭐ Free (OSS) |
| **Complexity** | ⭐⭐⭐ Moderate | ⭐⭐ Low | ⭐⭐⭐⭐ High |
| **Vendor Lock-in** | ⭐⭐ High | ⭐⭐⭐⭐ Low | ⭐⭐⭐⭐ Low |
| **Team Familiarity** | ⭐⭐⭐⭐⭐ Already using | ⭐⭐ New tool | ⭐⭐⭐⭐ Know GitHub |
| **RBAC** | ⭐⭐⭐⭐⭐ Pipeline-level | ⭐⭐⭐⭐ App-level | ⭐⭐⭐ Repo-level |
| **Audit Trail** | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐ Git history | ⭐⭐⭐ Actions logs |

---

## Implementation Plan

### Phase 1: Proof of Concept (Week 1-2)

**Goal**: Validate approach with 3 pilot services

1. **Setup Infrastructure**
   - Deploy backend API (FastAPI)
   - Setup PostgreSQL for audit
   - Configure Harness API access

2. **Create Pipeline Template**
   - Define Harness pipeline template
   - Test with one service manually

3. **Build UI Prototype**
   - Simple React form
   - Preview configuration
   - Call backend API

4. **Pilot Services**
   - Migrate 3 services to new approach
   - Test end-to-end flow
   - Gather feedback

**Success Criteria**:
- ✅ Can create service via UI in < 5 min
- ✅ Pipeline deploys to int-stable automatically
- ✅ Manual approval works for prod

---

### Phase 2: Core Features (Week 3-4)

1. **Enhance UI**
   - Add service listing page
   - Pipeline status dashboard
   - Edit service configuration

2. **Template Management**
   - Version pipeline templates
   - Create templates per archetype
   - Test template updates

3. **RBAC Integration**
   - Connect to Okta/SSO
   - Map teams to Harness user groups
   - Implement permission checks

4. **Migrate 20 Services**
   - Validate scalability
   - Test concurrent pipeline executions

**Success Criteria**:
- ✅ 20 pipelines running independently
- ✅ No Harness performance issues
- ✅ Teams can self-service

---

### Phase 3: Production Readiness (Week 5-6)

1. **Observability**
   - Harness → Datadog integration
   - Slack notifications
   - PagerDuty escalations

2. **Cleanup Automation**
   - Detect orphaned pipelines
   - Archive old pipelines
   - Garbage collection

3. **Template Update Automation**
   - Bulk pipeline update script
   - Test before apply
   - Rollback mechanism

4. **Documentation**
   - User guide
   - Video tutorials
   - Runbooks

**Success Criteria**:
- ✅ Production-grade monitoring
- ✅ Self-healing (auto-cleanup)
- ✅ Complete documentation

---

### Phase 4: Full Migration (Week 7-12)

1. **Migrate Remaining Services**
   - 10 services per week
   - Validate each batch
   - Monitor Harness usage/cost

2. **Decommission Old System**
   - Archive old Helm charts
   - Document migration
   - Celebrate! 🎉

---

## Cost Analysis

### Harness Pricing (Estimated)

**Assumptions**:
- 100 services
- 3 environments per service
- 5 deployments per service per week
- Harness pricing: ~$100/month per service pipeline

**Monthly Cost**:
```
100 services × $100/month = $10,000/month
```

**Annual Cost**: ~$120,000/year

**Compare to**:
- ArgoCD: $0 (open-source)
- GitHub Actions: ~$0 (within free tier)
- Engineer time saved: Priceless

**ROI Calculation**:
- Platform team time saved: 40 hours/month (worth $10,000)
- Developer time saved: 200 hours/month (worth $50,000)
- Faster deployments: Ship features faster (hard to quantify)

**Verdict**: Worth it if you value time > cost

---

## Decision Matrix

### When to Use This Approach

**✅ Use Harness Per-Service Pipelines if**:
1. Already using Harness (sunk cost)
2. Need enterprise-grade approvals
3. Compliance requirements (audit trail)
4. Team prefers UI over Git
5. Budget allows ($10K+/month)
6. Need canary/blue-green deployments
7. Integration with ServiceNow, PagerDuty
8. Production deployments require human gates

**❌ Don't Use This Approach if**:
1. Cost-sensitive (Harness is expensive)
2. Prefer open-source (ArgoCD is free)
3. Simple use case (GitHub Actions sufficient)
4. Small team (< 20 services)
5. GitOps is mandated
6. Want to avoid vendor lock-in

---

## Final Recommendation

### Verdict: **This Approach is VALID and WORTH TRYING**

**Why?**:
1. ✅ Solves scalability problem elegantly
2. ✅ Leverages existing Harness investment
3. ✅ Better production controls than GitOps
4. ✅ Single catalog file (cleaner than per-service files)
5. ✅ Teams already know Harness

**Caveats**:
1. ⚠️ Expensive (but you save engineer time)
2. ⚠️ Vendor lock-in (but kustomize is portable)
3. ⚠️ Template management (but solvable)

### Hybrid Approach (Best of Both Worlds)

**Use Harness for Production**, **Use GitOps for Non-Prod**:

```
Non-Prod (int, pre):
  → GitOps (ArgoCD) for fast iteration

Production:
  → Harness pipelines with approvals
```

**Benefits**:
- Free ArgoCD for dev/test
- Paid Harness for prod (only 100 pipelines, not 300)
- Best of both worlds

---

## Next Steps

1. **Pilot with 3 Services**
   - Build POC (2 weeks)
   - Test end-to-end
   - Measure time/cost

2. **Decision Point**
   - If POC succeeds → full migration
   - If issues found → reassess

3. **Go/No-Go Criteria**
   - Can onboard service in < 5 min? ✅
   - Pipelines run independently? ✅
   - Cost acceptable? ✅
   - Team approves? ✅

**If all ✅ → Proceed with full implementation**

---

**This is a solid, production-ready approach!** 🚀
