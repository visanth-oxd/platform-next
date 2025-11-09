# Backstage + Harness Integration - Unified Interface

## The Better Approach

**Reuse existing tools instead of building custom UI**:
- ✅ **Backstage** → Service onboarding and catalog
- ✅ **Harness Console** → Deployment interface with runtime inputs
- ✅ **No custom UI needed** → Leverage existing investments

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backstage Developer Portal                    │
│                  https://backstage.company.com                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Developer clicks "Create New Service"                       │
│     Software Template: "Kubernetes Service"                     │
│                                                                  │
│  2. Fills form:                                                 │
│     - Service Name: payment-service                             │
│     - Archetype: api                                            │
│     - Profile: public-api                                       │
│     - Size: medium                                              │
│     - Team: payments                                            │
│                                                                  │
│  3. Backstage executes template actions:                        │
│     a. Create PR to platform-next (catalog update)              │
│     b. Register service in Backstage catalog                    │
│     c. Call Pipeline Orchestrator API                           │
│     d. Show progress and results                                │
│                                                                  │
│  Result: Service onboarded, manifest generated, pipeline created│
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Links to ↓
                 │
┌─────────────────────────────────────────────────────────────────┐
│                      Harness Console                             │
│                   https://harness.company.com                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  4. Developer navigates to service pipeline                     │
│     Backstage → Links → "Deploy" → Opens Harness                │
│                                                                  │
│  5. Harness shows pipeline: payment-service-cd                  │
│     Runtime Inputs Required:                                    │
│     - Image Tag: [v2.3.1__________]                            │
│     - Environment: [prod ▼]                                     │
│                                                                  │
│  6. Click "Run Pipeline"                                        │
│     → Fetches latest manifests from Git                         │
│     → Injects image tag                                         │
│     → Deploys to selected environment                           │
│                                                                  │
│  7. Monitor deployment in Harness UI                            │
│     → View logs                                                 │
│     → Approve production gate                                   │
│     → Watch rollout                                             │
│                                                                  │
│  Result: App deployed with config from Git + image tag          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Backstage Software Template

### What is Backstage Software Template?

**Backstage Software Templates** = Scaffolding tool for creating new services/components

**Features**:
- Form-based UI (no custom code needed)
- GitHub integration (create PRs)
- API calls (webhook to external services)
- Catalog registration (auto-add to Backstage)

### Template Definition

**File**: `backstage/templates/kubernetes-service.yaml`

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: kubernetes-service
  title: Deploy Kubernetes Service
  description: Onboard a new service to the Kubernetes platform
  tags:
    - kubernetes
    - platform
    - recommended
