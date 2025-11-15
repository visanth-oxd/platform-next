# Platform-Next Architecture Documentation Index

**Date**: 2025-11-15

Complete guide to understanding Platform-Next architecture, cost integration, and deployment pipeline.

---

## Core Architecture Documents

### 1. [00_Architecture_decision.md](./00_Architecture_decision.md)
**Overview**: Strategic architecture decisions for Platform-Next

**Key Content**:
- 4-component architecture (Backstage, Platform-Next, Harness, Apptio)
- 7 key design decisions
- Data flows (onboarding, deployment, configuration updates)
- Benefits and trade-offs
- Alternatives considered

**Read when**: Understanding the "why" behind the platform design

---

### 2. [COST_INTEGRATION_SUMMARY.md](./COST_INTEGRATION_SUMMARY.md)
**Overview**: Complete summary of cost integration into Platform-Next

**Key Content**:
- Four enforcement layers (UI, schema, CI/CD, manifest generation)
- Complete implementation checklist
- Integration points between all components
- Success metrics and measurement

**Read when**: Getting a high-level overview of how cost flows through the system

---

## Operational Guides

### 3. [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) ⭐ START HERE
**Overview**: Complete operational guide for service onboarding with cost management

**Key Content**:
- 5 enforcement layers for cost configuration
- Backstage template specification
- Service catalog structure with examples
- Cost estimation formulas
- Step-by-step onboarding workflow
- Alert strategies and configuration
- Real-world examples (Payment Service, Fraud Detection, Internal Tools)
- Troubleshooting guide and FAQ
- **NEW**: Two options for Apptio sync (Cloud Functions vs Kubernetes Service)

**Read when**: 
- Onboarding a new service
- Understanding how cost config is enforced
- Troubleshooting cost-related issues
- Setting up Apptio sync

---

## Advanced Architecture & Design

### 4. [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) ⭐ NEW
**Overview**: Complete architecture for cost metadata abstraction and deployment pipeline

**Key Content**:
- Cost metadata abstraction strategy
- Service definitions vs. cost configurations (separation of concerns)
- Cost profiles, alert policies, and budget templates
- Per-service cost configurations
- Cost center mappings and policies
- **Complete data flow**: From abstracted configs → Backstage → Catalog → Manifests → Apptio
- How profiles, sizes, and cost interact (3-dimensional model)
- End-to-end example: Payment Service
- Implementation phases
- Benefits of abstraction

**Read when**:
- Designing cost infrastructure
- Understanding how cost data flows through the system
- Implementing cost metadata abstraction
- Creating cost templates and policies
- Understanding Kustomize integration with cost

**Recommended Path**:
1. Start with this document if implementing from scratch
2. Understand abstraction model
3. Then read 06_COST_ONBOARDING.md for operational details

---

## Design Documents (Cost Alternatives)

### 5. [docs/04_COST_MANAGEMENT_DESIGN.md](./docs/04_COST_MANAGEMENT_DESIGN.md)
**Overview**: Original cost design with OpenCost (alternative approach)

**Key Content**:
- OpenCost-based architecture
- Prometheus + TimescaleDB stack
- Cost aggregation pipeline
- Why this was rejected in favor of Apptio

**Read when**: Understanding alternative approaches and decisions

---

### 6. [docs/04b_COST_MANAGEMENT_GCP_NATIVE.md](./docs/04b_COST_MANAGEMENT_GCP_NATIVE.md)
**Overview**: GCP-native cost tools alternative

**Key Content**:
- Cloud Budgets for spending limits
- Cloud Monitoring for alerts
- BigQuery ML for forecasting
- Cloud Functions for automation

**Read when**: Considering GCP-only cost approach

---

## Configuration & Implementation

### 7. [DECOUPLED_PIPELINE_DESIGN.md](./DECOUPLED_PIPELINE_DESIGN.md)
**Overview**: Pipeline architecture decoupling configuration from deployment

**Read when**: Understanding manifest generation and pipeline design

---

### 8. [docs/02_KUSTOMIZE_CONFIG_MANAGEMENT.md](./docs/02_KUSTOMIZE_CONFIG_MANAGEMENT.md)
**Overview**: Kustomize-based configuration management

**Read when**: Understanding how Kustomize integrates with cost labels

---

### 9. [docs/03_HARNESS_INTEGRATION_DESIGN.md](./docs/03_HARNESS_INTEGRATION_DESIGN.md)
**Overview**: Harness CD platform integration

**Read when**: Understanding deployment orchestration and label preservation

---

## Monitoring & Observability

### 10. [08_MONITORING_METRICS_COST_INTEGRATION.md](./08_MONITORING_METRICS_COST_INTEGRATION.md)
**Overview**: Cost metrics and monitoring integration

**Read when**: Setting up cost monitoring and observability

---

### 11. [MONITORING_DELIVERY_SUMMARY.md](./MONITORING_DELIVERY_SUMMARY.md)
**Overview**: Summary of monitoring delivery and metrics

**Read when**: Understanding monitoring architecture

---

## Checklists & Planning

### 12. [DELIVERABLES_CHECKLIST.md](./DELIVERABLES_CHECKLIST.md)
**Overview**: Implementation checklist and deliverables

**Read when**: Planning or tracking implementation

---

### 13. [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
**Overview**: Phased implementation plan

**Read when**: Planning rollout and timeline

---

## Quick Navigation by Role

