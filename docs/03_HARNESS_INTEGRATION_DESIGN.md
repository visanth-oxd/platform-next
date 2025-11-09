# Harness CD Integration - Detailed Design

## Executive Summary

This document describes how Harness CD orchestrates deployments, fetches manifests from the config repo, and manages multi-cluster deployments.

**Key Points**:
- Per-service pipelines (100+ pipelines)
- Runtime image tag injection
- Cross-org manifest fetching
- Multi-cluster delegate architecture
- GitOps-compliant (deploys from Git)

---

## 1. Why Harness for CD?

### Rationale

**Alternatives Considered**:
| Tool | Pros | Cons | Verdict |
|------|------|------|---------|
| **ArgoCD** | Free, GitOps-native | Weak approvals, new tool | ❌ Rejected |
| **Flux** | Free, declarative | No UI, limited controls | ❌ Rejected |
| **GitHub Actions** | Integrated, free | Not enterprise-grade | ❌ Rejected |
| **Harness** | Enterprise features, familiar | Cost, vendor lock-in | ✅ **Selected** |

**Why Harness Won**:
1. ✅ **Already deployed** - Teams know it
2. ✅ **Enterprise approvals** - Multi-gate, role-based
3. ✅ **Canary/Blue-Green** - Production-grade deployment strategies
4. ✅ **Audit trail** - Compliance requirements met
5. ✅ **Multi-cluster** - Native support via delegates
6. ✅ **RBAC** - Pipeline-level permissions
7. ✅ **Integrations** - PagerDuty, Slack, Jira, ServiceNow
8. ✅ **Runtime inputs** - Image tag at deployment time

**Cost Justification**:
- Harness: ~$120K/year for 100 services
- Engineer time saved: ~200 hours/month (worth ~$50K/month)
- **ROI**: Positive within 3 months

---

## 2. Pipeline Architecture

### Per-Service Pipeline Model

**Why Per-Service (not mono-pipeline)?**

| Aspect | Mono-Pipeline | Per-Service Pipelines | Winner |
|--------|---------------|----------------------|--------|
| **Isolation** | ❌ Shared execution | ✅ Independent | Per-service |
| **Scalability** | ❌ Bottleneck | ✅ Parallel (20+) | Per-service |
| **RBAC** | ❌ All-or-nothing | ✅ Granular | Per-service |
| **Rollback** | ❌ Affects all | ✅ Per-service | Per-service |
| **Customization** | ❌ Hard | ✅ Easy | Per-service |

**Decision**: One pipeline per service

---

### Pipeline Template Structure

**Location**: `harness-pipelines/templates/api-pipeline-template.yaml`

**Sections**:
1. **Metadata** - Name, ID, tags
2. **Variables** - Runtime inputs (imageTag, environment, region)
3. **Stages** - Deployment stages (int → pre → prod)
4. **Steps** - K8s operations (apply, rolling deploy, verify)
5. **Triggers** - Git webhook, API webhook

### Complete Pipeline Template

