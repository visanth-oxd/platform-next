# API Archetype: Complete Component Breakdown

## Executive Summary

This document breaks down the `api` archetype to identify:
1. What's **IN** the archetype (core structure)
2. What **components** are typically used with it
3. What's needed for **Phase 1** implementation

---

## 1. API Archetype Core (What's IN the Archetype)

### Resources Included

#### **1. Deployment**
- Kubernetes Deployment controller
- Container image (placeholder, replaced by Harness)
- Port definitions (8080 for HTTP)
- Basic resource requests/limits (placeholders, replaced by size)
- Security context (runAsNonRoot, capabilities)
- Environment variables (POD_NAME, etc.)

#### **2. Service**
- ClusterIP Service
- Port mapping (80 → 8080)
- Selector matching Deployment labels

#### **3. ServiceAccount**
- Basic ServiceAccount
- Minimal permissions (if any)

#### **4. RBAC** (Role/RoleBinding)
- Basic Role (if needed)
- RoleBinding to ServiceAccount

#### **5. Health Probes**
- Readiness probe (HTTP GET /health/ready)
- Liveness probe (HTTP GET /health/live)
- Startup probe (optional, for slow-starting apps)

#### **6. Security Context**
- Pod-level security context
- Container-level security context
- Default security policies

---

## 2. Components Typically Used with API Archetype

### Essential Components (Most Common)

#### **1. ingress** ⭐ **HIGH PRIORITY**
**Why**: Most APIs need external access
- Adds Ingress resource
- Configures host/FQDN
- Sets up TLS certificates
- Routes external traffic to Service

**Phase 1**: ✅ **YES** - Essential for API services

---

#### **2. hpa** ⭐ **HIGH PRIORITY**
**Why**: APIs need to scale based on load
- Adds HorizontalPodAutoscaler
- Configures min/max replicas (from size)
- Sets CPU/memory targets
- Enables auto-scaling

**Phase 1**: ✅ **YES** - Essential for production APIs

---

#### **3. pdb** ⭐ **HIGH PRIORITY**
**Why**: Production APIs need high availability
- Adds PodDisruptionBudget
- Ensures minimum pods during upgrades
- Prevents cascading failures

**Phase 1**: ✅ **YES** - Essential for production

---

### Important Components (Common)

#### **4. network-policy** ⭐ **MEDIUM PRIORITY**
**Why**: Network isolation and security
- Adds NetworkPolicy
- Controls ingress/egress traffic
- Enforces namespace isolation

**Phase 1**: ⚠️ **MAYBE** - Depends on security requirements

---

#### **5. security-hardening** ⭐ **MEDIUM PRIORITY**
**Why**: Enhanced security for production
- Patches security context
- Adds security annotations
- Enforces pod security standards

**Phase 1**: ⚠️ **MAYBE** - Can start with basic security in archetype

---

### Advanced Components (Optional)

#### **6. retry** ⚠️ **LOW PRIORITY (Phase 1)**
**Why**: HTTP retry policies
- Adds Istio VirtualService
- Configures retry logic
- **Dependency**: Requires service mesh (Istio)

**Phase 1**: ❌ **NO** - Requires service mesh setup

---

#### **7. circuit-breaker** ⚠️ **LOW PRIORITY (Phase 1)**
**Why**: Resilience patterns
- Adds Istio DestinationRule
- Configures circuit breaker
- **Dependency**: Requires service mesh (Istio)

**Phase 1**: ❌ **NO** - Requires service mesh setup

---

#### **8. mtls** ⚠️ **LOW PRIORITY (Phase 1)**
**Why**: Service-to-service encryption
- Adds Istio DestinationRule
- Enables mTLS
- **Dependency**: Requires service mesh (Istio)

**Phase 1**: ❌ **NO** - Requires service mesh setup

---

#### **9. topology** ⚠️ **LOW PRIORITY (Phase 1)**
**Why**: Pod distribution across zones
- Patches Deployment with topologySpreadConstraints
- Spreads pods across availability zones

**Phase 1**: ❌ **NO** - Can add later, not critical for MVP

---

#### **10. serviceaccount-rbac** ⚠️ **LOW PRIORITY (Phase 1)**
**Why**: Custom RBAC permissions
- Adds custom ServiceAccount
- Adds Role/ClusterRole
- Adds RoleBinding

**Phase 1**: ❌ **NO** - Basic RBAC in archetype is sufficient

---

## 3. Phase 1 Component Recommendation

### **Minimum Viable Components for API Archetype**

For Phase 1, focus on the **essential components** that enable basic API functionality:

#### **✅ MUST HAVE (Phase 1)**

1. **ingress**
   - External access to API
   - TLS termination
   - Host/FQDN routing

2. **hpa**
   - Auto-scaling capability
   - Resource-based scaling
   - Min/max replica management

3. **pdb**
   - High availability
   - Pod disruption protection
   - Upgrade safety

