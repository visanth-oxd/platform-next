# Phase 1 JIRA Stories: One Archetype, One Service Proof of Concept

## Story Organization

Stories are organized by logical dependencies and can be worked on in parallel where possible.

---

## EPIC: Phase 1 - Kustomize Config Management Proof of Concept

**Epic Description**: Prove that the Kustomize-based config management system works end-to-end for one archetype (`api`) using one service (`test-api-service`).

**Epic Goal**: Generate valid Kubernetes manifests from a catalog entry and successfully deploy to a test cluster.

---

## Story 1: Spike - DNS, Ingress, and Certificate Issuer Investigation

**Story Type**: Spike  
**Priority**: High  
**Estimate**: 3-5 days  
**Labels**: `spike`, `infrastructure`, `ingress`

### Description
Investigate and document the approach for handling DNS, Ingress, and Certificate Issuer configuration in the Kustomize-based system. This spike will determine:
- How to configure Ingress resources with FQDNs
- How to handle DNS management (manual vs automated)
- How to configure certificate issuers (cert-manager integration)
- How to handle gateway classes per region
- Whether these should be in environment overlays, region overlays, or service catalog

### Acceptance Criteria
- [ ] Document current DNS management approach
- [ ] Document current Ingress controller setup (nginx/istio/other)
- [ ] Document current certificate issuer setup (cert-manager/other)
- [ ] Document gateway class configuration per region
- [ ] Create proof-of-concept Ingress resource with placeholder replacement
- [ ] Document recommended approach for Phase 1
- [ ] Identify any blockers or dependencies
- [ ] Create decision document with recommendations

### Deliverables
- Decision document: `docs/SPIKE_DNS_INGRESS_CERT_DECISION.md`
- Proof-of-concept Ingress resource (if feasible)
- List of dependencies/blockers

### Dependencies
- None (can start immediately)

### Notes
- This spike will inform Story 7 (Ingress Component) and Story 11 (Placeholder Replacement)
- If Ingress is too complex for Phase 1, we can defer it and prove the system without external access

---

## Story 2: Create Service Catalog Structure and Test Service Definition

**Story Type**: Story  
**Priority**: High  
**Estimate**: 2 days  
**Labels**: `catalog`, `foundation`

### Description
Create the service catalog structure and define a test service (`test-api-service`) that will be used to prove the system end-to-end.

### Acceptance Criteria
- [ ] Create `kustomize/catalog/` directory structure
- [ ] Create `kustomize/catalog/services.yaml` with proper schema
- [ ] Define test service `test-api-service` with:
  - [ ] archetype: `api`
  - [ ] size: `medium`
  - [ ] components: `ingress`, `hpa`, `pdb`
  - [ ] resources: cpu, memory
  - [ ] hpa: min/max replicas, cpu target
  - [ ] ingress: domain/FQDN
  - [ ] ports: servicePort, targetPort
  - [ ] namespaceTemplate
- [ ] Service definition is valid YAML
- [ ] Service definition can be parsed by `yq`
- [ ] Document service catalog schema

### Technical Details
**File**: `kustomize/catalog/services.yaml`

```yaml
services:
  - name: test-api-service
    archetype: api
    size: medium
    image: gcr.io/project/test-api-service
    tagStrategy: gar-latest-by-branch
    channel: stable
    regions: [euw1]
    enabledIn: [int-stable]
    namespaceTemplate: "{env}-{service}-{region}-stable"
    
    components:
      - ingress
      - hpa
      - pdb
    
    resources:
      defaults:
        cpu: "250m"
        memory: "512Mi"
    
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
    
    domains:
      int-stable: test-api-service.int.example.com
    
    ports:
      servicePort: 80
      targetPort: 8080
```

### Dependencies
- None (foundation story)

### Testing
- [ ] Validate YAML syntax
- [ ] Test parsing with `yq eval '.services[] | select(.name == "test-api-service")'`
- [ ] Verify all required fields are present

---

## Story 3: Create Base Configuration (cb-base)

**Story Type**: Story  
**Priority**: High  
**Estimate**: 3 days  
**Labels**: `base`, `foundation`

### Description
Create the organization-wide base configuration (`cb-base`) that applies to all services. This includes common labels, annotations, network policies, and ServiceAccount defaults.