```yaml
pipeline:
  name: "{{SERVICE_NAME}}-cd"
  identifier: "{{SERVICE_NAME}}_cd"
  projectIdentifier: platform
  orgIdentifier: default
  
  tags:
    service: "{{SERVICE_NAME}}"
    archetype: "{{ARCHETYPE}}"
    team: "{{TEAM}}"
    managed-by: platform-next
  
  # ================================================
  # VARIABLES - Runtime Inputs
  # ================================================
  variables:
    - name: imageTag
      type: String
      description: "Docker image tag to deploy (e.g., v2.3.1, latest, abc123)"
      required: true
      value: <+input>
      default: latest
    
    - name: targetEnvironment
      type: String
      description: "Environment to deploy to"
      required: true
      value: <+input>.allowedValues(int-stable,pre-stable,prod)
      default: int-stable
    
    - name: targetRegion
      type: String
      description: "Region to deploy to"
      required: true
      value: <+input>.allowedValues(euw1,euw2)
      default: euw1
  
  # ================================================
  # STAGES - Deployment Stages
  # ================================================
  stages:
    # ------------------------------------------------
    # Stage 1: Deploy to Selected Environment
    # ------------------------------------------------
    - stage:
        name: Deploy to <+pipeline.variables.targetEnvironment>
        identifier: deploy_service
        type: Deployment
        
        # Stage execution condition
        when:
          pipelineStatus: Success
          condition: <+pipeline.variables.targetEnvironment> != ""
        
        spec:
          deploymentType: Kubernetes
          
          # ================================================
          # SERVICE DEFINITION
          # ================================================
          service:
            serviceRef: "{{SERVICE_NAME}}"
            serviceDefinition:
              type: Kubernetes
              spec:
                # Variables used in manifests
                variables:
                  - name: serviceName
                    type: String
                    value: "{{SERVICE_NAME}}"
                  
                  - name: imageTag
                    type: String
                    value: <+pipeline.variables.imageTag>
                  
                  - name: environment
                    type: String
                    value: <+pipeline.variables.targetEnvironment>
                  
                  - name: region
                    type: String
                    value: <+pipeline.variables.targetRegion>
                
                # ================================================
                # MANIFESTS - Fetch from Config Repo (GitOps)
                # ================================================
                manifests:
                  - manifest:
                      identifier: k8s_manifests_gitops
                      type: K8sManifest
                      spec:
                        store:
                          type: Github
                          spec:
                            # Cross-org connector to platform-next
                            connectorRef: github_platform_next_cross_org
                            gitFetchType: Branch
                            branch: main
                            paths:
                              # Dynamic path based on runtime inputs
                              - generated/{{SERVICE_NAME}}/<+pipeline.variables.targetEnvironment>/<+pipeline.variables.targetRegion>/manifests.yaml
                        
                        # Don't skip versioning (for rollback)
                        skipResourceVersioning: false
          
          # ================================================
          # ENVIRONMENT & INFRASTRUCTURE
          # ================================================
          environment:
            # Dynamic environment ref
            environmentRef: <+pipeline.variables.targetEnvironment>
            deployToAll: false
            
            # Infrastructure definition per env/region
            infrastructureDefinitions:
              - identifier: <+pipeline.variables.targetEnvironment>_<+pipeline.variables.targetRegion>_k8s
                inputs:
                  type: KubernetesDirect
                  spec:
                    # Kubernetes connector (per cluster)
                    connectorRef: k8s_<+pipeline.variables.targetEnvironment>_<+pipeline.variables.targetRegion>
                    
                    # Namespace (dynamic)
                    namespace: <+pipeline.variables.targetEnvironment>-{{SERVICE_NAME}}-<+pipeline.variables.targetRegion>
                    
                    # Release name
                    releaseName: {{SERVICE_NAME}}
                    
                    # ✅ KEY: Delegate selection (multi-cluster)
                    delegateSelectors:
                      - harness-delegate-<+pipeline.variables.targetEnvironment>-<+pipeline.variables.targetRegion>
          
          # ================================================
          # EXECUTION STEPS
          # ================================================
          execution:
            steps:
              # ============================================
              # Conditional Approval for Production
              # ============================================
              - step:
                  type: HarnessApproval
                  name: Production Approval Gate
                  identifier: prod_approval
                  
                  # Only run for production
                  when:
                    stageStatus: Success
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
                  
                  spec:
                    approvalMessage: |
                      ## Production Deployment Request
                      
                      **Service**: {{SERVICE_NAME}}
                      **Image Tag**: <+pipeline.variables.imageTag>
                      **Region**: <+pipeline.variables.targetRegion>
                      **Requester**: <+pipeline.triggeredBy.email>
                      
                      **Required Approvers**: 2
                      - 1 from {{TEAM}}
                      - 1 from Platform Team
                      
                      **Please provide**:
                      - Change ticket ID
                      - Rollback plan
                      - Business justification
                    
                    approvers:
                      userGroups:
                        - {{TEAM}}
                        - platform_team
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
                      
                      - name: business_justification
                        type: String
                        label: "Business Justification"
                        required: false
                  
                  timeout: 7d
                  failureStrategies:
                    - onFailure:
                        errors:
                          - Timeout
                        action:
                          type: Abort
              
              # ============================================
              # Production Change Window Check
              # ============================================
              - step:
                  type: Policy
                  name: Check Production Change Window
                  identifier: change_window_policy
                  
                  when:
                    stageStatus: Success
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
                  
                  spec:
                    policySets:
                      - prod_change_window
                    type: Custom
                    policySpec:
                      payload: |
                        {
                          "environment": "prod",
                          "currentTime": "<+currentTime>",
                          "dayOfWeek": "<+currentDate.dayOfWeek>",
                          "service": "{{SERVICE_NAME}}"
                        }
                  
                  timeout: 1m
                  failureStrategies:
                    - onFailure:
                        errors:
                          - PolicyEvaluationFailure
                        action:
                          type: Abort
              
              # ============================================
              # Fetch and Apply Manifests (K8s Native)
              # ============================================
              - step:
                  type: K8sApply
                  name: Apply Kubernetes Manifests
                  identifier: k8s_apply
                  
                  spec:
                    # Fetch from Git (GitOps)
                    filePaths:
                      - generated/{{SERVICE_NAME}}/<+pipeline.variables.targetEnvironment>/<+pipeline.variables.targetRegion>/manifests.yaml
                    
                    # Dry run first
                    skipDryRun: false
                    
                    # Wait for steady state
                    skipSteadyStateCheck: false
                    
                    # Command flags
                    commandFlags:
                      - --prune
                      - --selector=app={{SERVICE_NAME}}
                  
                  timeout: 10m
                  failureStrategies:
                    - onFailure:
                        errors:
                          - AllErrors
                        action:
                          type: StageRollback
              
              # ============================================
              # Rolling Deployment (K8s Native)
              # ============================================
              - step:
                  type: K8sRollingDeploy
                  name: Rolling Deployment
                  identifier: rolling_deploy
                  
                  spec:
                    skipDryRun: false
                    pruningEnabled: false
                  
                  timeout: 10m
              
              # ============================================
              # Canary Deployment (Production Only)
              # ============================================
              - stepGroup:
                  name: Canary Deployment
                  identifier: canary_group
                  
                  when:
                    stageStatus: Success
                    condition: <+pipeline.variables.targetEnvironment> == "prod"
                  
                  steps:
                    - step:
                        type: K8sCanaryDeploy
                        name: Deploy Canary (10%)
                        identifier: canary_10
                        spec:
                          instanceSelection:
                            type: Count
                            spec:
                              count: 1
                        timeout: 10m
                    
                    - step:
                        type: Verify
                        name: Verify Canary Metrics
                        identifier: verify_canary_10
                        spec:
                          type: Canary
                          spec:
                            sensitivity: MEDIUM
                            duration: 5m
                            deploymentTag: <+service.name>-<+pipeline.sequenceId>
                        timeout: 5m
                    
                    - step:
                        type: K8sCanaryDeploy
                        name: Deploy Canary (50%)
                        identifier: canary_50
                        spec:
                          instanceSelection:
                            type: Percentage
                            spec:
                              percentage: 50
                        timeout: 10m
                    
                    - step:
                        type: Verify
                        name: Verify 50% Metrics
                        identifier: verify_canary_50
                        spec:
                          type: Canary
                          duration: 10m
                        timeout: 10m
                    
                    - step:
                        type: K8sCanaryDelete
                        name: Complete Rollout (100%)
                        identifier: canary_complete
                        timeout: 5m
              
              # ============================================
              # Health Check (K8s Native)
              # ============================================
              - step:
                  type: K8sBlueGreenDeploy
                  name: Verify Deployment Health
                  identifier: verify_health
                  
                  spec:
                    skipDryRun: false
                  
                  timeout: 5m
            
            # ================================================
            # ROLLBACK STEPS
            # ================================================
            rollbackSteps:
              - step:
                  type: K8sRollingRollback
                  name: Rollback to Previous Version
                  identifier: rollback
                  timeout: 5m
        
        # Stage failure handling
        failureStrategies:
          - onFailure:
              errors:
                - AllErrors
              action:
                type: StageRollback
  
  # ================================================
  # TRIGGERS - How Pipeline Gets Invoked
  # ================================================
  triggers:
    # Trigger 1: API/Webhook (from app build)
    - trigger:
        name: App Image Built
        identifier: app_image_trigger
        enabled: true
        source:
          type: Webhook
          spec:
            type: Custom
            spec:
              payloadConditions:
                - key: service_name
                  operator: Equals
                  value: "{{SERVICE_NAME}}"
                - key: image_tag
                  operator: NotNull
                  value: ""
                - key: target_env
                  operator: NotNull
                  value: ""
        
        # Map webhook payload to pipeline variables
        inputYaml: |
          pipeline:
            identifier: {{SERVICE_NAME}}_cd
            variables:
              imageTag: <+trigger.payload.image_tag>
              targetEnvironment: <+trigger.payload.target_env>
              targetRegion: <+trigger.payload.target_region>
    
    # Trigger 2: Manual (from Backstage/UI)
    # (No configuration needed, always available)
```

