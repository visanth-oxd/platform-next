# Backstage Catalog & Service Onboarding - Detailed Design

## Executive Summary

This document describes how Backstage serves as the **developer interface** for service onboarding and management in the Platform-Next system.

**Key Points**:
- Backstage provides self-service UI (no custom development)
- Software templates create services in 5 minutes
- Catalog integrates with Kubernetes, Harness, GitHub
- Single pane of glass for developers

---

## 1. Why Backstage?

### The Rationale

**Without Backstage, we'd need to build**:
- Service creation UI (6-8 weeks)
- Service catalog/directory (4 weeks)
- Kubernetes dashboard integration (4 weeks)
- Harness integration (2 weeks)
- Documentation portal (3 weeks)
- **Total**: ~20 weeks of development

**With Backstage**:
- All features available out of the box
- Declarative YAML configuration
- Rich plugin ecosystem
- Industry-proven (Spotify, Netflix, Zalando)

### Core Capabilities We Leverage

| Capability | Purpose | Plugin |
|------------|---------|--------|
| **Software Templates** | Service onboarding forms | Core |
| **Service Catalog** | Searchable service directory | Core |
| **Kubernetes Integration** | Pod status, logs, describe | `@backstage/plugin-kubernetes` |
| **Harness Integration** | Pipeline links, deployment history | `@backstage-community/plugin-harness` |
| **GitHub Integration** | Code links, PR status | `@backstage/plugin-github` |
| **TechDocs** | Auto-generated documentation | `@backstage/plugin-techdocs` |

---

## 2. Software Template Design

### Template Structure

**Location**: `backstage/templates/kubernetes-service.yaml`

**Three Main Sections**:
1. **Metadata** - Template info, tags, description
2. **Parameters** - Form fields (UI definition)
3. **Steps** - Actions to execute when user submits

### Complete Template Definition

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: kubernetes-service
  title: Deploy New Kubernetes Service
  description: Onboard a microservice to the Kubernetes platform with GitOps and Harness CD
  tags:
    - recommended
    - kubernetes
    - platform
    - gitops
