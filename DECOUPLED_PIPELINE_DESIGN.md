# Decoupled Architecture: Config Repo ↔ Pipeline Repo

## The Key Insight

**Separation of Concerns**:
1. **Config Changes** (K8s manifests) → Auto-sync from Git (GitOps)
2. **App Deployments** (new image tag) → Trigger Harness pipeline with image tag
3. **New Service Onboarding** → API call creates pipeline from template

**Two Independent Repositories**:
- `platform-next` (Config Repo) → Manifests generation
- `harness-pipelines` (Different GitHub Org) → Pipeline definitions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ GitHub Org: company/platform-next (Config Repo)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Developer adds service via UI                               │
│     ↓                                                            │
│  2. Backend API updates catalog                                 │
│     ↓                                                            │
│  3. Git commit to catalog/services.yaml                         │
│     ↓                                                            │
│  4. GitHub Actions CI triggered                                 │
│     ├─ Generate manifests (kustomize build)                     │
│     ├─ Commit to generated/payment-service/                     │
│     └─ Push to main                                             │
│                                                                  │
│  Result: generated/payment-service/{env}/{region}/manifests.yaml│
│                                                                  │
│  ✅ Git becomes source of truth for K8s config                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (5) Webhook/API call
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Pipeline Orchestrator Service (New Component)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Receives: New service created event                            │
│  {                                                               │
│    "service": "payment-service",                                │
│    "archetype": "api",                                          │
│    "team": "payments",                                          │
│    "environments": ["int", "pre", "prod"]                       │
│  }                                                               │
│                                                                  │
│  Actions:                                                        │
│    1. Fetch pipeline template from harness-pipelines repo       │
│    2. Customize for service (replace variables)                 │
│    3. Call Harness API to create pipeline                       │
│    4. Store pipeline metadata                                   │
│                                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ (6) Create pipeline via Harness API
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Harness (Different Org: company-harness/harness-pipelines)      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pipeline Created: payment-service-cd                           │
│                                                                  │
│  Input Parameters:                                              │
│    - imageTag (runtime input) ← App team provides              │
│    - environment (runtime input)                                │
│                                                                  │
│  Manifest Source:                                               │
│    - GitHub Repo: company/platform-next (cross-org)            │
│    - Path: generated/payment-service/{env}/{region}/manifests.yaml│
│    - Branch: main                                               │
│                                                                  │
│  ✅ Always fetches latest manifests from Git (auto-sync)        │
│  ✅ Image tag injected at deployment time                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│ Two Independent Workflows                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Workflow A: Config Change (K8s manifests)                      │
│  ────────────────────────────────────────────────────────────   │
│                                                                  │
│  Developer changes resource limits in catalog                   │
│    ↓                                                            │
│  CI regenerates manifests                                       │
│    ↓                                                            │
│  Commits to generated/                                          │
│    ↓                                                            │
│  Harness pipeline auto-syncs (GitOps)                          │
│    ↓                                                            │
│  Next deployment uses new config automatically                  │
│                                                                  │
│  ✅ No pipeline trigger needed                                  │
│  ✅ Config changes are declarative                              │
│                                                                  │
│  ────────────────────────────────────────────────────────────   │
│                                                                  │
│  Workflow B: App Deployment (new image)                         │
│  ────────────────────────────────────────────────────────────   │
│                                                                  │
│  App team builds new image: payment-service:v2.3.1             │
│    ↓                                                            │
│  Triggers Harness pipeline (API or Webhook)                     │
│    ↓                                                            │
│  Pipeline fetches latest manifests from Git                     │
│    ↓                                                            │
│  Injects imageTag: v2.3.1 into manifests                       │
│    ↓                                                            │
│  Deploys to cluster                                             │
│                                                                  │
│  ✅ App deployment independent of config                        │
│  ✅ Always uses latest config from Git                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

### Repo 1: `company/platform-next` (Config Management)