---

## 3. Multi-Cluster Architecture

### The Challenge

**Different environments are in different clusters and different networks**:

```
Environment   | Cluster       | Network CIDR | Access
--------------|---------------|--------------|-------------
int-stable    | k8s-int.cloud | 10.1.0.0/16  | VPN/Direct
pre-stable    | k8s-pre.cloud | 10.2.0.0/16  | VPN/Direct
prod          | k8s-prod.cloud| 10.3.0.0/16  | Bastion only
```

**Implication**: Cannot use single Harness delegate for all clusters

---

### Solution: Delegate Per Cluster

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│ Harness SaaS Platform                                   │
│ https://app.harness.io                                  │
└────────────┬────────────┬────────────┬──────────────────┘
             │            │            │
             │            │            │
    ┌────────┴───┐   ┌───┴─────┐   ┌─┴──────────┐
    │ Delegate A │   │Delegate B│   │ Delegate C │
    │ int-stable │   │pre-stable│   │    prod    │
    └────────┬───┘   └───┬─────┘   └─┬──────────┘
             │            │            │
   ┌─────────┴───────────┴────────────┴─────────┐
   │                                              │
┌──┴──────────────┐  ┌──────────────┐  ┌────────┴──────┐
│ Cluster A       │  │ Cluster B    │  │ Cluster C     │
│ (int-stable)    │  │ (pre-stable) │  │ (prod)        │
│ Network A       │  │ Network B    │  │ Network C     │
│ 10.1.0.0/16     │  │ 10.2.0.0/16  │  │ 10.3.0.0/16   │
└─────────────────┘  └──────────────┘  └───────────────┘
```

### Delegate Deployment

**Deploy one delegate per cluster**:

```bash
# Int-Stable Cluster
kubectl create namespace harness-delegate-ng