spec:
  owner: platform-team
  type: service
  
  # ================================================
  # PARAMETERS - Form Fields (UI)
  # ================================================
  parameters:
    # Page 1: Basic Information
    - title: Service Information
      required:
        - serviceName
        - archetype
        - owner
      properties:
        serviceName:
          title: Service Name
          type: string
          description: Unique name for your service (lowercase, hyphens only)
          pattern: '^[a-z][a-z0-9-]*[a-z0-9]$'
          maxLength: 50
          ui:autofocus: true
          ui:help: 'Examples: payment-api, event-processor, user-service'
        
        description:
          title: Service Description
          type: string
          description: Brief description of what this service does
          ui:widget: textarea
          ui:options:
            rows: 3
        
        archetype:
          title: Service Archetype
          type: string
          description: Type of workload pattern
          enum:
            - api
            - listener
            - streaming
            - scheduler
            - job
          enumNames:
            - 'API - HTTP/REST/gRPC services'
            - 'Listener - Event consumers (Kafka, PubSub)'
            - 'Streaming - WebSocket, long-lived connections'
            - 'Scheduler - Periodic CronJobs'
            - 'Job - One-time batch processing'
          default: api
          ui:help: 'Archetype determines the Kubernetes resources created'
        
        owner:
          title: Team
          type: string
          description: Which team owns this service?
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group
    
    # Page 2: Configuration
    - title: Resource & Behavior Configuration
      required:
        - profile
        - size
      properties:
        profile:
          title: Behavior Profile
          type: string
          description: Pre-configured bundle of components and capabilities
          enum:
            - public-api
            - internal-api
            - event-consumer
            - websocket-server
            - batch-job
            - scheduled-task
          enumNames:
            - 'Public API - External exposure, Ingress, Istio traffic management'
            - 'Internal API - Service mesh only, no external access'
            - 'Event Consumer - Kafka/PubSub listener, internal processing'
            - 'WebSocket Server - Long-lived connections, session affinity'
            - 'Batch Job - One-time data processing'
            - 'Scheduled Task - Periodic execution (CronJob)'
          default: public-api
          ui:help: |
            Profile determines:
            - Which components are enabled (Ingress, HPA, PDB, Istio)
            - Default configurations
            - Security posture
        
        size:
          title: Resource Size
          type: string
          description: T-shirt sizing for CPU, memory, and replica count
          enum:
            - small
            - medium
            - large
            - xlarge
          enumNames:
            - 'Small - 100m CPU, 256Mi RAM, 1-3 replicas (dev/test, low traffic)'
            - 'Medium - 250m CPU, 512Mi RAM, 2-6 replicas (standard production)'
            - 'Large - 500m CPU, 1Gi RAM, 3-10 replicas (high traffic)'
            - 'X-Large - 1000m CPU, 2Gi RAM, 4-15 replicas (critical services)'
          default: medium
        
        prodSizeOverride:
          title: Production Size Override (Optional)
          type: string
          description: Use different size for production environment
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
          ui:help: 'Leave empty to use same size across all environments'
    
    # Page 3: Deployment
    - title: Deployment Configuration
      required:
        - environments
        - regions
      properties:
        environments:
          title: Deploy to Environments
          type: array
          description: Select which environments this service should run in
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
          ui:widget: checkboxes
        
        regions:
          title: Deploy to Regions
          type: array
          description: Geographic regions for deployment
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
          ui:widget: checkboxes
          ui:help: 'euw1=Primary, euw2=DR (disaster recovery)'
    
    # Page 4: Ownership & Alerts
    - title: Ownership & Notifications
      required:
        - slackChannel
      properties:
        slackChannel:
          title: Slack Channel
          type: string
          description: Team Slack channel for deployment notifications
          pattern: '^#[a-z0-9-]+$'
          default: '#platform-notifications'
          ui:help: 'Must start with # (e.g., #team-payments)'
        
        pagerduty:
          title: PagerDuty Service (Optional)
          type: string
          description: PagerDuty service ID for incident alerts
          ui:help: 'Leave empty if no PagerDuty integration needed'
        
        email:
          title: Email Notifications (Optional)
          type: string
          description: Email address for deployment notifications
          format: email
  
  # ================================================
  # STEPS - Actions Executed When User Submits
  # ================================================
  steps:
    # ------------------------------------------------
    # Step 1: Update Service Catalog
    # ------------------------------------------------
    - id: fetch-catalog
      name: Fetch Current Catalog
      action: fetch:plain:file
      input:
        url: https://github.com/company/platform-next/blob/main/kustomize/catalog/services.yaml
        targetPath: ./catalog-current.yaml
    
    - id: update-catalog
      name: Update Service Catalog
      action: roadiehq:utils:fs:append
      input:
        path: catalog-current.yaml
        content: |
          
            - name: ${{ parameters.serviceName }}
              archetype: ${{ parameters.archetype }}
              profile: ${{ parameters.profile }}
              size: ${{ parameters.size }}
              environments: ${{ parameters.environments | dump }}
              regions: ${{ parameters.regions | dump }}
              team: ${{ parameters.owner }}
              slack: ${{ parameters.slackChannel }}
              ${{ parameters.pagerduty && 'pagerduty: ' + parameters.pagerduty }}
              ${{ parameters.prodSizeOverride && 'resources:\n  overrides:\n    prod:\n      size: ' + parameters.prodSizeOverride }}
              harness:
                pipelineId: ${{ parameters.serviceName }}-cd
                createdAt: ${{ '' | now }}
                createdBy: ${{ user.entity.metadata.name }}
    
    # ------------------------------------------------
    # Step 2: Create Pull Request
    # ------------------------------------------------
    - id: create-pr
      name: Create Pull Request
      action: publish:github:pull-request
      input:
        repoUrl: github.com?repo=platform-next&owner=company
        title: 'feat: Add service ${{ parameters.serviceName }}'
        description: |
          ## New Service Onboarding via Backstage
          
          **Service**: `${{ parameters.serviceName }}`
          **Archetype**: ${{ parameters.archetype }}
          **Profile**: ${{ parameters.profile }}
          **Size**: ${{ parameters.size }}
          **Team**: ${{ parameters.owner }}
          
          ### Configuration
          
          ```yaml
          name: ${{ parameters.serviceName }}
          archetype: ${{ parameters.archetype }}
          profile: ${{ parameters.profile }}
          size: ${{ parameters.size }}
          environments: ${{ parameters.environments | dump }}
          regions: ${{ parameters.regions | dump }}
          ```
          
          ### What Happens Next
          
          1. ✅ This PR will trigger CI to generate Kubernetes manifests
          2. ✅ Manifests will be committed to `generated/${{ parameters.serviceName }}/`
          3. ✅ Harness CD pipeline will be created automatically
          4. ✅ Service will be ready to deploy
          
          ### Auto-Merge
          
          This PR will auto-merge after validation passes (approx. 5 minutes).
          
          ---
          
          **Created by**: ${{ user.entity.metadata.name }} via Backstage
          **Template**: kubernetes-service v1.0
        branchName: backstage/add-${{ parameters.serviceName }}
        targetBranchName: main
        sourcePath: catalog-current.yaml
        targetPath: kustomize/catalog/services.yaml
    
    # ------------------------------------------------
    # Step 3: Create Harness Pipeline
    # ------------------------------------------------
    - id: create-harness-pipeline
      name: Create Harness CD Pipeline
      action: http:backstage:request
      input:
        method: POST
        url: ${{ secrets.PIPELINE_ORCHESTRATOR_URL }}/api/v1/pipelines/create
        headers:
          Content-Type: 'application/json'
          Authorization: 'Bearer ${{ secrets.PIPELINE_ORCHESTRATOR_TOKEN }}'
        body:
          service: ${{ parameters.serviceName }}
          archetype: ${{ parameters.archetype }}
          team: ${{ parameters.owner }}
          environments: ${{ parameters.environments }}
          regions: ${{ parameters.regions }}
          profile: ${{ parameters.profile }}
          size: ${{ parameters.size }}
    
    # ------------------------------------------------
    # Step 4: Create Catalog Entity
    # ------------------------------------------------
    - id: create-catalog-entity
      name: Register in Backstage Catalog
      action: catalog:write
      input:
        filePath: backstage/catalog/${{ parameters.serviceName }}.yaml
        entity:
          apiVersion: backstage.io/v1alpha1
          kind: Component
          metadata:
            name: ${{ parameters.serviceName }}
            description: ${{ parameters.description }}
            
            annotations:
              # Kubernetes integration
              backstage.io/kubernetes-id: ${{ parameters.serviceName }}
              backstage.io/kubernetes-label-selector: 'app=${{ parameters.serviceName }}'
              
              # Harness integration
              harness.io/project: platform
              harness.io/pipeline-url: ${{ steps['create-harness-pipeline'].output.pipelineUrl }}
              
              # GitHub integration
              github.com/project-slug: company/platform-next
              
              # Source location
              backstage.io/source-location: url:https://github.com/company/platform-next/tree/main/generated/${{ parameters.serviceName }}
            
            tags:
              - ${{ parameters.archetype }}
              - kubernetes
              - kustomize
              - ${{ parameters.profile }}
            
            links:
              - url: ${{ steps['create-harness-pipeline'].output.pipelineUrl }}
                title: Deploy in Harness
                icon: harness
              
              - url: https://github.com/company/platform-next/tree/main/generated/${{ parameters.serviceName }}
                title: View Generated Manifests
                icon: github
              
              - url: https://github.com/company/platform-next/blob/main/kustomize/catalog/services.yaml
                title: View in Service Catalog
                icon: catalog
          
          spec:
            type: service
            lifecycle: production
            owner: ${{ parameters.owner }}
            system: platform-next
    
    # ------------------------------------------------
    # Step 5: Create Catalog PR
    # ------------------------------------------------
    - id: register-catalog-pr
      name: Register Catalog Entity
      action: publish:github:pull-request
      input:
        repoUrl: github.com?repo=platform-next&owner=company
        title: 'catalog: Register ${{ parameters.serviceName }} in Backstage'
        description: |
          Auto-generated catalog entity for ${{ parameters.serviceName }}
          
          This creates the Backstage catalog entry that enables:
          - Service discovery
          - Kubernetes pod viewing
          - Harness deployment links
          - Documentation
        branchName: backstage/catalog-${{ parameters.serviceName }}
        sourcePath: backstage/catalog/${{ parameters.serviceName }}.yaml
        targetPath: backstage/catalog/${{ parameters.serviceName }}.yaml
  
  # ================================================
  # OUTPUT - Show to User After Completion
  # ================================================
  output:
    links:
      - title: View Pull Request (Catalog Update)
        url: ${{ steps['create-pr'].output.remoteUrl }}
        icon: github
      
      - title: View Pull Request (Backstage Registry)
        url: ${{ steps['register-catalog-pr'].output.remoteUrl }}
        icon: github
      
      - title: View Harness Pipeline
        url: ${{ steps['create-harness-pipeline'].output.pipelineUrl }}
        icon: harness
      
      - title: View in Backstage Catalog
        url: /catalog/default/component/${{ parameters.serviceName }}
        icon: catalog
    
    text:
      - title: Service Onboarded Successfully! 🎉
        content: |
          ## Next Steps
          
          ### 1. Wait for Manifest Generation (5-10 minutes)
          
          Two pull requests have been created:
          - **Service Catalog PR**: Updates `services.yaml` with your service
          - **Backstage Catalog PR**: Registers service in Backstage
          
          Both PRs will auto-merge after CI validation passes.
          
          ### 2. Deploy Your Service
          
          Once PRs are merged:
          
          **Option A: Via Backstage (Quick Deploy)**
          1. Go to [Service Page](/catalog/default/component/${{ parameters.serviceName }})
          2. Click "Deploy to Int-Stable"
          3. Enter your Docker image tag
          4. Click Deploy
          
          **Option B: Via Harness Console (Full Control)**
          1. Open [Harness Pipeline](${{ steps['create-harness-pipeline'].output.pipelineUrl }})
          2. Click "Run Pipeline"
          3. Enter runtime inputs:
             - Image Tag: (e.g., v1.0.0)
             - Environment: int-stable / pre-stable / prod
             - Region: euw1 / euw2
          4. Click "Run"
          
          ### 3. Monitor Your Service
          
          - **Backstage Catalog**: View pods, logs, metrics
          - **Harness Console**: View deployment history, approvals
          - **Slack**: Get notifications in ${{ parameters.slackChannel }}
          
          ### Service Details
          
          - **Service Name**: ${{ parameters.serviceName }}
          - **Archetype**: ${{ parameters.archetype }}
          - **Profile**: ${{ parameters.profile }}
          - **Size**: ${{ parameters.size }}
          - **Environments**: ${{ parameters.environments | join(', ') }}
          - **Regions**: ${{ parameters.regions | join(', ') }}
          - **Team**: ${{ parameters.owner }}
          - **Pipeline ID**: ${{ steps['create-harness-pipeline'].output.pipelineId }}
          
          ---
          
          **Questions?** Ask in #platform-support
