# Complete Layer Definitions: Kustomize Config Management System

## Executive Summary

This document provides **detailed definitions** for each layer in the Kustomize-based config management system. Each definition includes purpose, structure, examples, and how it relates to other layers.

---

## Table of Contents

1. [Catalog](#1-catalog)
2. [Service](#2-service)
3. [Profile](#3-profile)
4. [Size](#4-size)
5. [Archetype](#5-archetype)
6. [Component](#6-component)
7. [Base (cb-base)](#7-base-cb-base)
8. [Environment Overlay](#8-environment-overlay)
9. [Region Overlay](#9-region-overlay)
10. [How Layers Work Together](#10-how-layers-work-together)

---

## 1. Catalog

### **Definition**

The **Catalog** is the **single source of truth** for all service metadata and configuration. It's a collection of YAML files in `kustomize/catalog/` that define:
- What services exist
- How services are configured
- What profiles are available
- What sizes are available
- Release channel mappings
- Environment version pins

### **Purpose**

- **Centralized Configuration**: All service definitions in one place
- **Developer Interface**: Simple YAML files that developers can edit
- **Version Control**: All changes tracked in Git
- **Validation**: Schema-validated to prevent errors
- **Automation**: CI/CD reads catalog to generate manifests

### **Structure**

```
kustomize/catalog/
├── services.yaml      # Service definitions (main catalog)
├── profiles.yaml      # Behavior profile templates
├── sizes.yaml         # Resource size definitions
├── channels.yaml      # Release channel mappings
└── env-pins.yaml      # Environment version pins
```

### **Catalog Files Explained**

#### **1.1 services.yaml**

**Purpose**: Defines all services in the platform

**What it Contains**:
- Service name
- Archetype (what type of workload)
- Profile (which behavior profile to use)
- Size (resource sizing)
- Image location
- Components to enable
- Environment-specific overrides
- Region configuration
- Resource requirements
- Scaling configuration

**Example**:
```yaml
services:
  - name: payment-processor
    archetype: api              # Workload type
    profile: public-api          # Behavior profile
    size: large                 # Resource size
    image: gcr.io/project/payment-processor
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
    enabledIn: [int-stable, pre-stable, prod]
    
    # Components (can come from profile or be explicit)
    components:
      - ingress
      - hpa
      - pdb
    
    # Resource configuration
    resources:
      defaults:
        cpu: "500m"
        memory: "1Gi"
      overrides:
        prod:
          cpu: "1000m"
          memory: "2Gi"
    
    # HPA configuration
    hpa:
      enabled: true
      minReplicas:
        defaults: 3
        overrides:
          prod: 4
      maxReplicas:
        defaults: 10
        overrides:
          prod: 15
    
    # Ingress configuration
    domains:
      int-stable: payment-processor.int.example.com
      prod: payment-processor.example.com
```

**Key Points**:
- One entry per service
- References other catalog files (profile, size)
- Can have environment-specific overrides
- Single source of truth for service configuration

---

#### **1.2 profiles.yaml**

**Purpose**: Defines reusable behavior profiles that bundle archetype + components + settings

**What it Contains**:
- Profile name
- Which archetype it uses
- Which components are enabled
- Default probe paths
- Default configurations

**Example**:
```yaml
profiles:
  public-api:
    description: "External-facing REST API with full feature set"
    archetype: api
    components:
      - ingress          # External access
      - hpa              # Auto-scaling
      - pdb              # High availability
      - retry            # HTTP retry policies
      - circuit-breaker  # Resilience
      - mtls             # Service mesh security
      - network-policy   # Network isolation
      - security-hardening
    probes:
      readiness: /health/ready
      liveness: /health/live
  
  internal-api:
    description: "Internal-only API, no external access"
    archetype: api
    components:
      - hpa
      - pdb
      - mtls
      - network-policy
    probes:
      readiness: /health/ready
      liveness: /health/live
  
  event-consumer:
    description: "Kafka/PubSub event consumer"
    archetype: listener
    components:
      - pdb
      - security-hardening
    probes:
      liveness: /health/live  # No readiness probe for listeners
```

**Key Points**:
- **Reusable templates**: One profile can be used by many services
- **Bundles components**: Instead of listing components per service, use a profile
- **DRY principle**: Define once, use many times
- **Archetype + Components**: Profile specifies both the workload type and features

**Profile vs Archetype**:
- **Archetype**: Defines the **structure** (Deployment, Service, probes)
- **Profile**: Defines the **behavior** (which components, which settings)
- **Profile includes archetype**: A profile always specifies which archetype to use

---

#### **1.3 sizes.yaml**

**Purpose**: Defines T-shirt sizing for resources (CPU, memory) and scaling (replicas)

**What it Contains**:
- Size name (small, medium, large, xlarge, xxlarge)
- CPU request and limit
- Memory request and limit
- Scaling configuration (min/max replicas, CPU target)

**Example**:
```yaml
sizes:
  small:
    cpu: 100m              # CPU request
    memory: 256Mi          # Memory request
    limits:
      cpu: 200m            # CPU limit
      memory: 512Mi        # Memory limit
    scaling:
      min: 1               # Minimum replicas
      max: 3               # Maximum replicas
      cpuTarget: 80        # CPU target for HPA (%)
  
  medium:
    cpu: 250m
    memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi
    scaling:
      min: 2
      max: 6
      cpuTarget: 75
  
  large:
    cpu: 500m
    memory: 1Gi
    limits:
      cpu: 1000m
      memory: 2Gi
    scaling:
      min: 3
      max: 10
      cpuTarget: 70
  
  xlarge:
    cpu: 1000m
    memory: 2Gi
    limits:
      cpu: 2000m
      memory: 4Gi
    scaling:
      min: 4
      max: 15
      cpuTarget: 65
```

**Key Points**:
- **Standardized sizing**: Consistent resource allocation across services
- **Scaling included**: Min/max replicas and CPU target for HPA
- **Request vs Limit**: Both defined for proper resource management
- **Reusable**: Same size definition used by all services of that size

**How Size is Used**:
1. Service specifies `size: large` in catalog
2. Manifest generation script reads `sizes.yaml` for `large`
3. Extracts CPU, memory, min/max replicas
4. Patches Deployment with CPU/memory
5. Patches HPA with min/max replicas

---

#### **1.4 channels.yaml**

**Purpose**: Maps release channels (stable, beta, alpha) to Git refs (branches, tags)

**What it Contains**:
- Channel name
- Git ref (branch or tag)

**Example**:
```yaml
channels:
  stable: main              # Stable channel → main branch
  beta: develop            # Beta channel → develop branch
  alpha: feature/*         # Alpha channel → feature branches
```

**Key Points**:
- **Release management**: Different channels for different stability levels
- **Git ref mapping**: Maps abstract channels to concrete Git refs
- **Used by CI/CD**: Determines which code version to deploy

---

#### **1.5 env-pins.yaml**

**Purpose**: Pins environment versions (which Git ref to use per environment)

**What it Contains**:
- Environment name
- Git ref (tag or commit)

**Example**:
```yaml
envPins:
  int-stable: v1.2.3        # int-stable uses v1.2.3 tag
  pre-stable: v1.2.3        # pre-stable uses v1.2.3 tag
  prod: v1.2.2              # prod uses v1.2.2 tag (older, stable)
```

**Key Points**:
- **Version control**: Ensures environments use specific versions
- **Rollback safety**: Prod can use older, proven versions
- **Override mechanism**: Can override per region if needed

---

## 2. Service

### **Definition**

A **Service** is a single application/workload that runs in Kubernetes. It's defined in the catalog (`services.yaml`) and represents one deployable unit.

### **Purpose**

- **Service Identity**: Unique name and configuration
- **Deployment Target**: What gets deployed to clusters
- **Configuration Container**: Holds all service-specific settings

### **What a Service Contains**

```yaml
services:
  - name: payment-processor        # Service name (unique identifier)
    archetype: api                  # What type of workload
    profile: public-api             # Which behavior profile
    size: large                     # Resource size
    image: gcr.io/project/payment-processor
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]           # Where to deploy
    enabledIn: [int-stable, pre-stable, prod]  # Which environments
    
    # Components (optional, can come from profile)
    components:
      - ingress
      - hpa
      - pdb
    
    # Resource configuration
    resources:
      defaults:
        cpu: "500m"
        memory: "1Gi"
      overrides:
        prod:
          cpu: "1000m"
    
    # HPA configuration
    hpa:
      enabled: true
      minReplicas:
        defaults: 3
        overrides:
          prod: 4
    
    # Ingress configuration
    domains:
      int-stable: payment-processor.int.example.com
      prod: payment-processor.example.com
```

### **Key Concepts**

**Service Name**:
- Unique identifier
- Used for namespace, labels, resource names
- Must be DNS-compliant (lowercase, hyphens)

**Service References**:
- **Profile**: References a profile from `profiles.yaml`
- **Size**: References a size from `sizes.yaml`
- **Archetype**: Can be explicit or come from profile

**Service Overrides**:
- Can override profile defaults
- Can override size defaults
- Can have environment-specific overrides

---

## 3. Profile

### **Definition**

A **Profile** is a **reusable behavior template** that bundles:
- An archetype (workload type)
- A set of components (optional features)
- Default configurations (probes, settings)

### **Purpose**

- **DRY Principle**: Define behavior once, reuse many times
- **Consistency**: Services with same profile behave the same way
- **Simplicity**: Developers select a profile instead of configuring everything

### **What a Profile Contains**

```yaml
profiles:
  public-api:
    description: "External-facing REST API with full feature set"
    archetype: api                    # Which archetype to use
    components:                        # Which components to enable
      - ingress
      - hpa
      - pdb
      - retry
      - circuit-breaker
      - mtls
      - network-policy
      - security-hardening
    probes:                           # Default probe paths
      readiness: /health/ready
      liveness: /health/live
    defaults:                         # Default settings
      size: medium
```

### **Profile Examples**

#### **Profile: `public-api`**
- **Archetype**: `api`
- **Components**: ingress, hpa, pdb, retry, circuit-breaker, mtls, network-policy
- **Use Case**: External-facing REST APIs that need external access, scaling, resilience

#### **Profile: `internal-api`**
- **Archetype**: `api`
- **Components**: hpa, pdb, mtls, network-policy (NO ingress)
- **Use Case**: Internal-only APIs, no external access needed

#### **Profile: `event-consumer`**
- **Archetype**: `listener`
- **Components**: pdb, security-hardening
- **Use Case**: Kafka/PubSub consumers, no Service, no ingress

### **Profile vs Archetype**

| Aspect | Archetype | Profile |
|--------|-----------|---------|
| **Defines** | Structure (Deployment, Service, probes) | Behavior (components, settings) |
| **Contains** | Kubernetes resources | Component list + archetype reference |
| **Quantity** | ONE per service | ONE per service (but references archetype) |
| **Purpose** | "What type of workload" | "How should it behave" |
| **Example** | `api`, `listener`, `job` | `public-api`, `internal-api`, `event-consumer` |

**Key Insight**: 
- **Archetype** = The skeleton (Deployment, Service structure)
- **Profile** = The flesh (which features/components to add)

**Profile includes Archetype**:
```yaml
profiles:
  public-api:
    archetype: api    # ← Profile specifies which archetype to use
    components: [...] # ← Profile adds components on top
```

---

## 4. Size

### **Definition**

**Size** is a **T-shirt sizing system** that defines:
- Resource requests and limits (CPU, memory)
- Scaling configuration (min/max replicas, CPU target)

### **Purpose**

- **Standardization**: Consistent resource allocation
- **Simplicity**: Developers choose "large" instead of specifying exact CPU/memory
- **Scaling**: Includes HPA configuration (min/max replicas)

### **What a Size Contains**

```yaml
sizes:
  small:
    cpu: 100m              # CPU request
    memory: 256Mi          # Memory request
    limits:
      cpu: 200m            # CPU limit (2× request)
      memory: 512Mi        # Memory limit (2× request)
    scaling:
      min: 1               # Minimum replicas for HPA
      max: 3               # Maximum replicas for HPA
      cpuTarget: 80        # CPU target percentage for HPA
  
  medium:
    cpu: 250m
    memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi
    scaling:
      min: 2
      max: 6
      cpuTarget: 75
  
  large:
    cpu: 500m
    memory: 1Gi
    limits:
      cpu: 1000m
      memory: 2Gi
    scaling:
      min: 3
      max: 10
      cpuTarget: 70
```

### **Size Tiers**

| Size | CPU Request | Memory Request | Min Replicas | Max Replicas | Use Case |
|------|-------------|----------------|--------------|--------------|----------|
| **small** | 100m | 256Mi | 1 | 3 | Dev/test, low traffic |
| **medium** | 250m | 512Mi | 2 | 6 | Standard production |
| **large** | 500m | 1Gi | 3 | 10 | High traffic |
| **xlarge** | 1000m | 2Gi | 4 | 15 | Critical services |
| **xxlarge** | 2000m | 4Gi | 5 | 20 | ML, analytics |

### **How Size is Used**

1. **Service specifies size**:
   ```yaml
   services:
     - name: payment-processor
       size: large
   ```

2. **Manifest generation reads size**:
   ```bash
   # Script reads sizes.yaml
   SIZE_DATA=$(yq eval ".sizes.large" sizes.yaml)
   CPU=$(echo "$SIZE_DATA" | yq eval '.cpu')
   MEMORY=$(echo "$SIZE_DATA" | yq eval '.memory')
   MIN_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.min')
   MAX_REPLICAS=$(echo "$SIZE_DATA" | yq eval '.scaling.max')
   ```

3. **Size values applied**:
   - CPU/memory → Patched into Deployment
   - Min/max replicas → Patched into HPA

### **Size Overrides**

Services can override size per environment:
```yaml
services:
  - name: payment-processor
    size: large              # Default size
    resources:
      overrides:
        prod:
          size: xlarge       # Production uses xlarge
```

---

## 5. Archetype

### **Definition**

An **Archetype** defines the **fundamental structure** of a workload type. It answers:
- What Kubernetes controller? (Deployment, CronJob, Job, StatefulSet)
- Does it need a Service?
- What health probes?
- What ports?
- What security context?

### **Purpose**

- **Structure Definition**: Core Kubernetes resources for a workload type
- **Consistency**: All services of same archetype have same structure
- **Reusability**: One archetype used by many services

### **What an Archetype Contains**

```
archetype/api/
├── kustomization.yaml
├── deployment.yaml       # Deployment resource
├── service.yaml         # ClusterIP Service
├── rbac.yaml            # ServiceAccount, Role, RoleBinding
└── probes.yaml          # Health probes (readiness, liveness)
```

### **Archetype Examples**

#### **Archetype: `api`**
- **Controller**: Deployment
- **Service**: ✅ Yes (ClusterIP)
- **Probes**: ✅ Readiness + Liveness
- **Ports**: 8080 (container), 80 (service)
- **Use Case**: HTTP/REST APIs, gRPC services

#### **Archetype: `listener`**
- **Controller**: Deployment
- **Service**: ❌ No (no external access needed)
- **Probes**: ⚠️ Liveness only (no readiness)
- **Ports**: None (or internal only)
- **Use Case**: Kafka consumers, PubSub subscribers

#### **Archetype: `job`**
- **Controller**: Job
- **Service**: ❌ No
- **Probes**: ❌ No
- **Ports**: None
- **Use Case**: One-time batch jobs, migrations

### **Archetype Structure**

**deployment.yaml** (for `api` archetype):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 2                    # Placeholder, will be patched
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      serviceAccountName: app-sa
      containers:
        - name: app
          image: placeholder:latest  # Replaced by Harness
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "250m"         # Placeholder, will be patched
              memory: "512Mi"     # Placeholder, will be patched
```

**Key Points**:
- **Minimal**: Only core structure, no optional features
- **Placeholders**: Image, resources, replicas are placeholders
- **Patchable**: Can be customized via patches
- **Reusable**: Same archetype for all services of that type

---

## 6. Component

### **Definition**

A **Component** is an **optional, composable feature** that modifies or extends an archetype. Components add resources or patch existing ones.

### **Purpose**

- **Feature Add-ons**: Enable optional capabilities (ingress, HPA, PDB)
- **Composability**: Can combine multiple components
- **Flexibility**: Enable/disable features per service

### **What a Component Contains**

```
components/ingress/
├── kustomization.yaml    # kind: Component
└── ingress.yaml          # Ingress resource
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component  # ← Important: kind=Component

resources:
  - ingress.yaml
```

### **Component Examples**

#### **Component: `ingress`**
- **Adds**: Ingress resource
- **Purpose**: External HTTP(S) access
- **Compatible with**: `api`, `streaming` archetypes

#### **Component: `hpa`**
- **Adds**: HorizontalPodAutoscaler resource
- **Purpose**: Automatic scaling based on CPU/memory
- **Compatible with**: `api`, `listener`, `streaming` archetypes

#### **Component: `pdb`**
- **Adds**: PodDisruptionBudget resource
- **Purpose**: High availability during disruptions
- **Compatible with**: `api`, `listener`, `streaming` archetypes

### **Component vs Archetype**

| Aspect | Archetype | Component |
|--------|-----------|-----------|
| **Kind** | `Kustomization` | `Component` |
| **Quantity** | ONE per service | MANY per service |
| **Purpose** | Define structure | Modify behavior |
| **Required** | ✅ Yes | ❌ No (optional) |
| **Contains** | Core resources | Optional features |

**Key Insight**:
- **Archetype** = The foundation (Deployment, Service)
- **Component** = The features (Ingress, HPA, PDB)

---

## 7. Base (cb-base)

### **Definition**

**Base** (also called `cb-base`) is the **organization-wide foundation** that applies to ALL services. It enforces company-wide standards and policies.

### **Purpose**

- **Consistency**: All services get same base configuration
- **Compliance**: Enforces security and policy requirements
- **Standards**: Common labels, annotations, network policies

### **What Base Contains**

```
cb-base/
├── kustomization.yaml
├── labels-annotations.yaml    # Common labels/annotations
├── base-netpol.yaml           # Base network policy
└── serviceaccount-defaults.yaml  # ServiceAccount defaults
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - labels-annotations.yaml
  - base-netpol.yaml
  - serviceaccount-defaults.yaml

commonLabels:
  platform: kubernetes
  managed-by: kustomize
  company: mycompany

commonAnnotations:
  platform.company.com/managed: "true"
```

### **Base Contents Explained**

#### **labels-annotations.yaml**
- Common labels applied to all resources
- Common annotations applied to all resources
- Examples: `platform: kubernetes`, `managed-by: kustomize`

#### **base-netpol.yaml**
- Base NetworkPolicy applied to all namespaces
- Can be minimal (allow-all) or restrictive
- Ensures network isolation baseline

#### **serviceaccount-defaults.yaml**
- Default ServiceAccount configuration
- Common RBAC settings
- Security context defaults

### **Key Points**

- **Applied to ALL services**: Every service gets base configuration
- **Change once, affects all**: Update base, all services get update
- **Lowest layer**: Base is included first in kustomization.yaml
- **Organization standards**: Enforces company-wide policies

---

## 8. Environment Overlay

### **Definition**

An **Environment Overlay** provides **environment-specific configuration** that varies by environment (int-stable, pre-stable, prod).

### **Purpose**

- **Environment Differences**: Different configs for dev vs prod
- **Resource Controls**: Stricter limits in prod
- **Policy Toggles**: Enable/disable features per environment

### **What an Environment Overlay Contains**

```
envs/int-stable/
├── kustomization.yaml
├── limitrange.yaml              # Container resource limits
├── resourcequota.yaml          # Namespace resource quotas
├── dns-config-patch.yaml       # DNS configuration
└── certificate-issuer-patch.yaml  # Certificate issuer
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - limitrange.yaml
  - resourcequota.yaml

patches:
  - path: dns-config-patch.yaml
  - path: certificate-issuer-patch.yaml
```

### **Environment Overlay Contents Explained**

#### **limitrange.yaml**
- Container resource limits per environment
- Default requests/limits
- Example: Prod has higher limits than int-stable

#### **resourcequota.yaml**
- Namespace resource quotas
- Total CPU/memory/pods allowed per namespace
- Example: Prod namespace can have more resources

#### **dns-config-patch.yaml**
- DNS configuration patches
- Custom DNS settings per environment
- Example: Prod uses different DNS servers

#### **certificate-issuer-patch.yaml**
- Certificate issuer configuration
- Different cert issuers per environment
- Example: int-stable uses `letsencrypt-staging`, prod uses `letsencrypt-prod`

### **Environment Examples**

#### **int-stable Environment**
- **Purpose**: Integration testing
- **Characteristics**: Lower resource limits, staging certificates, relaxed policies
- **Use Case**: Pre-production testing

#### **pre-stable Environment**
- **Purpose**: Pre-production validation
- **Characteristics**: Production-like limits, production certificates, stricter policies
- **Use Case**: Final validation before prod

#### **prod Environment**
- **Purpose**: Production
- **Characteristics**: Highest limits, production certificates, strictest policies
- **Use Case**: Live customer traffic

### **Key Points**

- **Environment-specific**: Each environment has its own overlay
- **Applied after base**: Overlays modify base configuration
- **Patches resources**: Can patch Deployment, Service, etc.
- **Policy enforcement**: Different policies per environment

---

## 9. Region Overlay

### **Definition**

A **Region Overlay** provides **region-specific configuration** that varies by geographic region (euw1, euw2).

### **Purpose**

- **Geographic Differences**: Different configs for different regions
- **Infrastructure Variations**: Different node pools, availability zones
- **Regional Policies**: Region-specific labels, tolerations

### **What a Region Overlay Contains**

```
regions/euw1/
├── kustomization.yaml
├── region-labels-patch.yaml    # Region labels
├── gateway-class-patch.yaml   # Gateway class for ingress
└── topology-spread-patch.yaml # Topology spread constraints
```

**kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

patches:
  - path: region-labels-patch.yaml
  - path: gateway-class-patch.yaml
  - path: topology-spread-patch.yaml
```

### **Region Overlay Contents Explained**

#### **region-labels-patch.yaml**
- Adds region label to all resources
- Example: `region: euw1`
- Used for cost tracking, monitoring

#### **gateway-class-patch.yaml**
- Gateway class for Ingress
- Different gateway classes per region
- Example: `nginx-euw1` for euw1, `nginx-euw2` for euw2

#### **topology-spread-patch.yaml**
- Topology spread constraints
- Pod distribution across availability zones
- Example: Spread pods across 3 AZs in euw1

### **Region Examples**

#### **euw1 (EU West 1)**
- **Purpose**: Primary region
- **Characteristics**: Full infrastructure, all features
- **Use Case**: Main production region

#### **euw2 (EU West 2)**
- **Purpose**: Disaster recovery region
- **Characteristics**: Similar to euw1, different infrastructure
- **Use Case**: DR, regional failover

### **Key Points**

- **Region-specific**: Each region has its own overlay
- **Applied after environment**: Region overlays modify environment overlays
- **Infrastructure-aware**: Reflects actual infrastructure differences
- **Geographic separation**: Different configs for different locations

---

## 10. How Layers Work Together

### **Layer Hierarchy**

The layers are applied in this order (bottom to top):

```
1. Base (cb-base)                    ← Organization standards
   ↓
2. Archetype (api)                   ← Workload structure
   ↓
3. Components (ingress, hpa, pdb)     ← Optional features
   ↓
4. Environment Overlay (int-stable)   ← Environment config
   ↓
5. Region Overlay (euw1)              ← Region config
   ↓
6. Service-specific patches           ← Service overrides
   ↓
Final Kubernetes Manifests
```

### **Complete Example: payment-processor**

**Service Definition** (catalog):
```yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    regions: [euw1]
    enabledIn: [int-stable]
```

**Generated kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# 1. Base (organization standards)
resources:
  - ../../../../kustomize/cb-base

# 2. Archetype (workload structure)
  - ../../../../kustomize/archetype/api

# 3. Environment Overlay (environment config)
  - ../../../../kustomize/envs/int-stable

# 4. Region Overlay (region config)
  - ../../../../kustomize/regions/euw1

# 5. Components (optional features from profile)
components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa
  - ../../../../kustomize/components/pdb

# 6. Service-specific configuration
namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

# 7. Service-specific patches (from size)
patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "500m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "1Gi"
  
  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 3
      - op: replace
        path: /spec/maxReplicas
        value: 10
```

### **Data Flow**

```
1. Catalog (services.yaml)
   ↓
   Service: payment-processor
   - archetype: api
   - profile: public-api
   - size: large
   ↓
2. Profile Lookup (profiles.yaml)
   ↓
   Profile: public-api
   - archetype: api
   - components: [ingress, hpa, pdb, ...]
   ↓
3. Size Lookup (sizes.yaml)
   ↓
   Size: large
   - cpu: 500m
   - memory: 1Gi
   - scaling: {min: 3, max: 10}
   ↓
4. Manifest Generation Script
   ↓
   Generates kustomization.yaml with:
   - Base + Archetype + Components + Overlays
   - Patches from size
   ↓
5. Kustomize Build
   ↓
   Final Kubernetes Manifests
```

### **Key Relationships**

**Service → Profile → Archetype**:
- Service references a profile
- Profile references an archetype
- Service gets archetype structure + profile components

**Service → Size → Resources**:
- Service references a size
- Size defines CPU/memory/replicas
- Service gets resources from size

**Service → Environment → Overlays**:
- Service specifies environments
- Each environment has its own overlay
- Overlays modify base configuration

**Service → Region → Overlays**:
- Service specifies regions
- Each region has its own overlay
- Overlays modify environment configuration

---

## 11. Summary Table

| Layer | Purpose | Contains | Kind | Required | Example |
|-------|---------|----------|------|----------|---------|
| **Catalog** | Service definitions | services.yaml, profiles.yaml, sizes.yaml | YAML data | ✅ Yes | Service metadata |
| **Service** | Single application | Name, archetype, profile, size, config | YAML entry | ✅ Yes | payment-processor |
| **Profile** | Behavior template | Archetype + components + settings | YAML entry | ✅ Yes | public-api |
| **Size** | Resource sizing | CPU, memory, replicas | YAML entry | ✅ Yes | large |
| **Archetype** | Workload structure | Deployment, Service, RBAC, probes | Kustomization | ✅ Yes | api |
| **Component** | Optional feature | Ingress, HPA, PDB resources | Component | ❌ No | ingress |
| **Base** | Org standards | Labels, annotations, policies | Kustomization | ✅ Yes | cb-base |
| **Environment Overlay** | Env-specific config | Limits, quotas, DNS, certs | Kustomization | ✅ Yes | int-stable |
| **Region Overlay** | Region-specific config | Labels, gateway class, topology | Kustomization | ✅ Yes | euw1 |

---

## 12. Quick Reference

### **What is a Catalog?**
The catalog is the collection of YAML files that define all services, profiles, and sizes. It's the single source of truth.

### **What is a Service?**
A service is a single application/workload defined in the catalog. It references a profile and size.

### **What is a Profile?**
A profile is a reusable behavior template that bundles an archetype + components + settings. Examples: `public-api`, `internal-api`.

### **What is a Size?**
A size is a T-shirt sizing system (small, medium, large) that defines CPU, memory, and scaling configuration.

### **What is an Archetype?**
An archetype defines the fundamental structure of a workload type (Deployment, Service, probes). Examples: `api`, `listener`, `job`.

### **What is a Component?**
A component is an optional feature that adds resources or patches existing ones. Examples: `ingress`, `hpa`, `pdb`.

### **What is Base (cb-base)?**
Base is the organization-wide foundation that applies to all services (labels, annotations, policies).

### **What is an Environment Overlay?**
An environment overlay provides environment-specific configuration (int-stable, pre-stable, prod).

### **What is a Region Overlay?**
A region overlay provides region-specific configuration (euw1, euw2).

---

This document provides complete definitions for each layer in the Kustomize config management system.