helm install harness-delegate harness-delegate/harness-delegate-ng \
  --namespace harness-delegate-ng \
  --set delegateName=harness-delegate-int-euw1 \
  --set delegateProfile=int-stable \
  --set accountId=${HARNESS_ACCOUNT_ID} \
  --set delegateToken=${HARNESS_DELEGATE_TOKEN} \
  --set managerEndpoint=https://app.harness.io/gratis \
  --set tags="int-stable,euw1,network-a"

# Pre-Stable Cluster
# (Same, but different name and tags)
helm install harness-delegate harness-delegate/harness-delegate-ng \
  --namespace harness-delegate-ng \
  --set delegateName=harness-delegate-pre-euw1 \
  --set tags="pre-stable,euw1,network-b"

# Prod Cluster
helm install harness-delegate harness-delegate/harness-delegate-ng \
  --namespace harness-delegate-ng \
  --set delegateName=harness-delegate-prod-euw1 \
  --set tags="prod,euw1,network-c"
```

### Infrastructure Definitions

**In Harness UI**: Setup → Environments → {env} → Infrastructure Definitions

```yaml
# Int-Stable EUW1
name: int-stable-euw1
identifier: int_stable_euw1_k8s
environmentRef: int_stable
type: KubernetesDirect
spec:
  connectorRef: k8s_int_stable_euw1
  namespace: <+service.name>-<+env.name>
  releaseName: <+service.name>
  delegateSelectors:
    - harness-delegate-int-euw1  # ← Specific delegate

# Pre-Stable EUW1
name: pre-stable-euw1
identifier: pre_stable_euw1_k8s
environmentRef: pre_stable
spec:
  connectorRef: k8s_pre_stable_euw1
  delegateSelectors:
    - harness-delegate-pre-euw1  # ← Different delegate

# Prod EUW1
name: prod-euw1
identifier: prod_euw1_k8s
environmentRef: prod
spec:
  connectorRef: k8s_prod_euw1
  delegateSelectors:
    - harness-delegate-prod-euw1  # ← Production delegate
