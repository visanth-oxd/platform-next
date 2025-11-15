# Cost Data Flow: Visual Guide

**Purpose**: Visual representation of how cost data flows from abstraction through onboarding to deployment and tracking.

---

## 1. Complete End-to-End Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      COST METADATA ABSTRACTION LAYER                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  cost-profiles.yaml         alert-policies.yaml      cost-center-mappings.yaml
│  ┌────────────────┐         ┌─────────────────┐      ┌──────────────────┐   │
│  │ Size-based cost│         │ Alert Thresholds│      │ CC-XXXXX codes  │   │
│  │ estimates      │         │ Channels        │      │ Team mappings   │   │
│  │ • Small: $150  │         │ • 50% → Info    │      │ • CC-12345      │   │
│  │ • Large: $1000 │         │ • 80% → Warning │      │ • CC-20001      │   │
│  │ Replicas/env   │         │ • 100% → Critical       │ • CC-30001      │   │
│  │ Resources      │         │ Frequency       │      │ Department map  │   │
│  └────────┬────────┘         └────────┬────────┘      └────────┬─────────┘   │
│           │                          │                        │             │
│  budget-policy.yaml           standard-budget-policy.yaml                   │
│  ┌──────────────────┐         ┌──────────────────────┐                     │
│  │ Per-size ranges  │         │ Budget ranges        │                     │
│  │ • Small: $50-500 │         │ • Min/Max per size   │                     │
│  │ • Large: $500-10K│         │ Escalation rules     │                     │
│  │ Env multipliers  │         │ • Need approval >10K │                     │
│  │ • Int: 10%       │         │ • Need CFO >30K      │                     │
│  │ • Pre: 30%       │         │ Policy enforcement   │                     │
│  │ • Prod: 100%     │         └──────────────────────┘                     │
│  └─────────────────┘                                                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                        BACKSTAGE ONBOARDING FORM                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Developer fills form:                                                     │
│  ┌─────────────────────────────────────────────────────────────┐          │
│  │ Service Basics:                                             │          │
│  │  • Name: payment-service                                    │          │
│  │  • Archetype: api-service ──→ Query cost-profiles ──→       │          │
│  │  • Profile: standard           "Est: $1000/month"           │          │
│  │  • Size: large ────────────→ Query policy ranges ──→        │          │
│  │                              "Budget range: $500-10K"       │          │
│  │ COST SECTION (MANDATORY):                                   │          │
│  │  • Cost Center: [Query cost-center-mappings → CC-12345]    │          │
│  │  • Cost Owner: john.doe@company.com                        │          │
│  │  • Business Unit: retail-banking                           │          │
│  │  • Budget Prod: $5000 (suggested: $1000 + 30% = $1300)    │          │
│  │  • Alert Policy: [Query alert-policies → standard-alerts] │          │
│  │ CONFIRMATION                                               │          │
│  └─────────────────────────────────────────────────────────────┘          │
│                                  ↓                                         │
│  Developer clicks Submit → Backstage generates TWO PRs                     │
│                            (Service + Cost Config)                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                      DUAL PR CREATION & VALIDATION                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PR #1: kustomize/catalog/services.yaml          PR #2: cost-config/services/
│  ┌──────────────────────────────┐                ┌──────────────────────┐  │
│  │ - name: payment-service      │                │ ServiceCostConfig    │  │
│  │   archetype: api-service     │                │ metadata:            │  │
│  │   profile: standard          │                │   name: payment...   │  │
│  │   size: large                │                │ spec:                │  │
│  │   team: payments-team        │                │   costAllocation:    │  │
│  │   costConfigRef:             │                │     owner: john...   │  │
│  │     name: payment-service... │                │     costCenter: CC.. │  │
│  │                              │                │   budgetOverrides:   │  │
│  └───────────┬──────────────────┘                │     prod: 5000       │  │
│              │                                    │   alertPolicy: ...   │  │
│              ↓                                    │                      │  │
│  Validation:                                      └──────────┬───────────┘  │
│  • Service schema valid                                     │              │
│  • Profile exists                                          ↓              │
│  • Size valid                                   Validation:             │
│  • costConfigRef found                          • Cost center exists    │
│  • Team exists                                  • Budget in ranges      │
│  • Both PRs linked                              • Owner email valid     │
│                                                  • Alert policy exists   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                    BOTH PRs MERGED → MANIFEST GENERATION                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GitHub Actions triggered: generate-kz-v3.sh                               │
│                                                                              │
│  Script loads and MERGES:                                                 │
│                                                                              │
│  services.yaml                cost-config/payment-service.yaml           │
│  ┌──────────────────────┐     ┌─────────────────────────────────────┐  │
│  │ name: payment-service│     │ budgets: {prod: 5000}               │  │
│  │ archetype: api       │ +   │ costAllocation: {owner, costCenter} │  │
│  │ profile: standard    │     │ alertPolicy: standard-alerts        │  │
│  │ size: large          │     │ optimization: {rightSizing,         │  │
│  │ team: payments-team  │     │   autoScaling, spotInstances}      │  │
│  └──────────────────────┘     └─────────────────────────────────────┘  │
│           ↓ + ↓                                                            │
│  cost-profiles.yaml (Query for size=large, profile=standard)              │
│  ┌───────────────────────────────────────────────────────┐               │
│  │ costBySize:                                           │               │
│  │   large:                                              │               │
│  │     baselineResources: {cpu: 2, memory: 2Gi}         │               │
│  │     replicas: {prod: 8}                               │               │
│  └───────────────────────────────────────────────────────┘               │
│                                                                            │
│  MERGE INTO KUSTOMIZE:                                                   │
│  ┌──────────────────────────────────────────────────────┐                │
│  │ commonLabels:                                        │                │
│  │   cost.service: payment-service                      │                │
│  │   cost.team: payments-team                           │                │
│  │   cost.costCenter: CC-12345          (from cost-cfg) │                │
│  │   cost.owner: john.doe@company.com   (from cost-cfg) │                │
│  │   cost.budget: "5000"                (from cost-cfg) │                │
│  │   cost.businessUnit: retail-banking  (from cost-cfg) │                │
│  │                                                       │                │
│  │ replicas: 8                          (from profile)  │                │
│  │ resources:                           (from profile)  │                │
│  │   requests: {cpu: 2, memory: 2Gi}                    │                │
│  │   limits: {cpu: 4, memory: 4Gi}                      │                │
│  └──────────────────────────────────────────────────────┘                │
│                                                                            │
│  RUN: kubectl kustomize build → Generate final manifests                 │
│                                                                            │
│  RESULT: Manifests with cost labels + resource settings committed to Git│
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                      APPTIO SYNC (PARALLEL PROCESS)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trigger: cost-config/payment-service.yaml merged to main                  │
│                                                                              │
│  Apptio Sync Service (Cloud Function or K8s Service)                       │
│  ┌────────────────────────────────────────────────────────┐               │
│  │ 1. Read: cost-config/payment-service.yaml              │               │
│  │    Extract: budgets, alerts, owner, cost center        │               │
│  │                                                          │               │
│  │ 2. Create budgets in Apptio:                            │               │
│  │    POST /api/budgets {                                 │               │
│  │      name: "payment-service-prod",                     │               │
│  │      amount: 5000,                                     │               │
│  │      filters: {cost.service: "payment-service"},       │               │
│  │      owner: "john.doe@company.com"                     │               │
│  │    }                                                    │               │
│  │                                                          │               │
│  │ 3. Configure alerts in Apptio:                          │               │
│  │    • 50% threshold  → Teams: #team-payments (once)     │               │
│  │    • 80% threshold  → Teams: #finops (daily)           │               │
│  │    • 100% threshold → Teams: #leadership + PagerDuty   │               │
│  │                                                          │               │
│  │ 4. Store mapping:                                       │               │
│  │    cost-center: CC-12345 ← payment-service             │               │
│  │                                                          │               │
│  └────────────────────────────────────────────────────────┘               │
│                                                                            │
│  RESULT: Service budgets & alerts ready in Apptio                        │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT (HARNESS)                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Developer triggers deployment:                                            │
│  1. Harness fetches manifests from Git                                    │
│     (Already have cost.* labels from generation phase)                    │
│                                                                            │
│  2. Deploy to Kubernetes cluster                                          │
│     kubectl apply -f manifests/payment-service/prod/euw1/generated.yaml  │
│                                                                            │
│  3. Kubernetes resources created with labels:                             │
│     Deployment:                                                           │
│       labels:                                                             │
│         cost.service: payment-service ✓                                  │
│         cost.team: payments-team ✓                                       │
│         cost.costCenter: CC-12345 ✓                                      │
│         cost.owner: john.doe@company.com ✓                              │
│         cost.budget: "5000" ✓                                            │
│                                                                            │
│     Pods (inherited labels):                                              │
│       All 8 pods have the same cost.* labels                             │
│                                                                            │
│  4. Labels flow to GCP Billing (24 hours)                                │
│  5. Costs appear in Apptio (48 hours)                                    │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                    COST TRACKING & MONITORING (APPTIO)                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Daily/Weekly:                                                             │
│  • Costs appear in Apptio dashboard                                       │
│  • Budget tracking: Actual spend vs Budgeted $5000                        │
│  • Alerts fire:                                                           │
│    - 50% ($2500) → Team notification                                    │
│    - 80% ($4000) → Finance notification                                 │
│    - 100% ($5000) → Leadership + PagerDuty                             │
│                                                                            │
│  Cost breakdown by labels:                                                │
│  • By service: payment-service: $4200/mo                                 │
│  • By team: payments-team: $12000/mo                                    │
│  • By cost center: CC-12345: $45000/mo                                  │
│  • By environment: prod: $4200, pre: $1800, int: $600                  │
│                                                                            │
│  Reports for Finance:                                                     │
│  • Chargeback by cost center (CC-12345 charge $4200 to Retail Banking) │
│  • Forecasting based on trends                                          │
│  • Optimization recommendations                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Transformation at Each Step

