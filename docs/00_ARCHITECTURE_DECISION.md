# Architecture Decision Record

## Status

**ACCEPTED** - 2025-11-09

---

## Context & Problem

We need a Kubernetes configuration management platform that:
- Supports 100+ microservices across multiple teams
- Deploys to multiple environments (int-stable, pre-stable, prod)
- Deploys to multiple regions (euw1, euw2) in different networks
- Provides self-service for developers
- Maintains GitOps compliance
- Enforces enterprise-grade approvals
- Scales without bottlenecks

**Current Pain Points**:
- Manual service onboarding (takes days)
- Scattered configuration (inconsistent)
- Deployment bottlenecks (single pipeline)
- No self-service (platform team overloaded)
- Merge conflicts (everyone editing same files)

---

## Decision

We will implement a **three-component architecture**:

### Component 1: Backstage (Developer Portal)
**Purpose**: Service onboarding and catalog interface
**Why**: Reuse existing tool, no custom UI development

### Component 2: Platform-Next Repo (Config Management)
**Purpose**: Kustomize-based K8s configuration
**Why**: GitOps-compliant, declarative, composable

### Component 3: Harness (CD Orchestration)
**Purpose**: Deployment pipelines and controls
**Why**: Enterprise features, already deployed, multi-cluster support

---

## Detailed Rationale

### Why Backstage?

**Problem**: Need self-service UI for developers