### Acceptance Criteria
- [ ] Create `kustomize/cb-base/` directory
- [ ] Create `kustomize/cb-base/kustomization.yaml` with proper structure
- [ ] Create `kustomize/cb-base/labels-annotations.yaml` with:
  - [ ] Common labels (platform, managed-by, company)
  - [ ] Common annotations (platform.company.com/managed)
- [ ] Create `kustomize/cb-base/base-netpol.yaml` with:
  - [ ] Base NetworkPolicy (can be minimal/allow-all for Phase 1)
- [ ] Create `kustomize/cb-base/serviceaccount-defaults.yaml` with:
  - [ ] Default ServiceAccount configuration
- [ ] All files are valid YAML
- [ ] Can build with `kustomize build kustomize/cb-base`
- [ ] Document base configuration structure

### Technical Details
**Files to Create**:
- `kustomize/cb-base/kustomization.yaml`
- `kustomize/cb-base/labels-annotations.yaml`
- `kustomize/cb-base/base-netpol.yaml`
- `kustomize/cb-base/serviceaccount-defaults.yaml`

### Dependencies
- None (foundation story)

### Testing
- [ ] Validate YAML syntax
- [ ] Test `kustomize build kustomize/cb-base` succeeds
- [ ] Verify common labels are applied
- [ ] Verify common annotations are applied

---

## Story 4: Create API Archetype Core Structure

**Story Type**: Story  
**Priority**: High  
**Estimate**: 5 days  
**Labels**: `archetype`, `api`, `core`

### Description
Create the `api` archetype with core Kubernetes resources: Deployment, Service, RBAC (ServiceAccount, Role, RoleBinding), and health probes.

### Acceptance Criteria
- [ ] Create `kustomize/archetype/api/` directory
- [ ] Create `kustomize/archetype/api/kustomization.yaml` with proper structure
- [ ] Create `kustomize/archetype/api/deployment.yaml` with:
  - [ ] Deployment resource
  - [ ] Container with placeholder image
  - [ ] Port 8080 (http)
  - [ ] Placeholder resources (cpu, memory) - will be patched
  - [ ] Security context (runAsNonRoot, capabilities)
  - [ ] Environment variables (POD_NAME, etc.)
- [ ] Create `kustomize/archetype/api/service.yaml` with:
  - [ ] ClusterIP Service
  - [ ] Port 80 → 8080
  - [ ] Selector matching Deployment labels
- [ ] Create `kustomize/archetype/api/rbac.yaml` with:
  - [ ] ServiceAccount
  - [ ] Basic Role (if needed)
  - [ ] RoleBinding
- [ ] Create `kustomize/archetype/api/probes.yaml` with:
  - [ ] Readiness probe: HTTP GET `/health/ready`
  - [ ] Liveness probe: HTTP GET `/health/live`
  - [ ] Startup probe (optional)
- [ ] All resources are valid Kubernetes resources
- [ ] Can build with `kustomize build kustomize/archetype/api`
- [ ] Deployment and Service labels match
- [ ] ServiceAccount is referenced in Deployment
- [ ] Document archetype structure

### Technical Details
**Files to Create**:
- `kustomize/archetype/api/kustomization.yaml`
- `kustomize/archetype/api/deployment.yaml`
- `kustomize/archetype/api/service.yaml`
- `kustomize/archetype/api/rbac.yaml`
- `kustomize/archetype/api/probes.yaml`