```

---

## 3. Catalog Entity Structure

### Backstage Component Entity

**Location**: `backstage/catalog/{service-name}.yaml` (auto-generated)

**Purpose**: Represents service in Backstage catalog for discovery and integration

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payment-service
  description: Payment processing API for checkout flow
  
  # ================================================
  # Annotations - Integration Points
  # ================================================
  annotations:
    # Kubernetes Plugin Integration
    backstage.io/kubernetes-id: payment-service
    backstage.io/kubernetes-label-selector: 'app=payment-service'
    backstage.io/kubernetes-namespace: prod-payment-service-euw1
    
    # Harness Plugin Integration
    harness.io/project: platform
    harness.io/pipeline-url: https://harness.company.com/ng/account/abc/cd/orgs/default/projects/platform/pipelines/payment-service-cd
    harness.io/services: payment-service
    
    # GitHub Integration
    github.com/project-slug: company/platform-next
    
    # TechDocs Integration
    backstage.io/techdocs-ref: dir:.
    
    # Source Location
    backstage.io/source-location: url:https://github.com/company/platform-next/tree/main/generated/payment-service
    
    # PagerDuty Integration (optional)
    pagerduty.com/integration-key: pd-payments-service
  
  # ================================================
  # Tags - For Searching and Filtering
  # ================================================
  tags:
    - api
    - kubernetes
    - kustomize
    - payments
    - public-api
    - prod
  
  # ================================================
  # Links - Quick Actions
  # ================================================
  links:
    - url: https://harness.company.com/ng/.../pipelines/payment-service-cd
      title: Deploy in Harness
      icon: harness
    
    - url: https://github.com/company/platform-next/tree/main/generated/payment-service
      title: View Generated Manifests
      icon: github
    
    - url: https://github.com/company/platform-next/blob/main/kustomize/catalog/services.yaml
      title: View in Catalog
      icon: catalog
    
    - url: https://grafana.company.com/d/payment-service
      title: Metrics Dashboard
      icon: grafana
    
    - url: https://logs.company.com/?service=payment-service
      title: Logs
      icon: dashboard
    
    - url: https://docs.company.com/services/payment-service
      title: Documentation
      icon: docs

spec:
  # ================================================
  # Component Specification
  # ================================================
  type: service
  lifecycle: production
  owner: payments-team
  system: platform-next
  
  # ================================================
  # Dependencies - API Relationships
  # ================================================
  providesApis:
    - payment-api
  
  consumesApis:
    - account-api
    - fraud-detection-api
  
  # ================================================
  # Depends On - Infrastructure Dependencies
  # ================================================
  dependsOn:
    - component:postgres-payment-db
    - component:redis-payment-cache
```