```

**Why This Works**:
- Each delegate runs in its cluster (can access K8s API locally)
- Network isolation maintained (delegate doesn't cross networks)
- Harness routes commands to correct delegate based on selector

---

## 4. Cross-Org Integration

### The Challenge

**Harness pipelines in different GitHub org than manifests**:
- Pipelines: `company-harness/harness-pipelines`
- Manifests: `company/platform-next`

**Need**: Harness must fetch manifests from different GitHub org

### Solution: Cross-Org GitHub Connector

**Setup in Harness**:

1. **Create GitHub Connector**
   - Name: `github_platform_next_cross_org`
   - URL: `https://github.com/company/platform-next`
   - Connection Type: HTTP
   - Authentication: Personal Access Token

2. **GitHub PAT Requirements**:
   - Create service account: `harness-bot@company.com`
   - Generate PAT with `repo` scope (read access)
   - Store in Harness Secrets: `github_platform_next_pat`
   - Add service account to `company/platform-next` repo (Read permission)

3. **Test Connection**:
   ```
   Harness → Connectors → github_platform_next_cross_org
   → Test Connection → Should succeed
   ```

4. **Use in Pipeline**:
   ```yaml
   manifests:
     - manifest:
         spec:
           store:
             type: Github
             spec:
               connectorRef: github_platform_next_cross_org  # ← Cross-org
               branch: main
               paths:
                 - generated/payment-service/prod/euw1/manifests.yaml
   ```

---

## 5. Image Tag Injection

### The Problem

**Manifests in Git have placeholder**:
```yaml
# generated/payment-service/prod/euw1/manifests.yaml
spec:
  containers:
    - name: app
      image: gcr.io/project/payment-service:PLACEHOLDER_TAG
```

**Need**: Replace `PLACEHOLDER_TAG` with actual image tag at deployment time

### Solution: Harness Image Replacement

**Method 1: Via Service Definition Variables**

```yaml
# In pipeline template
service:
  serviceDefinition:
    spec:
      variables:
        - name: imageTag
          value: <+pipeline.variables.imageTag>
      
      artifacts:
        primary:
          primaryArtifactRef: <+input>
          sources:
            - identifier: docker_image
              type: DockerRegistry
              spec:
                connectorRef: gcr_connector
                imagePath: gcr.io/project/{{SERVICE_NAME}}
                tag: <+pipeline.variables.imageTag>
```

**Method 2: Via Kustomize Images Transformer**

```yaml
# Generated by script in kustomization.yaml
images:
  - name: placeholder
    newName: gcr.io/project/payment-service
    newTag: PLACEHOLDER_TAG  # Will be replaced

# Harness replaces at runtime
# Final result: gcr.io/project/payment-service:v2.3.1
```

---

## 6. Pipeline Execution Flow

### Deployment Sequence

```
Developer triggers pipeline
  ├─ Inputs: imageTag=v2.3.1, targetEnvironment=prod, targetRegion=euw1
  │
  ├─ Step 1: Production Approval Gate
  │   ├─ Check if env=prod → Yes
  │   ├─ Wait for 2 approvers
  │   ├─ Collect: change_ticket, rollback_plan
  │   └─ Approved ✓
  │
  ├─ Step 2: Change Window Policy Check
  │   ├─ Evaluate OPA policy
  │   ├─ Check current time: Monday 14:00 UTC
  │   ├─ Change window: Mon-Thu 10:00-16:00 → Allowed ✓
  │   └─ Pass
  │
  ├─ Step 3: Fetch Manifests from Git
  │   ├─ Connector: github_platform_next_cross_org
  │   ├─ Branch: main
  │   ├─ Path: generated/payment-service/prod/euw1/manifests.yaml
  │   ├─ Content fetched ✓
  │   └─ Stored in Harness workspace
  │
  ├─ Step 4: K8s Apply
  │   ├─ Select delegate: harness-delegate-prod-euw1
  │   ├─ Dry run: Success
  │   ├─ Apply to cluster
  │   ├─ Wait for steady state
  │   └─ Complete ✓
  │
  ├─ Step 5: Canary 10%
  │   ├─ Deploy 1 pod with new version
  │   ├─ Monitor metrics (5 min)
  │   ├─ Check error rate, latency
  │   └─ Healthy ✓
  │
  ├─ Step 6: Canary 50%
  │   ├─ Deploy 50% pods with new version
  │   ├─ Monitor metrics (10 min)
  │   └─ Healthy ✓
  │
  ├─ Step 7: Complete Rollout
  │   ├─ Deploy to all pods
  │   ├─ Delete canary resources
  │   └─ Complete ✓
  │
  └─ Step 8: Verify Health
      ├─ Check pod status: 6/6 running
      ├─ Check readiness probes: All passing
      └─ Deployment successful ✓
```