spec:
  owner: platform-team
  type: service
  
  # ============================================
  # Form Definition (UI)
  # ============================================
  parameters:
    - title: Service Information
      required:
        - serviceName
        - archetype
        - profile
      properties:
        serviceName:
          title: Service Name
          type: string
          description: Name of your service (lowercase, hyphens only)
          pattern: '^[a-z][a-z0-9-]*[a-z0-9]$'
          ui:autofocus: true
          ui:help: 'Example: payment-service, account-api'
        
        description:
          title: Description
          type: string
          description: What does this service do?
        
        archetype:
          title: Service Archetype
          type: string
          description: What type of workload is this?
          enum:
            - api
            - listener
            - streaming
            - scheduler
            - job
          enumNames:
            - 'API - HTTP/REST services'
            - 'Listener - Event consumers'
            - 'Streaming - WebSocket/long-lived connections'
            - 'Scheduler - Periodic CronJobs'
            - 'Job - One-time batch processing'
          default: api
        
        profile:
          title: Behavior Profile
          type: string
          description: Pre-configured bundle of components and settings
          enum:
            - public-api
            - internal-api
            - event-consumer
            - websocket-server
            - batch-job
            - scheduled-task
          enumNames:
            - 'Public API - External exposure with Ingress'
            - 'Internal API - Service mesh only'
            - 'Event Consumer - Kafka/PubSub listener'
            - 'WebSocket Server - Long-lived connections'
            - 'Batch Job - One-time processing'
            - 'Scheduled Task - Periodic execution'
          default: public-api
          ui:help: 'Profile determines which components are enabled'
    
    - title: Resource Configuration
      required:
        - size
      properties:
        size:
          title: Resource Size
          type: string
          description: T-shirt sizing for CPU/memory/replicas
          enum:
            - small
            - medium
            - large
            - xlarge
          enumNames:
            - 'Small - 100m CPU, 256Mi RAM (1-3 replicas)'
            - 'Medium - 250m CPU, 512Mi RAM (2-6 replicas)'
            - 'Large - 500m CPU, 1Gi RAM (3-10 replicas)'
            - 'X-Large - 1000m CPU, 2Gi RAM (4-15 replicas)'
          default: medium
        
        prodSizeOverride:
          title: Production Size Override (Optional)
          type: string
          description: Different size for production environment
          enum:
            - ''
            - small
            - medium
            - large
            - xlarge
          enumNames:
            - 'Same as default'
            - 'Small'
            - 'Medium'
            - 'Large'
            - 'X-Large'
    
    - title: Deployment Configuration
      required:
        - environments
        - regions
      properties:
        environments:
          title: Deploy to Environments
          type: array
          description: Which environments should this service run in?
          items:
            type: string
            enum:
              - int
              - pre
              - prod
          default:
            - int
            - pre
            - prod
          uniqueItems: true
          minItems: 1
        
        regions:
          title: Deploy to Regions
          type: array
          description: Which regions should this service run in?
          items:
            type: string
            enum:
              - euw1
              - euw2
          default:
            - euw1
            - euw2
          uniqueItems: true
          minItems: 1
    
    - title: Team & Ownership
      required:
        - team
      properties:
        team:
          title: Team Name
          type: string
          description: Which team owns this service?
          ui:field: EntityPicker
          ui:options:
            catalogFilter:
              kind: Group
        
        slackChannel:
          title: Slack Channel
          type: string
          description: Team Slack channel for notifications
          pattern: '^#[a-z0-9-]+$'
          default: '#team-platform'
        
        pagerduty:
          title: PagerDuty Service
          type: string
          description: PagerDuty service for alerts
  
  # ============================================
  # Actions (What Happens When User Submits)
  # ============================================
  steps:
    # Step 1: Update catalog in platform-next repo
    - id: update-catalog
      name: Update Service Catalog
      action: github:catalog:update
      input:
        repoUrl: github.com?repo=platform-next&owner=company
        filePath: kustomize/catalog/services.yaml
        update: |
          services:
            - name: ${{ parameters.serviceName }}
              archetype: ${{ parameters.archetype }}
              profile: ${{ parameters.profile }}
              size: ${{ parameters.size }}
              environments: ${{ parameters.environments }}
              regions: ${{ parameters.regions }}
              team: ${{ parameters.team }}
              slack: ${{ parameters.slackChannel }}
              pagerduty: ${{ parameters.pagerduty }}
              ${{ parameters.prodSizeOverride && format('resources:\n  overrides:\n    prod:\n      size: {0}', parameters.prodSizeOverride) }}
        branch: add-${{ parameters.serviceName }}
        createPullRequest: true
        pullRequestTitle: 'Add service: ${{ parameters.serviceName }}'
        pullRequestBody: |
          ## New Service Onboarding
          
          **Service**: ${{ parameters.serviceName }}
          **Archetype**: ${{ parameters.archetype }}
          **Profile**: ${{ parameters.profile }}
          **Size**: ${{ parameters.size }}
          **Team**: ${{ parameters.team }}
          
          This PR adds a new service to the platform.
          
          Once merged:
          - Manifests will be generated
          - Harness pipeline will be created
          - Service will be ready to deploy
    
    # Step 2: Call Pipeline Orchestrator to create Harness pipeline
    - id: create-pipeline
      name: Create Harness Pipeline
      action: http:backstage:request
      input:
        method: POST
        url: https://pipeline-orchestrator.company.com/api/v1/pipelines/create
        headers:
          Content-Type: application/json
          Authorization: Bearer ${{ secrets.PIPELINE_ORCHESTRATOR_TOKEN }}
        body:
          service: ${{ parameters.serviceName }}
          archetype: ${{ parameters.archetype }}
          team: ${{ parameters.team }}
          environments: ${{ parameters.environments }}
          regions: ${{ parameters.regions }}
    
    # Step 3: Register service in Backstage catalog
    - id: register-catalog
      name: Register in Backstage
      action: catalog:register
      input:
        repoContentsUrl: https://github.com/company/platform-next/blob/main
        catalogInfoPath: /backstage/catalog/${{ parameters.serviceName }}.yaml
        optional: true
    
    # Step 4: Create catalog-info.yaml for Backstage
    - id: create-catalog-info
      name: Create Catalog Info
      action: github:catalog:write
      input:
        repoUrl: github.com?repo=platform-next&owner=company
        filePath: backstage/catalog/${{ parameters.serviceName }}.yaml
        entity:
          apiVersion: backstage.io/v1alpha1
          kind: Component
          metadata:
            name: ${{ parameters.serviceName }}
            description: ${{ parameters.description }}
            annotations:
              backstage.io/kubernetes-id: ${{ parameters.serviceName }}
              harness.io/pipeline-url: ${{ steps['create-pipeline'].output.pipelineUrl }}
              github.com/project-slug: company/platform-next
            tags:
              - ${{ parameters.archetype }}
              - kubernetes
            links:
              - url: ${{ steps['create-pipeline'].output.pipelineUrl }}
                title: Harness Pipeline
                icon: harness
              - url: https://github.com/company/platform-next/tree/main/generated/${{ parameters.serviceName }}
                title: Generated Manifests
                icon: github
          spec:
            type: service
            lifecycle: production
            owner: ${{ parameters.team }}
            system: platform
  
  # ============================================
  # Output (Show to User)
  # ============================================
  output:
    links:
      - title: View Pull Request
        url: ${{ steps['update-catalog'].output.remoteUrl }}
        icon: github
      
      - title: View Harness Pipeline
        url: ${{ steps['create-pipeline'].output.pipelineUrl }}
        icon: harness
      
      - title: View in Backstage Catalog
        url: /catalog/default/component/${{ parameters.serviceName }}
        icon: catalog
    
    text:
      - title: Next Steps
        content: |
          ## Service Onboarded! 🎉
          
          **Service**: ${{ parameters.serviceName }}
          **Pipeline**: Created and ready
          
          ### What happens next:
          
          1. ✅ Pull request created in platform-next repo
          2. ✅ PR will auto-merge after validation passes
          3. ✅ Manifests will be generated automatically
          4. ✅ Harness pipeline is ready to use
          
          ### To deploy your service:
          
          1. Go to [Harness Pipeline](${{ steps['create-pipeline'].output.pipelineUrl }})
          2. Click "Run Pipeline"
          3. Enter your image tag (e.g., v1.0.0)
          4. Select environment (int, pre, or prod)
          5. Click "Run"
          
          ### Monitor your service:
          
          - View in [Backstage Catalog](/catalog/default/component/${{ parameters.serviceName }})
          - Check Kubernetes pods, logs, metrics
          - View deployment history in Harness
