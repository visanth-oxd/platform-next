# Phase 1: Proof of Concept - One Archetype, One Service

## Executive Summary

This document defines the **minimal scope** needed to prove that the Kustomize-based config management system works end-to-end for **one archetype (`api`)** using **one service**.

**Goal**: Prove the complete flow from catalog entry → manifest generation → valid Kubernetes manifests → successful deployment.

---

## 1. Scope Definition

### **What We're Proving**
- ✅ One archetype: `api`
- ✅ One service: `test-api-service` (example name)
- ✅ One environment: `int-stable`
- ✅ One region: `euw1`
- ✅ Essential components: `ingress`, `hpa`, `pdb`
- ✅ Manifest generation works
- ✅ Generated manifests are valid
- ✅ Can deploy to a test cluster

### **What We're NOT Proving (Deferred)**
- ❌ Multiple archetypes
- ❌ Multiple services
- ❌ Multiple environments/regions
- ❌ Advanced components (retry, circuit-breaker, mtls)
- ❌ Cost and monitoring integration
- ❌ Backstage integration
- ❌ Harness deployment (can be manual for proof)

---

## 2. Complete Breakdown: What's Needed

### **Layer 1: Catalog (Service Definition)**

#### **File**: `kustomize/catalog/services.yaml`
**Purpose**: Define the test service

**Required Content**:
```yaml
services:
  - name: test-api-service
    archetype: api
    profile: public-api  # Or we can hardcode components
    size: medium
    image: gcr.io/project/test-api-service
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1]
    enabledIn: [int-stable]
    namespaceTemplate: "{env}-{service}-{region}-stable"
    
    # Components (can be from profile or direct)
    components:
      - ingress
      - hpa
      - pdb
    
    # Resource configuration
    resources:
      defaults:
        cpu: "250m"
        memory: "512Mi"
    
    # HPA configuration
    hpa:
      enabled: true
      minReplicas:
        defaults: 2
      maxReplicas:
        defaults: 6
      metrics:
        - type: Resource
          resource:
            name: cpu
            target:
              type: Utilization
              averageUtilization: 75
    
    # Ingress configuration
    domains:
      int-stable: test-api-service.int.example.com
    
    ports:
      servicePort: 80
      targetPort: 8080
```

**Acceptance Criteria**:
- [ ] Service definition exists in catalog
- [ ] All required fields present
- [ ] Valid YAML syntax
- [ ] Can be parsed by yq

---

### **Layer 2: Profiles (Optional - Can Hardcode)**

#### **File**: `kustomize/catalog/profiles.yaml`
**Purpose**: Define behavior profile (optional for Phase 1)

**Option A**: Use profiles
```yaml
profiles:
  public-api:
    archetype: api
    components:
      - ingress
      - hpa
      - pdb
```

**Option B**: Hardcode components in service definition (simpler for Phase 1)

**Decision**: For Phase 1, we can hardcode components in service definition to reduce complexity.

---

### **Layer 3: Sizes (Optional - Can Hardcode)**

#### **File**: `kustomize/catalog/sizes.yaml`
**Purpose**: Define resource sizes (optional for Phase 1)

**Option A**: Use sizes
```yaml
sizes:
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
```

**Option B**: Hardcode resources in service definition (simpler for Phase 1)

**Decision**: For Phase 1, we can hardcode resources in service definition to reduce complexity.

---

### **Layer 4: Base Configuration**

#### **File**: `kustomize/cb-base/kustomization.yaml`
**Purpose**: Organization-wide standards

**Required Content**:
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

**Required Files**:
- [ ] `kustomize/cb-base/labels-annotations.yaml` - Common labels/annotations
- [ ] `kustomize/cb-base/base-netpol.yaml` - Base network policy (can be minimal)
- [ ] `kustomize/cb-base/serviceaccount-defaults.yaml` - ServiceAccount defaults

**Acceptance Criteria**:
- [ ] Base kustomization.yaml exists
- [ ] All referenced resources exist
- [ ] Valid Kustomize structure
- [ ] Can be built with `kustomize build`

---

### **Layer 5: API Archetype**

#### **File**: `kustomize/archetype/api/kustomization.yaml`
**Purpose**: Core API service structure

