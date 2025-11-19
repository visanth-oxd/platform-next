# Component Definition and Classification

## Executive Summary

This document defines what a **Component** is in the Kustomize-based config management system, how it differs from an **Archetype**, and provides a complete classification of all components.

---

## 1. Core Definitions

### **Archetype** (Layer 1: Workload Shapes)

**Definition**: The fundamental structure/workload shape that defines WHAT you're deploying.

**Characteristics**:
- Uses `kind: Kustomization` (Kustomize base)
- Defines the core Kubernetes controller (Deployment, CronJob, Job, StatefulSet)
- Includes essential resources (Service, ServiceAccount, RBAC, probes)
- **Mutually exclusive**: A service can only have ONE archetype
- **Minimal**: Contains only the essential structure, no optional features

**Examples**:
- `api`: HTTP/REST services (Deployment + Service + probes)
- `listener`: Event consumers (Deployment, no Service, liveness only)
- `streaming`: WebSocket/long-lived connections (Deployment + Service + session affinity)
- `scheduler`: Periodic tasks (CronJob)
- `job`: One-time batch jobs (Job)

**What's IN an Archetype**:
- ✅ Kubernetes controller (Deployment/CronJob/Job)
- ✅ Service (if applicable)
- ✅ ServiceAccount + basic RBAC
- ✅ Health probes (readiness/liveness if applicable)
- ✅ Security context defaults
- ✅ Port definitions
- ✅ Basic resource requests/limits (placeholders)

**What's NOT in an Archetype**:
- ❌ Optional features (ingress, HPA, PDB)
- ❌ Environment-specific config
- ❌ Region-specific config
- ❌ Advanced features (circuit breakers, retries)

---

### **Component** (Layer 2: Behavior Modifiers)

**Definition**: Optional, composable features that modify or extend archetypes to define HOW the service behaves.

**Characteristics**:
- Uses `kind: Component` (Kustomize Component type)
- **Composable**: A service can have MANY components
- **Optional**: Enable/disable per service via profiles
- **Additive**: Components add resources or patch existing ones
- **Reusable**: Same component works across different archetypes

**What Components Do**:
1. **Add new Kubernetes resources** (Ingress, HPA, PDB, NetworkPolicy)
2. **Patch existing resources** (add annotations, modify security context)
3. **Enable features** (Istio VirtualService, DestinationRule)

**Component Structure**:
```
components/{component-name}/
├── kustomization.yaml    # kind: Component
├── {resource}.yaml      # New resources to add
└── patches/             # Optional patches to existing resources
    └── {patch}.yaml
```

---

## 2. Component Classification

### Category 1: Networking & Access

#### **ingress**
**Purpose**: Enable external HTTP(S) access to the service

**Adds Resources**:
- `Ingress` resource with host, path, TLS configuration

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `streaming`

**Configuration**:
- Host/FQDN (from service catalog)
- Path routing
- TLS certificate (from cert-manager)
- Gateway class (from region overlay)

**Example Use Case**: Public-facing REST API that needs external access

---

#### **network-policy**
**Purpose**: Network isolation and traffic control

**Adds Resources**:
- `NetworkPolicy` resource defining ingress/egress rules

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: All (api, listener, streaming, scheduler, job)

**Configuration**:
- Ingress rules (who can talk to this service)
- Egress rules (who this service can talk to)
- Namespace selectors
- Pod selectors

**Example Use Case**: Restrict service to only accept traffic from specific namespaces

---

#### **mtls** (Mutual TLS)
**Purpose**: Enable service mesh mTLS for secure service-to-service communication

**Adds Resources**:
- `DestinationRule` (Istio) with mTLS enabled

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `streaming` (services with Service resource)

**Configuration**:
- mTLS mode (STRICT, PERMISSIVE)
- Service mesh configuration

**Example Use Case**: Internal API that requires encrypted service-to-service communication

---

### Category 2: Scaling & Availability

#### **hpa** (Horizontal Pod Autoscaler)
**Purpose**: Automatic horizontal scaling based on metrics

**Adds Resources**:
- `HorizontalPodAutoscaler` resource

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `listener`, `streaming` (Deployment-based)

**Configuration**:
- Min replicas (from size or service catalog)
- Max replicas (from size or service catalog)
- Target CPU utilization
- Target memory utilization
- Custom metrics (optional)

**Example Use Case**: API that needs to scale up during peak traffic

---

#### **pdb** (Pod Disruption Budget)
**Purpose**: Ensure high availability during voluntary disruptions (upgrades, node drains)

**Adds Resources**:
- `PodDisruptionBudget` resource

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `listener`, `streaming` (Deployment-based)

**Configuration**:
- Min available pods (e.g., 50% or absolute number)
- Max unavailable pods

**Example Use Case**: Production API that must maintain minimum availability during upgrades

---

#### **topology**
**Purpose**: Control pod distribution across nodes/zones for high availability

**Patches**:
- Adds `topologySpreadConstraints` to Deployment spec