**Total Time**: 5-30 minutes depending on environment and canary duration

---

## 7. Benefits & Rationale

### Why Harness CD?

| Requirement | Harness Solution | Alternative |
|-------------|------------------|-------------|
| **Multi-cluster** | Delegates per cluster | ArgoCD: Limited |
| **Approvals** | Native multi-gate | GitHub: Manual |
| **Canary** | Built-in | ArgoCD: Complex |
| **Runtime inputs** | Image tag injection | ArgoCD: Not supported |
| **Audit** | Full trail | Git: Limited |
| **RBAC** | Pipeline-level | Repo-level: Coarse |
| **Integrations** | PagerDuty, Slack, Jira | Manual setup |

### Why Not GitOps-Only?

**GitOps (ArgoCD/Flux) Limitations**:
- ❌ No runtime inputs (image tag must be in Git)
- ❌ Weak approval workflows
- ❌ Limited canary support
- ❌ No enterprise integrations

**Harness Advantages**:
- ✅ Runtime inputs (decouple app from config)
- ✅ Enterprise approvals (multi-gate, roles)
- ✅ Native canary (traffic splitting)
- ✅ Rich integrations (alerts, tickets)

### Hybrid Approach: Best of Both

```
Config Changes → GitOps (declarative, in Git)
App Deployments → Harness (runtime inputs, approvals)
```

**Result**: GitOps benefits + Enterprise controls

---

## 8. Integration with Backstage

### How They Connect

**Backstage → Harness Integration**:

1. **Links in Catalog Entity**
   ```yaml
   # backstage/catalog/payment-service.yaml
   metadata:
     annotations:
       harness.io/pipeline-url: https://harness.company.com/.../payment-service-cd
     links:
       - url: https://harness.company.com/.../pipelines/payment-service-cd
         title: Deploy in Harness
   ```

2. **Quick Deploy Action**
   ```yaml
   # Backstage custom action
   - id: deploy-to-env
     name: Deploy to Environment
     action: harness:trigger-pipeline
     input:
       pipelineId: payment-service-cd
       variables:
         imageTag: <+input>
         targetEnvironment: int-stable
   ```

3. **Deployment History Widget**
   ```yaml
   # Backstage service page shows Harness deployments
   # Via @backstage-community/plugin-harness
   
   Recent Deployments:
     ✓ v2.3.1 → prod (2 hours ago) - Success
     ✓ v2.3.0 → prod (1 day ago) - Success
     ✗ v2.2.9 → prod (3 days ago) - Failed
   ```

### Integration with Config Repo

**Harness → Platform-Next Integration**:

```yaml
# Pipeline fetches manifests from Git
manifests:
  - manifest:
      spec:
        store:
          type: Github
          spec:
            connectorRef: github_platform_next_cross_org
            branch: main
            paths:
              - generated/{{SERVICE_NAME}}/prod/euw1/manifests.yaml
```

**Key Points**:
- ✅ Always fetches latest from `main` branch
- ✅ Config changes auto-applied (GitOps)
- ✅ No manual sync needed
- ✅ Manifests are source of truth

---

## 9. Pipeline Lifecycle Management

### Pipeline Creation

**Trigger**: New service added via Backstage

**Flow**:
```
Backstage template executes
  ↓
Calls Pipeline Orchestrator API
  ↓
Pipeline Orchestrator:
  1. Fetch template from harness-pipelines repo
  2. Replace {{SERVICE_NAME}}, {{TEAM}}, etc.
  3. Call Harness API to create pipeline
  4. Commit pipeline YAML to harness-pipelines repo
  5. Return pipeline URL
```

**Result**: Pipeline ready to use in ~2 minutes

### Pipeline Updates

**When**: Template updated (new features, policy changes)

**Flow**:
```
Update template in harness-pipelines/templates/
  ↓
Run bulk update script
  ↓
For each pipeline:
  1. Regenerate from template
  2. Call Harness API to update
  3. Commit updated YAML
  ↓
All pipelines updated
```

**Script**: `harness-pipelines/scripts/update-all-pipelines.sh`

