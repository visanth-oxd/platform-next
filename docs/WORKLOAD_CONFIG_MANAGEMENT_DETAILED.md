# Workload Configuration Management: Detailed Explanation

## Executive Summary

This document provides a **comprehensive, detailed explanation** of how workload configuration is managed in the Kustomize-based system. It covers the complete flow from service definition in the catalog to final Kubernetes manifests, with detailed examples showing how each layer contributes to the final configuration.

---

## Table of Contents

1. [What is Workload Configuration Management?](#1-what-is-workload-configuration-management)
2. [The Configuration Hierarchy](#2-the-configuration-hierarchy)
3. [Detailed Configuration Flow](#3-detailed-configuration-flow)
4. [Layer-by-Layer Configuration Application](#4-layer-by-layer-configuration-application)
5. [Override Mechanisms](#5-override-mechanisms)
6. [Patch Application Process](#6-patch-application-process)
7. [Complete Example: payment-processor Service](#7-complete-example-payment-processor-service)
8. [Configuration Resolution Algorithm](#8-configuration-resolution-algorithm)
9. [How Configuration is Merged](#9-how-configuration-is-merged)
10. [Configuration Validation](#10-configuration-validation)

---

## 1. What is Workload Configuration Management?

### **Definition**

**Workload Configuration Management** is the process of:
1. **Defining** service requirements in a declarative catalog
2. **Resolving** configuration from multiple layers (base, archetype, components, overlays)
3. **Merging** configurations using Kustomize's strategic merge
4. **Patching** service-specific values (resources, replicas, labels)
5. **Generating** final Kubernetes manifests ready for deployment

### **Key Principles**

1. **Declarative**: Configuration is defined, not executed
2. **Layered**: Multiple layers contribute to final configuration
3. **Composable**: Components can be added/removed without modifying base
4. **Overrideable**: Higher layers can override lower layers
5. **Idempotent**: Same input always produces same output

---

## 2. The Configuration Hierarchy

### **Configuration Layers (Bottom to Top)**

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: Service-Specific Patches                          │ ← Highest Priority
│ (From catalog: resources, replicas, labels, image)        │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: Region Overlay (euw1, euw2)                       │
│ (Region-specific: gateway class, topology, tolerations)    │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Environment Overlay (int-stable, prod)           │
│ (Environment-specific: limits, quotas, DNS, certs)        │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Components (ingress, hpa, pdb)                     │
│ (Optional features: Ingress, HPA, PDB resources)           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Archetype (api, listener, job)                     │
│ (Workload structure: Deployment, Service, RBAC, probes)    │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Base (cb-base)                                     │ ← Lowest Priority
│ (Organization standards: labels, annotations, policies)   │
└─────────────────────────────────────────────────────────────┘
```

### **Priority Order**

**Lower layers are applied first, higher layers override lower layers.**

- **Layer 1 (Base)**: Applied first, sets foundation
- **Layer 2 (Archetype)**: Adds workload structure
- **Layer 3 (Components)**: Adds optional features
- **Layer 4 (Environment)**: Applies environment-specific config
- **Layer 5 (Region)**: Applies region-specific config
- **Layer 6 (Service Patches)**: Applies service-specific overrides

---

## 3. Detailed Configuration Flow

### **Step-by-Step Process**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Read Service from Catalog                          │
├─────────────────────────────────────────────────────────────┤
│ Input: services.yaml                                        │
│ Output: Service definition with archetype, profile, size    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Resolve Profile                                     │
├─────────────────────────────────────────────────────────────┤
│ Input: profiles.yaml                                       │
│ Output: List of components to enable                        │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Resolve Size                                        │
├─────────────────────────────────────────────────────────────┤
│ Input: sizes.yaml                                           │
│ Output: CPU, memory, min/max replicas                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Generate kustomization.yaml                        │
├─────────────────────────────────────────────────────────────┤
│ Input: All resolved values                                  │
│ Output: kustomization.yaml with resources, components,     │
│         patches, labels, images                            │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Kustomize Build                                     │
├─────────────────────────────────────────────────────────────┤
│ Input: kustomization.yaml + all referenced resources        │
│ Process: Kustomize applies layers in order, merges configs │
│ Output: Final Kubernetes manifests (YAML)                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Placeholder Replacement                             │
├─────────────────────────────────────────────────────────────┤
│ Input: Generated manifests with placeholders                │
│ Process: Replace placeholders (FQDN, gateway class, etc.)    │
│ Output: Final manifests ready for deployment               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Layer-by-Layer Configuration Application

### **Layer 1: Base (cb-base)**

**Purpose**: Organization-wide standards applied to ALL services

**What it Contains**:
```yaml
# kustomize/cb-base/kustomization.yaml
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
  platform.company.com/version: "1.0"
```

**What Gets Applied**:
- **Common Labels**: Added to ALL resources (Deployment, Service, Ingress, etc.)
- **Common Annotations**: Added to ALL resources
- **Base NetworkPolicy**: Applied to namespace
- **ServiceAccount Defaults**: Default ServiceAccount configuration

**Example Output** (after Layer 1):
```yaml
# Any resource will have these labels:
metadata:
  labels:
    platform: kubernetes
    managed-by: kustomize
    company: mycompany
  annotations:
    platform.company.com/managed: "true"
    platform.company.com/version: "1.0"
```

**Key Point**: Base sets the foundation. Everything else builds on top.

---

### **Layer 2: Archetype (api)**

**Purpose**: Define the fundamental structure of the workload

**What it Contains**:
```yaml
# kustomize/archetype/api/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - rbac.yaml

patchesStrategicMerge:
  - probes.yaml

commonLabels:
  workload.archetype: api
```

**Deployment Resource** (from archetype):
```yaml
# kustomize/archetype/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    workload.archetype: api  # From archetype commonLabels
    platform: kubernetes      # From base (merged)
    managed-by: kustomize     # From base (merged)
spec:
  replicas: 2                 # Placeholder, will be patched
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
        workload.archetype: api
        platform: kubernetes
        managed-by: kustomize
    spec:
      serviceAccountName: app-sa
      containers:
        - name: app
          image: placeholder:latest  # Will be replaced
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "250m"      # Placeholder, will be patched
              memory: "512Mi"  # Placeholder, will be patched
          # Probes will be added by probes.yaml patch
```

**Service Resource** (from archetype):
```yaml
# kustomize/archetype/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: app
  labels:
    workload.archetype: api
    platform: kubernetes
    managed-by: kustomize
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: app
```

**Probes Patch** (from archetype):
```yaml
# kustomize/archetype/api/probes.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
        - name: app
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
```

**What Gets Applied**:
- **Deployment**: Core workload structure
- **Service**: ClusterIP service for internal access
- **RBAC**: ServiceAccount, Role, RoleBinding
- **Probes**: Health check configuration
- **Labels**: `workload.archetype: api` added to all resources

**Example Output** (after Layer 2):
```yaml
# Deployment now has:
metadata:
  labels:
    workload.archetype: api      # From archetype
    platform: kubernetes          # From base
    managed-by: kustomize         # From base
spec:
  replicas: 2                     # Placeholder
  template:
    spec:
      containers:
        - name: app
          image: placeholder:latest
          resources:
            requests:
              cpu: "250m"          # Placeholder
              memory: "512Mi"      # Placeholder
          readinessProbe:          # From probes.yaml
            httpGet:
              path: /health/ready
              port: 8080
```

**Key Point**: Archetype provides the structure. It doesn't set final values (those come from size and service patches).

---

### **Layer 3: Components (ingress, hpa, pdb)**

**Purpose**: Add optional features as composable units

**Ingress Component**:
```yaml
# kustomize/components/ingress/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - ingress.yaml
```

```yaml
# kustomize/components/ingress/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  labels:
    platform: kubernetes          # From base
    managed-by: kustomize         # From base
    workload.archetype: api       # From archetype
  annotations:
    kubernetes.io/ingress.class: "<GATEWAY_CLASS_KEY>"  # Placeholder
    cert-manager.io/cluster-issuer: "<CERT_ISSUER_KEY>"  # Placeholder
spec:
  ingressClassName: "<GATEWAY_CLASS_KEY>"  # Placeholder
  rules:
    - host: "<FQDN_KEY>"  # Placeholder
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 80
```

**HPA Component**:
```yaml
# kustomize/components/hpa/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - hpa.yaml
```

```yaml
# kustomize/components/hpa/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app
  labels:
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: <MIN_REPLICAS>  # Placeholder
  maxReplicas: <MAX_REPLICAS>  # Placeholder
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: <CPU_TARGET>  # Placeholder
```

**PDB Component**:
```yaml
# kustomize/components/pdb/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - pdb.yaml
```

```yaml
# kustomize/components/pdb/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app
  labels:
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: app
```

**What Gets Applied**:
- **Ingress**: External access resource (with placeholders)
- **HPA**: Auto-scaling resource (with placeholders)
- **PDB**: High availability resource

**Example Output** (after Layer 3):
```yaml
# New resources added:
- Ingress (with placeholders for FQDN, gateway class, cert issuer)
- HorizontalPodAutoscaler (with placeholders for min/max replicas, CPU target)
- PodDisruptionBudget (complete, no placeholders)
```

**Key Point**: Components add new resources. They don't modify existing resources (that's what patches do).

---

### **Layer 4: Environment Overlay (int-stable)**

**Purpose**: Apply environment-specific configuration

**What it Contains**:
```yaml
# kustomize/envs/int-stable/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - limitrange.yaml
  - resourcequota.yaml

patches:
  - path: dns-config-patch.yaml
  - path: certificate-issuer-patch.yaml
```

**LimitRange**:
```yaml
# kustomize/envs/int-stable/limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limitrange
  namespace: <NAMESPACE>  # Will be set by kustomize
spec:
  limits:
    - default:
        cpu: "500m"
        memory: "1Gi"
      defaultRequest:
        cpu: "250m"
        memory: "512Mi"
```

**ResourceQuota**:
```yaml
# kustomize/envs/int-stable/resourcequota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: <NAMESPACE>
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

**DNS Config Patch**:
```yaml
# kustomize/envs/int-stable/dns-config-patch.yaml
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
          - name: edns0
```

**Certificate Issuer Patch**:
```yaml
# kustomize/envs/int-stable/certificate-issuer-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-staging"  # int-stable uses staging
```

**What Gets Applied**:
- **LimitRange**: Default container resource limits for namespace
- **ResourceQuota**: Total resource limits for namespace
- **DNS Config**: DNS settings for pods
- **Certificate Issuer**: Cert issuer annotation for Ingress

**Example Output** (after Layer 4):
```yaml
# Deployment now has:
spec:
  template:
    spec:
      dnsConfig:                  # From environment overlay
        options:
          - name: ndots
            value: "2"
          - name: edns0
      containers:
        - name: app
          # ... existing config ...

# Ingress now has:
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-staging"  # From environment overlay
```

**Key Point**: Environment overlay modifies existing resources (patches) and adds new resources (LimitRange, ResourceQuota).

---

### **Layer 5: Region Overlay (euw1)**

**Purpose**: Apply region-specific configuration

**What it Contains**:
```yaml
# kustomize/regions/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

patches:
  - path: region-labels-patch.yaml
  - path: gateway-class-patch.yaml
  - path: topology-spread-patch.yaml
```

**Region Labels Patch**:
```yaml
# kustomize/regions/euw1/region-labels-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels:
    region: euw1
spec:
  template:
    metadata:
      labels:
        region: euw1
```

**Gateway Class Patch**:
```yaml
# kustomize/regions/euw1/gateway-class-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    kubernetes.io/ingress.class: "nginx-euw1"  # euw1 specific
spec:
  ingressClassName: "nginx-euw1"
```

**Topology Spread Patch**:
```yaml
# kustomize/regions/euw1/topology-spread-patch.yaml
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

**What Gets Applied**:
- **Region Labels**: `region: euw1` added to all resources
- **Gateway Class**: Region-specific ingress class
- **Topology Spread**: Pod distribution across availability zones

**Example Output** (after Layer 5):
```yaml
# Deployment now has:
metadata:
  labels:
    region: euw1                 # From region overlay
spec:
  template:
    metadata:
      labels:
        region: euw1
    spec:
      topologySpreadConstraints:  # From region overlay
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: app

# Ingress now has:
metadata:
  annotations:
    kubernetes.io/ingress.class: "nginx-euw1"  # From region overlay
spec:
  ingressClassName: "nginx-euw1"
```

**Key Point**: Region overlay adds region-specific labels and configurations.

---

### **Layer 6: Service-Specific Patches**

**Purpose**: Apply service-specific values from catalog (size, resources, replicas)

**What it Contains** (from generated kustomization.yaml):
```yaml
# tmp/payment-processor/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# ... resources, components from previous layers ...

namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor         # Service-specific
  env: int-stable                 # Environment-specific
  region: euw1                   # Region-specific (already from region overlay, but explicit)

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

patches:
  # Patch 1: Deployment Resources (from size)
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "500m"  # From size: large
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "1Gi"   # From size: large
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/cpu
        value: "1000m"  # From size: large
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: "2Gi"    # From size: large
  
  # Patch 2: HPA Min/Max Replicas (from size)
  - target:
      kind: HorizontalPodAutoscaler
      name: app
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 3  # From size: large
      - op: replace
        path: /spec/maxReplicas
        value: 10  # From size: large
      - op: replace
        path: /spec/metrics/0/resource/target/averageUtilization
        value: 70  # From size: large
```

**What Gets Applied**:
- **Namespace**: Service-specific namespace name
- **Common Labels**: Service, environment, region labels
- **Image**: Service-specific image name
- **Resource Patches**: CPU/memory from size
- **HPA Patches**: Min/max replicas and CPU target from size

**Example Output** (after Layer 6):
```yaml
# Deployment now has:
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor        # From service patch
    env: int-stable               # From service patch
    region: euw1                  # From region overlay + service patch
    platform: kubernetes          # From base
    managed-by: kustomize        # From base
    workload.archetype: api       # From archetype
spec:
  template:
    spec:
      containers:
        - name: app
          image: gcr.io/project/payment-processor:PLACEHOLDER_TAG  # From service patch
          resources:
            requests:
              cpu: "500m"         # From service patch (size: large)
              memory: "1Gi"       # From service patch (size: large)
            limits:
              cpu: "1000m"        # From service patch (size: large)
              memory: "2Gi"       # From service patch (size: large)

# HPA now has:
spec:
  minReplicas: 3                 # From service patch (size: large)
  maxReplicas: 10                 # From service patch (size: large)
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # From service patch (size: large)
```

**Key Point**: Service patches apply the final, service-specific values. This is where placeholders get replaced with actual values.

---

## 5. Override Mechanisms

### **How Overrides Work**

Overrides follow a **priority hierarchy**:

```
Service Override (highest priority)
    ↓
Environment Override
    ↓
Size Default
    ↓
Profile Default
    ↓
Archetype Default (lowest priority)
```

### **Example: Resource Overrides**

**Service Definition**:
```yaml
services:
  - name: payment-processor
    size: large  # Default size
    resources:
      defaults:
        cpu: "500m"      # From size: large
        memory: "1Gi"
      overrides:
        prod:
          cpu: "1000m"   # Production override
          memory: "2Gi"
```

**Resolution Logic**:
```bash
# For int-stable environment:
CPU=$(echo "$SERVICE_DATA" | yq eval ".resources.overrides.int-stable.cpu // .resources.defaults.cpu" -)
# Result: "500m" (no override for int-stable, use default)

# For prod environment:
CPU=$(echo "$SERVICE_DATA" | yq eval ".resources.overrides.prod.cpu // .resources.defaults.cpu" -)
# Result: "1000m" (prod override exists, use it)
```

### **Example: Replica Overrides**

**Service Definition**:
```yaml
services:
  - name: payment-processor
    hpa:
      minReplicas:
        defaults: 3      # From size: large
        overrides:
          prod: 5       # Production needs more replicas
      maxReplicas:
        defaults: 10    # From size: large
        overrides:
          prod: 15
```

**Resolution Logic**:
```bash
# For int-stable:
MIN_REPLICAS=$(echo "$SERVICE_DATA" | yq eval ".hpa.minReplicas.overrides.int-stable // .hpa.minReplicas.defaults" -)
# Result: 3 (no override, use default)

# For prod:
MIN_REPLICAS=$(echo "$SERVICE_DATA" | yq eval ".hpa.minReplicas.overrides.prod // .hpa.minReplicas.defaults" -)
# Result: 5 (prod override exists, use it)
```

---

## 6. Patch Application Process

### **How Kustomize Applies Patches**

Kustomize uses **strategic merge patches** to combine configurations:

1. **Base resources** are loaded first
2. **Patches** are applied in order
3. **Higher layers** override lower layers

### **Patch Types**

#### **1. Strategic Merge Patches**

**Used for**: Merging YAML structures

**Example**:
```yaml
# Base Deployment
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: app
          image: placeholder:latest

# Patch
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "500m"

# Result (merged):
spec:
  replicas: 2  # Preserved from base
  template:
    spec:
      containers:
        - name: app
          image: placeholder:latest  # Preserved from base
          resources:                  # Added by patch
            requests:
              cpu: "500m"
```

#### **2. JSON Patch (RFC 6902)**

**Used for**: Precise field replacements

**Example**:
```yaml
patches:
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "500m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "1Gi"
```

**Result**: Exact field replacement, no merging.

#### **3. Common Labels/Annotations**

**Used for**: Adding labels/annotations to all resources

**Example**:
```yaml
commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1
```

**Result**: These labels are added to ALL resources (Deployment, Service, Ingress, HPA, PDB, etc.)

---

## 7. Complete Example: payment-processor Service

### **Input: Service Definition**

```yaml
# kustomize/catalog/services.yaml
services:
  - name: payment-processor
    archetype: api
    profile: public-api
    size: large
    regions: [euw1]
    enabledIn: [int-stable]
    image: gcr.io/project/payment-processor
    domains:
      int-stable: payment-processor.int.example.com
```

### **Step 1: Resolve Profile**

```yaml
# kustomize/catalog/profiles.yaml
profiles:
  public-api:
    archetype: api
    components:
      - ingress
      - hpa
      - pdb
```

**Result**: Components = `[ingress, hpa, pdb]`

### **Step 2: Resolve Size**

```yaml
# kustomize/catalog/sizes.yaml
sizes:
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

**Result**: 
- CPU = `500m`
- Memory = `1Gi`
- Min Replicas = `3`
- Max Replicas = `10`
- CPU Target = `70`

### **Step 3: Generate kustomization.yaml**

```yaml
# tmp/payment-processor/int-stable/euw1/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/int-stable
  - ../../../../kustomize/regions/euw1
  - ./namespace.yaml

components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa
  - ../../../../kustomize/components/pdb

namespace: int-stable-payment-processor-euw1-stable

commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1

images:
  - name: placeholder
    newName: gcr.io/project/payment-processor
    newTag: PLACEHOLDER_TAG

patches:
  - target:
      kind: Deployment
      name: app
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/cpu
        value: "500m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/requests/memory
        value: "1Gi"
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/cpu
        value: "1000m"
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: "2Gi"
  
  - target:
      kind: HorizontalPodAutoscaler
      name: app
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 3
      - op: replace
        path: /spec/maxReplicas
        value: 10
      - op: replace
        path: /spec/metrics/0/resource/target/averageUtilization
        value: 70
```

### **Step 4: Kustomize Build**

**Command**: `kustomize build tmp/payment-processor/int-stable/euw1/`

**Process**:
1. Loads `cb-base` → Applies common labels/annotations
2. Loads `archetype/api` → Adds Deployment, Service, RBAC, probes
3. Loads `envs/int-stable` → Adds LimitRange, ResourceQuota, DNS config, cert issuer
4. Loads `regions/euw1` → Adds region labels, gateway class, topology spread
5. Loads `components/ingress` → Adds Ingress resource
6. Loads `components/hpa` → Adds HPA resource
7. Loads `components/pdb` → Adds PDB resource
8. Applies `namespace` → Sets namespace for all resources
9. Applies `commonLabels` → Adds service-specific labels
10. Applies `images` → Replaces image name and tag
11. Applies `patches` → Replaces CPU/memory, min/max replicas

### **Step 5: Final Output**

**Generated manifests.yaml** (excerpt):

```yaml
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  replicas: 2  # From archetype (will be managed by HPA)
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
        app: payment-processor      # From commonLabels
        env: int-stable            # From commonLabels
        region: euw1               # From region overlay + commonLabels
        platform: kubernetes       # From base
        managed-by: kustomize      # From base
        workload.archetype: api    # From archetype
    spec:
      serviceAccountName: app-sa
      dnsConfig:                   # From environment overlay
        options:
          - name: ndots
            value: "2"
      topologySpreadConstraints:   # From region overlay
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: app
      containers:
        - name: app
          image: gcr.io/project/payment-processor:PLACEHOLDER_TAG
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "500m"          # From service patch (size: large)
              memory: "1Gi"        # From service patch (size: large)
            limits:
              cpu: "1000m"         # From service patch (size: large)
              memory: "2Gi"        # From service patch (size: large)
          readinessProbe:          # From archetype probes.yaml
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:           # From archetype probes.yaml
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: app

---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
  annotations:
    kubernetes.io/ingress.class: "nginx-euw1"  # From region overlay
    cert-manager.io/cluster-issuer: "letsencrypt-staging"  # From environment overlay
spec:
  ingressClassName: "nginx-euw1"
  rules:
    - host: "<FQDN_KEY>"  # Placeholder, will be replaced
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 80

---
# HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 3              # From service patch (size: large)
  maxReplicas: 10             # From service patch (size: large)
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # From service patch (size: large)

---
# PDB
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app
  namespace: int-stable-payment-processor-euw1-stable
  labels:
    app: payment-processor
    env: int-stable
    region: euw1
    platform: kubernetes
    managed-by: kustomize
    workload.archetype: api
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: app

---
# LimitRange
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limitrange
  namespace: int-stable-payment-processor-euw1-stable
spec:
  limits:
    - default:
        cpu: "500m"
        memory: "1Gi"
      defaultRequest:
        cpu: "250m"
        memory: "512Mi"

---
# ResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: int-stable-payment-processor-euw1-stable
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

### **Step 6: Placeholder Replacement**

**Placeholders to Replace**:
- `<FQDN_KEY>` → `payment-processor.int.example.com` (from service catalog)
- `PLACEHOLDER_TAG` → Actual image tag (from Harness or CI/CD)

**Final Ingress** (after replacement):
```yaml
spec:
  rules:
    - host: payment-processor.int.example.com  # Replaced
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 80
```

---

## 8. Configuration Resolution Algorithm

### **Algorithm Pseudocode**

```
function resolveConfiguration(service, environment, region):
    // Step 1: Load service from catalog
    serviceData = loadService(service)
    
    // Step 2: Resolve archetype
    archetype = serviceData.archetype
    
    // Step 3: Resolve profile
    profile = serviceData.profile
    profileData = loadProfile(profile)
    components = profileData.components
    
    // Step 4: Resolve size
    size = serviceData.size
    sizeData = loadSize(size)
    
    // Step 5: Resolve resources with overrides
    cpu = serviceData.resources.overrides[environment].cpu 
          ?? serviceData.resources.defaults.cpu 
          ?? sizeData.cpu
    
    memory = serviceData.resources.overrides[environment].memory 
             ?? serviceData.resources.defaults.memory 
             ?? sizeData.memory
    
    // Step 6: Resolve HPA with overrides
    minReplicas = serviceData.hpa.minReplicas.overrides[environment] 
                  ?? serviceData.hpa.minReplicas.defaults 
                  ?? sizeData.scaling.min
    
    maxReplicas = serviceData.hpa.maxReplicas.overrides[environment] 
                  ?? serviceData.hpa.maxReplicas.defaults 
                  ?? sizeData.scaling.max
    
    cpuTarget = serviceData.hpa.metrics[0].resource.target.averageUtilization 
                ?? sizeData.scaling.cpuTarget
    
    // Step 7: Resolve namespace
    namespace = resolveNamespace(service, environment, region)
    
    // Step 8: Resolve image
    image = serviceData.image
    imageTag = resolveImageTag(image, serviceData.tagStrategy)
    
    // Step 9: Resolve FQDN
    fqdn = serviceData.domains[environment]
    
    // Step 10: Resolve gateway class (from region)
    gatewayClass = loadRegionConfig(region).gatewayClass
    
    // Step 11: Resolve cert issuer (from environment)
    certIssuer = loadEnvironmentConfig(environment).certIssuer
    
    // Step 12: Generate kustomization.yaml
    kustomization = generateKustomization(
        archetype,
        components,
        environment,
        region,
        namespace,
        cpu,
        memory,
        minReplicas,
        maxReplicas,
        cpuTarget,
        image,
        imageTag,
        fqdn,
        gatewayClass,
        certIssuer
    )
    
    return kustomization
```

---

## 9. How Configuration is Merged

### **Merge Strategy**

Kustomize uses **strategic merge** for combining YAML:

1. **Labels/Annotations**: Merged (all labels from all layers combined)
2. **Resources**: Added (resources from all layers included)
3. **Patches**: Applied in order (later patches override earlier ones)
4. **Images**: Replaced (last image replacement wins)

### **Label Merging Example**

```yaml
# Base
commonLabels:
  platform: kubernetes
  managed-by: kustomize

# Archetype
commonLabels:
  workload.archetype: api

# Service
commonLabels:
  app: payment-processor
  env: int-stable
  region: euw1

# Result (merged):
metadata:
  labels:
    platform: kubernetes        # From base
    managed-by: kustomize      # From base
    workload.archetype: api    # From archetype
    app: payment-processor     # From service
    env: int-stable            # From service
    region: euw1               # From service
```

### **Resource Merging Example**

```yaml
# Base: Adds NetworkPolicy
resources:
  - base-netpol.yaml

# Archetype: Adds Deployment, Service
resources:
  - deployment.yaml
  - service.yaml

# Components: Adds Ingress, HPA, PDB
components:
  - ingress
  - hpa
  - pdb

# Result (all resources included):
# - NetworkPolicy (from base)
# - Deployment (from archetype)
# - Service (from archetype)
# - Ingress (from component)
# - HPA (from component)
# - PDB (from component)
```

### **Patch Merging Example**

```yaml
# Archetype: Sets basic resources
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"

# Service Patch: Replaces with size values
patches:
  - op: replace
    path: /spec/template/spec/containers/0/resources/requests/cpu
    value: "500m"
  - op: replace
    path: /spec/template/spec/containers/0/resources/requests/memory
    value: "1Gi"

# Result (patched):
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "500m"      # Replaced by patch
              memory: "1Gi"    # Replaced by patch
```

---

## 10. Configuration Validation

### **Validation Steps**

1. **Catalog Validation**:
   - Service exists in catalog
   - Profile exists in profiles.yaml
   - Size exists in sizes.yaml
   - Required fields present

2. **Kustomize Validation**:
   - `kustomize build` succeeds
   - All resources are valid YAML
   - All resources reference each other correctly

3. **Kubernetes Schema Validation**:
   - `kubectl --dry-run=client` succeeds
   - All resources match Kubernetes schemas
   - Required fields present

4. **Placeholder Validation**:
   - No unreplaced placeholders remain
   - FQDN is valid
   - Gateway class exists
   - Cert issuer exists

### **Validation Script Example**

```bash
#!/usr/bin/env bash
set -euo pipefail

MANIFESTS="$1"

# 1. Validate YAML syntax
yq eval-all '.' "$MANIFESTS" > /dev/null || {
    echo "Error: Invalid YAML syntax"
    exit 1
}

# 2. Validate Kubernetes schemas
kubectl --dry-run=client -f "$MANIFESTS" > /dev/null || {
    echo "Error: Invalid Kubernetes resources"
    exit 1
}

# 3. Check for placeholders
if grep -q "<FQDN_KEY>\|<GATEWAY_CLASS_KEY>\|<CERT_ISSUER_KEY>\|PLACEHOLDER_TAG" "$MANIFESTS"; then
    echo "Error: Unreplaced placeholders found"
    exit 1
fi

# 4. Validate resource references
# (Service selector matches Deployment labels, HPA targets Deployment, etc.)
# ... custom validation logic ...

echo "Validation passed"
```

---

## Summary

**Workload Configuration Management** is a **layered, declarative system** that:

1. **Defines** services in a catalog (archetype, profile, size)
2. **Resolves** configuration from multiple sources (profiles, sizes, overrides)
3. **Generates** a Kustomize workspace with all layers
4. **Builds** final Kubernetes manifests using Kustomize
5. **Replaces** placeholders with actual values
6. **Validates** the final output

**Key Benefits**:
- **DRY**: Define once, reuse many times (profiles, sizes)
- **Consistency**: All services follow same structure
- **Flexibility**: Override at service/environment level
- **Maintainability**: Change base, all services get update
- **Scalability**: Add new services by editing catalog

This system enables **declarative, GitOps-compliant** workload configuration management at scale.