**Key Requirements**:
- Deployment uses placeholder image: `placeholder:latest`
- Resources use placeholders that will be patched: `cpu: "250m"`, `memory: "512Mi"`
- Probes use standard paths: `/health/ready`, `/health/live`
- Security context enforces: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`

### Dependencies
- Story 3 (cb-base) - for reference, but can work in parallel

### Testing
- [ ] Validate YAML syntax
- [ ] Test `kustomize build kustomize/archetype/api` succeeds
- [ ] Validate Kubernetes schemas with `kubectl --dry-run=client`
- [ ] Verify Deployment and Service labels match
- [ ] Verify ServiceAccount is referenced correctly

---

## Story 5: Create Environment Overlay (int-stable)

**Story Type**: Story  
**Priority**: High  
**Estimate**: 3 days  
**Labels**: `overlay`, `environment`

### Description
Create the environment overlay for `int-stable` that includes environment-specific configuration: resource quotas, limit ranges, DNS configuration, and certificate issuer settings.

### Acceptance Criteria
- [ ] Create `kustomize/envs/int-stable/` directory
- [ ] Create `kustomize/envs/int-stable/kustomization.yaml` with proper structure
- [ ] Create `kustomize/envs/int-stable/limitrange.yaml` with:
  - [ ] Container resource limits (cpu, memory)
  - [ ] Default requests/limits
- [ ] Create `kustomize/envs/int-stable/resourcequota.yaml` with:
  - [ ] Namespace resource quotas (cpu, memory, pods)
- [ ] Create `kustomize/envs/int-stable/dns-config-patch.yaml` with:
  - [ ] DNS configuration patches (if needed)
- [ ] Create `kustomize/envs/int-stable/certificate-issuer-patch.yaml` with:
  - [ ] Certificate issuer annotation/configuration
  - [ ] Can use placeholder that will be replaced
- [ ] All files are valid YAML
- [ ] Can build with `kustomize build kustomize/envs/int-stable`
- [ ] Document environment overlay structure

### Technical Details
**Files to Create**:
- `kustomize/envs/int-stable/kustomization.yaml`
- `kustomize/envs/int-stable/limitrange.yaml`
- `kustomize/envs/int-stable/resourcequota.yaml`
- `kustomize/envs/int-stable/dns-config-patch.yaml`
- `kustomize/envs/int-stable/certificate-issuer-patch.yaml`

**Note**: Certificate issuer patch can use placeholder like `<CERT_ISSUER_KEY>` that will be replaced during manifest generation.

### Dependencies
- Story 1 (Spike) - for certificate issuer approach
- Can work in parallel with Story 4

### Testing
- [ ] Validate YAML syntax
- [ ] Test `kustomize build kustomize/envs/int-stable` succeeds
- [ ] Verify LimitRange and ResourceQuota are valid Kubernetes resources

---

## Story 6: Create Region Overlay (euw1)

**Story Type**: Story  
**Priority**: High  
**Estimate**: 3 days  
**Labels**: `overlay`, `region`

### Description
Create the region overlay for `euw1` that includes region-specific configuration: region labels, gateway class, and topology spread constraints.

### Acceptance Criteria
- [ ] Create `kustomize/regions/euw1/` directory
- [ ] Create `kustomize/regions/euw1/kustomization.yaml` with proper structure
- [ ] Create `kustomize/regions/euw1/region-labels-patch.yaml` with:
  - [ ] Region label: `region: euw1`
  - [ ] Additional region-specific labels
- [ ] Create `kustomize/regions/euw1/gateway-class-patch.yaml` with:
  - [ ] Gateway class annotation/configuration
  - [ ] Can use placeholder that will be replaced
- [ ] Create `kustomize/regions/euw1/topology-spread-patch.yaml` with:
  - [ ] Topology spread constraints (optional for Phase 1)
- [ ] All files are valid YAML
- [ ] Can build with `kustomize build kustomize/regions/euw1`
- [ ] Document region overlay structure

### Technical Details
**Files to Create**:
- `kustomize/regions/euw1/kustomization.yaml`
- `kustomize/regions/euw1/region-labels-patch.yaml`
- `kustomize/regions/euw1/gateway-class-patch.yaml`
- `kustomize/regions/euw1/topology-spread-patch.yaml` (optional)

**Note**: Gateway class patch can use placeholder like `<GATEWAY_CLASS_KEY>` that will be replaced during manifest generation.

### Dependencies
- Story 1 (Spike) - for gateway class approach
- Can work in parallel with Story 4 and Story 5

### Testing
- [ ] Validate YAML syntax
- [ ] Test `kustomize build kustomize/regions/euw1` succeeds
- [ ] Verify patches are valid Kustomize patches

---

## Story 7: Create Ingress Component

**Story Type**: Story  
**Priority**: Medium (depends on spike)  
**Estimate**: 3-4 days  
**Labels**: `component`, `ingress`, `networking`

### Description
Create the `ingress` component that adds an Ingress resource for external access. This component will be enabled for services that need external HTTP(S) access.

### Acceptance Criteria
- [ ] Create `kustomize/components/ingress/` directory
- [ ] Create `kustomize/components/ingress/kustomization.yaml` with `kind: Component`
- [ ] Create `kustomize/components/ingress/ingress.yaml` with:
  - [ ] Ingress resource
  - [ ] Host/FQDN configuration (from service catalog)
  - [ ] Path routing (default: `/`)
  - [ ] TLS configuration
  - [ ] Gateway class annotation (from region)
  - [ ] Certificate issuer annotation (from environment)
- [ ] Component uses placeholders for:
  - [ ] FQDN (from service catalog: `domains.int-stable`)
  - [ ] Gateway class (from region overlay)
  - [ ] Certificate issuer (from environment overlay)
- [ ] Component can be included in kustomization.yaml
- [ ] Can build with `kustomize build` when component is included
- [ ] Document ingress component structure

### Technical Details
**Files to Create**:
- `kustomize/components/ingress/kustomization.yaml`
- `kustomize/components/ingress/ingress.yaml`

**Placeholders to Use**:
- `<FQDN_KEY_INT>` → Replaced with actual FQDN from service catalog
- `<GATEWAY_CLASS_KEY>` → Replaced with gateway class from region
- `<CERT_ISSUER_KEY>` → Replaced with cert issuer from environment

### Dependencies
- Story 1 (Spike) - **BLOCKER** - Need to understand DNS/Ingress/Cert approach
- Story 2 (Catalog) - Need service definition
- Story 5 (Environment Overlay) - For cert issuer
- Story 6 (Region Overlay) - For gateway class

### Testing
- [ ] Validate YAML syntax
- [ ] Test component can be included in kustomization.yaml
- [ ] Test `kustomize build` succeeds with ingress component
- [ ] Verify Ingress resource is valid Kubernetes resource
- [ ] Verify placeholders are present (will be replaced later)

### Notes
- If spike determines Ingress is too complex, this story can be deferred
- System can still be proven without external access (using port-forward)

---

## Story 8: Create HPA Component

**Story Type**: Story  
**Priority**: High  
**Estimate**: 3 days  
**Labels**: `component`, `hpa`, `scaling`

### Description
Create the `hpa` component that adds a HorizontalPodAutoscaler resource for automatic scaling based on CPU/memory metrics.

### Acceptance Criteria
- [ ] Create `kustomize/components/hpa/` directory
- [ ] Create `kustomize/components/hpa/kustomization.yaml` with `kind: Component`
- [ ] Create `kustomize/components/hpa/hpa.yaml` with:
  - [ ] HorizontalPodAutoscaler resource
  - [ ] Min replicas (from service catalog or size)
  - [ ] Max replicas (from service catalog or size)
  - [ ] CPU target (from service catalog)
  - [ ] Selects Deployment by labels
- [ ] Component can be included in kustomization.yaml
- [ ] Can build with `kustomize build` when component is included
- [ ] HPA can be patched with min/max replicas during manifest generation
- [ ] Document HPA component structure

### Technical Details
**Files to Create**:
- `kustomize/components/hpa/kustomization.yaml`
- `kustomize/components/hpa/hpa.yaml`

**Configuration**:
- Min replicas: From service catalog `hpa.minReplicas.defaults` (e.g., 2)
- Max replicas: From service catalog `hpa.maxReplicas.defaults` (e.g., 6)
- CPU target: From service catalog `hpa.metrics[0].resource.target.averageUtilization` (e.g., 75)

**Note**: Min/max replicas can be patched during manifest generation based on service catalog values.

### Dependencies
- Story 2 (Catalog) - Need service definition with HPA config
- Story 4 (Archetype) - HPA selects Deployment

### Testing
- [ ] Validate YAML syntax
- [ ] Test component can be included in kustomization.yaml
- [ ] Test `kustomize build` succeeds with HPA component
- [ ] Verify HPA resource is valid Kubernetes resource
- [ ] Verify HPA selector matches Deployment labels
- [ ] Test patching min/max replicas works

---

## Story 9: Create PDB Component

**Story Type**: Story  
**Priority**: High  
**Estimate**: 2 days  
**Labels**: `component`, `pdb`, `availability`

### Description
Create the `pdb` component that adds a PodDisruptionBudget resource to ensure high availability during voluntary disruptions.

### Acceptance Criteria
- [ ] Create `kustomize/components/pdb/` directory
- [ ] Create `kustomize/components/pdb/kustomization.yaml` with `kind: Component`
- [ ] Create `kustomize/components/pdb/pdb.yaml` with:
  - [ ] PodDisruptionBudget resource
  - [ ] Min available pods (calculated or default: 50% or 1, whichever is higher)
  - [ ] Selects Deployment by labels
- [ ] Component can be included in kustomization.yaml
- [ ] Can build with `kustomize build` when component is included
- [ ] PDB min available can be calculated based on min replicas
- [ ] Document PDB component structure

### Technical Details
**Files to Create**:
- `kustomize/components/pdb/kustomization.yaml`
- `kustomize/components/pdb/pdb.yaml`

**Configuration**:
- Min available: Calculated as `max(1, minReplicas * 0.5)` or can use fixed value like `minAvailable: 1`

### Dependencies
- Story 2 (Catalog) - Need service definition
- Story 4 (Archetype) - PDB selects Deployment

### Testing
- [ ] Validate YAML syntax
- [ ] Test component can be included in kustomization.yaml
- [ ] Test `kustomize build` succeeds with PDB component
- [ ] Verify PDB resource is valid Kubernetes resource
- [ ] Verify PDB selector matches Deployment labels
- [ ] Test min available calculation

---

## Story 10: Create Manifest Generation Script

**Story Type**: Story  
**Priority**: High  
**Estimate**: 5 days  
**Labels**: `script`, `automation`, `core`

### Description
Create the manifest generation script (`generate-kz.sh`) that reads the service catalog and generates a complete `kustomization.yaml` file, then builds the final Kubernetes manifests.

### Acceptance Criteria
- [ ] Create `scripts/generate-kz.sh` script
- [ ] Script accepts parameters: `<SERVICE> <ENV> <REGION>`
- [ ] Script reads service from `kustomize/catalog/services.yaml`
- [ ] Script extracts:
  - [ ] Archetype
  - [ ] Components list
  - [ ] Resources (cpu, memory)
  - [ ] HPA configuration (min/max replicas, cpu target)
  - [ ] Ingress configuration (FQDN)
  - [ ] Ports (servicePort, targetPort)
  - [ ] Namespace template
- [ ] Script generates `namespace.yaml` with:
  - [ ] Namespace name (from template: `{env}-{service}-{region}-stable`)
  - [ ] Labels (app, env, region)
- [ ] Script generates `kustomization.yaml` with:
  - [ ] Resources: cb-base, archetype, envs, regions
  - [ ] Components: from service catalog
  - [ ] Namespace
  - [ ] Common labels (app, env, region)
  - [ ] Image configuration (placeholder image)
  - [ ] Patches for:
    - [ ] Deployment resources (cpu, memory)
    - [ ] HPA min/max replicas
    - [ ] HPA cpu target
- [ ] Script runs `kustomize build` to generate final manifests
- [ ] Script outputs to `tmp/{SERVICE}/{ENV}/{REGION}/manifests.yaml`
- [ ] Script handles errors gracefully
- [ ] Script validates service exists in catalog
- [ ] Document script usage and parameters

### Technical Details
**File**: `scripts/generate-kz.sh`

**Script Flow**:
1. Parse command-line arguments
2. Load service from catalog using `yq`
3. Extract all configuration values
4. Generate namespace.yaml
5. Generate kustomization.yaml
6. Run `kustomize build`
7. Output manifests.yaml

**Dependencies**:
- `yq` - YAML processor
- `kustomize` - Kustomize CLI

### Dependencies
- Story 2 (Catalog) - Need service definition
- Story 3 (Base) - Need cb-base
- Story 4 (Archetype) - Need api archetype
- Story 5 (Environment Overlay) - Need int-stable overlay
- Story 6 (Region Overlay) - Need euw1 overlay
- Story 7 (Ingress Component) - If including ingress
- Story 8 (HPA Component) - If including hpa
- Story 9 (PDB Component) - If including pdb

### Testing
- [ ] Script runs without errors
- [ ] Script validates service exists
- [ ] Generated namespace.yaml is valid
- [ ] Generated kustomization.yaml is valid
- [ ] Kustomize build succeeds
- [ ] Output manifests.yaml is valid YAML
- [ ] Output manifests.yaml contains expected resources
- [ ] Test with missing service (error handling)
- [ ] Test with invalid parameters (error handling)

---

## Story 11: Implement Placeholder Replacement

**Story Type**: Story  
**Priority**: Medium  
**Estimate**: 3 days  
**Labels**: `script`, `placeholder`, `replacement`

### Description
Implement placeholder replacement logic to replace placeholders in generated manifests with actual values from service catalog, environment overlays, and region overlays.

### Acceptance Criteria
- [ ] Create placeholder replacement logic (can be in generate-kz.sh or separate script)
- [ ] Replace `<FQDN_KEY_INT>` with actual FQDN from service catalog
- [ ] Replace `<GATEWAY_CLASS_KEY>` with gateway class from region overlay
- [ ] Replace `<CERT_ISSUER_KEY>` with cert issuer from environment overlay
- [ ] Replace `PLACEHOLDER_TAG` with image tag (can be `latest` for Phase 1)
- [ ] Replacement happens after kustomize build
- [ ] All placeholders are replaced (no placeholders remain in final manifests)
- [ ] Replacement is idempotent (can run multiple times)
- [ ] Document placeholder replacement approach

### Technical Details
**Placeholders to Replace**:
- `<FQDN_KEY_INT>` → From `services[].domains.int-stable`
- `<GATEWAY_CLASS_KEY>` → From region overlay (e.g., `nginx-euw1`)
- `<CERT_ISSUER_KEY>` → From environment overlay (e.g., `letsencrypt-int`)
- `PLACEHOLDER_TAG` → Image tag (can be `latest` for Phase 1)

**Implementation Options**:
1. Inline replacement in `generate-kz.sh` after kustomize build
2. Separate script `scripts/replace-placeholders.sh`
3. Use `sed` or `yq` for replacement

### Dependencies
- Story 1 (Spike) - Need to understand what values to use
- Story 10 (Manifest Generation) - Need generated manifests
- Story 7 (Ingress Component) - If replacing ingress placeholders

### Testing
- [ ] All placeholders are replaced
- [ ] No placeholders remain in final manifests
- [ ] Replacement values are correct
- [ ] Replacement is idempotent
- [ ] Test with missing values (error handling)

---

## Story 12: Create Manifest Validation Script

**Story Type**: Story  
**Priority**: High  
**Estimate**: 3 days  
**Labels**: `script`, `validation`, `quality`

### Description
Create a validation script that validates generated manifests for correctness: YAML syntax, Kubernetes schema validation, and placeholder detection.

### Acceptance Criteria
- [ ] Create `scripts/validate-manifests.sh` script
- [ ] Script accepts manifest file path as parameter
- [ ] Script validates YAML syntax
- [ ] Script validates Kubernetes resource schemas using `kubectl --dry-run=client`
- [ ] Script detects remaining placeholder values
- [ ] Script validates resource references:
  - [ ] Service selector matches Deployment labels
  - [ ] HPA selects Deployment
  - [ ] PDB selects Deployment
- [ ] Script provides clear error messages
- [ ] Script exits with non-zero code on validation failure
- [ ] Document validation checks

### Technical Details
**File**: `scripts/validate-manifests.sh`

**Validation Checks**:
1. YAML syntax (using `yq` or `yamllint`)
2. Kubernetes schemas (`kubectl --dry-run=client -f manifests.yaml`)
3. Placeholder detection (grep for `<PLACEHOLDER>` patterns)
4. Resource references (using `yq` to check selectors)

### Dependencies
- Story 10 (Manifest Generation) - Need generated manifests to validate
- Story 11 (Placeholder Replacement) - Need to validate no placeholders remain

### Testing
- [ ] Script validates valid manifests successfully
- [ ] Script detects YAML syntax errors
- [ ] Script detects Kubernetes schema errors
- [ ] Script detects placeholder values
- [ ] Script detects incorrect resource references
- [ ] Script provides clear error messages
- [ ] Test with invalid manifests (error handling)

---

## Story 13: End-to-End Testing and Deployment Verification

**Story Type**: Story  
**Priority**: High  
**Estimate**: 5 days  
**Labels**: `testing`, `e2e`, `deployment`, `verification`

### Description
Perform end-to-end testing by deploying the generated manifests to a test Kubernetes cluster and verifying all resources are created and working correctly.

### Acceptance Criteria
- [ ] Set up test Kubernetes cluster (minikube, kind, or cloud)
- [ ] Install required infrastructure:
  - [ ] Ingress controller (if testing ingress)
  - [ ] Metrics server (for HPA)
- [ ] Deploy generated manifests using `kubectl apply -f manifests.yaml`
- [ ] Verify all resources are created:
  - [ ] Namespace exists
  - [ ] Deployment created and pods running
  - [ ] Service created
  - [ ] Ingress created (if ingress component included)
  - [ ] HPA created and active
  - [ ] PDB created
- [ ] Verify resource labels are correct
- [ ] Verify health probes are working (pods are ready)
- [ ] Verify service is accessible:
  - [ ] Via Ingress (if ingress controller installed)
  - [ ] Via port-forward (if no ingress)
- [ ] Verify HPA is active and can scale
- [ ] Document deployment process
- [ ] Document any issues or blockers

### Technical Details
**Test Cluster Setup**:
- Local: minikube or kind
- Cloud: GKE test cluster
- Required: Ingress controller, Metrics server

**Verification Steps**:
1. Apply manifests
2. Check namespace: `kubectl get namespace`
3. Check deployment: `kubectl get deployment -n <namespace>`
4. Check pods: `kubectl get pods -n <namespace>`
5. Check service: `kubectl get service -n <namespace>`
6. Check ingress: `kubectl get ingress -n <namespace>`
7. Check HPA: `kubectl get hpa -n <namespace>`
8. Check PDB: `kubectl get pdb -n <namespace>`
9. Verify labels: `kubectl get all -n <namespace> --show-labels`
10. Test service access

### Dependencies
- All previous stories (complete system needed)
- Test Kubernetes cluster
- Infrastructure (ingress controller, metrics server)

### Testing
- [ ] All resources deploy successfully
- [ ] Pods are running and ready
- [ ] Service is accessible
- [ ] HPA is active
- [ ] No errors in cluster
- [ ] All labels are correct

---

## Story Dependencies Summary

```
Story 1 (Spike) ──┐
                  │