```bash
#!/bin/bash
# Update all pipelines from template

for SERVICE in $(yq eval '.services[].name' ../platform-next/kustomize/catalog/services.yaml); do
  ARCHETYPE=$(yq eval ".services[] | select(.name == \"$SERVICE\") | .archetype" ../platform-next/kustomize/catalog/services.yaml)
  
  # Regenerate pipeline
  ./generate-pipeline.sh $SERVICE $ARCHETYPE
  
  # Update in Harness
  harness pipeline update --file pipelines/${SERVICE}-cd.yaml
done
```

### Pipeline Deletion

**Trigger**: Service decommissioned

**Flow**:
```
Remove service from catalog
  ↓
Call Pipeline Orchestrator API DELETE
  ↓
Pipeline Orchestrator:
  1. Call Harness API to delete pipeline
  2. Move pipeline YAML to archived/
  3. Remove from harness-pipelines repo
```

---

## 10. Security & Compliance

### Security Controls

| Control | Implementation | Enforcement |
|---------|----------------|-------------|
| **No shell scripts** | Only K8s native steps | Policy blocked |
| **Image scanning** | Harness policy (before deploy) | OPA |
| **Resource limits** | Validated in CI | JSON schema |
| **Network policies** | Applied via components | K8s |
| **Pod security** | Security context in archetypes | K8s admission |
| **RBAC** | Pipeline-level permissions | Harness |

### Compliance Features

**Audit Trail**:
- Git history (who changed what config)
- Harness execution history (who deployed what)
- Approval records (who approved prod deploys)
- Change tickets (linked to deployments)

**Change Management**:
- Change window enforcement (OPA policy)
- Mandatory approvals (2+ for prod)
- Rollback plan required
- Business justification captured

---

## 11. Operational Procedures

### Deploy New Version

**Via Backstage**:
1. Navigate to service page
2. Click "Deploy to Environment"
3. Enter image tag
4. Redirects to Harness

**Via Harness Console**:
1. Navigate to Pipelines → {service}-cd
2. Click "Run Pipeline"
3. Enter runtime inputs:
   - imageTag: v2.3.1
   - targetEnvironment: prod
   - targetRegion: euw1
4. Click "Run"
5. Approve when prompted (if prod)

**Via API/Webhook**:
```bash
# From app CI/CD
curl -X POST \
  "https://app.harness.io/gateway/ng/api/webhook/..." \
  -H "x-api-key: $HARNESS_WEBHOOK_TOKEN" \
  -d '{
    "service_name": "payment-service",
    "image_tag": "v2.3.1",
    "target_env": "prod",
    "target_region": "euw1"
  }'
```

### Rollback

**Method 1: Deploy Previous Version**
```
Harness → Run Pipeline
  → imageTag: v2.3.0 (previous version)
  → Deploy
```

**Method 2: Harness Rollback**
```
Harness → Execution History
  → Select failed deployment
  → Click "Rollback"
  → Automatic rollback to previous version
```

**Method 3: Git Revert (Config Issue)**
```
git revert <bad-commit>
git push
CI regenerates manifests
Next deploy uses reverted config
```

---

## Summary

### Three-Component Integration

```
┌─────────────────────────────────────────────────────────┐
│ 1. Backstage (Developer Interface)                      │
│    - Self-service onboarding                            │
│    - Service catalog and discovery                      │
│    - Links to Harness pipelines                         │
│    - Pod status and monitoring                          │
└────────────┬────────────────────────────────────────────┘
             │
             │ Creates service entry
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Platform-Next (Config Management)                    │
│    - Kustomize archetypes and components                │
│    - Service catalog (single file)                      │
│    - Manifest generation (CI)                           │
│    - Git as source of truth (GitOps)                    │
└────────────┬────────────────────────────────────────────┘
             │
             │ Fetches manifests
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Harness (Deployment Orchestration)                   │
│    - Per-service pipelines                              │
│    - Runtime image tag injection                        │
│    - Multi-cluster delegates                            │
│    - Enterprise approvals and controls                  │
└─────────────────────────────────────────────────────────┘
```

### Developer Journey

**Onboard** (once): Backstage form → 5 min → Service ready
**Deploy** (recurring): Harness console → Enter image tag → Deploy → 5-10 min
**Monitor**: Backstage → View pods, logs, metrics

**Platform handles**: Config generation, GitOps, approvals, multi-cluster

---

**This is the complete, production-ready architecture!** 🚀