```
ABSTRACTION LAYER         →  BACKSTAGE FORM        →  SERVICE CATALOG
─────────────────────────────────────────────────────────────────────
cost-profiles.yaml            User enters:          services.yaml:
├─ size: large                ├─ service name       ├─ name: payment-service
├─ cpu: 2                     ├─ archetype: api     ├─ archetype: api-service
├─ memory: 2Gi        ────→   ├─ profile: standard  ├─ profile: standard
├─ replicas.prod: 8  │        ├─ size: large    ───→├─ size: large
└─ est: $1000        │        └─ COST SECTION       ├─ team: payments-team
                     │          Backstage queries   └─ costConfigRef: ...
cost-center-mappings.yaml │   ├─ Profile: $1000
├─ CC-12345: Retail  │        ├─ Range: $500-10K
├─ Team: Finance     ├─→      ├─ Cost centers: [CC-*]
└─ Services: [...]   │        ├─ Alert policies: [standard-alerts]
                     │        └─ Policy rules: Yes/No enforcement
alert-policies.yaml  │
├─ 50%: Info    ─────┤  Generated PRs: ┌─────────────┬──────────────┐
├─ 80%: Warning      │                  │ services.yaml │ cost-config/ │
└─ 100%: Critical    │                  │               │ payment...   │
                     │                  └─────────────┴──────────────┘
budget-policy.yaml   │
└─ Range: $50-10K ───┘


COST CONFIG              →  MANIFEST GENERATION  →  DEPLOYED MANIFESTS
─────────────────────────────────────────────────────────────────────────
cost-config/payment.yaml    generate-kz-v3.sh     Generated K8s YAML:
├─ owner: john.doe                                ├─ apiVersion: apps/v1
├─ costCenter: CC-12345 ──→  Load & merge    ──→  ├─ kind: Deployment
├─ budget.prod: 5000          ├─ services.yaml   ├─ labels:
└─ alerts: standard-alerts    ├─ cost-profiles   │  ├─ cost.service: payment...
                              ├─ cost-config    │  ├─ cost.costCenter: CC-12345
cost-profiles/               │  └─ merges       │  ├─ cost.owner: john...
├─ cpu: 2                    │                  │  └─ cost.budget: "5000"
├─ memory: 2Gi        ───→   Outputs:           ├─ spec:
├─ replicas: 8              ├─ kustomization   │  ├─ replicas: 8
└─ resources: ...           │  ├─ commonLabels │  ├─ resources:
                            │  ├─ replicas     │  │  ├─ requests:
                            │  └─ patches      │  │  │  ├─ cpu: "2"
                            │                  │  │  │  └─ memory: "2Gi"
                            └─ commits to Git  │  │  └─ limits: {...}
                                              └─ ...
                                              └─ COMPLETE: Ready for deploy
```

