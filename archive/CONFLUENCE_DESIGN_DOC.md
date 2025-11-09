# Kustomize-Based Config Management Platform - Design Document

---

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Last Updated** | 2025-11-08 |
| **Status** | Active |
| **Owner** | Platform Engineering Team |
| **Reviewers** | DevOps, SRE, Development Teams |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Design Goals](#design-goals)
4. [Architecture Overview](#architecture-overview)
5. [Repository Structure](#repository-structure)
6. [Core Concepts](#core-concepts)
7. [Design Layers](#design-layers)
8. [Workflow](#workflow)
9. [Component Details](#component-details)
10. [Configuration Versioning](#configuration-versioning)
11. [Multi-Region Strategy](#multi-region-strategy)
12. [Security & RBAC](#security--rbac)
13. [Operational Procedures](#operational-procedures)
14. [Best Practices](#best-practices)
15. [Future Enhancements](#future-enhancements)

---

## Executive Summary

This document describes the design and architecture of our Kustomize-based configuration management system for deploying Kubernetes workloads across multiple environments and regions.

### Key Highlights

- **Catalog-Driven**: Service configurations defined in a central catalog (`services.yaml`)
- **Just-in-Time Generation**: Kustomization manifests generated on-demand (no per-service folders)
- **Scalable**: Supports hundreds of services without repository bloat
- **Multi-Environment**: Supports int-stable, pre-stable, and production environments
- **Multi-Region**: Active-passive deployment to euw1 (primary) and euw2 (DR)
- **GitOps Ready**: Versioned configuration with git refs and channels
- **Component-Based**: Composable optional features (Ingress, Istio, HPA, PDB, etc.)

---

## Problem Statement

### Challenges with Previous Approach

**Before implementing this system, we faced:**

1. **Configuration Sprawl**
   - Each service had its own deployment YAML scattered across repositories
   - Duplication of similar configurations
   - Inconsistent patterns across services

2. **Environment Management**
   - Manual management of environment-specific values
   - No centralized view of service configurations
   - Difficult to ensure consistency across environments

3. **Scaling Issues**
   - Per-service folders lead to repository bloat at scale (100+ services)
   - Difficult to apply organization-wide policy changes
   - Hard to maintain consistency across similar workload types

4. **Versioning Complexity**
   - No clear versioning strategy for configuration
   - Difficult to rollback configuration changes
   - No separation between application version and config version

### Solution Approach

**Our Kustomize-based platform solves these by:**

- ✅ Centralized service catalog with all configuration metadata
- ✅ Template-based archetypes for common workload patterns
- ✅ Composable components for optional features
- ✅ Environment and region overlays for customization
- ✅ Git-based versioning with channels and pinning
- ✅ Automated generation of deployment manifests

---

## Design Goals

### Primary Goals

1. **Scalability**
   - Support 100+ microservices without repository bloat
   - No per-service folders (catalog-driven approach)

2. **Consistency**
   - Enforce organizational standards via base configurations
   - Reusable patterns via archetypes
   - Composable optional features via components

3. **Flexibility**
   - Per-service customization where needed
   - Environment-specific and region-specific overrides
   - Gradual rollout via channels and pinning

4. **Maintainability**
   - DRY (Don't Repeat Yourself) principle
   - Clear separation of concerns
   - Easy to apply platform-wide changes

5. **GitOps Compatibility**
   - All configuration versioned in Git
   - Declarative manifest generation
   - Reproducible builds

### Non-Goals

- ❌ Not a Helm replacement (Kustomize-native approach)
- ❌ Not a CD tool (generates manifests for ArgoCD/Flux/kubectl)
- ❌ Not responsible for application code builds (only config)

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    CATALOG LAYER                                │
│  Single Source of Truth for all service configurations         │
│  • services.yaml - Service definitions                          │
│  • channels.yaml - Release channel mappings                     │
│  • env-pins.yaml - Environment version pins                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 GENERATION LAYER                                │
│  generate-kz.sh - Reads catalog, generates kustomization       │
│  • Resolves image tags from GAR                                 │
│  • Composes archetype + components + overlays                   │
│  • Outputs to tmp/{service}/{env}/{region}/                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 KUSTOMIZE BUILD LAYER                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐           │
│  │  Archetype   │  │  Components  │  │  Overlays   │           │
│  │  (Workload   │  │  (Optional   │  │  (Env +     │           │
│  │   Shape)     │  │   Features)  │  │   Region)   │           │
│  └──────────────┘  └──────────────┘  └─────────────┘           │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                           │                                      │
│                           ▼                                      │
│                 kustomize build                                  │
│                           │                                      │
│                           ▼                                      │
│              Final Kubernetes Manifests                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DEPLOYMENT LAYER                               │
│  kubectl apply / ArgoCD / Flux                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**
   - Catalog defines "WHAT" (service metadata)
   - Archetypes define "SHAPE" (workload pattern)
   - Components define "FEATURES" (optional capabilities)
   - Overlays define "WHERE" (environment/region specifics)

2. **Composition over Inheritance**
   - Services composed from: archetype + components + overlays
   - No deep inheritance hierarchies
   - Clear, flat structure

3. **Convention over Configuration**
   - Sensible defaults in archetypes
   - Overrides only when necessary
   - Consistent naming and labeling

4. **Immutability**
   - Configuration versions pinned via git refs
   - Image tags resolved at generation time
   - Reproducible builds

---

## Repository Structure

### Directory Layout

```
platform-next/
├── kustomize/
│   ├── archetype/              # Workload type templates
│   │   ├── api/               # HTTP/REST services
│   │   ├── listener/          # Event consumers
│   │   ├── streaming/         # WebSocket/gRPC streams
│   │   ├── scheduler/         # CronJob-based tasks
│   │   └── job/              # Batch jobs
│   │
│   ├── cb-base/               # Organization-wide base config
│   │   ├── labels-annotations.yaml
│   │   ├── base-netpol.yaml
│   │   ├── pdb-defaults.yaml
│   │   └── serviceaccount-defaults.yaml
│   │
│   ├── components/            # Optional feature components
│   │   ├── ingress/          # Ingress configuration
│   │   ├── hpa/              # Horizontal Pod Autoscaler
│   │   ├── pdb/              # Pod Disruption Budget
│   │   ├── retry/            # Istio retry policies
│   │   ├── circuit-breaker/  # Istio circuit breaker
│   │   ├── mtls/             # Istio mutual TLS
│   │   ├── network-policy/   # NetworkPolicy rules
│   │   ├── security-hardening/ # Pod security
│   │   ├── topology/         # Topology spread
│   │   └── ...
│   │
│   ├── envs/                  # Environment overlays
│   │   ├── int-stable/       # Integration environment
│   │   ├── pre-stable/       # Pre-production
│   │   └── prod/             # Production
│   │
│   ├── regions/               # Region overlays
│   │   ├── euw1/             # EU West 1 (primary)
│   │   └── euw2/             # EU West 2 (DR)
│   │
│   ├── catalog/               # Service catalog metadata
│   │   ├── services.yaml     # Service definitions
│   │   ├── channels.yaml     # Channel to git ref mapping
│   │   ├── env-pins.yaml     # Environment version pins
│   │   ├── region-pins.yaml  # Region-specific pins
│   │   ├── regions.yaml      # Region metadata
│   │   └── policies.yaml     # Validation policies
│   │
│   └── kustomizeconfig/       # Kustomize configuration
│       └── varreference.yaml  # Variable reference config
│
├── scripts/
│   ├── generate-kz.sh         # Main generation script
│   └── gar.sh                 # GAR image tag resolver
│
├── tmp/                       # Generated kustomizations (gitignored)
│   └── {service}/{env}/{region}/
│       ├── kustomization.yaml
│       └── namespace.yaml
│
└── README.md
```

---

## Core Concepts

### 1. Catalog

**Definition**: Single source of truth for all service configurations

**Location**: `kustomize/catalog/services.yaml`

**Purpose**:
- Centralize service metadata
- Define service characteristics
- Specify components to enable
- Configure per-environment overrides

**Example**:
```yaml
services:
  - name: account-service
    type: api                    # Archetype
    image: gcr.io/project/account-service
    tagStrategy: gar-latest-by-branch
    channel: stable              # Release channel
    regions: [euw1, euw2]        # Deployed regions
    enabledIn: [int-stable, pre-stable, prod]
    
    components:                  # Optional features
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - hpa
    
    hpa:                         # Component configuration
      enabled: true
      minReplicas:
        defaults: 2
        overrides:
          prod: 4
      maxReplicas:
        defaults: 6
        overrides:
          prod: 10
    
    resources:                   # Resource limits
      defaults:
        cpu: "250m"
        memory: "512Mi"
      overrides:
        prod:
          cpu: "500m"
          memory: "1Gi"
```

### 2. Archetypes

**Definition**: Templates defining workload patterns (the "shape" of a service)

**Purpose**:
- Enforce consistent structure for similar workloads
- Provide sensible defaults
- Reduce duplication

**Available Archetypes**:

| Archetype | Purpose | Controller | Has Service | Has Probes | Typical Use Case |
|-----------|---------|------------|-------------|------------|------------------|
| **api** | HTTP/REST services | Deployment | ✅ Yes | ✅ Readiness + Liveness | REST APIs, gRPC services |
| **listener** | Event consumers | Deployment | ❌ No | ⚠️ Liveness only | Kafka consumers, PubSub subscribers |
| **streaming** | Long-lived connections | Deployment | ✅ Yes | ✅ Readiness + Liveness | WebSocket, Server-Sent Events |
| **scheduler** | Periodic tasks | CronJob | ❌ No | ❌ No | Scheduled jobs, cleanup tasks |
| **job** | One-time batch | Job | ❌ No | ❌ No | Migrations, data imports |

**What Archetypes Include**:
- Deployment/CronJob/Job manifest
- Service (if applicable)
- ServiceAccount and basic RBAC
- Health probes (if applicable)
- Security context defaults

**Example - API Archetype**:
```yaml
# kustomize/archetype/api/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - rbac.yaml
  - probes.yaml
```

### 3. Components

**Definition**: Optional, composable features that modify behavior

**Purpose**:
- Add optional capabilities to any archetype
- Keep archetypes minimal
- Promote reusability

**Component Type**: Kustomize `kind: Component`

**Available Components**:

| Component | Purpose | Adds Resources | Patches | Compatible Archetypes |
|-----------|---------|----------------|---------|----------------------|
| **ingress** | External HTTP(S) access | Ingress | - | api, streaming |
| **hpa** | Autoscaling | HorizontalPodAutoscaler | - | api, listener, streaming |
| **pdb** | High availability | PodDisruptionBudget | - | api, listener, streaming |
| **retry** | HTTP retry policies | VirtualService | - | api, streaming |
| **circuit-breaker** | Resilience | DestinationRule | - | api, streaming |
| **mtls** | Service mesh mTLS | DestinationRule | - | api, streaming |
| **network-policy** | Network isolation | NetworkPolicy | - | All |
| **security-hardening** | Enhanced pod security | - | Pod security patches | All |
| **topology** | Topology spread | - | Topology patches | api, listener, streaming |

**Example - HPA Component**:
```yaml
# kustomize/components/hpa/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - hpa.yaml
```

### 4. Base Configuration

**Definition**: Organization-wide defaults applied to all services

**Location**: `kustomize/cb-base/`

**Purpose**:
- Enforce company-wide standards
- Ensure compliance
- Reduce duplication

**Includes**:
- Default labels and annotations
- Base network policies
- Pod disruption budget defaults
- ServiceAccount defaults

### 5. Overlays

**Definition**: Environment and region-specific configurations

**Types**:
- **Environment Overlays** (`envs/`): int-stable, pre-stable, prod
- **Region Overlays** (`regions/`): euw1, euw2

**Environment Overlay Contents**:
- ResourceQuota
- LimitRange
- DNS configuration patches
- Certificate issuer configuration
- Network policy defaults
- Policy toggles

**Region Overlay Contents**:
- Tolerations and taints
- Topology spread constraints
- Regional certificate issuers
- Gateway class configuration
- Region-specific labels

---

## Design Layers

### Layer 1: Catalog Layer (Source of Truth)

**Responsibility**: Define WHAT to deploy

**Files**:
- `services.yaml` - Service definitions
- `channels.yaml` - Channel mappings (stable → git ref)
- `env-pins.yaml` - Environment version pins
- `region-pins.yaml` - Optional region overrides

**Key Decisions**:
- ✅ Single file per service (no per-service folders)
- ✅ Declarative configuration
- ✅ Schema-validated (JSON schema)
- ✅ Environment-specific overrides inline

### Layer 2: Archetype Layer (Workload Shape)

**Responsibility**: Define HOW to deploy (structure)

**Characteristics**:
- Each archetype is a Kustomize base (`kind: Kustomization`)
- Contains core resources for that workload type
- Minimal configuration (no environment specifics)
- Reusable across all services of same type

**Design Decision**: Use `Kustomization` (not `Component`)
- Archetypes are mutually exclusive (service is ONE type)
- Components are composable (service can have MANY)

### Layer 3: Component Layer (Optional Features)

**Responsibility**: Modify BEHAVIOR

**Characteristics**:
- Each component is `kind: Component`
- Adds resources OR patches existing ones
- Composable (multiple components per service)
- Optional (enabled via catalog)

**Design Decision**: Components are feature flags
- Service enables components in catalog
- Generator script includes enabled components
- Kustomize applies in order

### Layer 4: Base Layer (Organization Standards)

**Responsibility**: Enforce POLICIES

**Characteristics**:
- Applied to ALL services
- Organization-wide standards
- Security baselines
- Compliance requirements

### Layer 5: Overlay Layer (Environment/Region Customization)

**Responsibility**: Customize WHERE to deploy

**Characteristics**:
- Environment-specific resources
- Region-specific patches
- Layered application (env → region → service)

---

## Workflow

### Service Deployment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Developer Updates Catalog                                │
│    Edit: kustomize/catalog/services.yaml                    │
│    • Add new service OR                                      │
│    • Update existing service configuration                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Run Generation Script                                    │
│    ./scripts/generate-kz.sh account-service int-stable euw1 │
│    • Reads catalog                                           │
│    • Resolves image tag from GAR                            │
│    • Generates kustomization.yaml in tmp/                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Build Manifests                                          │
│    cd tmp/account-service/int-stable/euw1                   │
│    kustomize build . > manifests.yaml                       │
│    • Combines: archetype + components + overlays            │
│    • Applies patches                                         │
│    • Resolves values                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Validate Manifests                                       │
│    kubeconform --strict manifests.yaml                      │
│    kubectl apply --dry-run=client -f manifests.yaml         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Deploy to Cluster                                        │
│    kubectl apply -f manifests.yaml                          │
│    OR                                                        │
│    ArgoCD/Flux picks up changes                             │
└─────────────────────────────────────────────────────────────┘
```

### Generation Logic

**Script**: `scripts/generate-kz.sh`

**Steps**:

1. **Parse Input**
   ```bash
   SERVICE=account-service
   ENV=int-stable
   REGION=euw1
   TAG=<optional>
   ```

2. **Load Catalog**
   ```bash
   SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" services.yaml)
   TYPE=$(echo "$SERVICE_DATA" | yq eval '.type' -)
   COMPONENTS=$(echo "$SERVICE_DATA" | yq eval '.components[]' -)
   ```

3. **Resolve Config Version**
   ```
   channel → env-pin → region-pin
   stable → refs/tags/config-2025.11.06
   ```

4. **Resolve Image Tag**
   ```bash
   TAG=$(./gar.sh resolve --image $IMAGE --strategy $TAG_STRATEGY)
   ```

5. **Generate kustomization.yaml**
   ```yaml
   resources:
     - ../../../../kustomize/cb-base
     - ../../../../kustomize/archetype/api
     - ../../../../kustomize/envs/int-stable
     - ../../../../kustomize/regions/euw1
   
   components:
     - ../../../../kustomize/components/ingress
     - ../../../../kustomize/components/hpa
   
   namespace: int-stable-account-service-euw1
   
   images:
     - name: app
       newName: gcr.io/project/account-service
       newTag: v1.2.3
   ```

6. **Generate Environment-Specific Patches**
   - HPA replica counts
   - Resource limits
   - Ingress domain
   - Retry policies
   - Circuit breaker settings

---

## Component Details

### Archetype: API

**Files**:
```
archetype/api/
├── deployment.yaml    # Deployment with ports, probes
├── service.yaml       # ClusterIP Service
├── rbac.yaml         # ServiceAccount, RoleBinding
├── probes.yaml       # Readiness, liveness, startup
└── kustomization.yaml
```

**Characteristics**:
- Deployment controller
- Service for external exposure
- Ports: 8080 (configurable)
- All three probes (readiness, liveness, startup)
- HPA-compatible

**Typical Components**: ingress, retry, circuit-breaker, mtls, hpa, pdb

### Archetype: Listener

**Files**:
```
archetype/listener/
├── deployment.yaml    # Deployment without ports
├── rbac.yaml         # ServiceAccount, RoleBinding
├── probes.yaml       # Liveness probe only
└── kustomization.yaml
```

**Characteristics**:
- Deployment controller
- No Service (internal processing)
- No container ports
- Liveness probe only (no readiness)
- HPA-compatible

**Typical Components**: security-hardening, network-policy, pdb

### Environment Overlay: int-stable

**Files**:
```
envs/int-stable/
├── limitrange.yaml               # Resource limits
├── resourcequota.yaml            # Namespace quotas
├── networkpolicy-defaults.yaml   # Default network policies
├── dns-config-patch.yaml         # DNS configuration
├── certificate-issuer-key.yaml   # Cert-manager issuer
├── labels-annotations.yaml       # Environment labels
├── pdb-defaults.yaml            # PDB configuration
├── policy-toggles.yaml          # Feature flags
└── kustomization.yaml
```

**Purpose**:
- Enforce environment-specific policies
- Configure DNS for environment
- Set resource quotas
- Define certificate issuers

### Region Overlay: euw1

**Files**:
```
regions/euw1/
├── tolerations-taints.yaml          # Node tolerations
├── topology-spread-constraints.yaml  # AZ spread
├── certificate-issuer-key.yaml      # Regional cert issuer
├── gateway-class-key.yaml           # Ingress gateway
├── region-labels.yaml               # Region metadata
└── kustomization.yaml
```

**Purpose**:
- Configure region-specific infrastructure
- Set node affinity/tolerations
- Configure regional gateways
- Add region labels

---

## Configuration Versioning

### Channel System

**Concept**: Channels map to git refs (tags/commits)

**Channels**:
- `stable` → Production-ready configuration
- `next` → Upcoming configuration (RC)

**File**: `catalog/channels.yaml`
```yaml
channels:
  stable: refs/tags/config-2025.11.06
  next: refs/tags/config-2025.11.06-rc1
```

### Environment Pinning

**Concept**: Pin environments to specific configuration versions

**File**: `catalog/env-pins.yaml`
```yaml
envPins:
  int-stable: refs/tags/config-2025.11.06
  pre-stable: refs/tags/config-2025.11.06
  prod: refs/tags/config-2025.10.28        # Pinned to older version

defaultChannel:
  int-stable: next    # Uses 'next' channel
  pre-stable: stable  # Uses 'stable' channel
  prod: stable        # Uses 'stable' channel
```

### Region Pinning (Optional)

**Concept**: Override environment pin for specific regions

**File**: `catalog/region-pins.yaml`
```yaml
regionPins:
  euw2:
    prod: refs/tags/config-2025.11.06  # DR region gets newer config
```

### Resolution Order

```
1. Check service.channel in catalog
   ↓
2. If channel specified → use channels.yaml
   ↓
3. If no channel → check region-pins.yaml
   ↓
4. If no region pin → use env-pins.yaml
```

---

## Multi-Region Strategy

### Architecture

**Active-Passive Deployment**:
- **euw1 (EU West 1)**: Primary region, receives all traffic
- **euw2 (EU West 2)**: DR region, deployed but receives no traffic

**Traffic Routing**:
- Managed externally (Apigee, Cloud Load Balancer)
- Failover to euw2 during euw1 outage

### Deployment Pattern

**All services deployed to both regions**:
```yaml
# In catalog/services.yaml
regions: [euw1, euw2]
```

**Regional Differences**:
- Node pools (tolerations/taints)
- Availability zones (topology spread)
- Certificate issuers
- Gateway classes

**Same Configuration**:
- Image versions
- Replica counts
- Resource limits
- Application configuration

---

## Security & RBAC

### Pod Security

**Applied via**:
- Archetype defaults (runAsNonRoot, drop ALL capabilities)
- `security-hardening` component (additional hardening)

**Pod Security Context**:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
```

**Container Security Context**:
```yaml
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop: [ALL]
```

### RBAC

**Basic RBAC** (in all archetypes):
- ServiceAccount
- Role (namespace-scoped)
- RoleBinding

**Extended RBAC** (`serviceaccount-rbac` component):
- Additional permissions
- ClusterRole (if needed)
- ClusterRoleBinding (if needed)

### Network Policies

**Base NetworkPolicy** (in `cb-base`):
- Default deny all ingress
- Allow DNS

**Service-Specific** (`network-policy` component):
- Allow specific ingress/egress
- Defined per service

---

## Operational Procedures

### Adding a New Service

1. **Add to Catalog**
   ```yaml
   # kustomize/catalog/services.yaml
   services:
     - name: new-service
       type: api
       image: gcr.io/project/new-service
       tagStrategy: gar-latest
       channel: stable
       regions: [euw1, euw2]
       enabledIn: [int-stable, pre-stable, prod]
       components:
         - ingress
         - hpa
   ```

2. **Generate and Deploy**
   ```bash
   ./scripts/generate-kz.sh new-service int-stable euw1
   cd tmp/new-service/int-stable/euw1
   kustomize build . > manifests.yaml
   kubectl apply -f manifests.yaml
   ```

### Updating Service Configuration

1. **Edit Catalog**
   ```yaml
   # Change HPA settings
   hpa:
     minReplicas:
       overrides:
         prod: 6  # Increased from 4
   ```

2. **Regenerate and Deploy**
   ```bash
   ./scripts/generate-kz.sh account-service prod euw1
   kustomize build tmp/account-service/prod/euw1 | kubectl apply -f -
   ```

### Rolling Out Config Changes

1. **Update archetype/component/overlay**
2. **Tag new config version**
   ```bash
   git tag config-2025.11.08
   git push origin config-2025.11.08
   ```

3. **Update channels**
   ```yaml
   channels:
     next: refs/tags/config-2025.11.08  # Test in next first
   ```

4. **Test in int-stable** (uses 'next' channel)
5. **Promote to stable**
   ```yaml
   channels:
     stable: refs/tags/config-2025.11.08
   ```

6. **Update production pin** (when ready)
   ```yaml
   envPins:
     prod: refs/tags/config-2025.11.08
   ```

---

## Best Practices

### Catalog Management

✅ **DO**:
- Use schema validation before committing
- Keep service definitions DRY (use defaults, override only when needed)
- Document complex configurations with comments
- Use consistent naming (lowercase, hyphens)

❌ **DON'T**:
- Hardcode environment-specific values in archetype
- Duplicate configuration across services
- Skip validation

### Archetype Design

✅ **DO**:
- Keep archetypes minimal (only essential resources)
- Use components for optional features
- Provide sensible defaults
- Document expected behavior

❌ **DON'T**:
- Mix environment-specific logic into archetypes
- Create too many archetypes (keep it simple)
- Include optional features in archetypes

### Component Development

✅ **DO**:
- Make components self-contained
- Document compatibility (which archetypes work with this component)
- Use `kind: Component`
- Test with multiple archetypes

❌ **DON'T**:
- Create inter-dependencies between components
- Assume specific archetype structure
- Hardcode values (use patches/replacements)

### Environment Management

✅ **DO**:
- Use overlays for environment-specific resources (quotas, limits)
- Keep overlay patches minimal
- Document environment differences
- Test changes in int-stable first

❌ **DON'T**:
- Modify workload structure in overlays
- Create environment-specific archetypes

---

## Future Enhancements

### Planned Improvements

1. **Kustomize v5+ Features**
   - Static replacement sources (no ConfigMap needed)
   - OCI remote bases (archetypes as container images)
   - Helm chart inflation (native Helm support)
   - Enhanced image transformer (digest pinning)

2. **KRM Functions**
   - Replace `generate-kz.sh` with containerized KRM function
   - Better testability
   - Version-controlled function images

3. **Validation**
   - JSON schema validation for catalog
   - OPA policy validation
   - Pre-deployment checks

4. **GitOps Integration**
   - ArgoCD ApplicationSets
   - Flux Kustomizations
   - Automated sync

5. **Observability**
   - Config change tracking
   - Deployment metrics
   - Drift detection

### Under Consideration

- Namespace-as-a-Service
- Automatic scaling recommendations
- Cost optimization insights
- Multi-cluster support (beyond multi-region)

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| **Archetype** | Template defining workload structure (api, listener, scheduler, job) |
| **Catalog** | Central configuration file (`services.yaml`) |
| **Channel** | Named git ref (stable, next) |
| **Component** | Optional, composable feature (ingress, hpa, pdb) |
| **Overlay** | Environment or region-specific customization |
| **Pin** | Explicit git ref assignment to environment/region |

### References

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Components](https://kubectl.docs.kubernetes.io/guides/config_management/components/)
- [GitOps Principles](https://opengitops.dev/)

### Contact

- **Team**: Platform Engineering
- **Slack**: #platform-engineering
- **Email**: platform-team@company.com

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-08  
**Next Review**: 2025-12-08