**Required Content**:
```yaml
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

**Required Files**:

1. **`kustomize/archetype/api/deployment.yaml`**
   - Deployment with placeholder image
   - Container port 8080
   - Placeholder resources (replaced by patches)
   - Security context
   - Environment variables

2. **`kustomize/archetype/api/service.yaml`**
   - ClusterIP Service
   - Port 80 → 8080
   - Selector matching Deployment

3. **`kustomize/archetype/api/rbac.yaml`**
   - ServiceAccount
   - Basic Role (if needed)
   - RoleBinding

4. **`kustomize/archetype/api/probes.yaml`**
   - Readiness probe: `/health/ready`
   - Liveness probe: `/health/live`
   - Startup probe (optional)

**Acceptance Criteria**:
- [ ] All archetype files exist
- [ ] Valid Kubernetes resources
- [ ] Can be built with `kustomize build`
- [ ] Deployment has correct structure
- [ ] Service matches Deployment labels

---

### **Layer 6: Environment Overlay**

#### **File**: `kustomize/envs/int-stable/kustomization.yaml`
**Purpose**: Environment-specific configuration

**Required Content**:
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

**Required Files**:
- [ ] `kustomize/envs/int-stable/limitrange.yaml` - Container limits
- [ ] `kustomize/envs/int-stable/resourcequota.yaml` - Namespace quotas
- [ ] `kustomize/envs/int-stable/dns-config-patch.yaml` - DNS configuration
- [ ] `kustomize/envs/int-stable/certificate-issuer-patch.yaml` - Cert issuer (can be minimal)

**Acceptance Criteria**:
- [ ] Environment overlay exists
- [ ] All referenced resources exist
- [ ] Valid Kustomize structure
- [ ] Can be built with `kustomize build`

---

### **Layer 7: Region Overlay**

#### **File**: `kustomize/regions/euw1/kustomization.yaml`
**Purpose**: Region-specific configuration

**Required Content**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

patches:
  - path: region-labels-patch.yaml
  - path: gateway-class-patch.yaml
  - path: topology-spread-patch.yaml
```

**Required Files**:
- [ ] `kustomize/regions/euw1/region-labels-patch.yaml` - Region labels
- [ ] `kustomize/regions/euw1/gateway-class-patch.yaml` - Gateway class (for ingress)
- [ ] `kustomize/regions/euw1/topology-spread-patch.yaml` - Topology spread (optional)

**Acceptance Criteria**:
- [ ] Region overlay exists
- [ ] All referenced patches exist
- [ ] Valid Kustomize structure
- [ ] Can be built with `kustomize build`

---

### **Layer 8: Components**

#### **Component 1: ingress**

**File**: `kustomize/components/ingress/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - ingress.yaml
```

**File**: `kustomize/components/ingress/ingress.yaml`
- Ingress resource
- Host configuration (from service catalog)
- TLS configuration
- Path routing
- Gateway class annotation (from region)
- Cert issuer annotation (from environment)

**Acceptance Criteria**:
- [ ] Component structure exists
- [ ] Ingress resource is valid
- [ ] Placeholders can be replaced (FQDN, gateway class, cert issuer)
- [ ] Can be included in kustomization.yaml

---

#### **Component 2: hpa**

**File**: `kustomize/components/hpa/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - hpa.yaml
```

**File**: `kustomize/components/hpa/hpa.yaml`
- HorizontalPodAutoscaler resource
- Min/max replicas (from service catalog or size)
- CPU target (from service catalog)
- Selects Deployment

**Acceptance Criteria**:
- [ ] Component structure exists
- [ ] HPA resource is valid
- [ ] Min/max replicas can be patched
- [ ] Can be included in kustomization.yaml

---

#### **Component 3: pdb**

**File**: `kustomize/components/pdb/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - pdb.yaml
```

**File**: `kustomize/components/pdb/pdb.yaml`
- PodDisruptionBudget resource
- Min available pods (calculated or default)
- Selects Deployment

**Acceptance Criteria**:
- [ ] Component structure exists
- [ ] PDB resource is valid
- [ ] Min available can be calculated
- [ ] Can be included in kustomization.yaml

---

### **Layer 9: Manifest Generation Script**

#### **File**: `scripts/generate-kz.sh`
**Purpose**: Read catalog → Generate kustomization.yaml → Build manifests

**Required Functionality**:
1. Read service from catalog
2. Extract: archetype, components, size, resources, hpa config, ingress config
3. Generate namespace.yaml
4. Generate kustomization.yaml with:
   - Resources: cb-base, archetype, envs, regions
   - Components: ingress, hpa, pdb
   - Namespace
   - Common labels
   - Image configuration
   - Patches for resources, replicas, HPA