---

## 4. Integration Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      Backstage                                │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │   Software     │  │    Service     │  │    Plugins     │ │
│  │   Templates    │  │    Catalog     │  │  (K8s, Harness)│ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘ │
│           │                   │                    │          │
└───────────┼───────────────────┼────────────────────┼──────────┘
            │                   │                    │
            │ (1) Create        │ (5) Display        │ (6) Monitor
            │ Service           │ Status             │ Pods/Deploy
            │                   │                    │
            ▼                   ▼                    ▼
┌────────────────────────────────────────────────────────────────┐
│                    External Integrations                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  (1) GitHub (platform-next)                                     │
│      - Create PR to update catalog                              │
│      - Trigger CI workflows                                     │
│                                                                 │
│  (2) Pipeline Orchestrator Service                              │
│      - HTTP POST: Create pipeline request                       │
│      - Response: Pipeline ID, URL                               │
│                                                                 │
│  (3) Harness API                                                │
│      - Fetch pipeline details                                   │
│      - Get deployment history                                   │
│                                                                 │
│  (4) Kubernetes API (via delegates)                             │
│      - Get pod status                                           │
│      - Fetch logs                                               │
│      - Describe resources                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Flow: Service Creation

```
User fills form in Backstage
          ↓
Step 1: fetch-catalog
   ├─ Download services.yaml from GitHub
   └─ Store locally in workflow
          ↓
Step 2: update-catalog
   ├─ Append new service entry
   └─ Format YAML correctly
          ↓
Step 3: create-pr
   ├─ Create branch: backstage/add-{service}
   ├─ Commit updated catalog
   ├─ Open PR to platform-next repo
   └─ Tag PR with "backstage-onboarding"
          ↓
Step 4: create-harness-pipeline
   ├─ HTTP POST to Pipeline Orchestrator
   ├─ Payload: service config
   ├─ Pipeline Orchestrator creates Harness pipeline
   └─ Returns: pipeline ID, URL
          ↓
Step 5: create-catalog-entity
   ├─ Generate Backstage Component YAML
   ├─ Include annotations for integrations
   ├─ Add links to Harness, GitHub, docs
   └─ Create PR to register in catalog
          ↓
Backstage shows success page with links
```