**Alternatives**:
- Build custom UI (6-8 weeks dev, ongoing maintenance)
- Use CLI only (poor developer experience)
- Manual onboarding (doesn't scale)

**Decision**: Use Backstage

**Rationale**:
1. ✅ Already deployed in organization
2. ✅ Software Templates = declarative forms (no coding)
3. ✅ Service Catalog = built-in discovery
4. ✅ Rich plugins (K8s, Harness, GitHub, PagerDuty)
5. ✅ Industry standard (Spotify, Netflix, etc.)
6. ✅ Saves 6-8 weeks of development
7. ✅ Extensible (can add custom plugins)

**Trade-offs Accepted**:
- Dependency on Backstage platform
- Need to maintain templates (YAML)
- Requires Backstage knowledge

**Verdict**: Benefits far outweigh costs

---

### Why Kustomize?

**Problem**: Need declarative K8s configuration management

**Alternatives**:
- Helm (templating, complex, not GitOps-native)
- Jsonnet (steep learning curve, non-standard)
- Plain YAML (massive duplication)
- Custom tool (reinventing wheel)

**Decision**: Use Kustomize

**Rationale**:
1. ✅ K8s-native (built into kubectl)
2. ✅ No templating (pure YAML, easy to debug)
3. ✅ Composable (archetypes + components + overlays)
4. ✅ GitOps-native (declarative patches)
5. ✅ Strategic merge patches (DRY principle)
6. ✅ Components (optional features)
7. ✅ Simple learning curve

**Trade-offs Accepted**:
- No complex logic (but we don't need it)
- Verbose patches (but readable)
- Generated files in Git (but good for audit)

**Verdict**: Best tool for our use case

---

### Why Harness CD?

**Problem**: Need enterprise-grade deployment orchestration

**Alternatives**:
- ArgoCD (free, but weak approvals, no runtime inputs)
- Flux (free, but no UI, limited controls)
- GitHub Actions (free, but not enterprise-grade)
- Jenkins (legacy, maintenance burden)

**Decision**: Use Harness

**Rationale**:
1. ✅ Already deployed (sunk cost)
2. ✅ Teams already trained
3. ✅ Enterprise approvals (multi-gate, role-based)
4. ✅ Multi-cluster support (delegates)
5. ✅ Runtime inputs (image tag at deploy time)
6. ✅ Canary/Blue-Green (production-grade strategies)
7. ✅ Audit trail (compliance requirements)
8. ✅ Integrations (PagerDuty, Slack, Jira, ServiceNow)
9. ✅ RBAC (pipeline-level permissions)
10. ✅ Continuous Verification (automated metrics check)

**Trade-offs Accepted**:
- Cost (~$120K/year for 100 services)
- Vendor lock-in (mitigated by keeping Kustomize portable)
- Pipeline sprawl (100+ pipelines to manage)

**Verdict**: Cost justified by features and team productivity

---

## Key Design Decisions

### Decision 1: Catalog-Driven Generation

**Problem**: How to manage 100+ services without folder explosion?

**Chosen Approach**: Single catalog file + just-in-time generation

**Alternatives Rejected**:
- ❌ Per-service folders (100+ folders, maintenance nightmare)
- ❌ Monolithic configuration (hard to manage)

**Rationale**:
- ✅ Single source of truth (services.yaml)
- ✅ No folder sprawl (scales to 1000s of services)
- ✅ Easy to query and update
- ✅ UI-friendly (Backstage can render easily)

---

### Decision 2: GitOps for Config, Runtime for Images

**Problem**: Balance between GitOps purity and deployment velocity

**Chosen Approach**: Hybrid model
- Config in Git (GitOps)
- Image tag as runtime input (Harness)

**Alternatives Rejected**:
- ❌ Pure GitOps (image tag in Git) - too slow, requires PR for every app deploy
- ❌ Pure imperative (no Git) - loses audit trail, not compliant

**Rationale**:
- ✅ Config changes are infrequent (GitOps appropriate)
- ✅ App deployments are frequent (runtime input appropriate)
- ✅ Decouples app velocity from config governance
- ✅ Best of both worlds

---

### Decision 3: Per-Service Pipelines

**Problem**: Single pipeline bottleneck vs pipeline sprawl

**Chosen Approach**: Per-service pipelines (100+ pipelines)

**Alternatives Rejected**:
- ❌ Single pipeline for all services - bottleneck, no isolation
- ❌ Per-team pipeline - still creates contention within teams

**Rationale**:
- ✅ True isolation (no contention)
- ✅ Independent execution (parallel)
- ✅ Team-specific RBAC
- ✅ Customizable per service
- ✅ Scales infinitely

**Trade-off**: Pipeline management complexity (mitigated by templates + automation)

---

### Decision 4: Manifests Committed to Git

**Problem**: Should generated manifests be in Git?

**Chosen Approach**: Yes, commit to `generated/` directory

**Alternatives Rejected**:
- ❌ Generate at deployment time - violates security policy (no scripts in Harness)
- ❌ Generate in Harness - not GitOps, no audit trail
- ❌ Don't version generated files - can't see what was deployed

**Rationale**:
- ✅ GitOps-compliant (Git = source of truth)
- ✅ Harness security policy (no scripts allowed)
- ✅ Audit trail (see exactly what deployed when)
- ✅ Reproducible (can rebuild from history)
- ✅ Rollback-friendly (git revert)

**Trade-off**: Repo size grows (but negligible with 100 services)

---

### Decision 5: Cross-Org Repository Structure

**Problem**: Should pipelines be in same repo as config?

**Chosen Approach**: Separate repos in different GitHub orgs

**Alternatives Rejected**:
- ❌ Same repo - couples pipeline changes to config changes
- ❌ Same org, different repo - organizational structure doesn't allow

**Rationale**:
- ✅ Matches org structure (pipelines owned by different team)
- ✅ Independent versioning
- ✅ Clear separation of concerns
- ✅ Harness supports cross-org (via connector)

**Trade-off**: Need cross-org connector (easily configured)

---

### Decision 6: No Shell Scripts in Harness

**Problem**: Security policy blocks shell scripts in CD pipelines

**Chosen Approach**: Scripts in CI (GitHub Actions), only K8s native steps in Harness

**Alternatives Rejected**:
- ❌ Request policy exception - violates security standards
- ❌ Use Harness plugins only - limited functionality

**Rationale**:
- ✅ Complies with security policy
- ✅ Better separation (CI = build, CD = deploy)
- ✅ GitOps-compliant (manifests pre-generated)
- ✅ Reproducible (same manifest, same result)

**Trade-off**: CI dependency (but fast, 5-10 min)

---

### Decision 7: T-Shirt Sizing for Resources

**Problem**: Developers don't know CPU/memory values

**Chosen Approach**: Pre-defined sizes (small, medium, large, xlarge)

**Alternatives Rejected**:
- ❌ Let developers specify CPU/mem - error-prone, inconsistent
- ❌ Auto-detect from metrics - complex, not available for new services

**Rationale**:
- ✅ Simple for developers (choose size, not values)
- ✅ Consistent (all medium services same size)
- ✅ Right-sized (based on real-world data)
- ✅ Cost-optimized (prevents over-provisioning)
- ✅ Easy to update (change definition, affects all)

**Trade-off**: Less granular control (but can override per service)

---

### Decision 8: Behavior Profiles

**Problem**: 50+ fields to configure per service

**Chosen Approach**: Pre-defined profiles (public-api, internal-api, event-consumer, etc.)

**Alternatives Rejected**:
- ❌ Manual component selection - tedious, error-prone
- ❌ No profiles - 50+ fields to fill

**Rationale**:
- ✅ Reduces 50 fields to 5
- ✅ Enforces best practices
- ✅ Faster onboarding (minutes vs hours)
- ✅ Consistent configurations
- ✅ Easy to add new profiles

**Trade-off**: Less flexibility (but can still override)

---

## Consequences

### Positive

1. ✅ **Scalability**: Supports 100+ services without bottlenecks
2. ✅ **Self-Service**: Developers onboard in 5 minutes
3. ✅ **GitOps**: Full audit trail and declarative config
4. ✅ **Enterprise Controls**: Multi-gate approvals, change windows
5. ✅ **Multi-Cluster**: Native support via delegates
6. ✅ **No Custom UI**: Reuse Backstage + Harness
7. ✅ **Consistent**: T-shirt sizing and profiles enforce standards
8. ✅ **Fast**: Parallel pipelines, 5-10 min deployments

### Negative

1. ⚠️ **Cost**: Harness licensing (~$120K/year)
2. ⚠️ **Complexity**: Three components to maintain
3. ⚠️ **Vendor Lock-in**: Dependent on Harness (mitigated by Kustomize portability)
4. ⚠️ **Pipeline Sprawl**: 100+ pipelines to manage (mitigated by templates)
5. ⚠️ **Cross-Org Dependency**: Requires connector setup

### Mitigations

- **Cost**: ROI positive (saves engineer time)
- **Complexity**: Good documentation, training
- **Vendor Lock-in**: Keep Kustomize layer portable
- **Pipeline Sprawl**: Automation for updates, good templates
- **Cross-Org**: One-time setup, well-documented

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Onboarding Time** | < 10 min | Backstage form to pipeline ready |
| **Deployment Time** | < 10 min | Pipeline trigger to pods running |
| **Self-Service %** | > 80% | Services onboarded without platform team |
| **Failed Deployments** | < 5% | Deployment success rate |
| **Concurrent Deploys** | 20+ | Simultaneous pipeline executions |
| **Approval Time (Prod)** | < 4 hours | Request to approval |

---

## References

- [01_BACKSTAGE_DESIGN.md](./01_BACKSTAGE_DESIGN.md) - Backstage component details
- [02_KUSTOMIZE_CONFIG_MANAGEMENT.md](./02_KUSTOMIZE_CONFIG_MANAGEMENT.md) - Kustomize design
- [03_HARNESS_INTEGRATION_DESIGN.md](./03_HARNESS_INTEGRATION_DESIGN.md) - Harness integration

---

## Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Architect** | Platform Team Lead | 2025-11-09 | ✓ Approved |
| **Engineering** | Engineering Manager | Pending | |
| **Security** | Security Team | Pending | |
| **SRE** | SRE Lead | Pending | |

---

**Next Steps**: Proceed with Phase 1 implementation (Backstage + Pipeline Orchestrator)