**Compatible Archetypes**: `api`, `listener`, `streaming` (Deployment-based)

**Configuration**:
- Zone spreading (spread across availability zones)
- Node spreading (spread across nodes)
- Max skew (how uneven distribution can be)

**Example Use Case**: Production service that must be spread across multiple zones

---

### Category 3: Resilience & Reliability

#### **retry**
**Purpose**: HTTP retry policies for failed requests

**Adds Resources**:
- `VirtualService` (Istio) with retry configuration

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `streaming` (HTTP-based services)

**Configuration**:
- Retry attempts
- Retry timeout
- Retry conditions (5xx errors, connection failures)
- Retry backoff strategy

**Example Use Case**: API that needs automatic retries for transient failures

---

#### **circuit-breaker**
**Purpose**: Prevent cascading failures by breaking circuit when service is unhealthy

**Adds Resources**:
- `DestinationRule` (Istio) with circuit breaker configuration

**Patches**:
- None (standalone resource)

**Compatible Archetypes**: `api`, `streaming` (services with Service resource)

**Configuration**:
- Connection pool limits
- Outlier detection (eject unhealthy pods)
- Circuit breaker thresholds

**Example Use Case**: API that calls downstream services and needs protection from failures

---

### Category 4: Security

#### **security-hardening**
**Purpose**: Enhanced security policies and restrictions

**Patches**:
- Security context patches (runAsNonRoot, readOnlyRootFilesystem)
- Pod security standards
- Capability drops
- SELinux/AppArmor annotations

**Compatible Archetypes**: All

**Configuration**:
- Security context overrides
- Pod security policy settings
- Capability restrictions

**Example Use Case**: Production service requiring strict security compliance

---

#### **serviceaccount-rbac**
**Purpose**: Custom ServiceAccount with RBAC permissions

**Adds Resources**:
- `ServiceAccount` (if not in archetype)
- `Role` or `ClusterRole`
- `RoleBinding` or `ClusterRoleBinding`

**Patches**:
- Updates Deployment to use custom ServiceAccount

**Compatible Archetypes**: All

**Configuration**:
- ServiceAccount name
- Role permissions (API groups, resources, verbs)
- Namespace scope (Role) vs cluster scope (ClusterRole)

**Example Use Case**: Service that needs to read ConfigMaps or create resources

---

### Category 5: Observability & Monitoring

**Note**: Monitoring components (Prometheus ServiceMonitor, Dynatrace ConfigMap) are handled separately in the monitoring profiles system and are NOT traditional Kustomize components.

---

## 3. Component vs Archetype: Decision Matrix

| Aspect | Archetype | Component |
|--------|-----------|-----------|
| **Kind** | `Kustomization` | `Component` |
| **Quantity** | ONE per service | MANY per service |
| **Purpose** | Define structure | Modify behavior |
| **Required** | ✅ Yes (must have) | ❌ No (optional) |
| **Contains** | Core resources | Optional features |
| **Examples** | api, listener, job | ingress, hpa, pdb |

---

## 4. Component Selection Logic

### How Components Are Selected

1. **Via Profile** (recommended):
   ```yaml
   profiles:
     public-api:
       components:
         - ingress
         - hpa
         - pdb
         - retry
         - circuit-breaker
         - mtls
   ```

2. **Via Service Catalog** (override):
   ```yaml
   services:
     - name: payment-processor
       components:
         - ingress
         - hpa
         # Additional components beyond profile
   ```

3. **Via Profile + Service Override**:
   ```yaml
   # Profile defines base components
   # Service can add/remove components
   ```

---

## 5. Component Dependencies

Some components have dependencies:

| Component | Depends On | Reason |
|-----------|------------|--------|
| `retry` | Service mesh (Istio) | Requires VirtualService |
| `circuit-breaker` | Service mesh (Istio) | Requires DestinationRule |
| `mtls` | Service mesh (Istio) | Requires DestinationRule |
| `ingress` | Ingress controller | Requires IngressClass |
| `hpa` | Metrics server | Requires metrics API |

---

## 6. Component Compatibility Matrix

| Component | api | listener | streaming | scheduler | job |
|-----------|-----|----------|-----------|-----------|-----|
| **ingress** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **hpa** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **pdb** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **retry** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **circuit-breaker** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **mtls** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **network-policy** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **security-hardening** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **topology** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **serviceaccount-rbac** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 7. Summary

**Components are**:
- ✅ Optional features that modify behavior
- ✅ Composable (can combine multiple)
- ✅ Reusable across archetypes
- ✅ Defined as `kind: Component`

**Components are NOT**:
- ❌ Core structure (that's archetypes)
- ❌ Required (that's archetypes)
- ❌ Environment-specific (that's overlays)
- ❌ Region-specific (that's overlays)

**Key Principle**: 
- **Archetype** = What you're deploying (the structure)
- **Component** = How it behaves (the features)
- **Overlay** = Where it runs (environment/region)