---

## 5. User Flows

### Flow 1: Create New Service

**Actor**: Developer

**Steps**:

1. **Navigate to Backstage**
   - URL: `https://backstage.company.com`
   - Login with SSO

2. **Click "Create"**
   - Backstage home page → "Create" button
   - Shows list of available templates

3. **Select "Kubernetes Service"**
   - Template card with description
   - Click "Choose"

4. **Page 1: Service Information**
   - Service Name: `payment-service`
   - Description: `Processes payment transactions`
   - Archetype: `api`
   - Team: Select from dropdown (Backstage groups)
   - Click "Next"

5. **Page 2: Configuration**
   - Profile: `public-api`
   - Size: `medium`
   - Production Override: `large` (optional)
   - Click "Next"

6. **Page 3: Deployment**
   - Environments: ☑ int, ☑ pre, ☑ prod
   - Regions: ☑ euw1, ☑ euw2
   - Click "Next"

7. **Page 4: Ownership**
   - Slack: `#team-payments`
   - PagerDuty: `pd-payments-team`
   - Email: `payments-team@company.com`
   - Click "Next"

8. **Review & Create**
   - Shows summary of all inputs
   - Preview generated YAML
   - Click "Create"

9. **Execution Progress**
   ```
   ✓ Updating service catalog...
   ✓ Creating pull request...
   ✓ Creating Harness pipeline...
   ✓ Registering in Backstage catalog...
   ✓ Complete!
   ```

10. **Success Page**
    - Links to PRs, pipeline, catalog entry
    - Next steps instructions
    - Estimated time to ready: 5-10 minutes

**Total Time**: 3-5 minutes of developer time
**Automation Time**: 5-10 minutes for CI + pipeline creation

---

### Flow 2: Deploy Service

**Actor**: Developer or Release Manager

**Steps**:

1. **Navigate to Service in Backstage**
   - Search for `payment-service`
   - Click service card

