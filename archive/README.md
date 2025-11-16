# Platform-Next Documentation

## Overview

This directory contains detailed design documentation for the Platform-Next Kubernetes configuration management system.

---

## Document Index

### Core Documents (Read in Order)

1. **[00_ARCHITECTURE_DECISION.md](00_ARCHITECTURE_DECISION.md)**
   - **Purpose**: Architecture Decision Record (ADR)
   - **Audience**: All stakeholders
   - **Content**: Why we chose Backstage + Kustomize + Harness
   - **Read this first** to understand the overall approach

2. **[01_BACKSTAGE_DESIGN.md](01_BACKSTAGE_DESIGN.md)**
   - **Purpose**: Backstage component detailed design
   - **Audience**: Developers, Platform team
   - **Content**: 
     - Software template design
     - Catalog entity structure
     - Plugins and integrations
     - User workflows
   - **Read this** to understand service onboarding

3. **[02_KUSTOMIZE_CONFIG_MANAGEMENT.md](02_KUSTOMIZE_CONFIG_MANAGEMENT.md)**
   - **Purpose**: Config management repository design
   - **Audience**: Platform team, SRE
   - **Content**:
     - Archetype layer (workload shapes)
     - Component layer (optional features)
     - Base configuration (org standards)
     - Overlays (environment, region)
     - Manifest generation process
   - **Read this** to understand Kustomize structure

4. **[03_HARNESS_INTEGRATION_DESIGN.md](03_HARNESS_INTEGRATION_DESIGN.md)**
   - **Purpose**: Harness CD pipeline design
   - **Audience**: SRE, Release managers
   - **Content**:
     - Pipeline architecture
     - Multi-cluster delegate setup
     - Cross-org manifest fetching
     - Runtime image tag injection
     - Approval workflows
   - **Read this** to understand deployment orchestration

---

## Quick Reference

### Architecture Components

| Component | Purpose | Repository | Interface |
|-----------|---------|------------|-----------|
| **Backstage** | Service onboarding, catalog | - | UI: backstage.company.com |
| **Platform-Next** | Config management | company/platform-next | Git |
| **Harness Pipelines** | Pipeline definitions | company-harness/harness-pipelines | Git |
| **Harness Platform** | CD orchestration | - | UI: harness.company.com |
| **Pipeline Orchestrator** | Bridge service | - | API |

### User Journeys

| Journey | Frequency | Primary Interface | Documentation |
|---------|-----------|-------------------|---------------|
| **Onboard Service** | Once per service | Backstage UI | [01_BACKSTAGE_DESIGN.md](01_BACKSTAGE_DESIGN.md) |
| **Deploy App** | Daily | Harness Console | [03_HARNESS_INTEGRATION_DESIGN.md](03_HARNESS_INTEGRATION_DESIGN.md) |
| **Update Config** | Weekly | Git + CI | [02_KUSTOMIZE_CONFIG_MANAGEMENT.md](02_KUSTOMIZE_CONFIG_MANAGEMENT.md) |
| **Monitor Service** | Continuous | Backstage UI | [01_BACKSTAGE_DESIGN.md](01_BACKSTAGE_DESIGN.md) |

---

## Key Design Principles

1. **Separation of Concerns**
   - Backstage = Developer interface
   - Kustomize = Configuration management
   - Harness = Deployment orchestration

2. **GitOps Compliance**
   - All config in Git (source of truth)
   - Manifests pre-generated and committed
   - Harness deploys from Git (declarative)

3. **Self-Service**
   - Developers onboard without platform team
   - 5-field form (vs 50+ fields before)
   - T-shirt sizing (vs manual CPU/memory)

4. **Composability**
   - Archetypes define structure
   - Components add features
   - Overlays customize per env/region

5. **Scalability**
   - Per-service pipelines (no bottlenecks)
   - Parallel execution (20+ concurrent)
   - Catalog-driven (scales to 1000s of services)

---

## Glossary

| Term | Definition |
|------|------------|
| **Archetype** | Workload pattern template (api, listener, scheduler, job, streaming) |
| **Component** | Optional feature (ingress, hpa, pdb, circuit-breaker) |
| **Profile** | Pre-configured bundle (public-api, internal-api, event-consumer) |
| **Size** | T-shirt sizing for resources (small, medium, large, xlarge) |
| **Overlay** | Environment or region-specific customization |
| **Catalog** | Single source of truth (services.yaml) |
| **Delegate** | Harness agent running in K8s cluster |

---

## FAQ

**Q: Do I need to know Kustomize to onboard a service?**
A: No, use Backstage UI (5-field form).

**Q: Do I need to know Harness to deploy?**
A: Minimal - just enter image tag and click "Run".

**Q: How do I change resource limits?**
A: Update catalog (change size: medium → large) or override in services.yaml.

**Q: How long does onboarding take?**
A: 5-10 minutes (automated).

**Q: Can I deploy to int-stable without approval?**
A: Yes, int-stable has auto-approval.

**Q: How do I rollback a bad deployment?**
A: Harness Console → Execution History → Click "Rollback" or deploy previous image tag.

**Q: What if manifests fail validation?**
A: CI catches errors, PR won't merge, pipeline won't be created.

---

## Support

- **Questions**: #platform-support (Slack)
- **Issues**: GitHub Issues in platform-next repo
- **On-Call**: PagerDuty platform-team rotation

---

**Last Updated**: 2025-11-09
**Version**: 1.0