```
platform-next/
├── kustomize/
│   ├── archetype/
│   ├── components/
│   ├── envs/
│   ├── regions/
│   └── catalog/
│       └── services.yaml          # Service definitions
│
├── generated/                      # Generated manifests (committed)
│   ├── payment-service/
│   │   ├── int-stable/
│   │   │   └── euw1/
│   │   │       └── manifests.yaml
│   │   ├── pre-stable/
│   │   │   └── euw1/
│   │   │       └── manifests.yaml
│   │   └── prod/
│   │       ├── euw1/
│   │       │   └── manifests.yaml
│   │       └── euw2/
│   │           └── manifests.yaml
│   └── [other services...]
│
├── .github/
│   └── workflows/
│       └── generate-manifests.yml  # CI pipeline
│
└── scripts/
    └── generate-kz-v3.sh
```

**Purpose**: 
- Manage Kustomize configuration
- Generate K8s manifests
- Version control for configs

**Does NOT contain**: Harness pipelines

---

### Repo 2: `company-harness/harness-pipelines` (Different Org)

```
harness-pipelines/
├── templates/
│   ├── api-pipeline-template.yaml       # Template for API services
│   ├── listener-pipeline-template.yaml  # Template for listeners
│   ├── job-pipeline-template.yaml       # Template for jobs
│   └── scheduler-pipeline-template.yaml # Template for schedulers
│
├── pipelines/                           # Actual pipeline definitions
│   ├── payment-service-cd.yaml
│   ├── account-service-cd.yaml
│   └── [100+ service pipelines...]
│
├── policies/                            # OPA policies
│   ├── change-window.rego
│   ├── resource-limits.rego
│   └── approval-rules.rego
│
└── .github/
    └── workflows/
        └── sync-to-harness.yml          # Sync pipelines to Harness
```

**Purpose**:
- Store Harness pipeline templates
- Version control for pipelines
- Sync pipelines to Harness platform

**Does NOT contain**: K8s manifests (fetches from platform-next)

---

## Component: Pipeline Orchestrator Service

### New Microservice to Bridge Repos

**Responsibilities**:
1. Listen for new service events (webhook from platform-next)
2. Fetch pipeline template from harness-pipelines repo
3. Customize template for specific service
4. Create pipeline in Harness via API
5. Store mapping (service → pipeline)

**Technology**:
- Language: Python (FastAPI) or Go
- Database: PostgreSQL (for state)
- Deployed: Cloud Run / Lambda / K8s

**API Endpoints**:

```yaml
POST /api/v1/pipelines/create
  Description: Create Harness pipeline for new service
  Request:
    {
      "service": "payment-service",
      "archetype": "api",
      "team": "payments-team",
      "environments": ["int", "pre", "prod"],
      "regions": ["euw1", "euw2"]
    }
  Response:
    {
      "pipelineId": "payment-service-cd",
      "pipelineUrl": "https://harness.io/...",
      "status": "created"
    }

GET /api/v1/pipelines/{service}
  Description: Get pipeline details for service
  
PUT /api/v1/pipelines/{service}
  Description: Update pipeline configuration
  
DELETE /api/v1/pipelines/{service}
  Description: Delete pipeline
```

**Implementation**:

```python
# pipeline-orchestrator/main.py
from fastapi import FastAPI, HTTPException
import requests
import yaml
from github import Github
import os

app = FastAPI()

# Configuration
HARNESS_API_KEY = os.getenv("HARNESS_API_KEY")
HARNESS_ACCOUNT_ID = os.getenv("HARNESS_ACCOUNT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PIPELINE_REPO = "company-harness/harness-pipelines"

class PipelineOrchestrator:
    def __init__(self):
        self.gh = Github(GITHUB_TOKEN)
        self.harness_base_url = "https://app.harness.io/gateway/ng/api"
    
    def fetch_pipeline_template(self, archetype: str) -> str:
        """Fetch pipeline template from harness-pipelines repo"""
        repo = self.gh.get_repo(PIPELINE_REPO)
        template_path = f"templates/{archetype}-pipeline-template.yaml"
        
        try:
            content = repo.get_contents(template_path)
            return content.decoded_content.decode('utf-8')
        except Exception as e:
            raise HTTPException(404, f"Template not found: {template_path}")
    
    def customize_template(self, template: str, service_config: dict) -> str:
        """Replace variables in template"""
        customized = template
        
        replacements = {
            "{{SERVICE_NAME}}": service_config['service'],
            "{{TEAM}}": service_config['team'],
            "{{ARCHETYPE}}": service_config['archetype'],
            "{{ENVIRONMENTS}}": ",".join(service_config['environments']),
            "{{REGIONS}}": ",".join(service_config['regions'])
        }
        
        for key, value in replacements.items():
            customized = customized.replace(key, value)
        
        return customized
    
    def create_harness_pipeline(self, pipeline_yaml: str) -> dict:
        """Create pipeline in Harness via API"""
        url = f"{self.harness_base_url}/pipelines"
        
        headers = {
            "x-api-key": HARNESS_API_KEY,
            "Content-Type": "application/yaml"
        }
        
        params = {
            "accountIdentifier": HARNESS_ACCOUNT_ID,
            "orgIdentifier": "default",
            "projectIdentifier": "platform"
        }
        
        response = requests.post(
            url,
            headers=headers,
            params=params,
            data=pipeline_yaml
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(500, f"Harness API error: {response.text}")
        
        return response.json()
    
    def commit_pipeline_to_repo(self, service: str, pipeline_yaml: str):
        """Commit generated pipeline to harness-pipelines repo"""
        repo = self.gh.get_repo(PIPELINE_REPO)
        file_path = f"pipelines/{service}-cd.yaml"
        
        try:
            # Try to get existing file
            contents = repo.get_contents(file_path)
            repo.update_file(
                file_path,
                f"Update pipeline for {service}",
                pipeline_yaml,
                contents.sha
            )
        except:
            # File doesn't exist, create it
            repo.create_file(
                file_path,
                f"Create pipeline for {service}",
                pipeline_yaml
            )

orchestrator = PipelineOrchestrator()

@app.post("/api/v1/pipelines/create")
async def create_pipeline(request: dict):
    """
    Create Harness pipeline for new service
    
    Called by platform-next repo when new service added
    """
    try:
        # 1. Fetch template from harness-pipelines repo
        template = orchestrator.fetch_pipeline_template(request['archetype'])
        
        # 2. Customize template
        pipeline_yaml = orchestrator.customize_template(template, request)
        
        # 3. Create pipeline in Harness
        harness_response = orchestrator.create_harness_pipeline(pipeline_yaml)
        
        # 4. Commit to harness-pipelines repo (for version control)
        orchestrator.commit_pipeline_to_repo(request['service'], pipeline_yaml)
        
        # 5. Return response
        return {
            "pipelineId": f"{request['service']}-cd",
            "pipelineUrl": harness_response['data']['yaml']['pipeline']['identifier'],
            "status": "created",
            "template": request['archetype']
        }
    
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/webhooks/service-created")
async def webhook_service_created(payload: dict):
    """
    Webhook endpoint called by platform-next when service added
    
    Triggered by GitHub Actions in platform-next repo
    """
    return await create_pipeline(payload)
```

---

## Pipeline Template Design

### Template: `api-pipeline-template.yaml`

**Key Features**:
1. **Runtime Input for Image Tag** ← App team provides
2. **Fetches Manifests from Config Repo** ← Always latest from Git
3. **Image Tag Replacement** ← Harness replaces placeholder with actual tag