Story 2 (Catalog) │
                  │
Story 3 (Base)    │
                  │
Story 4 (Archetype) ──┐
                     │
Story 5 (Env Overlay) ──┐
                       │
Story 6 (Region Overlay) ──┐
                          │
Story 7 (Ingress) ────────┼──┐
                          │  │
Story 8 (HPA) ───────────┼──┼──┐
                          │  │  │
Story 9 (PDB) ────────────┼──┼──┼──┐
                          │  │  │  │
Story 10 (Manifest Gen) ──┘  │  │  │
                              │  │  │
Story 11 (Placeholder) ───────┘  │  │
                                  │  │
Story 12 (Validation) ───────────┘  │
                                    │
Story 13 (E2E Testing) ─────────────┘
```

---

## Story Estimates Summary

| Story | Title | Estimate | Priority |
|-------|-------|----------|----------|
| 1 | Spike - DNS/Ingress/Cert Investigation | 3-5 days | High |
| 2 | Service Catalog Structure | 2 days | High |
| 3 | Base Configuration (cb-base) | 3 days | High |
| 4 | API Archetype Core | 5 days | High |
| 5 | Environment Overlay (int-stable) | 3 days | High |
| 6 | Region Overlay (euw1) | 3 days | High |
| 7 | Ingress Component | 3-4 days | Medium |
| 8 | HPA Component | 3 days | High |
| 9 | PDB Component | 2 days | High |
| 10 | Manifest Generation Script | 5 days | High |
| 11 | Placeholder Replacement | 3 days | Medium |
| 12 | Manifest Validation Script | 3 days | High |
| 13 | End-to-End Testing | 5 days | High |

**Total Estimate**: 42-45 days (8-9 weeks for one engineer, or 4-5 weeks with 2 engineers in parallel)

---

## Parallel Work Opportunities

**Can work in parallel**:
- Stories 2, 3, 4, 5, 6 (foundation stories)
- Stories 7, 8, 9 (components)
- Story 10 can start once Stories 2-9 are done
- Story 11 can start once Story 10 is done
- Story 12 can start once Story 10 is done
- Story 13 needs all previous stories

**Critical Path**:
1. Story 1 (Spike) - Should start first
2. Stories 2-9 (Foundation) - Can work in parallel
3. Story 10 (Manifest Generation) - Needs 2-9
4. Stories 11-12 (Placeholder & Validation) - Can work in parallel after 10
5. Story 13 (E2E Testing) - Needs all