2. **Service Overview Page**
   - See current deployment status:
     - int-stable: v2.3.1 (✓ Healthy, 2/2 pods)
     - pre-stable: v2.3.1 (✓ Healthy, 3/3 pods)
     - prod: v2.3.0 (✓ Healthy, 6/6 pods)

3. **Quick Deploy Options**
   
   **Option A: Quick Deploy Button**
   - Click "Deploy to Int-Stable" button
   - Modal opens:
     ```
     ┌──────────────────────────────────────┐
     │ Deploy payment-service               │
     ├──────────────────────────────────────┤
     │ Image Tag: [v2.3.1__________]       │
     │ Region: [euw1 ▼]                     │
     │                                      │
     │ [Cancel] [Deploy via Harness]       │
     └──────────────────────────────────────┘
     ```
   - Click "Deploy via Harness"
   - Redirects to Harness Console with pre-filled inputs

   **Option B: Navigate to Harness**
   - Click "Deploy in Harness" link
   - Opens Harness Console in new tab

4. **In Harness Console**
   - Pipeline: `payment-service-cd` loaded
   - Click "Run Pipeline"
   - Enter runtime inputs:
     - Image Tag: `v2.3.1`
     - Target Environment: `prod`
     - Target Region: `euw1`
   - Click "Run"

5. **Pipeline Execution**
   - Stage 1: Production Approval
     - Waits for 2 approvers
     - Enter change ticket: `CHG0123456`
     - Enter rollback plan: `Git revert + redeploy previous version`
   - Stage 2: Deploy
     - Fetch manifests from Git
     - Inject image tag
     - Apply to cluster
     - Health check
   - Complete!

6. **Monitor in Backstage**
   - Return to Backstage
   - Service page auto-refreshes
   - Shows: prod: v2.3.1 (✓ Healthy, 6/6 pods)
   - Deployment appears in history

**Total Time**: 5-10 minutes
**Manual Steps**: Enter image tag, approve (if prod)

---

## 6. Plugins & Extensions

### Required Backstage Plugins

#### 1. **Kubernetes Plugin**

**Package**: `@backstage/plugin-kubernetes`

**Configuration**:
```yaml
# backstage/app-config.yaml
kubernetes:
  serviceLocatorMethod:
    type: 'multiTenant'
  clusterLocatorMethods:
    - type: 'config'
      clusters:
        - url: https://int-stable-cluster.company.com
          name: int-stable
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_INT_STABLE_TOKEN}
          caData: ${K8S_INT_STABLE_CA}
        
        - url: https://pre-stable-cluster.company.com
          name: pre-stable
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_PRE_STABLE_TOKEN}
          caData: ${K8S_PRE_STABLE_CA}
        
        - url: https://prod-cluster.company.com
          name: prod
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_PROD_TOKEN}
          caData: ${K8S_PROD_CA}
```

**Features Provided**:
- Pod list and status
- Logs viewer
- Describe resources
- Resource metrics (CPU, memory)
- Error detection

**UI Location**: Service page → "Kubernetes" tab

---

#### 2. **Harness Plugin**

**Package**: `@backstage-community/plugin-harness`

**Configuration**:
```yaml
# backstage/app-config.yaml
harness:
  baseUrl: https://app.harness.io
  apiKey: ${HARNESS_API_KEY}
  accountId: ${HARNESS_ACCOUNT_ID}
```

**Features Provided**:
- Pipeline list
- Execution history
- Status badges
- Links to pipelines
- Approval status

**UI Location**: Service page → "CI/CD" tab

---

#### 3. **GitHub Plugin**

**Package**: `@backstage/plugin-github`

**Configuration**:
```yaml
# backstage/app-config.yaml
integrations:
  github:
    - host: github.com
      token: ${GITHUB_TOKEN}
```

**Features Provided**:
- Code links
- PR status
- Contributors
- Repo insights

**UI Location**: Service page → "Code" tab

---

#### 4. **TechDocs Plugin**

**Package**: `@backstage/plugin-techdocs`

**Configuration**:
```yaml
# backstage/app-config.yaml
techdocs:
  builder: 'local'
  generator:
    runIn: 'docker'
  publisher:
    type: 'googleGcs'
    googleGcs:
      bucketName: 'backstage-techdocs'
```

**Features Provided**:
- Auto-generated docs from README.md
- Searchable documentation
- Versioned docs

**UI Location**: Service page → "Docs" tab

---

#### 5. **Scaffolder Backend (Actions)**