```

---

## Component 2: Backstage Catalog Integration

### Backstage Catalog Entity

**File**: `backstage/catalog/payment-service.yaml` (auto-generated)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payment-service
  description: Payment processing API service
  
  annotations:
    # Backstage plugins
    backstage.io/kubernetes-id: payment-service
    backstage.io/kubernetes-namespace: prod-payment-service-euw1
    
    # Harness integration
    harness.io/project: platform
    harness.io/pipeline-url: https://harness.company.com/ng/.../payment-service-cd
    
    # GitHub integration
    github.com/project-slug: company/platform-next
    
  tags:
    - api
    - kubernetes
    - payments
  
  links:
    # Direct link to Harness pipeline
    - url: https://harness.company.com/ng/account/abc/cd/orgs/default/projects/platform/pipelines/payment-service-cd
      title: Deploy in Harness
      icon: harness
    
    # Link to generated manifests
    - url: https://github.com/company/platform-next/tree/main/generated/payment-service
      title: View Manifests
      icon: github
    
    # Link to Grafana dashboard
    - url: https://grafana.company.com/d/payment-service
      title: Metrics
      icon: grafana

spec:
  type: service
  lifecycle: production
  owner: payments-team
  system: platform
  
  # Provides API
  providesApis:
    - payment-api
  
  # Consumes other services
  consumesApis:
    - account-api
```

### Backstage UI View

**Service Page in Backstage**:

```
┌──────────────────────────────────────────────────────────┐
│ payment-service                                 [API]     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ Overview | Kubernetes | CI/CD | API | Dependencies       │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ Quick Actions                                        │  │
│ ├─────────────────────────────────────────────────────┤  │
│ │                                                      │  │
│ │  [Deploy to Int-Stable]  ← Opens Harness with int   │  │
│ │  [Deploy to Pre-Stable]  ← Opens Harness with pre   │  │
│ │  [Deploy to Production]  ← Opens Harness with prod  │  │
│ │                                                      │  │
│ │  [View Manifests]        ← GitHub link              │  │
│ │  [View Logs]             ← K8s logs                 │  │
│ │  [View Metrics]          ← Grafana                  │  │
│ │                                                      │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ Kubernetes Resources (Backstage K8s Plugin)         │  │
│ ├─────────────────────────────────────────────────────┤  │
│ │                                                      │  │
│ │ Environment  | Pods | Status    | Version           │  │
│ │ ──────────────────────────────────────────────────  │  │
│ │ int-stable   | 2/2  | ✓ Healthy | v2.3.1            │  │
│ │ pre-stable   | 3/3  | ✓ Healthy | v2.3.1            │  │
│ │ prod         | 6/6  | ✓ Healthy | v2.3.0            │  │
│ │                                                      │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                           │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ Recent Deployments (Harness Plugin)                 │  │
│ ├─────────────────────────────────────────────────────┤  │
│ │                                                      │  │
│ │ 2 hours ago  | v2.3.1 → prod     | ✓ Success        │  │
│ │ 1 day ago    | v2.3.0 → prod     | ✓ Success        │  │
│ │ 3 days ago   | v2.2.5 → prod     | ✗ Failed         │  │
│ │                                                      │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Backstage Plugins Used**:
- ✅ `@backstage/plugin-kubernetes` - Show pod status, logs
- ✅ `@backstage-community/plugin-harness` - Show deployments, link to pipelines
- ✅ `@backstage/plugin-github-actions` - Show CI status
- ✅ `@backstage/plugin-pagerduty` - Show incidents
- ✅ `@backstage/plugin-grafana` - Embed metrics

---

## Component 3: Harness Pipeline with Runtime Inputs

### Pipeline Template (Simplified)

**File**: `harness-pipelines/templates/api-pipeline-template.yaml`

```yaml
pipeline:
  name: "{{SERVICE_NAME}}-cd"
  identifier: "{{SERVICE_NAME}}_cd"
  projectIdentifier: platform
  orgIdentifier: default
  
  tags:
    service: "{{SERVICE_NAME}}"
    team: "{{TEAM}}"
  
  # ============================================
  # ✅ Pipeline Variables (Runtime Inputs)
  # ============================================
  variables:
    - name: imageTag
      type: String
      description: "Docker image tag to deploy (e.g., v2.3.1)"
      required: true
      value: <+input>.default(latest).allowedValues(latest,v2.3.1,v2.3.0)
    
    - name: targetEnvironment
      type: String
      description: "Environment to deploy to"
      required: true
      value: <+input>.allowedValues(int-stable,pre-stable,prod)
    
    - name: targetRegion
      type: String
      description: "Region to deploy to"
      required: false
      value: <+input>.default(euw1).allowedValues(euw1,euw2)
  
  stages:
    - stage:
        name: Deploy Service
        identifier: deploy
        type: Deployment
        
        # ============================================
        # ✅ Dynamic environment selection
        # ============================================
        when:
          pipelineStatus: Success
          condition: <+pipeline.variables.targetEnvironment> != ""
        
        spec:
          deploymentType: Kubernetes
          
          service:
            serviceRef: "{{SERVICE_NAME}}"
            serviceDefinition:
              type: Kubernetes
              spec:
                # ============================================
                # ✅ Fetch manifests from platform-next repo
                # Path determined by runtime inputs
                # ============================================
                manifests:
                  - manifest:
                      identifier: k8s_manifests
                      type: K8sManifest
                      spec:
                        store:
                          type: Github
                          spec:
                            connectorRef: github_platform_next_cross_org
                            gitFetchType: Branch
                            branch: main
                            paths:
                              # ✅ Dynamic path based on runtime inputs
                              - generated/{{SERVICE_NAME}}/<+pipeline.variables.targetEnvironment>/<+pipeline.variables.targetRegion>/manifests.yaml
                        
                        skipResourceVersioning: false
          
          # ============================================
          # ✅ Dynamic infrastructure selection
          # ============================================
          environment:
            environmentRef: <+pipeline.variables.targetEnvironment>
            deployToAll: false
            infrastructureDefinitions:
              # Select infrastructure based on env + region
              - identifier: <+pipeline.variables.targetEnvironment>_<+pipeline.variables.targetRegion>_k8s
                inputs:
                  spec:
                    delegateSelectors:
                      # Dynamic delegate selection
                      - harness-delegate-<+pipeline.variables.targetEnvironment>-<+pipeline.variables.targetRegion>
          
          execution:
            steps:
              # ============================================
              # ✅ Conditional approval for prod
              # ============================================
              - step:
                  type: HarnessApproval
                  name: Production Approval
                  identifier: prod_approval
                  when:
                    stageStatus: Success
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
                  spec:
                    approvalMessage: |
                      Production deployment for {{SERVICE_NAME}}
                      
                      Image Tag: <+pipeline.variables.imageTag>
                      Region: <+pipeline.variables.targetRegion>
                    approvers:
                      userGroups:
                        - account.{{TEAM}}
                        - account.platform_team
                      minimumCount: 2
                    approverInputs:
                      - name: change_ticket
                        type: String
                        required: true
                  timeout: 7d
              
              # ============================================
              # ✅ Deploy with image tag injection
              # ============================================
              - step:
                  type: K8sApply
                  name: Apply Manifests
                  identifier: apply
                  spec:
                    filePaths:
                      - generated/{{SERVICE_NAME}}/<+pipeline.variables.targetEnvironment>/<+pipeline.variables.targetRegion>/manifests.yaml
                    skipDryRun: false
                  timeout: 10m
              
              - step:
                  type: K8sRollingDeploy
                  name: Rolling Deploy
                  identifier: rolling
                  spec:
                    skipDryRun: false
                  timeout: 10m
              
              # ============================================
              # ✅ Verify deployment
              # ============================================
              - step:
                  type: K8sRollingRollback
                  name: Verify Pods
                  identifier: verify
                  timeout: 5m
            
            rollbackSteps:
              - step:
                  type: K8sRollingRollback
                  name: Rollback
                  identifier: rollback