---

## 3. Key Data Mapping Table

```
Source                          → Transformation              → Destination
─────────────────────────────────────────────────────────────────────────────

ABSTRACTIONS:

cost-profiles.yaml              Queries by:                   Backstage Form
  size: large                     archetype: api-service        Suggested budget: $1300
  estimate: $1000               + profile: standard            (est + 30% buffer)

alert-policies.yaml             Referenced by:                cost-config
  standard-alerts               alertPolicy: standard-alerts    Thresholds & channels

cost-center-mappings.yaml       Dropdown list in:             cost-config
  CC-12345: Retail Banking      Cost Center selection          Selected: CC-12345

CATALOG:

services.yaml                   Merged with:                   Kustomize Build
  archetype: api-service        cost-config/payment-service    commonLabels:
  profile: standard             + cost-profiles               cost.service: payment...
  size: large                   + environment override         Replicas: 8
  team: payments-team           + budget selection            Resources: cpu: 2...

COST CONFIG:

cost-config/payment.yaml        Merged with:                   Apptio Sync
  owner: john.doe               Cost Center mapping            Budget created:
  costCenter: CC-12345          + alertPolicy details          name: payment-service-prod
  budget.prod: 5000             + Apptio API schema            amount: 5000
  alerts: standard-alerts                                      Alerts configured:
                                                               50%, 80%, 100%

MANIFESTS:

Generated deployment.yaml       Deployed via:                  GCP Billing
  cost.service: payment...      Harness                        Labels attached to resources
  cost.costCenter: CC-12345     kubectl apply                  Cost allocated by labels
  cost.budget: "5000"           (labels on pods)               (24hr delay)

GCP BILLING:                    Ingested by:                   Apptio Dashboard
  Labels + Costs                Apptio (auto)                  Service: payment-service
  payment-service: $4200        (48hr delay)                   Cost Center: CC-12345
  CC-12345: $45000                                             Budget: $5000
  payments-team: $12000                                        Actual: $4200
                                                               Status: 84% of budget
```