5. Run `kustomize build` to generate final manifests
6. Output to `tmp/{SERVICE}/{ENV}/{REGION}/manifests.yaml`

**Acceptance Criteria**:
- [ ] Script exists and is executable
- [ ] Can read service from catalog
- [ ] Generates valid kustomization.yaml
- [ ] Generates valid namespace.yaml
- [ ] Can build with kustomize
- [ ] Outputs valid Kubernetes manifests
- [ ] Handles errors gracefully

---

### **Layer 10: Placeholder Replacement**

**Purpose**: Replace placeholders in generated manifests

**Placeholders to Handle**:
- `<FQDN_KEY_INT>` → Actual FQDN from service catalog
- `<GATEWAY_CLASS_KEY>` → Gateway class from region overlay
- `<CERT_ISSUER_KEY>` → Certificate issuer from environment overlay
- `PLACEHOLDER_TAG` → Image tag (can be `latest` for proof)

**Implementation Options**:
1. **In generate-kz.sh**: Replace during generation
2. **Post-processing script**: Replace after kustomize build
3. **Kustomize patches**: Use patches to inject values

**Decision**: For Phase 1, use post-processing script or inline replacement in generate-kz.sh

**Acceptance Criteria**:
- [ ] All placeholders replaced with actual values
- [ ] Ingress has correct FQDN
- [ ] Ingress has correct gateway class
- [ ] Ingress has correct cert issuer
- [ ] Image tag is set (can be `latest` for proof)

---

### **Layer 11: Validation**

#### **File**: `scripts/validate-manifests.sh`
**Purpose**: Validate generated manifests

**Required Checks**:
1. Valid YAML syntax
2. Valid Kubernetes resource schemas
3. Required fields present
4. No placeholder values remaining
5. Resources reference each other correctly (Service → Deployment, HPA → Deployment)

**Tools**:
- `kubectl --dry-run=client -f manifests.yaml` (validates schemas)
- `yq` or `jq` (validates structure)
- Custom checks (no placeholders)

**Acceptance Criteria**:
- [ ] Validation script exists
- [ ] Can validate YAML syntax
- [ ] Can validate Kubernetes schemas
- [ ] Can detect placeholder values
- [ ] Provides clear error messages

---

### **Layer 12: Deployment (Manual for Proof)**

**Purpose**: Deploy to test cluster to prove it works

**Required**:
1. Test Kubernetes cluster (can be local: minikube, kind, or cloud: GKE)
2. Generated manifests from previous step
3. Manual deployment: `kubectl apply -f manifests.yaml`

**What to Verify**:
- [ ] Namespace created
- [ ] Deployment created and pods running
- [ ] Service created
- [ ] Ingress created (if ingress controller installed)
- [ ] HPA created and active
- [ ] PDB created
- [ ] All resources have correct labels
- [ ] Health probes working
- [ ] Service is accessible (via Ingress or port-forward)

**Acceptance Criteria**:
- [ ] All resources deployed successfully
- [ ] Pods are running
- [ ] Service is accessible
- [ ] HPA is active
- [ ] No errors in cluster

---

## 3. Complete File Structure for Phase 1

```
platform-next/
├── kustomize/
│   ├── catalog/
│   │   └── services.yaml                    # ✅ Test service definition
│   │
│   ├── cb-base/
│   │   ├── kustomization.yaml              # ✅ Base kustomization
│   │   ├── labels-annotations.yaml         # ✅ Common labels
│   │   ├── base-netpol.yaml                # ✅ Base network policy
│   │   └── serviceaccount-defaults.yaml    # ✅ ServiceAccount defaults
│   │
│   ├── archetype/
│   │   └── api/
│   │       ├── kustomization.yaml          # ✅ API archetype
│   │       ├── deployment.yaml            # ✅ Deployment
│   │       ├── service.yaml                # ✅ Service
│   │       ├── rbac.yaml                   # ✅ RBAC
│   │       └── probes.yaml                 # ✅ Health probes
│   │
│   ├── envs/
│   │   └── int-stable/
│   │       ├── kustomization.yaml          # ✅ Environment overlay
│   │       ├── limitrange.yaml             # ✅ Resource limits
│   │       ├── resourcequota.yaml          # ✅ Namespace quotas
│   │       ├── dns-config-patch.yaml       # ✅ DNS config
│   │       └── certificate-issuer-patch.yaml # ✅ Cert issuer
│   │
│   ├── regions/
│   │   └── euw1/
│   │       ├── kustomization.yaml          # ✅ Region overlay
│   │       ├── region-labels-patch.yaml     # ✅ Region labels
│   │       ├── gateway-class-patch.yaml    # ✅ Gateway class
│   │       └── topology-spread-patch.yaml  # ✅ Topology (optional)
│   │
│   └── components/
│       ├── ingress/
│       │   ├── kustomization.yaml          # ✅ Ingress component
│       │   └── ingress.yaml                # ✅ Ingress resource
│       ├── hpa/
│       │   ├── kustomization.yaml          # ✅ HPA component
│       │   └── hpa.yaml                    # ✅ HPA resource
│       └── pdb/
│           ├── kustomization.yaml          # ✅ PDB component
│           └── pdb.yaml                    # ✅ PDB resource
│
├── scripts/
│   ├── generate-kz.sh                      # ✅ Manifest generation
│   └── validate-manifests.sh               # ✅ Manifest validation
│
└── tmp/
    └── test-api-service/
        └── int-stable/
            └── euw1/
                ├── namespace.yaml          # ✅ Generated namespace
                ├── kustomization.yaml      # ✅ Generated kustomization
                └── manifests.yaml         # ✅ Final manifests
```