**Packages**:
- `@backstage/plugin-scaffolder-backend`
- `@roadiehq/scaffolder-backend-module-utils` (file operations)
- `@roadiehq/scaffolder-backend-module-http-requests` (API calls)

**Custom Actions Needed**:

```typescript
// backstage/plugins/scaffolder-backend/src/actions/updateCatalog.ts

import { createTemplateAction } from '@backstage/plugin-scaffolder-backend';
import yaml from 'yaml';
import { promises as fs } from 'fs';

export const updateCatalogAction = () => {
  return createTemplateAction({
    id: 'catalog:update',
    schema: {
      input: {
        required: ['service'],
        type: 'object',
        properties: {
          service: { type: 'object' },
        },
      },
    },
    async handler(ctx) {
      const { service } = ctx.input;
      
      // Load current catalog
      const catalogPath = 'kustomize/catalog/services.yaml';
      const catalogContent = await fs.readFile(catalogPath, 'utf8');
      const catalog = yaml.parse(catalogContent);
      
      // Append new service
      catalog.services.push(service);
      
      // Write back
      await fs.writeFile(catalogPath, yaml.stringify(catalog));
      
      ctx.logger.info(`Added service ${service.name} to catalog`);
    },
  });
};
```

---

## 7. Implementation Guide

### Step 1: Install Required Plugins

```bash
# In backstage/ directory

# Install Kubernetes plugin
yarn workspace backend add @backstage/plugin-kubernetes-backend

yarn workspace app add @backstage/plugin-kubernetes

# Install Harness plugin
yarn workspace app add @backstage-community/plugin-harness

# Install utility plugins
yarn workspace backend add @roadiehq/scaffolder-backend-module-utils
yarn workspace backend add @roadiehq/scaffolder-backend-module-http-requests
```

### Step 2: Configure Plugins

**File**: `backstage/app-config.yaml`

```yaml
app:
  title: Platform Developer Portal
  baseUrl: https://backstage.company.com

organization:
  name: Company

# Kubernetes configuration
kubernetes:
  serviceLocatorMethod:
    type: 'multiTenant'
  clusterLocatorMethods:
    - type: 'config'
      clusters:
        - url: ${K8S_INT_STABLE_URL}
          name: int-stable
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_INT_STABLE_TOKEN}
          dashboardUrl: https://k8s-dashboard.int-stable.company.com
        
        - url: ${K8S_PRE_STABLE_URL}
          name: pre-stable
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_PRE_STABLE_TOKEN}
        
        - url: ${K8S_PROD_URL}
          name: prod
          authProvider: 'serviceAccount'
          serviceAccountToken: ${K8S_PROD_TOKEN}
          dashboardUrl: https://k8s-dashboard.prod.company.com

# Harness configuration
harness:
  baseUrl: https://app.harness.io
  apiKey: ${HARNESS_API_KEY}
  accountId: ${HARNESS_ACCOUNT_ID}

# GitHub configuration
integrations:
  github:
    - host: github.com
      apps:
        - appId: ${GITHUB_APP_ID}
          privateKey: ${GITHUB_APP_PRIVATE_KEY}
          webhookSecret: ${GITHUB_WEBHOOK_SECRET}

# Catalog locations
catalog:
  locations:
    # Service catalog entities
    - type: url
      target: https://github.com/company/platform-next/blob/main/backstage/catalog/*.yaml
      rules:
        - allow: [Component]
    
    # Software templates
    - type: url
      target: https://github.com/company/platform-next/blob/main/backstage/templates/*.yaml
      rules:
        - allow: [Template]

# Pipeline Orchestrator
proxy:
  '/pipeline-orchestrator':
    target: https://pipeline-orchestrator.company.com
    headers:
      Authorization: Bearer ${PIPELINE_ORCHESTRATOR_TOKEN}
```

### Step 3: Register Template

**File**: `backstage/templates/kubernetes-service.yaml`

Place the complete template YAML from Section 2 in this file.

### Step 4: Create Catalog Location

**File**: `backstage/catalog-info.yaml` (in platform-next repo root)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: platform-next-catalog
  description: Platform-Next service catalog
spec:
  type: url
  targets:
    - https://github.com/company/platform-next/blob/main/backstage/catalog/*.yaml
    - https://github.com/company/platform-next/blob/main/backstage/templates/*.yaml