```

---

## Harness Console Experience

### Deploying from Harness UI

**Step 1: Navigate to Pipeline**

```
Harness Console
  → Pipelines
  → Search: "payment-service"
  → Click: payment-service-cd
```

**Step 2: Run Pipeline**

```
┌──────────────────────────────────────────────────────────┐
│ Run Pipeline: payment-service-cd                         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ Runtime Inputs Required:                                 │
│                                                           │
│ Image Tag:                                                │
│ [v2.3.1______________] (required)                        │
│ ℹ Enter the Docker image tag to deploy                   │
│                                                           │
│ Target Environment:                                       │
│ ● int-stable                                              │
│ ○ pre-stable                                              │
│ ○ prod                                                    │
│                                                           │
│ Target Region:                                            │
│ ● euw1 (Primary)                                          │
│ ○ euw2 (DR)                                               │
│                                                           │
│ ☐ Advanced Options                                        │
│                                                           │
│        [Cancel]              [Run Pipeline]               │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Step 3: Monitor Execution**

```
┌──────────────────────────────────────────────────────────┐
│ Pipeline Execution #42                                    │
│ payment-service-cd                                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│ Input: imageTag=v2.3.1, env=int-stable, region=euw1      │
│                                                           │
│ Stage: Deploy Service                           Running  │
│                                                           │
│   ✓ Production Approval            Skipped (not prod)    │
│   → Apply Manifests                Running (30s)          │
│      Fetching from Git: company/platform-next            │
│      Path: generated/payment-service/int-stable/euw1/    │
│      Replacing image: gcr.io/.../payment-service:v2.3.1  │
│      Applying to cluster via delegate-int-euw1           │
│   ⋯ Rolling Deploy                 Pending               │
│   ⋯ Verify Pods                    Pending               │
│                                                           │
│ [View Logs] [Abort] [Rollback]                           │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Backstage → Platform-Next (Config Repo)

**When**: Service creation
**Action**: Create PR with catalog update
**Result**: Manifests generated in CI

```yaml
# Backstage template action
- id: update-catalog
  action: github:catalog:update
  input:
    repoUrl: github.com?repo=platform-next&owner=company
    filePath: kustomize/catalog/services.yaml
    createPullRequest: true