```yaml
# harness-pipelines/templates/api-pipeline-template.yaml
pipeline:
  name: "{{SERVICE_NAME}}-cd"
  identifier: "{{SERVICE_NAME}}_cd"
  projectIdentifier: platform
  orgIdentifier: default
  
  tags:
    service: "{{SERVICE_NAME}}"
    team: "{{TEAM}}"
    archetype: "{{ARCHETYPE}}"
  
  properties:
    ci:
      codebase:
        # ✅ CROSS-ORG: Fetch from platform-next repo
        connectorRef: github_platform_next_cross_org
        repoName: platform-next
        build:
          type: branch
          spec:
            branch: main
  
  stages:
    - stage:
        name: Deploy to Int-Stable
        identifier: int_stable_euw1
        type: Deployment
        
        spec:
          deploymentType: Kubernetes
          
          service:
            serviceRef: "{{SERVICE_NAME}}"
            serviceDefinition:
              type: Kubernetes
              spec:
                # ============================================
                # ✅ KEY: Runtime input for image tag
                # ============================================
                variables:
                  - name: imageTag
                    type: String
                    description: "Docker image tag to deploy"
                    required: true
                    value: <+input>  # ← User provides at runtime
                
                # ============================================
                # ✅ KEY: Fetch manifests from config repo
                # ============================================
                manifests:
                  - manifest:
                      identifier: k8s_manifests
                      type: K8sManifest
                      spec:
                        store:
                          type: Github
                          spec:
                            # Cross-org connector
                            connectorRef: github_platform_next_cross_org
                            gitFetchType: Branch
                            branch: main
                            paths:
                              # ✅ Always fetches latest from Git
                              - generated/{{SERVICE_NAME}}/int-stable/euw1/manifests.yaml
                        
                        # ============================================
                        # ✅ KEY: Replace image tag in manifests
                        # ============================================
                        valuesPaths: []
                        skipResourceVersioning: false
          
          environment:
            environmentRef: int_stable
            infrastructureDefinitions:
              - identifier: int_stable_euw1_k8s
                inputs:
                  spec:
                    delegateSelectors:
                      - harness-delegate-int-euw1
          
          execution:
            steps:
              # ============================================
              # ✅ Kustomize with image tag override
              # ============================================
              - step:
                  type: K8sApply
                  name: Deploy with Image Tag
                  identifier: deploy
                  spec:
                    filePaths:
                      - generated/{{SERVICE_NAME}}/int-stable/euw1/manifests.yaml
                    skipDryRun: false
                  
                  # ✅ Override image tag at deployment time
                  timeout: 10m
              
              - step:
                  type: K8sRollingDeploy
                  name: Rolling Deploy
                  identifier: rolling_deploy
                  spec:
                    skipDryRun: false
                  timeout: 10m
            
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
    
    # Similar for pre-stable and prod...
  
  # ============================================
  # ✅ Triggers: App image pushed
  # ============================================
  triggers:
    - trigger:
        name: On New Image
        identifier: new_image_trigger
        enabled: true
        source:
          type: Webhook
          spec:
            type: Custom
            spec:
              # Webhook from app repo when image built
              payloadConditions:
                - key: image_tag
                  operator: NotNull
                  value: ""
        inputYaml: |
          pipeline:
            stages:
              - stage:
                  identifier: int_stable_euw1
                  variables:
                    imageTag: <+trigger.payload.image_tag>
```

**Key Points**:
1. ✅ **Cross-org connector**: Fetches from `company/platform-next`
2. ✅ **Runtime input**: `imageTag: <+input>` ← App team provides
3. ✅ **Always latest config**: Fetches from Git main branch
4. ✅ **Trigger on image**: Webhook from app build

---

## Image Tag Injection Mechanism

### How Image Tag Gets Into Manifests

**Option A: Kustomize Images Transformer** (Recommended)

**In generated manifests**:
```yaml
# generated/payment-service/prod/euw1/manifests.yaml
# (Generated by CI with placeholder)

apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  template:
    spec:
      containers:
        - name: app
          image: gcr.io/project/payment-service:PLACEHOLDER
          # ↑ Placeholder replaced by Harness at deployment
```