---

## 4. Layering & Separation of Concerns

```
LAYER 1: ABSTRACTION (Reusable Templates)
├─ cost-profiles.yaml          ← Maintained by: Platform Team
├─ alert-policies.yaml         ← Maintained by: Platform Team
├─ cost-center-mappings.yaml   ← Maintained by: Finance + Platform
└─ budget-policy.yaml          ← Maintained by: Finance + Platform

        ↓ REFERENCED BY

LAYER 2: CONFIGURATION (Per-Service)
├─ services.yaml               ← Maintained by: Service Teams
├─ cost-config/{service}.yaml  ← Maintained by: Service Teams + Finance
└─ Appplication code & deployment specs

        ↓ PROCESSED BY

LAYER 3: GENERATION (Automation)
├─ generate-kz-v3.sh           ← Maintained by: Platform Team
├─ sync-to-apptio.py           ← Maintained by: Platform Team
└─ Backstage templates         ← Maintained by: Platform Team

        ↓ PRODUCES

LAYER 4: EXECUTION (Deployed State)
├─ Kustomize manifests with cost labels
├─ Apptio budgets & alerts
├─ Kubernetes resources with labels
└─ Cost tracking in Apptio

        ↓ MONITORED BY

LAYER 5: OBSERVABILITY
├─ Cost dashboards in Apptio
├─ Budget tracking & alerts
├─ Chargeback reports
└─ FinOps metrics & trends
```

---

## 5. Decision Flow in Manifest Generation

```
"Which values go into the manifest?"

                    ┌─ Query services.yaml
                    │  ├─ archetype: api-service
                    │  ├─ profile: standard
                    │  ├─ size: large
                    │  └─ team: payments-team
                    │
Service Name ────→  ├─ Query cost-config/{service}.yaml
payment-service    │  ├─ owner: john.doe
                    │  ├─ costCenter: CC-12345
                    │  ├─ budget.prod: 5000
                    │  └─ businessUnit: retail-banking
                    │
                    └─ Query cost-profiles.yaml for (api-service, standard, large)
                       ├─ cpu: 2.0
                       ├─ memory: 2Gi
                       └─ replicas.prod: 8


Generate manifests with:
├─ Labels from cost-config:
│  ├─ cost.service: payment-service (from: SERVICE NAME)
│  ├─ cost.team: payments-team (from: services.yaml)
│  ├─ cost.owner: john.doe (from: cost-config)
│  ├─ cost.costCenter: CC-12345 (from: cost-config)
│  ├─ cost.budget: "5000" (from: cost-config)
│  └─ cost.businessUnit: retail-banking (from: cost-config)
│
├─ Resources from cost-profile:
│  ├─ replicas: 8 (from: cost-profiles.yaml)
│  ├─ cpu: 2.0 (from: cost-profiles.yaml)
│  └─ memory: 2Gi (from: cost-profiles.yaml)
│
└─ Overrides from environment/region specific settings
   ├─ Multi-region affinity
   ├─ Zone-specific constraints
   └─ Environment-specific versions
```

---

## 6. Cost Data Dependencies

```
What depends on what?

Apptio Budgets
    ↑
    └─ cost-config/{service}.yaml
         ↑
         └─ Service definition (services.yaml)
         ├─ Cost center mappings
         └─ Budget policy


Kubernetes Manifests
    ↑
    └─ Kustomization.yaml (with labels)
         ↑
         ├─ services.yaml (archetype, profile, size)
         ├─ cost-config/{service}.yaml (labels)
         ├─ cost-profiles.yaml (resources, replicas)
         └─ environment-specific settings


Backstage Form
    ↑
    └─ Queries at form load time:
         ├─ cost-profiles.yaml → Shows estimates
         ├─ cost-center-mappings.yaml → Dropdown list
         ├─ alert-policies.yaml → Policy selection
         └─ budget-policy.yaml → Budget ranges


Cost Tracking
    ↑
    └─ GCP Billing (labeled resources)
         ↑
         └─ Kubernetes deployment (with cost.* labels)
              ↑
              └─ Generated manifests from Kustomize
                   ↑
                   └─ Merged: services.yaml + cost-config + cost-profiles
```

---

**Summary**: Each layer builds on the previous, with clear data dependencies and transformations at each step.

