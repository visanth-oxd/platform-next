# Architecture Decision Record - Platform-Next Design

## Status

**ACCEPTED** - 2025-11-09

**Last Updated**: 2025-11-15 (Added Cost Management Component)

---

## Context

We need a **complete platform for Kubernetes service management** that:
- Supports 100+ microservices
- Multiple environments (int-stable, pre-stable, prod)
- Multiple regions (euw1, euw2)
- Self-service for development teams
- GitOps-compliant
- Enterprise-grade approvals and controls
- **Cost visibility from day 1** (new requirement)
- **Mandatory cost tracking** (new requirement)
- **Integrated with Apptio Cloudability** (existing investment)

## Decision

We will implement a **four-component architecture**:

1. **Backstage** - Service onboarding and catalog (with mandatory cost config)
2. **Platform-Next Repo** - Kustomize-based config management
3. **Harness** - CD pipelines and deployment control
4. **Apptio Cloudability** - Cost tracking and budget management (existing)

### Why This Approach?

**Reuse existing tools** instead of building custom solutions:
- ✅ Backstage already deployed (developer portal)
- ✅ Harness already deployed (CD platform)
- ✅ Apptio Cloudability already deployed (cost management)
- ✅ Teams already familiar with all three
- ✅ No custom UI or cost infrastructure to build
- ✅ Enterprise-grade features out of the box
- ✅ Cost management integrated from service creation, not bolted on later

---

## Architecture Components

### Component 1: Backstage (Developer Portal + Cost Onboarding)

**Purpose**: Service onboarding with mandatory cost configuration

**Responsibilities**:
- Provide self-service UI for service creation
- Validate input (service name, archetype, profile, size, **cost config**)
- **Mandatory cost section** (cannot skip):
  - Budget per environment (int-stable, pre-stable, prod)
  - Cost center code for chargeback
  - Business unit for cost reporting
  - Cost owner for responsibility
  - Alert thresholds and notification channels
- Update service catalog in platform-next repo (via PR) with cost config
- Trigger pipeline creation (via Pipeline Orchestrator API)
- Register service in Backstage catalog
- Display service status, links, documentation
- **Send cost config to Apptio** (via webhook after merge)

**Key Feature**: Software Templates
- Declarative YAML-based forms with validation
- GitHub integration (create PRs)
- API integration (webhook calls)
- **Form enforces all cost fields mandatory** - cannot submit without cost config
- Real-time validation of budget amounts, cost centers, alert channels
- Displays cost estimates based on service size
- Requires confirmation of cost responsibility before submission
- No custom code needed

### Component 2: Platform-Next Repo (Config Management + Cost Label Injection)

**Purpose**: Kubernetes configuration as code with cost tracking

**Responsibilities**:
- Store service catalog (single YAML file) with **mandatory cost config**:
  - Budgets per environment
  - Cost center, business unit, owner
  - Alert thresholds and channels
- Define archetypes (workload shapes)
- Define components (optional features)
- Define overlays (environment, region)
- **Generate K8s manifests with cost labels automatically** (via CI):
  - cost.service label
  - cost.team label
  - cost.environment label
  - cost.costCenter label
  - cost.businessUnit label
  - cost.budget label
- Commit manifests to Git (source of truth)
- **Validate cost configuration** in CI/CD:
  - Schema validation (all required fields present)
  - Budget amount validation (realistic ranges)
  - Cost center existence check
  - Alert threshold validation
- Trigger Apptio sync when cost config changes

**Key Feature**: GitOps-compliant with Cost Integration
- All changes via Git (including cost config)
- Manifests versioned in Git (with cost labels)
- CI generates manifests automatically with cost labels injected
- CI validates cost config before allowing merge
- Cost labels flow through to GCP billing automatically
- No runtime generation
- **Cost config cannot be bypassed** - manifest generation fails without it

### Component 3: Harness (CD Platform)

**Purpose**: Deployment orchestration and control

**Responsibilities**:
- Execute deployments across environments
- Provide runtime inputs (image tag, environment)
- Fetch manifests from Git (cross-org) - **manifests already have cost labels**
- Inject image tags into manifests
- Approval workflows (manual, auto, timed)
- Multi-cluster support (via delegates)
- Canary deployments, rollbacks
- **Deploy resources with cost labels intact** - labels flow to GCP billing