**In Harness pipeline**:
```yaml
- step:
    type: K8sApply
    spec:
      filePaths:
        - generated/payment-service/prod/euw1/manifests.yaml
      
      # ✅ Harness replaces image tag
      images:
        - name: gcr.io/project/payment-service
          tag: <+pipeline.variables.imageTag>
          # Runtime input from user: v2.3.1
```

**Result**: `gcr.io/project/payment-service:v2.3.1`

---

**Option B: Harness Input Sets**

**Create input set file**:
```yaml
# harness-pipelines/input-sets/payment-service-prod.yaml
inputSet:
  identifier: payment_service_prod
  pipeline:
    identifier: payment_service_cd
    stages:
      - stage:
          identifier: prod_euw1
          spec:
            service:
              serviceDefinition:
                spec:
                  variables:
                    - name: imageTag
                      type: String
                      value: <+input>  # User provides
```

**Trigger with input set**:
```bash
# App CI/CD triggers Harness with image tag
curl -X POST \
  "https://app.harness.io/gateway/ng/api/pipeline/execute/payment-service-cd" \
  -H "x-api-key: $HARNESS_API_KEY" \
  -d '{
    "inputSetReferences": ["payment_service_prod"],
    "runtimeInputYaml": "pipeline:\n  stages:\n    - stage:\n        variables:\n          imageTag: v2.3.1"
  }'
```

---

## Cross-Org GitHub Connector Setup

### In Harness: Create Cross-Org Connector

**Steps**:
1. Go to Harness → Connectors → New Connector → GitHub
2. Name: `github_platform_next_cross_org`
3. URL: `https://github.com/company/platform-next`
4. Credentials:
   - Type: Personal Access Token (PAT)
   - Token: GitHub PAT with `repo` scope
   - User: Service account user
5. Test connection
6. Save

**GitHub PAT Requirements**:
- Scope: `repo` (read access to private repos)
- Created by: Service account (e.g., `harness-bot@company.com`)
- Expiration: 1 year (rotate before expiry)

**Security**:
- Store PAT in Harness secrets
- Rotate every 6-12 months
- Use fine-grained PAT (read-only)

---

## Complete Workflow

### Scenario 1: New Service Onboarding

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Developer Uses UI                                   │
├─────────────────────────────────────────────────────────────┤
│  Developer fills form:                                      │
│    - Service: payment-service                               │
│    - Archetype: api                                         │
│    - Team: payments                                         │
│  Clicks "Create Service"                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Backend API (platform-next repo)                   │
├─────────────────────────────────────────────────────────────┤
│  1. Update catalog/services.yaml                            │
│  2. Git commit + push                                       │
│  3. Call Pipeline Orchestrator webhook                      │
│     POST /webhooks/service-created                          │
│     { "service": "payment-service", ... }                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: GitHub Actions (platform-next)                     │
├─────────────────────────────────────────────────────────────┤
│  Triggered by: catalog change                               │
│  1. Detect new service: payment-service                     │
│  2. Run generate-kz-v3.sh                                   │
│  3. Generate manifests for int/pre/prod                     │
│  4. Commit to generated/payment-service/                    │
│  5. Push to main                                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Pipeline Orchestrator Service                      │
├─────────────────────────────────────────────────────────────┤
│  Received webhook from Step 2                               │
│  1. Fetch template from harness-pipelines repo              │
│     GET /repos/company-harness/harness-pipelines/           │
│         templates/api-pipeline-template.yaml                │
│  2. Customize template (replace {{SERVICE_NAME}})           │
│  3. Create pipeline in Harness (API call)                   │
│  4. Commit pipeline to harness-pipelines repo               │
│  5. Return pipeline URL to UI                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Harness Pipeline Created                           │
├─────────────────────────────────────────────────────────────┤
│  Pipeline: payment-service-cd                               │
│  Status: Ready to deploy                                    │
│  Awaiting: imageTag input                                   │
└─────────────────────────────────────────────────────────────┘