#### **⚠️ NICE TO HAVE (Phase 1, if time permits)**

4. **network-policy**
   - Network isolation
   - Security hardening
   - Traffic control

5. **security-hardening**
   - Enhanced security
   - Compliance requirements
   - Pod security standards

#### **❌ DEFER TO LATER PHASES**

6. **retry** - Requires service mesh
7. **circuit-breaker** - Requires service mesh
8. **mtls** - Requires service mesh
9. **topology** - Advanced feature
10. **serviceaccount-rbac** - Advanced RBAC

---

## 4. Component Dependencies for Phase 1

### **ingress Component Dependencies**
- ✅ Ingress controller (nginx/istio) - Must be installed in cluster
- ✅ cert-manager - For TLS certificates
- ✅ Gateway class configuration - From region overlay
- ✅ Certificate issuer - From environment overlay

### **hpa Component Dependencies**
- ✅ Metrics Server - Must be installed in cluster
- ✅ Kubernetes metrics API - Built-in
- ✅ Resource metrics (CPU/memory) - From metrics server

### **pdb Component Dependencies**
- ✅ No external dependencies
- ✅ Built-in Kubernetes feature

---

## 5. Component Configuration Requirements

### **ingress Component**
**Configuration Needed**:
- Host/FQDN (from service catalog: `domains.int-stable`, `domains.prod`)
- Path routing (default: `/`)
- TLS enabled/disabled
- Gateway class (from region: `euw1`, `euw2`)
- Certificate issuer (from environment: `int-stable`, `prod`)

**Placeholders to Replace**:
- `<FQDN_KEY_INT>` → Actual FQDN for int-stable
- `<FQDN_KEY_PROD>` → Actual FQDN for prod
- `<GATEWAY_CLASS_KEY>` → Gateway class from region
- `<CERT_ISSUER_KEY>` → Certificate issuer from environment

---

### **hpa Component**
**Configuration Needed**:
- Min replicas (from size: `sizes.yaml`)
- Max replicas (from size: `sizes.yaml`)
- Target CPU utilization (from size: default 70%)
- Target memory utilization (optional)

**Size Mapping**:
```yaml
sizes:
  small:
    scaling: { min: 1, max: 3 }
  medium:
    scaling: { min: 2, max: 6 }
  large:
    scaling: { min: 3, max: 10 }
```

---

### **pdb Component**
**Configuration Needed**:
- Min available pods (percentage or absolute)
- Can be environment-specific (stricter in prod)

**Default Configuration**:
- Min available: 50% (or 1 pod, whichever is higher)
- Can override per environment

---

## 6. Component Implementation Checklist

### **ingress Component**
- [ ] Create `components/ingress/kustomization.yaml` (kind: Component)
- [ ] Create `components/ingress/ingress.yaml` with Ingress resource
- [ ] Add placeholder replacement logic for FQDN
- [ ] Add placeholder replacement logic for gateway class
- [ ] Add placeholder replacement logic for cert issuer
- [ ] Test with different environments (int-stable, prod)
- [ ] Test with different regions (euw1, euw2)

### **hpa Component**
- [ ] Create `components/hpa/kustomization.yaml` (kind: Component)
- [ ] Create `components/hpa/hpa.yaml` with HPA resource
- [ ] Add logic to read min/max replicas from size
- [ ] Add logic to read CPU target from size
- [ ] Add patches to inject values into HPA
- [ ] Test with different sizes (small, medium, large)

### **pdb Component**
- [ ] Create `components/pdb/kustomization.yaml` (kind: Component)
- [ ] Create `components/pdb/pdb.yaml` with PDB resource
- [ ] Add logic to calculate min available based on replicas
- [ ] Add environment-specific overrides (stricter in prod)
- [ ] Test with different replica counts

---

## 7. Summary: Phase 1 API Archetype Components

### **Core (In Archetype)**
- ✅ Deployment
- ✅ Service
- ✅ ServiceAccount
- ✅ RBAC
- ✅ Health Probes
- ✅ Security Context

### **Components (Phase 1)**
- ✅ **ingress** - External access
- ✅ **hpa** - Auto-scaling
- ✅ **pdb** - High availability
- ⚠️ **network-policy** - Network isolation (if time permits)
- ⚠️ **security-hardening** - Enhanced security (if time permits)

### **Components (Deferred)**
- ❌ retry (requires service mesh)
- ❌ circuit-breaker (requires service mesh)
- ❌ mtls (requires service mesh)
- ❌ topology (advanced feature)
- ❌ serviceaccount-rbac (advanced RBAC)

---

## 8. Next Steps

1. **Review this breakdown** - Confirm component priorities
2. **Identify dependencies** - Ensure cluster has required infrastructure
3. **Create JIRA stories** - Break down into implementable tasks
4. **Start with archetype** - Implement `api` archetype core first
5. **Add components incrementally** - Start with ingress, then hpa, then pdb