```

### 2. Backstage → Pipeline Orchestrator

**When**: Service creation
**Action**: HTTP call to create pipeline
**Result**: Harness pipeline created

```yaml
# Backstage template action
- id: create-pipeline
  action: http:backstage:request
  input:
    method: POST
    url: https://pipeline-orchestrator.company.com/api/v1/pipelines/create
    body:
      service: payment-service
      archetype: api
```

### 3. Pipeline Orchestrator → Harness API

**When**: Received webhook from Backstage
**Action**: Create pipeline via API
**Result**: Pipeline in Harness

```python
# Pipeline Orchestrator
def create_harness_pipeline(service_config):
    template = fetch_template(service_config['archetype'])
    pipeline_yaml = customize_template(template, service_config)
    
    # Call Harness API
    response = requests.post(
        "https://app.harness.io/gateway/ng/api/pipelines",
        headers={"x-api-key": HARNESS_API_KEY},
        data=pipeline_yaml
    )
    
    return response.json()
```

### 4. Harness → Platform-Next (Cross-Org)

**When**: Pipeline execution
**Action**: Fetch manifests from Git
**Result**: Latest config deployed

```yaml
# Harness pipeline
manifests:
  - manifest:
      type: K8sManifest
      spec:
        store:
          type: Github
          spec:
            connectorRef: github_platform_next_cross_org
            branch: main
            paths:
              - generated/payment-service/prod/euw1/manifests.yaml
```

### 5. App Repo → Harness (Webhook)

**When**: Image built
**Action**: Trigger pipeline with image tag
**Result**: Deployment started

```yaml
# App repo CI (e.g., .github/workflows/build.yml)
- name: Trigger Harness Deployment
  run: |
    curl -X POST \
      "https://app.harness.io/gateway/ng/api/webhooks/..." \
      -H "x-api-key: ${{ secrets.HARNESS_WEBHOOK_TOKEN }}" \
      -d '{
        "imageTag": "${{ steps.build.outputs.tag }}",
        "targetEnvironment": "int-stable",
        "targetRegion": "euw1"
      }'
```

---

## Complete User Journey

### Journey 1: Onboard New Service (One-Time)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Open Backstage                                           │
│    https://backstage.company.com                            │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Click "Create" → "Kubernetes Service"                   │
│    Fill form (5 fields):                                    │
│      - Name: payment-service                                │
│      - Archetype: api                                       │
│      - Profile: public-api                                  │
│      - Size: medium                                         │
│      - Environments: int, pre, prod                         │
│    Click "Create"                                           │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backstage executes template                             │
│    ✓ PR created in platform-next                           │
│    ✓ Pipeline created in Harness                           │
│    ✓ Service registered in Backstage catalog               │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. CI generates manifests (auto)                           │
│    ✓ PR auto-merges                                        │
│    ✓ Manifests committed to Git                            │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Backstage shows success                                 │
│    Links:                                                   │
│      → View in Catalog                                      │
│      → Deploy in Harness ← Click this                      │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Opens Harness Console                                   │
│    Pipeline ready, awaiting first deployment               │
└─────────────────────────────────────────────────────────────┘

Time: 5-10 minutes
Manual steps: 1 (fill form)
Result: Service ready to deploy
```

---

### Journey 2: Deploy New Version (Recurring)

**Option A: Via Backstage**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Open Backstage → Search "payment-service"              │
│    Click service card                                       │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Service page shows current deployments                  │
│    Prod: v2.3.0                                             │
│    Click "Deploy to Production"                             │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Redirects to Harness Console                            │
│    Opens payment-service-cd pipeline                        │
│    Pre-filled:                                              │
│      - targetEnvironment: prod                              │
│    User enters:                                             │
│      - imageTag: v2.3.1                                     │
│    Click "Run Pipeline"                                     │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Harness executes pipeline                               │
│    ✓ Fetches manifests from Git (latest config)            │
│    ✓ Injects image tag: v2.3.1                             │
│    ✓ Waits for 2 approvals                                 │
│    ✓ Deploys to prod via delegate                          │
│    ✓ Health check passes                                   │
└────────────────┬────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Backstage updates (via Harness plugin)                 │
│    Prod: v2.3.1 (deployed 2 min ago)                       │
│    Status: ✓ Healthy                                       │
└─────────────────────────────────────────────────────────────┘