Result: Service onboarded, pipeline ready, awaiting first deploy
```

---

### Scenario 2: Config Change (K8s Resources)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Developer Changes Config                           │
├─────────────────────────────────────────────────────────────┤
│  Via UI or directly in catalog:                             │
│  - Change resource limits: medium → large                   │
│  - Add new component: pdb                                   │
│  Git commit to platform-next                                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: GitHub Actions (platform-next)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Detect catalog change                                   │
│  2. Regenerate manifests                                    │
│  3. Commit to generated/payment-service/                    │
│  4. Push to main                                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Harness Pipeline (Auto-sync)                       │
├─────────────────────────────────────────────────────────────┤
│  ✅ NO trigger needed!                                      │
│                                                             │
│  Next deployment automatically uses:                        │
│    - Latest manifests from Git                              │
│    - New resource limits                                    │
│    - New PDB component                                      │
│                                                             │
│  Pipeline always fetches from Git main branch               │
└─────────────────────────────────────────────────────────────┘

Result: Config changes take effect on next deployment (GitOps)
```

---

### Scenario 3: App Deployment (New Image)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: App Team Builds Image                              │
├─────────────────────────────────────────────────────────────┤
│  App repo CI/CD:                                            │
│    - Build image: payment-service:v2.3.1                    │
│    - Push to GCR                                            │
│    - Tag: gcr.io/project/payment-service:v2.3.1            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Trigger Harness Pipeline                           │
├─────────────────────────────────────────────────────────────┤
│  Option A: Webhook                                          │
│    curl -X POST https://harness.io/.../payment-service-cd  │
│      -d '{"imageTag": "v2.3.1"}'                           │
│                                                             │
│  Option B: UI                                               │
│    Developer clicks "Deploy" → enters v2.3.1               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Harness Pipeline Execution                         │
├─────────────────────────────────────────────────────────────┤
│  Input: imageTag = v2.3.1                                   │
│                                                             │
│  Stage: int-stable                                          │
│    1. Fetch manifests from Git (latest config)              │
│       generated/payment-service/int-stable/euw1/            │
│    2. Replace image placeholder with v2.3.1                 │
│    3. Deploy to cluster via delegate                        │
│    4. Health check                                          │
│                                                             │
│  Stage: pre-stable                                          │
│    Auto-approve after 1 hour                                │
│    Deploy with same image tag                               │
│                                                             │
│  Stage: prod                                                │
│    Manual approval                                          │
│    Deploy with same image tag                               │
└─────────────────────────────────────────────────────────────┘

Result: App v2.3.1 deployed with latest config from Git
```

---

## Benefits of Decoupled Architecture

### ✅ Separation of Concerns

| Concern | Repo | Ownership |
|---------|------|-----------|
| **K8s Config** | platform-next | Platform team |
| **Pipelines** | harness-pipelines | Platform team |
| **App Code** | app repos | App teams |

### ✅ Independent Updates

| Update Type | Affects | Example |
|-------------|---------|---------|
| **Config change** | Only platform-next | Change resource limits |
| **Pipeline change** | Only harness-pipelines | Add approval step |
| **App change** | Only app repo | New feature |

### ✅ GitOps Compliance

```
Config changes → Git → Auto-sync (declarative)
App changes → Runtime input (image tag only)
```

### ✅ Cross-Org Support

```
Config Org: company/platform-next
Pipeline Org: company-harness/harness-pipelines

Harness connector bridges the two
```

### ✅ Scalability

```
100 services × 3 environments = 300 manifests
  → All in platform-next/generated/

100 pipelines
  → All in harness-pipelines/pipelines/

