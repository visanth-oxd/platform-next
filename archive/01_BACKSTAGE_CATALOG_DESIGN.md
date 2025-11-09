# Backstage Catalog & Service Onboarding Design

## Document Overview

**Purpose**: Define how Backstage is used for service onboarding and catalog management

**Scope**: 
- Backstage software templates
- Catalog entity structure
- Integration with platform-next repo
- Developer experience

---

## Table of Contents

1. [Why Backstage](#why-backstage)
2. [Software Template Design](#software-template-design)
3. [Catalog Entity Structure](#catalog-entity-structure)
4. [Integration Architecture](#integration-architecture)
5. [User Flows](#user-flows)
6. [Plugins & Extensions](#plugins--extensions)
7. [Implementation Guide](#implementation-guide)

---

## 1. Why Backstage

### Rationale for Using Backstage

**Problem Without Backstage**:
- Custom UI development (6-8 weeks)
- Maintenance burden
- Duplicate features (catalog, templates, integrations)
- Reinventing the wheel

**Benefits of Backstage**:
- ✅ **Already deployed** - Sunk cost, ready to use
- ✅ **Software Templates** - Declarative form builder (no coding)
- ✅ **Service Catalog** - Built-in discovery and documentation
- ✅ **Plugin Ecosystem** - Kubernetes, Harness, GitHub, PagerDuty integrations
- ✅ **Industry Standard** - Used by Spotify, Netflix, American Airlines
- ✅ **No UI Development** - Forms defined in YAML
- ✅ **Extensible** - Custom plugins if needed

### What Backstage Provides

| Feature | How We Use It | Alternative Cost |
|---------|---------------|------------------|
| **Service Catalog** | Searchable list of all services | 4 weeks dev |
| **Software Templates** | Service onboarding forms | 6 weeks dev |
| **Kubernetes Plugin** | Pod status, logs, metrics | 4 weeks dev |
| **Harness Plugin** | Deployment history, links | 2 weeks dev |
| **GitHub Plugin** | PR status, code links | 2 weeks dev |
| **TechDocs** | Auto-generated documentation | 3 weeks dev |

**Total savings**: ~21 weeks of development work

---

## 2. Software Template Design

### What is a Software Template?

**Backstage Software Template** = Declarative form + automated actions

**Components**:
1. **Parameters** - Form fields (UI)
2. **Steps** - Actions to execute (API calls, Git operations)
3. **Output** - Links and information to show user

### Template: `kubernetes-service`

**File**: `backstage/templates/kubernetes-service.yaml`

<function_calls>
<invoke name="Read">
<parameter name="path">/Users/visanth/Documents/copilot/platform-next/BACKSTAGE_HARNESS_INTEGRATION.md