### For Service Teams (Developers)
1. **START**: [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - How to onboard with cost management
2. Then: [00_Architecture_decision.md](./00_Architecture_decision.md) - Understand "why"
3. Reference: [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Deep dive on cost data flow

### For Platform Engineers
1. **START**: [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Cost abstraction & pipeline design
2. Then: [00_Architecture_decision.md](./00_Architecture_decision.md) - Overall architecture
3. Then: [COST_INTEGRATION_SUMMARY.md](./COST_INTEGRATION_SUMMARY.md) - Integration points
4. Reference: [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Operational guide

### For Finance/FinOps Teams
1. **START**: [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Section 6 (Cost Centers) and Section 5 (Alert Strategy)
2. Then: [COST_INTEGRATION_SUMMARY.md](./COST_INTEGRATION_SUMMARY.md) - High-level integration
3. Reference: [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Cost structure & governance

### For Architects/Decision Makers
1. **START**: [00_Architecture_decision.md](./00_Architecture_decision.md) - Strategic decisions
2. Then: [COST_INTEGRATION_SUMMARY.md](./COST_INTEGRATION_SUMMARY.md) - Integration overview
3. Then: [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Detailed design
4. Reference: [docs/04_COST_MANAGEMENT_DESIGN.md](./docs/04_COST_MANAGEMENT_DESIGN.md) & [docs/04b_COST_MANAGEMENT_GCP_NATIVE.md](./docs/04b_COST_MANAGEMENT_GCP_NATIVE.md) - Alternatives

---

## Key Concepts Glossary

### Services & Definitions
- **Service**: A microservice running on Kubernetes
- **Archetype**: Type of service (api-service, worker, stateful, tool)
- **Profile**: How service is deployed (standard, stateful, high-performance, cost-optimized)
- **Size**: Resource allocation (small, medium, large, xlarge)

### Cost Management
- **Cost Config**: Budget, alert thresholds, owner, cost center for a service
- **Cost Profile**: Template defining cost estimates by size and archetype
- **Cost Center**: Organization cost allocation code (CC-XXXXX)
- **Business Unit**: Department owning the service
- **Cost Owner**: Person responsible for cost management
- **Cost Labels**: Kubernetes labels injected into manifests for cost tracking

### Pipeline Components
- **Catalog**: Single YAML file (services.yaml) containing all service definitions
- **Kustomize**: Tool that generates K8s manifests from templates
- **Manifests**: Final Kubernetes YAML files with cost labels
- **Apptio**: Cost tracking and budget management system
- **GCP Billing**: Cloud provider billing with label-based allocation
- **Harness**: CD platform for deploying manifests to clusters

---

## Document Relationships

```
Architecture Decisions (00_)
    ↓
    ├→ Cost Integration Summary
    │   ↓
    │   ├→ Cost Onboarding (06_) [OPERATIONAL GUIDE]
    │   │   ├→ Enforcement Layers 1-4
    │   │   └→ Apptio Sync Options
    │   │
    │   └→ Cost Metadata Abstraction (10_) [DESIGN GUIDE]
    │       ├→ Profiles, Sizes, Policies
    │       ├→ Data Flow Pipeline
    │       └→ Kustomize Integration
    │
    ├→ Config Management (02_)
    │   └→ Kustomize Details
    │
    ├→ Deployment Integration (03_)
    │   └→ Harness Details
    │
    ├→ Alternatives (04_, 04b_)
    │   └→ Why Apptio was chosen
    │
    └→ Monitoring (08_)
        └→ Cost Metrics & Observability
```

---

## Implementation Sequence

### Phase 1: Foundation (Read these first)
1. [00_Architecture_decision.md](./00_Architecture_decision.md) - Understand design
2. [COST_INTEGRATION_SUMMARY.md](./COST_INTEGRATION_SUMMARY.md) - Overview of integration
3. [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Detailed pipeline design

### Phase 2: Implementation (Use these as guides)
1. [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Operational procedures
2. [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - Rollout plan
3. [DELIVERABLES_CHECKLIST.md](./DELIVERABLES_CHECKLIST.md) - Tracking progress

### Phase 3: Operations (Reference during execution)
1. [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Onboarding guide
2. [08_MONITORING_METRICS_COST_INTEGRATION.md](./08_MONITORING_METRICS_COST_INTEGRATION.md) - Monitoring setup
3. [MONITORING_DELIVERY_SUMMARY.md](./MONITORING_DELIVERY_SUMMARY.md) - Observability

---

## Document Maintenance

| Document | Owner | Review Frequency | Last Updated |
|----------|-------|------------------|--------------|
| 00_Architecture_decision.md | Platform Architects | Quarterly | 2025-11-15 |
| COST_INTEGRATION_SUMMARY.md | Platform Team | Quarterly | 2025-11-15 |
| docs/06_COST_ONBOARDING.md | Platform Team | Monthly | 2025-11-15 |
| docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md | Platform Architects | Quarterly | 2025-11-15 |
| docs/04_COST_MANAGEMENT_DESIGN.md | Architecture | Annually | 2025-11-15 |
| IMPLEMENTATION_ROADMAP.md | Program Manager | Weekly | 2025-11-15 |

---

## Questions & Troubleshooting

**"How do I onboard a new service?"**
→ See [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Section 3

**"How is cost data passed to manifests?"**
→ See [docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md](./docs/10_COST_METADATA_ABSTRACTION_PIPELINE.md) - Section 4

**"What's the architecture philosophy?"**
→ See [00_Architecture_decision.md](./00_Architecture_decision.md) - Section 1

**"How do I set up Apptio sync?"**
→ See [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Section 1.5

**"Why was this design chosen over alternatives?"**
→ See [00_Architecture_decision.md](./00_Architecture_decision.md) - Section 7 (Alternatives)

**"How do I troubleshoot cost issues?"**
→ See [docs/06_COST_ONBOARDING.md](./docs/06_COST_ONBOARDING.md) - Section 9 (Troubleshooting)

---

**Status**: Active

**Last Updated**: 2025-11-15

**Version**: 1.0