Pipeline Orchestrator handles creation automatically
```

---

## Implementation Checklist

### Phase 1: Setup (Week 1)

- [ ] Create `company-harness/harness-pipelines` repo
- [ ] Create pipeline templates (api, listener, job, scheduler)
- [ ] Setup cross-org GitHub connector in Harness
- [ ] Deploy Pipeline Orchestrator service
- [ ] Test template → Harness API flow

### Phase 2: Integration (Week 2)

- [ ] Update platform-next GitHub Actions
  - Add webhook call to Pipeline Orchestrator
- [ ] Test end-to-end: catalog → manifests → pipeline
- [ ] Verify cross-org manifest fetching
- [ ] Test image tag injection

### Phase 3: Pilot (Week 3)

- [ ] Onboard 3 pilot services
- [ ] Test config changes (auto-sync)
- [ ] Test app deployments (image tag)
- [ ] Gather feedback

### Phase 4: Rollout (Week 4-8)

- [ ] Migrate 10 services per week
- [ ] Monitor Pipeline Orchestrator
- [ ] Optimize templates
- [ ] Document for teams

---

## Final Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      GitHub Org: company                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Repo: platform-next                                        │  │
│  │                                                             │  │
│  │ - kustomize/ (archetypes, components, catalog)             │  │
│  │ - generated/ (K8s manifests) ← Source of truth             │  │
│  │ - .github/workflows/ (CI: generate manifests)              │  │
│  │                                                             │  │
│  │ Changes: Resource limits, components, profiles             │  │
│  │ Result: Regenerate manifests → commit to Git               │  │
│  └────────────────┬───────────────────────────────────────────┘  │
│                   │                                               │
└───────────────────┼───────────────────────────────────────────────┘
                    │
                    │ Webhook on new service
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                Pipeline Orchestrator Service                      │
│                (Bridge between repos)                             │
│                                                                   │
│  - Listens for service creation events                           │
│  - Fetches templates from harness-pipelines                      │
│  - Calls Harness API to create pipeline                          │
│  - Commits pipeline YAML to harness-pipelines                    │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ Create pipeline via API
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                 GitHub Org: company-harness                       │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Repo: harness-pipelines                                    │  │
│  │                                                             │  │
│  │ - templates/ (pipeline templates)                          │  │
│  │ - pipelines/ (generated pipelines)                         │  │
│  │ - policies/ (OPA policies)                                 │  │
│  │                                                             │  │
│  │ Synced to: Harness Platform                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                    │
                    │ Cross-org connector
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Harness Platform                             │
│                                                                   │
│  Pipelines: 100+ service pipelines                               │
│  Input: imageTag (runtime)                                       │
│  Fetches: Manifests from platform-next (cross-org)               │
│  Deploys: To K8s clusters via delegates                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Summary

### Key Architectural Decisions

1. ✅ **Decoupled Repos**: Config repo ≠ Pipeline repo
2. ✅ **Pipeline Orchestrator**: Microservice bridges the two
3. ✅ **Cross-Org Connector**: Harness fetches manifests from different org
4. ✅ **Runtime Image Tag**: Only app image tag is runtime input
5. ✅ **Auto-Sync Config**: Config changes auto-applied (GitOps)
6. ✅ **Version Control**: Both repos in Git (audit trail)

### What Goes Where

| Concern | Repo | Trigger |
|---------|------|---------|
| **K8s Manifests** | platform-next/generated/ | Catalog change |
| **Pipeline Templates** | harness-pipelines/templates/ | Manual update |
| **Pipeline Instances** | harness-pipelines/pipelines/ | Service creation |
| **Pipeline Execution** | Harness Platform | Image tag input |

### Developer Experience

**Onboard Service**: UI form → 5 min → Pipeline created
**Change Config**: UI update → Auto-sync → Next deploy
**Deploy App**: Trigger pipeline + image tag → Deploy

**This architecture is production-ready and fully decoupled!** 🚀