**Key Feature**: Runtime image tag injection with Cost Label Preservation
- Manifests in Git have placeholder (for image) AND cost labels
- User provides image tag at deployment time
- Harness injects tag and deploys (cost labels already present)
- Decouples app version from config version
- **Cost labels automatically attached to all deployed resources**
- Enables cost tracking from day 1 of deployment

### Component 4: Apptio Cloudability (Cost Tracking & Budget Management)

**Purpose**: Centralized cost visibility and budget enforcement (existing enterprise tool)

**Responsibilities**:
- **Ingest GCP billing data** (automatic, via existing connection)
- **Read cost labels** from Kubernetes resources (cost.*, labels in GCP billing)
- **Allocate costs** by service, team, cost center, business unit, environment
- **Track budgets** against actual spending (per service, per environment)
- **Generate alerts** when thresholds crossed (50%, 80%, 100%+)
- **Route notifications** to Teams, email, PagerDuty based on configuration
- **Provide dashboards** for cost visibility by team, cost center, business unit
- **Generate optimization recommendations** (right-sizing, reserved instances, etc.)
- **Enable chargeback** reporting to Finance/Cost Centers
- **Store alert configuration** from service catalog (synced automatically)

**Key Feature**: Zero Custom Infrastructure
- **No custom databases** (uses Apptio's platform)
- **No custom APIs** (uses Apptio's APIs)
- **No custom dashboards** (uses Apptio's dashboards)
- **No custom alerting** (uses Apptio's alerting engine)
- **Leverages existing Apptio investment** - no new tools to operate
- **Integration via labels** - cost config in catalog → labels in manifests → Apptio reads labels

**Integration Points**:
1. **Catalog-Driven Configuration**: Service budget/alert config stored in platform-next catalog
2. **Label-Based Allocation**: Cost labels injected by Kustomize → flow through GCP → read by Apptio
3. **Automatic Sync**: Cloud Function syncs catalog to Apptio budgets when config changes
4. **Budget Enforcement**: Apptio publishes alerts when thresholds crossed
5. **Chargeback Ready**: Cost center + labels enable accurate billing per team

---

## Data Flow

### Service Onboarding (With Mandatory Cost Config)

```
Developer → Backstage UI → Fill form
            (Service Basics)
                ↓
          MANDATORY: Cost & Budget Section
            • Budget per environment
            • Cost center code
            • Business unit
            • Cost owner
            • Alert thresholds & channels
            (Cannot skip - form enforces)
                ↓
          Review & Confirm Cost Responsibility
            • Acknowledge understanding
            • Accept budget ownership
                ↓
          Form Validation
            ✓ Cost fields complete
            ✓ Budget amounts realistic
            ✓ Cost center format valid
                ↓
          Create PR to platform-next
            • catalog/services.yaml updated
            • Includes full cost config
                ↓
          CI/CD Validation
            ✓ Schema validation (cost required)
            ✓ Budget validation ($50-$50K ranges)
            ✓ Cost center exists in Apptio
            ✓ Alert thresholds valid
            ✓ All cost fields present
            (PR fails if cost config invalid)
                ↓
          GitHub Actions (CI) triggered
                ↓
          Generate manifests with cost labels:
            • cost.service
            • cost.team
            • cost.environment
            • cost.costCenter
            • cost.businessUnit
            • cost.owner
            • cost.budget
            (Script fails if cost config missing)
                ↓
          Commit to Git (source of truth)
                ↓
          Cloud Function: Apptio Sync
            • Parse cost config from catalog
            • Create budgets in Apptio
            • Store alert config
            • Enable monitoring
                ↓
          Call Pipeline Orchestrator API
                ↓
          Create Harness pipeline
                ↓
          Service ready to deploy
            ✓ Cost config in catalog
            ✓ Manifests have cost labels
            ✓ Budgets created in Apptio
            ✓ Alerts configured
            ✓ Cost tracking ready on day 1
```

### Application Deployment (Cost Tracking Begins)

```
App team builds image → Push to registry
                       ↓
          Open Harness Console
                       ↓
          Select pipeline → Enter image tag
                       ↓
          Pipeline fetches manifests from Git
            (Manifests already have cost labels)
                       ↓
          Inject image tag → Deploy to cluster
                       ↓
          Pods deployed with cost labels:
            • cost.service
            • cost.team
            • cost.costCenter
            • cost.environment
            • etc. (all intact)
                       ↓
          GCP billing includes labels
            (Automatic, within 24 hours)
                       ↓
          Apptio ingests costs
            (Allocates by service/team/cost-center)
                       ↓
          Cost tracking visible in Apptio
            (Budget monitoring active)
                       ↓
          Alerts fire when thresholds crossed
            (Teams/email/PagerDuty notifications)
                       ↓
          Monitor in Harness + Apptio + Backstage
```

### Configuration & Cost Config Update

```
Platform team updates:
  • catalog/archetype/component
  • OR cost config (budget/alerts)
                       ↓
          GitHub Actions regenerates manifests
            (With updated cost labels if changed)
                       ↓
          Commit to Git
                       ↓
          If cost config changed:
            → Apptio sync triggered
            → Budgets updated in Apptio
            → New alerts configured
                       ↓
          Next deployment automatically uses new config
                       ↓
          No pipeline trigger needed (GitOps)
                       ↓
          Cost tracking updated immediately
```

---

## Key Design Decisions

### Decision 1: Single Catalog File (Not Per-Service Files)

**Rationale**:
- Backstage updates catalog via API (no manual edits)
- No merge conflicts (UI serializes updates)
- Simpler to query and search
- Easier for UI rendering
- **Single source of truth for cost config** (budgets, alerts, cost centers)
- Easier to validate all cost fields in one place

**Alternative Rejected**: Per-service files
- Would cause merge conflicts with UI updates
- Harder to implement atomic updates
- More complex file management
- Would make cost validation harder

### Decision 2: Manifests Generated in CI with Cost Labels (Not in Harness)

**Rationale**:
- Harness blocks shell scripts (security policy)
- CI allows script execution
- GitOps compliance (manifests in Git)
- Decouples generation from deployment
- **Cost labels can be injected at generation time** (from catalog)
- **Validates cost config before manifest generation** (fail-fast)
- Cost labels are versioned in Git (audit trail)
- Cannot bypass cost tracking (manifest generation fails without cost config)

**Alternative Rejected**: Generate in Harness
- Violates security policy
- Not GitOps-compliant
- Can't version manifests
- Cost labels wouldn't be enforced
- Cost tracking could be skipped

### Decision 3: Harness Pipelines in Separate Repo

**Rationale**:
- Different GitHub org for Harness
- Separation of concerns
- Independent versioning
- Cross-org connector supported

**Alternative Rejected**: Same repo
- Doesn't match organizational structure
- Pipeline changes would trigger config CI unnecessarily

### Decision 4: Runtime Image Tag (Not in Manifests)

**Rationale**:
- App version changes frequently
- Config changes infrequently
- Decouples app deployment from config deployment
- Harness native image replacement

**Alternative Rejected**: Image tag in manifests
- Would require regenerating manifests for every app deploy
- Couples app and config
- More Git commits

### Decision 5: Per-Service Pipelines (Not Mono-Pipeline)

**Rationale**:
- True isolation (no contention)
- Independent execution
- Team-specific RBAC
- Scalable to 100+ services

**Alternative Rejected**: Single pipeline for all services
- Bottleneck
- No isolation
- Complex RBAC

### Decision 6: Mandatory Cost Config at Onboarding (Not Post-Deployment)

**Rationale**:
- **Cost management from day 1**, not an afterthought
- **Catch cost issues early** (at service creation, not after deployment)
- **Enforce accountability** (cost owner assigned upfront)
- **Enable chargeback immediately** (cost center defined from start)
- **Apptio budgets created before service goes live** (alerts ready)
- **Prevent cost surprises** (budgets set realistically)
- **Cannot be bypassed** (form requires, schema validates, CI enforces)

**Alternative Rejected**: Optional cost config added later
- Cost surprises after deployment
- No accountability until after spending occurs
- Harder to retro-fit cost allocation
- Finance doesn't have initial chargeback data
- Teams don't prioritize cost management

### Decision 7: Leverage Apptio Cloudability (Not Custom Cost Infrastructure)

**Rationale**:
- **Apptio already deployed** (existing investment)
- **Zero custom infrastructure** to build or operate
- **No custom databases** (uses Apptio's)
- **No custom APIs** (uses Apptio's APIs)
- **No custom dashboards** (uses Apptio's dashboards)
- **Enterprise features** (optimization, chargeback, forecasting, etc.)
- **Labels drive allocation** (simple, clean integration)
- **Cloud Function sync** (minimal custom code, just orchestration)

**Alternative Rejected**: Build custom cost system
- Development cost
- Operational overhead
- Re-inventing wheel
- Missing enterprise features
- Would duplicate Apptio capabilities

---

## Constraints Satisfied

| Constraint | Solution |
|------------|----------|
| **GitOps-compliant** | ✅ Manifests in Git (with cost labels), Harness deploys from Git |
| **No shell scripts in Harness** | ✅ Scripts run in CI only, Harness uses K8s native steps |
| **Multi-cluster (different networks)** | ✅ Delegates per cluster, infrastructure definitions |
| **Scalability (100+ services)** | ✅ Per-service pipelines, parallel execution, parallel cost tracking |
| **Self-service** | ✅ Backstage UI with mandatory cost config, no platform team bottleneck |
| **Approval controls** | ✅ Harness native approvals, tiered gates, budget enforcement in Apptio |
| **Single catalog** | ✅ One file, UI-managed, includes cost configuration |
| **Reuse existing tools** | ✅ Backstage + Harness + Apptio (no custom UI or cost infrastructure) |
| **Cost visibility from day 1** | ✅ Mandatory cost config at onboarding, labels injected in CI, Apptio tracking immediate |
| **Cost tracking per service** | ✅ Labels in manifests → GCP billing → Apptio allocation by service/team/cost-center |
| **Budget enforcement** | ✅ Apptio monitors budgets, alerts at 50%/80%/100% thresholds |
| **Cost allocation for chargeback** | ✅ Cost center codes in catalog, Apptio groups by cost center, Finance reporting ready |
| **Prevent cost surprises** | ✅ Budgets set at onboarding, Apptio alerts when spending approaches limits |
| **Cannot skip cost setup** | ✅ Form mandatory, schema enforces, CI validates, manifest generation fails without cost config |

---

## Benefits

### For Developers
- ✅ Self-service onboarding (Backstage UI)
- ✅ Simple deployment (Harness Console, 2 inputs)
- ✅ Single portal (Backstage) for everything
- ✅ Familiar tools (no learning curve)
- ✅ **Cost estimates shown during onboarding** (informed decisions)
- ✅ **Cost tracking from day 1** (no surprises after deployment)
- ✅ **Budget alerts in Teams** (immediate notification of issues)

### For Platform Team
- ✅ No custom UI to maintain
- ✅ No custom cost infrastructure to build
- ✅ Declarative configuration (Kustomize + Catalog)
- ✅ GitOps-compliant (audit trail, including cost config)
- ✅ Automated pipeline creation
- ✅ Automated Apptio budget/alert setup
- ✅ Policy enforcement (OPA, Harness policies, cost schema validation)
- ✅ **Cost labels automatically injected** (no manual setup)
- ✅ **Cost validation in CI/CD** (prevents bad configs)

### For Organization
- ✅ Scalable to 1000+ services (with parallel cost tracking)
- ✅ Enterprise compliance (approvals, audit, cost allocation)
- ✅ Cost-effective (reuse Backstage + Harness + Apptio)
- ✅ Fast deployments (parallel pipelines)
- ✅ **Cost visibility from day 1** (Apptio budgets ready before deploy)
- ✅ **Chargeback ready** (cost centers assigned upfront)
- ✅ **FinOps culture** (cost is everyone's responsibility, not afterthought)
- ✅ **Budget enforcement** (Apptio alerts prevent runaway costs)
- ✅ **Finance reporting** (accurate allocation by team/cost-center)
- ✅ **Optimization opportunity** (Apptio recommendations ready)

---

## Trade-offs

### What We Gain
- Leverage existing Backstage + Harness + Apptio investment
- Enterprise-grade features (approvals, RBAC, audit, cost management)
- True GitOps compliance (including cost config)
- Multi-cluster support
- Self-service developer experience
- **Cost visibility from day 1** (budgets before deployment)
- **FinOps culture** (cost accountability built-in)
- **Zero custom infrastructure** (use Apptio for all cost needs)
- **Automatic cost tracking** (labels → GCP → Apptio)

### What We Accept
- Harness licensing cost (~$120K/year for 100 services)
- Apptio licensing cost (already budgeted, existing tool)
- Dependency on Harness platform
- Dependency on Apptio platform
- Pipeline sprawl (100+ pipelines to manage)
- Cross-org complexity (config repo ≠ pipeline repo)
- **Mandatory cost config** (teams must define budgets at onboarding)
- **Cost labels in manifests** (increases manifest size slightly, negligible impact)

---

## Alternatives Considered

### Alternative 1: Pure GitOps (ArgoCD) + OpenCost
- **Pros**: Free, declarative, simple, open-source cost tracking
- **Cons**: Weaker approval controls, no runtime inputs, new tools to learn, operational overhead
- **Verdict**: Rejected due to:
  - Lack of approval workflows
  - Team not familiar with ArgoCD
  - OpenCost requires operational overhead (database, monitoring)
  - Missing enterprise features (chargeback, optimization, ML forecasting)

### Alternative 2: GitHub Actions Matrix + Custom Cost Infrastructure
- **Pros**: Free, integrated with GitHub
- **Cons**: Not enterprise-grade, limited approvals, no canary, custom cost infrastructure needed
- **Verdict**: Rejected due to:
  - Lack of production deployment controls
  - Would require building custom cost system
  - Duplicating Apptio functionality

### Alternative 3: Custom UI + GitOps + Custom Cost System
- **Pros**: Tailored experience, full control
- **Cons**: Development cost, maintenance burden, reinventing wheel for both UI and cost system
- **Verdict**: Rejected due to:
  - Significant development cost
  - Ongoing maintenance burden
  - Apptio already handles cost management
  - No advantage over leveraging existing tools

### Alternative 4: Per-Service Files + ArgoCD + Cost Sync
- **Pros**: Simple, free, costs tracked
- **Cons**: Merge conflicts, no approval controls, still operational overhead for cost system
- **Verdict**: Rejected due to:
  - Merge conflicts in per-service files
  - Lack of Harness features (approvals, canary, RBAC)
  - Team familiarity with Harness, not ArgoCD

### Alternative 5: Apptio-Only (No Custom Catalogs)
- **Pros**: Simpler, all-in-one cost solution
- **Cons**: Apptio doesn't manage K8s deployments, teams need separate workflow for service onboarding/deployment
- **Verdict**: Rejected due to:
  - Doesn't solve deployment automation
  - Would still need Backstage + Harness for service management
  - Better to integrate cost into existing platform workflow

### Chosen Approach: Backstage + Platform-Next + Harness + Apptio (Integrated)
- **Best of all worlds**:
  - Leverage existing Backstage (onboarding UI)
  - Leverage existing Harness (deployment automation)
  - Leverage existing Apptio (cost management)
  - **Integrate cost into onboarding workflow** (mandatory, not optional)
  - **Automatic label injection** (no manual setup)
  - **Zero custom infrastructure** (Apptio handles all cost needs)
  - **GitOps-compliant** (including cost config)

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)
- Create Backstage software template **with mandatory cost section**
- Create JSON schema for service catalog **with required cost fields**
- Create Harness pipeline templates
- Deploy Pipeline Orchestrator service
- **Setup Apptio sync Cloud Function** (reads catalog, creates budgets)
- Test with 3 pilot services (including cost config)

### Phase 2: Cost Integration (Week 3-4)
- GitHub Actions workflows (manifest generation **with cost label injection**)
- **Add cost validation in CI/CD** (schema, budgets, cost centers)
- Cross-org connector setup
- Harness delegate per cluster
- **Test Apptio budget creation** (verify budgets appear, alerts fire)
- **Test alert routing** (Teams, email notifications)
- End-to-end testing (onboarding → deployment → cost tracking in Apptio)

### Phase 3: Rollout (Week 5-12)
- Migrate 10 services per week (with cost config)
- **Verify cost config in catalog** for each service
- **Verify cost labels in manifests** 
- **Verify budgets created in Apptio**
- Document processes (including cost onboarding)
- Train teams on mandatory cost config
- Monitor and optimize deployment + cost tracking

### Phase 4: Enhancements (Month 4+)
- Advanced features (canary, blue-green)
- Policy automation (OPA **including cost policies**)
- Observability integration (cost visibility in dashboards)
- **Apptio optimization recommendations** (right-sizing, reserved instances)
- **FinOps metrics & reporting** (cost trends, budget variance)

---

## Success Criteria

### Deployment & Operations
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Onboarding Time** | < 15 min | Time from Backstage form start to pipeline ready (includes mandatory cost section) |
| **Deployment Time** | < 10 min | Time from pipeline trigger to pods running |
| **Self-Service Adoption** | > 80% | % of services onboarded without platform team help |
| **Approval Time (Prod)** | < 4 hours | Time from deployment trigger to approval |
| **Failed Deployments** | < 5% | % of deployments that fail |
| **Concurrent Deployments** | 20+ | Number of simultaneous deployments |

### Cost Management
| Metric | Target | Measurement |
|--------|--------|-------------|
| **Cost Config Completeness** | 100% | % of services with all cost fields defined (non-negotiable) |
| **Cost Config Validation** | 100% | % of PRs validated against schema before merge |
| **Apptio Budget Creation** | 100% | % of services with budgets created in Apptio within 1 hour of catalog update |
| **Cost Label Injection** | 100% | % of manifests with cost labels present |
| **Budget Alert Accuracy** | > 95% | % of alerts that fire at correct thresholds |
| **Cost Data Latency** | < 48 hours | Time from deployment to costs visible in Apptio |
| **Cost Anomaly Detection** | > 80% | % of unusual spending patterns detected by Apptio |
| **FinOps Maturity** | Level 3 | Structured approach, cost ownership, optimization active |

---

## References

- [Backstage Software Templates](https://backstage.io/docs/features/software-templates/)
- [Harness GitOps](https://developer.harness.io/docs/continuous-delivery/gitops/)
- [Kustomize Documentation](https://kustomize.io/)
- [Apptio Cloudability Integration](./docs/cost-management-apptio-integration.md)
- [Cost Onboarding Guide](./docs/06_COST_ONBOARDING.md) ⭐ Required reading for service teams
- [Cost Management Design](./docs/04_COST_MANAGEMENT_DESIGN.md)
- [GCP Native Cost Tools](./docs/04b_COST_MANAGEMENT_GCP_NATIVE.md)

---

## Document Evolution

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-09 | Initial decision: Backstage + Harness approach |
| 2.0 | 2025-11-15 | Added cost management component (Apptio integration), mandatory cost onboarding, design decisions 6-7 |

---

## Key Takeaways

**Platform-Next is not just a deployment platform; it is a complete service management platform that integrates:**

1. **Service Onboarding** (Backstage) - Self-service with mandatory cost config
2. **Configuration Management** (Platform-Next Repo) - Kustomize-based with cost labels
3. **Deployment Automation** (Harness) - CD pipelines with cost tracking
4. **Cost Management** (Apptio) - Budget enforcement and optimization

**Core Principle**: *Cost management is not optional. Every service must define budgets, cost ownership, and alert thresholds at creation time, not after deployment. This ensures FinOps culture from day 1.*

**Implementation**: Leverage existing tools (Backstage, Harness, Apptio), integrate cost into onboarding workflow, automatically inject labels, let Apptio handle the rest.

---

**Status**: ✅ Approved and ready for implementation

**Last Updated**: 2025-11-15

**Next Steps**:
1. Create cost onboarding documentation (06_COST_ONBOARDING.md) ✅
2. Update Backstage template with mandatory cost section
3. Create JSON schema for catalog with required cost fields
4. Add CI/CD cost validation workflows
5. Setup Apptio sync Cloud Function
6. Train teams on cost onboarding process