---

## 4. Success Criteria

### **Phase 1 is Complete When**:

1. ✅ **Catalog Entry**: Service defined in `services.yaml`
2. ✅ **Base Structure**: cb-base, archetype, envs, regions exist
3. ✅ **Components**: ingress, hpa, pdb components exist
4. ✅ **Manifest Generation**: Script generates valid kustomization.yaml
5. ✅ **Kustomize Build**: Can build manifests successfully
6. ✅ **Placeholder Replacement**: All placeholders replaced
7. ✅ **Validation**: Manifests pass validation
8. ✅ **Deployment**: Can deploy to test cluster
9. ✅ **Verification**: All resources created and working
10. ✅ **Documentation**: Process documented

---

## 5. Dependencies

### **External Tools Required**:
- ✅ `kubectl` - Kubernetes CLI
- ✅ `kustomize` - Kustomize CLI (or `kubectl kustomize`)
- ✅ `yq` - YAML processor
- ✅ `jq` - JSON processor (optional, for validation)

### **Kubernetes Cluster**:
- ✅ Test cluster (minikube, kind, or cloud)
- ✅ Ingress controller (if testing ingress)
- ✅ Metrics server (if testing HPA)

### **Infrastructure**:
- ✅ DNS (for FQDN, can use hosts file for proof)
- ✅ Certificate issuer (cert-manager, can be minimal for proof)
- ✅ Gateway class (can use default for proof)

---

## 6. Testing Strategy

### **Unit Tests**:
- [ ] Catalog parsing works
- [ ] Manifest generation script works
- [ ] Placeholder replacement works
- [ ] Validation script works

### **Integration Tests**:
- [ ] Kustomize build succeeds
- [ ] Generated manifests are valid YAML
- [ ] Generated manifests are valid Kubernetes resources
- [ ] No placeholders remain

### **End-to-End Tests**:
- [ ] Can deploy to test cluster
- [ ] All resources created
- [ ] Pods running
- [ ] Service accessible
- [ ] HPA active
- [ ] Ingress working (if ingress controller installed)

---

## 7. Next Steps After Phase 1

Once Phase 1 is proven:
1. Add more components (network-policy, security-hardening)
2. Add more environments (pre-stable, prod)
3. Add more regions (euw2)
4. Add profiles.yaml and sizes.yaml
5. Add CI/CD integration
6. Add cost and monitoring integration

---

## 8. Summary

**To prove one archetype (api) with one service, we need**:

1. ✅ **Catalog**: Service definition
2. ✅ **Base**: cb-base structure
3. ✅ **Archetype**: api archetype (Deployment, Service, RBAC, probes)
4. ✅ **Environment Overlay**: int-stable configuration
5. ✅ **Region Overlay**: euw1 configuration
6. ✅ **Components**: ingress, hpa, pdb
7. ✅ **Manifest Generation Script**: generate-kz.sh
8. ✅ **Placeholder Replacement**: Replace FQDN, gateway class, cert issuer
9. ✅ **Validation**: Validate generated manifests
10. ✅ **Deployment**: Deploy to test cluster and verify

**Total Files Needed**: ~25-30 files
**Estimated Effort**: 2-3 weeks for one engineer