```

### Step 5: Configure Service Account (K8s)

Each cluster needs a ServiceAccount for Backstage to query pod status:

```yaml
# Deploy to each cluster (int-stable, pre-stable, prod)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backstage-reader
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: backstage-reader
rules:
  - apiGroups: ['']
    resources: ['pods', 'pods/log', 'services', 'configmaps']
    verbs: ['get', 'list', 'watch']
  - apiGroups: ['apps']
    resources: ['deployments', 'replicasets', 'statefulsets']
    verbs: ['get', 'list', 'watch']
  - apiGroups: ['batch']
    resources: ['jobs', 'cronjobs']
    verbs: ['get', 'list', 'watch']
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: backstage-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: backstage-reader
subjects:
  - kind: ServiceAccount
    name: backstage-reader
    namespace: default
```

Get token:
```bash
kubectl -n default create token backstage-reader --duration=8760h
# Store in K8S_INT_STABLE_TOKEN secret
```

---

## 8. Benefits Summary

### For Developers

| Benefit | How Backstage Helps |
|---------|---------------------|
| **Easy Onboarding** | Fill form (5 fields), click Create |
| **Service Discovery** | Search catalog, find any service |
| **Quick Deployment** | One-click deploy buttons |
| **Visibility** | See pod status, logs, deployments in one place |
| **Documentation** | Auto-generated from README |

### For Platform Team

| Benefit | How Backstage Helps |
|---------|---------------------|
| **No UI Development** | Templates are YAML (declarative) |
| **Standardization** | Templates enforce standards |
| **Self-Service** | Developers onboard without help |
| **Integration** | Connects all tools (K8s, Harness, GitHub) |
| **Extensible** | Add custom plugins as needed |

---

## 9. Maintenance & Operations

### Template Updates

**When**: Add new archetype, change process

**How**:
1. Edit `backstage/templates/kubernetes-service.yaml`
2. Add new enum value or field
3. Commit to Git
4. Backstage auto-reloads (within 5 min)
5. New template available immediately

**Example**: Adding new archetype
```yaml
# Add to archetype enum
enum:
  - api
  - listener
  - streaming
  - scheduler
  - job
  - worker  # ← New archetype
enumNames:
  - 'API - HTTP/REST/gRPC services'
  - 'Listener - Event consumers'
  - 'Streaming - WebSocket servers'
  - 'Scheduler - CronJobs'
  - 'Job - Batch processing'
  - 'Worker - Background processors'  # ← New description
```

### Catalog Cleanup

**When**: Service decommissioned

**How**:
1. Remove service from `kustomize/catalog/services.yaml`
2. Delete `backstage/catalog/{service}.yaml`
3. Archive in Backstage (mark lifecycle: deprecated)
4. Pipeline Orchestrator auto-deletes Harness pipeline

---

## 10. Security & Access Control

### RBAC in Backstage

**File**: `backstage/rbac-policy.csv`

```csv
# Permission, EntityRef
catalog.entity.create, group:default/platform-team
catalog.entity.delete, group:default/platform-team
scaffolder.template.use, group:default/all-users
scaffolder.action.execute, group:default/all-users
kubernetes.proxy, group:default/platform-team
kubernetes.proxy, group:default/sre-team
```

### Permissions Model

| Role | Permissions |
|------|-------------|
| **All Developers** | Create services (templates), view catalog |
| **Team Members** | View own team's services, deploy to int/pre |
| **Platform Team** | All permissions, modify templates, delete services |
| **SRE Team** | View all services, access K8s, approve prod deploys |

---

## Summary

### What Backstage Provides

- ✅ **Self-Service UI** - No custom development
- ✅ **Service Catalog** - Searchable, filterable directory
- ✅ **Integration Hub** - Connects K8s, Harness, GitHub
- ✅ **Developer Portal** - Single pane of glass
- ✅ **Extensible** - Plugin ecosystem

### Integration Points

```
Backstage ←→ GitHub (platform-next): Create PRs, show code
Backstage ←→ Pipeline Orchestrator: Create pipelines
Backstage ←→ Harness: Show deployments, trigger pipelines
Backstage ←→ Kubernetes: Show pods, logs, metrics
```

### Developer Experience

**Before**: Email platform team, wait for onboarding, learn kubectl
**After**: Fill Backstage form (3 min), click Deploy in Harness (2 min), Done!

**Time saved**: ~2 hours per service onboarding
**Services per year**: 50-100
**Total time saved**: 100-200 hours/year

---

**This is how Backstage becomes the frontend for Platform-Next!**