Time: 5-10 minutes
Manual steps: 2 (enter image tag, approve)
Result: New version deployed
```

**Option B: Via Harness Directly**

```
Developer goes directly to Harness
  → Pipelines → payment-service-cd
  → Run Pipeline → Enter image tag
  → Deploy
```

**Option C: Automated (Webhook)**

```
App repo builds image
  → CI triggers Harness webhook
  → Pipeline auto-deploys to int-stable
  → No UI needed
```

---

## Benefits of This Approach

### ✅ Reuses Existing Tools

| Tool | Purpose | Already Have? |
|------|---------|---------------|
| **Backstage** | Service catalog, onboarding UI | ✅ Yes |
| **Harness** | CD pipelines, deployment UI | ✅ Yes |
| **GitHub** | Version control, CI | ✅ Yes |

**No custom UI development needed!**

### ✅ Single Pane of Glass

**Backstage = Developer portal**:
- Discover services
- View status
- Quick deploy buttons
- Links to Harness, logs, metrics

**Harness = Deployment control**:
- Enter image tag
- Control environments
- Approve production
- Monitor rollout

### ✅ Best of Both Worlds

```
Backstage: Developer-friendly, service catalog
           ↕
Harness: Production-grade CD, controls, approvals
```

### ✅ Proper Separation

| Interface | Purpose | Users |
|-----------|---------|-------|
| **Backstage** | Onboarding, discovery | All developers |
| **Harness** | Deployment execution | Release managers, SREs |

---

## Configuration Files Needed

### In `platform-next` Repo

```
platform-next/
├── backstage/
│   ├── templates/
│   │   └── kubernetes-service.yaml      # ✅ Backstage template
│   └── catalog/
│       └── payment-service.yaml         # Auto-generated
│
└── kustomize/
    └── catalog/
        └── services.yaml                 # Updated by Backstage
```

### In `harness-pipelines` Repo

```
harness-pipelines/
├── templates/
│   ├── api-pipeline-template.yaml       # ✅ With runtime inputs
│   ├── listener-pipeline-template.yaml
│   └── ...
│
└── pipelines/
    └── payment-service-cd.yaml          # Auto-generated
```

### Pipeline Orchestrator Service

```
pipeline-orchestrator/
├── main.py                              # ✅ FastAPI service
├── requirements.txt
├── Dockerfile
└── k8s/
    └── deployment.yaml
```

---

## Implementation Roadmap

### Week 1: Backstage Setup
- [ ] Install Backstage (if not already)
- [ ] Install Harness plugin
- [ ] Install Kubernetes plugin
- [ ] Create software template

### Week 2: Pipeline Templates
- [ ] Create Harness pipeline templates
- [ ] Add runtime input support
- [ ] Test cross-org connector
- [ ] Test manifest fetching

### Week 3: Pipeline Orchestrator
- [ ] Deploy orchestrator service
- [ ] Implement Harness API integration
- [ ] Test webhook from Backstage
- [ ] Test pipeline creation

### Week 4: Integration Testing
- [ ] Onboard 3 pilot services via Backstage
- [ ] Deploy via Harness console
- [ ] Verify end-to-end flow
- [ ] Document process

### Week 5+: Rollout
- [ ] Migrate existing services
- [ ] Train teams on Backstage
- [ ] Monitor adoption
- [ ] Iterate based on feedback

---

## Summary

### What We're NOT Building

❌ Custom service onboarding UI (use Backstage)
❌ Custom deployment UI (use Harness console)
❌ Custom service catalog (use Backstage catalog)

### What We ARE Building

✅ Backstage software template (declarative YAML)
✅ Harness pipeline templates (YAML)
✅ Pipeline Orchestrator service (small microservice)
✅ GitHub Actions workflows (manifest generation)

### Developer Experience

**Onboarding (Backstage)**:
1. Open Backstage → Create → Kubernetes Service
2. Fill 5-field form
3. Click Create
4. Wait 5 minutes
5. Service ready!

**Deployment (Harness Console)**:
1. Open Harness → Pipelines → {service}-cd
2. Click Run Pipeline
3. Enter image tag: v2.3.1
4. Select environment: prod
5. Click Run
6. Approve when prompted
7. Done!

**Monitoring (Backstage)**:
1. Open Backstage → Catalog → {service}
2. View pod status, logs, metrics
3. See deployment history
4. Quick-deploy buttons

### This is the simplest, most integrated approach! 🎯

**No custom UI, leverages existing tools, single interface for everything.**
