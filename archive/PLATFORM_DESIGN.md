# Platform-Next Kustomize Config Management - Complete Design

---

## Table of Contents

1. [Repository Structure Overview](#1-repository-structure-overview)
2. [Archetypes - Workload Shapes](#2-archetypes---workload-shapes)
3. [Components - Behavior Modifiers](#3-components---behavior-modifiers)
4. [Base Configuration - Organization Standards](#4-base-configuration---organization-standards)
5. [Overlays - Environment & Region Customization](#5-overlays---environment--region-customization)
6. [Patches & Replacements](#6-patches--replacements)
7. [Catalog - Developer Interface](#7-catalog---developer-interface)
8. [T-Shirt Sizing System](#8-t-shirt-sizing-system)
9. [How It All Works Together](#9-how-it-all-works-together)

---

## 1. Repository Structure Overview

### What We Have in `kustomize/`

```
kustomize/
├── archetype/           # Layer 1: Workload Shapes (WHAT you're deploying)
│   ├── api/            #   - HTTP/REST services
│   ├── listener/       #   - Event consumers
│   ├── streaming/      #   - WebSocket/long-lived connections
│   ├── scheduler/      #   - CronJobs
│   └── job/            #   - Batch jobs
│
├── components/          # Layer 2: Behavior Modifiers (HOW it behaves)
│   ├── ingress/        #   - External access
│   ├── hpa/            #   - Auto-scaling
│   ├── pdb/            #   - High availability
│   ├── retry/          #   - HTTP retry policies
│   ├── circuit-breaker/#   - Resilience patterns
│   ├── mtls/           #   - Service mesh security
│   ├── network-policy/ #   - Network isolation
│   ├── security-hardening/
│   ├── topology/       #   - Pod spread
│   └── ...
│
├── cb-base/             # Layer 3: Organization Standards (BASELINE)
│   ├── labels-annotations.yaml
│   ├── base-netpol.yaml
│   ├── pdb-defaults.yaml
│   └── serviceaccount-defaults.yaml
│
├── envs/                # Layer 4: Environment Overlays (WHERE - Environment)
│   ├── int-stable/
│   ├── pre-stable/
│   └── prod/
│
├── regions/             # Layer 5: Region Overlays (WHERE - Geography)
│   ├── euw1/           #   - EU West 1 (primary)
│   └── euw2/           #   - EU West 2 (DR)
│
└── catalog/             # Layer 6: Configuration Metadata (CATALOG)
    ├── services.yaml        # Service definitions
    ├── profiles.yaml        # Behavior profiles (NEW)
    ├── sizes.yaml          # T-shirt sizing (NEW)
    ├── channels.yaml       # Release channels
    ├── env-pins.yaml       # Environment versioning
    └── policies.yaml       # Validation rules
```

### Design Philosophy

**Each layer has a single responsibility:**

| Layer | Responsibility | Kind | Files |
|-------|---------------|------|-------|
| **Archetype** | Define structure | `Kustomization` | deployment.yaml, service.yaml, rbac.yaml |
| **Component** | Add/modify features | `Component` | hpa.yaml, ingress.yaml, etc. |
| **Base** | Enforce standards | `Kustomization` | Organization-wide defaults |
| **Environment Overlay** | Environment-specific | `Kustomization` | Quotas, limits, policies |
| **Region Overlay** | Region-specific | `Kustomization` | Tolerations, topology |
| **Catalog** | Developer interface | YAML data | Service metadata |

---

## 2. Archetypes - Workload Shapes

### What Are Archetypes?

**Archetypes define the fundamental structure of your workload** - the "shape" of the deployment.

Think of archetypes as **templates** that answer:
- What Kubernetes controller? (Deployment, CronJob, Job)
- Does it need a Service?
- What health checks?
- What ports?
- What security baseline?

### Why "Archetype" and not "Base"?

**Terminology**:
- **Archetype** = Workload pattern/template (api, listener, job)
- **Base** = Organization-wide foundation (cb-base)
- **Component** = Optional feature add-on
- **Overlay** = Environment/region customization

### Available Archetypes

#### Archetype: `api`

**Purpose**: HTTP/REST APIs, gRPC services

**Structure**:
```
archetype/api/
├── deployment.yaml       # Deployment with ports
├── service.yaml         # ClusterIP Service
├── rbac.yaml           # ServiceAccount + RoleBinding
├── probes.yaml         # Readiness, Liveness, Startup
└── kustomization.yaml
```

**What It Creates**:
```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: app
          ports:
            - containerPort: 8080  # ✅ Has ports
          readinessProbe: ...      # ✅ Has readiness probe
          livenessProbe: ...       # ✅ Has liveness probe

---
# Service
apiVersion: v1
kind: Service                      # ✅ Has Service
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080

---
# ServiceAccount
apiVersion: v1
kind: ServiceAccount                # ✅ Has RBAC
```

**Typical Use Cases**:
- REST APIs (account-service, user-service)
- gRPC services
- GraphQL endpoints

---

#### Archetype: `listener`

**Purpose**: Event consumers, queue processors

**Structure**:
```
archetype/listener/
├── deployment.yaml       # Deployment WITHOUT ports
├── rbac.yaml           # ServiceAccount + RoleBinding
├── probes.yaml         # Liveness only (no readiness)
└── kustomization.yaml
```

**What It Creates**:
```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: app
          # ❌ NO ports (doesn't receive HTTP traffic)
          livenessProbe: ...       # ✅ Has liveness probe
          # ❌ NO readiness probe (doesn't route traffic)

# ❌ NO Service (internal processing only)

---
# ServiceAccount
apiVersion: v1
kind: ServiceAccount                # ✅ Has RBAC
```

**Typical Use Cases**:
- Kafka consumers
- PubSub subscribers
- Queue processors
- Event handlers

---

#### Archetype: `streaming`

**Purpose**: WebSocket, long-lived connections

**Structure**:
```
archetype/streaming/
├── deployment.yaml       # Deployment with multiple ports
├── service.yaml         # Service with session affinity
├── rbac.yaml           # ServiceAccount + RoleBinding
├── probes.yaml         # Probes with longer timeouts
└── kustomization.yaml
```

**What It Creates**:
```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          ports:
            - containerPort: 8080  # HTTP
            - containerPort: 9090  # WebSocket

---
# Service with session affinity
apiVersion: v1
kind: Service
spec:
  sessionAffinity: ClientIP        # ✅ Sticky sessions
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 3600         # 1 hour
```

**Typical Use Cases**:
- WebSocket servers
- Server-Sent Events (SSE)
- gRPC streaming

---

#### Archetype: `scheduler`

**Purpose**: Periodic scheduled tasks

**Structure**:
```
archetype/scheduler/
├── cronjob.yaml         # CronJob resource
├── rbac.yaml           # ServiceAccount + RoleBinding
└── kustomization.yaml
```

**What It Creates**:
```yaml
# CronJob
apiVersion: batch/v1
kind: CronJob                      # ✅ CronJob, not Deployment
spec:
  schedule: "0 0 * * *"            # Daily
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          # ❌ NO probes (short-lived)
          # ❌ NO Service
```

**Typical Use Cases**:
- Daily cleanup jobs
- Periodic report generation
- Scheduled maintenance tasks

---

#### Archetype: `job`

**Purpose**: One-time batch processing

**Structure**:
```
archetype/job/
├── job.yaml            # Job resource
├── rbac.yaml          # ServiceAccount + RoleBinding
└── kustomization.yaml
```

**What It Creates**:
```yaml
# Job
apiVersion: batch/v1
kind: Job                          # ✅ Job, not Deployment
spec:
  backoffLimit: 3
  completions: 1
  template:
    spec:
      restartPolicy: OnFailure
      # ❌ NO probes
      # ❌ NO Service
```

**Typical Use Cases**:
- Database migrations
- Data imports/exports
- One-time setup tasks

---

### Archetype Comparison

| Aspect | api | listener | streaming | scheduler | job |
|--------|-----|----------|-----------|-----------|-----|
| **Controller** | Deployment | Deployment | Deployment | CronJob | Job |
| **Service** | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Ports** | ✅ Yes (8080) | ❌ No | ✅ Yes (multiple) | ❌ No | ❌ No |
| **Readiness Probe** | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Liveness Probe** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Session Affinity** | ❌ No | N/A | ✅ Yes | N/A | N/A |
| **Long-Running** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Typical Components** | ingress, hpa, retry | pdb, security | hpa, ingress | security | security |

---

## 3. Components - Behavior Modifiers

### What Are Components?

**Components are optional features that modify or extend archetypes.**

Think of components as **plugins** that add functionality:
- Add new resources (Ingress, HPA, PDB)
- Patch existing resources (add annotations, security)
- Enable features (Istio, network policies)

### Why Components?

**Problem**: If we put everything in archetypes, they become bloated
**Solution**: Archetypes = minimal core, Components = optional add-ons

### Component Structure

Each component is a Kustomize `Component` (not `Kustomization`):

```yaml
# kustomize/components/hpa/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component                    # ✅ Component type

resources:
  - hpa.yaml                       # Adds HPA resource
```

### Available Components

#### 1. **ingress** - External Access

**Purpose**: Expose service externally via Ingress

**Adds**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  rules:
    - host: app.company.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: app
                port:
                  number: 80
```

**Compatible with**: api, streaming

---

#### 2. **hpa** - Horizontal Pod Autoscaler

**Purpose**: Auto-scale based on CPU/memory

**Adds**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
```

**Compatible with**: api, listener, streaming

---

#### 3. **pdb** - Pod Disruption Budget

**Purpose**: Ensure minimum availability during disruptions

**Adds**:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: app
```

**Compatible with**: api, listener, streaming

---

#### 4. **retry** - HTTP Retry Policies (Istio)

**Purpose**: Automatic retry on failures

**Adds**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app
spec:
  hosts:
    - app
  http:
    - retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: 5xx,reset,connect-failure
```

**Compatible with**: api, streaming

---

#### 5. **circuit-breaker** - Circuit Breaker (Istio)

**Purpose**: Prevent cascade failures

**Adds**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: app
spec:
  host: app
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 5s
      baseEjectionTime: 30s
      maxEjectionPercent: 20
```

**Compatible with**: api, streaming

---

#### 6. **mtls** - Mutual TLS (Istio)

**Purpose**: Encrypted service-to-service communication

**Patches**:
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: app
spec:
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

**Compatible with**: api, streaming

---

#### 7. **network-policy** - Network Isolation

**Purpose**: Restrict network traffic

**Adds**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-netpol
spec:
  podSelector:
    matchLabels:
      app: app
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              env: prod
  egress:
    - to:
        - namespaceSelector: {}
```

**Compatible with**: All archetypes

---

#### 8. **security-hardening** - Enhanced Pod Security

**Purpose**: Additional security constraints

**Patches**:
```yaml
# Patches deployment with stricter security
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      securityContext:
        seccompProfile:
          type: RuntimeDefault
        runAsNonRoot: true
      containers:
        - name: app
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
```

**Compatible with**: All archetypes

---

#### 9. **topology** - Topology Spread

**Purpose**: Spread pods across zones/nodes

**Patches**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: app
```

**Compatible with**: api, listener, streaming

---

### Component Compatibility Matrix

| Component | api | listener | streaming | scheduler | job | Notes |
|-----------|-----|----------|-----------|-----------|-----|-------|
| **ingress** | ✅ | ❌ | ✅ | ❌ | ❌ | Only for externally-exposed services |
| **hpa** | ✅ | ✅ | ✅ | ❌ | ❌ | Only for long-running workloads |
| **pdb** | ✅ | ✅ | ✅ | ❌ | ❌ | Only for high-availability needs |
| **retry** | ✅ | ❌ | ✅ | ❌ | ❌ | Only for HTTP services |
| **circuit-breaker** | ✅ | ❌ | ✅ | ❌ | ❌ | Only for services with Service resource |
| **mtls** | ✅ | ❌ | ✅ | ❌ | ❌ | Only for Istio-enabled services |
| **network-policy** | ✅ | ✅ | ✅ | ✅ | ✅ | All archetypes |
| **security-hardening** | ✅ | ✅ | ✅ | ✅ | ✅ | All archetypes |
| **topology** | ✅ | ✅ | ✅ | ❌ | ❌ | Long-running only |

---

## 4. Base Configuration - Organization Standards

### What is `cb-base`?

**cb-base = Organization-wide baseline configuration**

Applied to **ALL services**, regardless of archetype or components.

### Purpose

- Enforce company-wide standards
- Ensure compliance
- Provide common defaults
- Reduce duplication

### Structure

```
cb-base/
├── labels-annotations.yaml        # Standard labels/annotations
├── base-netpol.yaml              # Default network policy
├── pdb-defaults.yaml             # PDB defaults
├── serviceaccount-defaults.yaml   # SA defaults
└── kustomization.yaml
```

### What's Inside

#### labels-annotations.yaml

```yaml
# Applied to all resources
apiVersion: v1
kind: Namespace
metadata:
  labels:
    managed-by: kustomize
    platform: kubernetes
    company: mycompany
  annotations:
    platform.kubernetes.io/managed: "true"
```

#### base-netpol.yaml

```yaml
# Default deny-all, allow DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53  # Allow DNS
```

### When to Use Base vs Component

**Use Base for**:
- ✅ Universal requirements (all services need it)
- ✅ Compliance requirements
- ✅ Security baselines
- ✅ Organizational standards

**Use Component for**:
- ✅ Optional features
- ✅ Service-specific needs
- ✅ Technology choices (Istio, Ingress)

---

## 5. Overlays - Environment & Region Customization

### What Are Overlays?

**Overlays customize configuration based on WHERE you're deploying**

Two types:
1. **Environment Overlays** (int-stable, pre-stable, prod)
2. **Region Overlays** (euw1, euw2)

### Environment Overlays

#### Structure

```
envs/
├── int-stable/
│   ├── limitrange.yaml
│   ├── resourcequota.yaml
│   ├── networkpolicy-defaults.yaml
│   ├── dns-config-patch.yaml
│   ├── certificate-issuer-key.yaml
│   ├── labels-annotations.yaml
│   ├── pdb-defaults.yaml
│   ├── policy-toggles.yaml
│   └── kustomization.yaml
├── pre-stable/
│   └── ...
└── prod/
    └── ...
```

#### What They Contain

**1. Resource Quotas**
```yaml
# envs/prod/resourcequota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: namespace-quota
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
    pods: "500"
```

**2. Limit Ranges**
```yaml
# envs/prod/limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: namespace-limits
spec:
  limits:
    - max:
        cpu: "4"
        memory: 8Gi
      min:
        cpu: "10m"
        memory: 10Mi
      type: Container
```

**3. Environment-Specific Patches**
```yaml
# envs/prod/dns-config-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      dnsConfig:
        options:
          - name: ndots
            value: "2"
```

### Region Overlays

#### Structure

```
regions/
├── euw1/
│   ├── tolerations-taints.yaml
│   ├── topology-spread-constraints.yaml
│   ├── certificate-issuer-key.yaml
│   ├── gateway-class-key.yaml
│   ├── region-labels.yaml
│   └── kustomization.yaml
└── euw2/
    └── ...
```

#### What They Contain

**1. Node Tolerations**
```yaml
# regions/euw1/tolerations-taints.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      tolerations:
        - key: region
          operator: Equal
          value: euw1
          effect: NoSchedule
```

**2. Topology Constraints**
```yaml
# regions/euw1/topology-spread-constraints.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
```

**3. Regional Configuration**
```yaml
# regions/euw1/certificate-issuer-key.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: regional-config
data:
  CERT_ISSUER: letsencrypt-euw1
  GATEWAY_CLASS: nginx-euw1
```

### Overlay Application Order

```
archetype (structure)
  ↓
components (features)
  ↓
cb-base (standards)
  ↓
environment overlay (env config)
  ↓
region overlay (region config)
  ↓
service-specific patches (final customization)
```

---

## 6. Patches & Replacements

### What Are Patches?

**Patches modify existing resources** without replacing them entirely.

### Types of Patches in Kustomize

#### 1. Strategic Merge Patches

**Used in**: Archetypes, Components, Overlays

**Example**:
```yaml
# archetype/api/probes.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          readinessProbe:    # ✅ Adds probe to existing container
            httpGet:
              path: /health/ready
              port: 8080
```

#### 2. JSON Patches (RFC 6902)

**Used in**: Precise modifications

**Example**:
```yaml
# Generated by script
patches:
  - target:
      kind: Deployment
    patch: |-
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: SERVICE_NAME
          value: account-service
```

#### 3. Replacements (Kustomize v5+)

**Used in**: Dynamic value injection

**Example**:
```yaml
# kustomization.yaml
replacements:
  - source:
      kind: ConfigMap
      name: service-config
      fieldPath: data.replicas
    targets:
      - select:
          kind: Deployment
        fieldPaths:
          - spec.replicas
```

### When to Use Each

| Type | Use Case | Example |
|------|----------|---------|
| **Strategic Merge** | Add/modify sections | Add probes, add env vars |
| **JSON Patch** | Precise changes | Add to array, replace specific value |
| **Replacements** | Dynamic values | Inject from ConfigMap |

---

## 7. Catalog - Developer Interface

### Simplified Catalog Design

**Goal**: Developers specify **5 fields**, system handles the rest.

### Structure

```
catalog/
├── services.yaml        # Service definitions (simplified)
├── profiles.yaml        # Behavior profiles (NEW)
├── sizes.yaml          # T-shirt sizing (NEW)
├── channels.yaml       # Release channels
├── env-pins.yaml       # Environment versioning
└── policies.yaml       # Validation rules
```

### Developer Experience

#### What Developer Writes

```yaml
# catalog/services.yaml
services:
  - name: account-service
    profile: public-api      # Behavior profile
    size: medium            # Resource size
    environments: [int, pre, prod]
    
    # Optional overrides
    resources:
      overrides:
        prod:
          size: large
```

**That's it! 5 lines.**

#### What System Expands To

```yaml
# Expanded by system (internal)
services:
  - name: account-service
    
    # From profile: public-api
    archetype: api
    features:
      - ingress
      - retry
      - circuit-breaker
      - mtls
      - hpa
      - pdb
      - security-hardening
      - network-policy
    
    # From size: medium
    resources:
      cpu: 250m
      memory: 512Mi
    scaling:
      min: 2
      max: 6
      cpuTarget: 75
    
    # From size: large (prod override)
    resources:
      overrides:
        prod:
          cpu: 500m
          memory: 1Gi
    
    # Defaults
    image: gcr.io/project/account-service
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1, euw2]
```

---

## 8. T-Shirt Sizing System

### What is T-Shirt Sizing?

**Pre-defined resource configurations** so developers don't need to know CPU/memory values.

### Size Definitions

#### catalog/sizes.yaml

```yaml
sizes:
  small:
    description: "Low-traffic services, dev/test"
    resources:
      cpu: 100m
      memory: 256Mi
      limits:
        cpu: 200m
        memory: 512Mi
    scaling:
      min: 1
      max: 3
      cpuTarget: 80
    typicalUse: "Dev environments, low-traffic APIs"
  
  medium:
    description: "Standard production services"
    resources:
      cpu: 250m
      memory: 512Mi
      limits:
        cpu: 500m
        memory: 1Gi
    scaling:
      min: 2
      max: 6
      cpuTarget: 75
    typicalUse: "Production APIs, standard workloads"
  
  large:
    description: "High-traffic services"
    resources:
      cpu: 500m
      memory: 1Gi
      limits:
        cpu: 1000m
        memory: 2Gi
    scaling:
      min: 3
      max: 10
      cpuTarget: 70
    typicalUse: "High-traffic APIs, critical services"
  
  xlarge:
    description: "Very high-traffic, data-intensive"
    resources:
      cpu: 1000m
      memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    scaling:
      min: 4
      max: 15
      cpuTarget: 65
    typicalUse: "Payment APIs, analytics services"
```

### How Sizing Works

#### 1. Developer Selects Size

```yaml
services:
  - name: my-service
    profile: public-api
    size: medium        # ← Developer choice
```

#### 2. System Applies Size Configuration

```yaml
# Generated in kustomization.yaml
resources:
  - ../../../../kustomize/archetype/api

patches:
  - target:
      kind: Deployment
    patch: |-
      - op: add
        path: /spec/template/spec/containers/0/resources
        value:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi

  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 2
      - op: replace
        path: /spec/maxReplicas
        value: 6
```

#### 3. Environment Overrides

```yaml
services:
  - name: payment-api
    size: medium        # Int/Pre: medium
    resources:
      overrides:
        prod:
          size: large   # Prod: large
```

### Size Selection Guide

| Size | Traffic | Complexity | CPU/Mem | Replicas | Use For |
|------|---------|------------|---------|----------|---------|
| **small** | < 10 RPS | Simple | 100m/256Mi | 1-3 | Dev, test, low-traffic |
| **medium** | 10-100 RPS | Standard | 250m/512Mi | 2-6 | Most production services |
| **large** | 100-500 RPS | Complex | 500m/1Gi | 3-10 | High-traffic APIs |
| **xlarge** | > 500 RPS | Very complex | 1000m/2Gi | 4-15 | Critical, high-volume |

---

## 9. How It All Works Together

### Complete Flow

```
┌────────────────────────────────────────────────────────┐
│ 1. Developer Defines Service in Catalog               │
│                                                        │
│    services:                                           │
│      - name: account-service                           │
│        profile: public-api                             │
│        size: medium                                    │
│        environments: [int, pre, prod]                  │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 2. Generation Script Expands Configuration             │
│                                                        │
│    • Load profile: public-api                          │
│      → archetype: api                                  │
│      → features: [ingress, retry, circuit-breaker, hpa]│
│                                                        │
│    • Load size: medium                                 │
│      → resources: 250m CPU, 512Mi RAM                  │
│      → scaling: min=2, max=6                           │
│                                                        │
│    • Resolve image tag from GAR                        │
│    • Compute namespace                                 │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 3. Generate kustomization.yaml                         │
│                                                        │
│    resources:                                          │
│      - ../../../../kustomize/cb-base                   │
│      - ../../../../kustomize/archetype/api             │
│      - ../../../../kustomize/envs/int-stable           │
│      - ../../../../kustomize/regions/euw1              │
│                                                        │
│    components:                                         │
│      - ../../../../kustomize/components/ingress        │
│      - ../../../../kustomize/components/retry          │
│      - ../../../../kustomize/components/hpa            │
│                                                        │
│    patches:                                            │
│      - Resources (from size)                           │
│      - Replicas (from size)                            │
│      - Image (from GAR)                                │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 4. Kustomize Build Process                             │
│                                                        │
│    Layer 1: cb-base                                    │
│      ✓ Standard labels/annotations                     │
│      ✓ Base network policy                             │
│      ✓ ServiceAccount defaults                         │
│                                                        │
│    Layer 2: archetype/api                              │
│      ✓ Deployment (with structure)                     │
│      ✓ Service                                         │
│      ✓ RBAC                                            │
│      ✓ Probes                                          │
│                                                        │
│    Layer 3: components                                 │
│      ✓ Ingress (from component)                        │
│      ✓ HPA (from component)                            │
│      ✓ Retry policies (from component)                 │
│                                                        │
│    Layer 4: envs/int-stable                            │
│      ✓ ResourceQuota                                   │
│      ✓ LimitRange                                      │
│      ✓ DNS config patch                                │
│                                                        │
│    Layer 5: regions/euw1                               │
│      ✓ Tolerations/taints                              │
│      ✓ Topology spread                                 │
│      ✓ Regional labels                                 │
│                                                        │
│    Layer 6: Service-specific patches                   │
│      ✓ Resource limits (from size: medium)             │
│      ✓ Replica count (from size: medium)               │
│      ✓ Image tag (from GAR)                            │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 5. Final Kubernetes Manifests                          │
│                                                        │
│    • Deployment (fully configured)                     │
│    • Service                                           │
│    • ServiceAccount + RBAC                             │
│    • Ingress                                           │
│    • HorizontalPodAutoscaler                           │
│    • PodDisruptionBudget                               │
│    • VirtualService (Istio retry)                      │
│    • DestinationRule (Istio circuit-breaker)           │
│    • NetworkPolicy                                     │
│    • ResourceQuota                                     │
│    • LimitRange                                        │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 6. Deploy to Kubernetes                                │
│    kubectl apply -f manifests.yaml                     │
└────────────────────────────────────────────────────────┘
```

### Example: Complete Service Deployment

**Input (Developer)**:
```yaml
services:
  - name: account-service
    profile: public-api
    size: medium
    environments: [int, pre, prod]
```

**Generated Structure**:
```
tmp/account-service/int-stable/euw1/
├── kustomization.yaml
│   resources:
│     - ../../../../kustomize/cb-base
│     - ../../../../kustomize/archetype/api
│     - ../../../../kustomize/envs/int-stable
│     - ../../../../kustomize/regions/euw1
│   components:
│     - ../../../../kustomize/components/ingress
│     - ../../../../kustomize/components/retry
│     - ../../../../kustomize/components/circuit-breaker
│     - ../../../../kustomize/components/mtls
│     - ../../../../kustomize/components/hpa
│     - ../../../../kustomize/components/pdb
│   patches:
│     - resources-patch.yaml (250m CPU, 512Mi RAM)
│     - replicas-patch.yaml (min=2, max=6)
│     - image-patch.yaml (gcr.io/.../account-service:v1.2.3)
└── namespace.yaml
```

**Output (Kubernetes)**:
```yaml
# 1. Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: int-stable-account-service-euw1

---
# 2. ServiceAccount (from archetype + cb-base)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: account-service-sa
  namespace: int-stable-account-service-euw1

---
# 3. RoleBinding (from archetype)
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
...

---
# 4. Deployment (from archetype + patches)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: account-service
  namespace: int-stable-account-service-euw1
spec:
  replicas: 2  # From size: medium
  template:
    spec:
      containers:
        - name: app
          image: gcr.io/project/account-service:v1.2.3
          ports:
            - containerPort: 8080  # From archetype/api
          resources:
            requests:
              cpu: 250m      # From size: medium
              memory: 512Mi  # From size: medium
          readinessProbe:    # From archetype/api
            httpGet:
              path: /health/ready
              port: 8080
          livenessProbe:     # From archetype/api
            httpGet:
              path: /health/live
              port: 8080

---
# 5. Service (from archetype/api)
apiVersion: v1
kind: Service
metadata:
  name: account-service
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080

---
# 6. Ingress (from component)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: account-service
spec:
  rules:
    - host: account.company.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: account-service
                port:
                  number: 80

---
# 7. HPA (from component + size)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: account-service-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: account-service
  minReplicas: 2   # From size: medium
  maxReplicas: 6   # From size: medium
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75  # From size: medium

---
# 8. PDB (from component)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: account-service-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: account-service

---
# 9. VirtualService (from retry component)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: account-service
spec:
  http:
    - retries:
        attempts: 3
        perTryTimeout: 2s

---
# 10. DestinationRule (from circuit-breaker + mtls components)
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: account-service
spec:
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
    outlierDetection:
      consecutiveErrors: 5
      interval: 5s

---
# 11. NetworkPolicy (from envs/int-stable)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
...

---
# 12. ResourceQuota (from envs/int-stable)
apiVersion: v1
kind: ResourceQuota
...

---
# 13. LimitRange (from envs/int-stable)
apiVersion: v1
kind: LimitRange
...
```

**Result**: 13+ Kubernetes resources generated from 5 lines of YAML!

---

## Summary

### What We Built

| Layer | Purpose | Developer Input | Result |
|-------|---------|-----------------|--------|
| **Archetype** | Workload structure | Select type (api/listener) | Deployment, Service, RBAC, Probes |
| **Components** | Optional features | Via profile | Ingress, HPA, PDB, Istio resources |
| **Sizes** | Resources + scaling | Select size (medium) | CPU, RAM, replicas configured |
| **Profiles** | Behavior bundles | Select profile (public-api) | Archetype + Components selected |
| **Overlays** | Env/Region config | Auto-applied | Quotas, policies, regional settings |
| **Catalog** | Developer interface | 5 fields | Full deployment configuration |

### Developer Experience

**Before**: 50+ lines of complex YAML
**After**: 5 lines of simple configuration

**Platform handles**:
- Archetype selection
- Component composition
- Resource sizing
- Environment customization
- Region deployment
- Security hardening
- Network policies
- RBAC
- Versioning

**Developer focuses on**:
- Service name
- Behavior profile
- Size
- Environments

---

**This is the complete platform-next design!**
