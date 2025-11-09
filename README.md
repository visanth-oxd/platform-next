# Platform-Next: Kubernetes Config Management Platform

This repository contains the Kustomize-based configuration management system for deploying Kubernetes workloads across multiple environments and regions.

**Key Features**:
- 🚀 **Self-Service**: Onboard services via Backstage in 5 minutes
- 📦 **Catalog-Driven**: Single source of truth for all services
- 🔄 **GitOps**: All configuration versioned in Git
- 🎯 **Enterprise CD**: Harness pipelines with multi-gate approvals
- 🌍 **Multi-Region**: Active-passive deployment (euw1 primary, euw2 DR)
- 🏗️ **Composable**: Archetypes + Components = flexible configurations

---

## Documentation

📚 **Start here for detailed design**:

- [00_ARCHITECTURE_DECISION.md](docs/00_ARCHITECTURE_DECISION.md) - Why we chose this approach
- [01_BACKSTAGE_DESIGN.md](docs/01_BACKSTAGE_DESIGN.md) - Service onboarding via Backstage
- [02_KUSTOMIZE_CONFIG_MANAGEMENT.md](docs/02_KUSTOMIZE_CONFIG_MANAGEMENT.md) - Kustomize layer design
- [03_HARNESS_INTEGRATION_DESIGN.md](docs/03_HARNESS_INTEGRATION_DESIGN.md) - Harness CD pipelines

---

## Quick Start

### For Developers: Onboard a New Service

1. **Open Backstage Portal**
   ```
   https://backstage.company.com → Create → Kubernetes Service
   ```

2. **Fill the Form** (5 fields):
   - Service Name: `my-service`
   - Archetype: `api`
   - Profile: `public-api`
   - Size: `medium`
   - Environments: `int, pre, prod`

3. **Click Create**
   - Manifests auto-generated
   - Harness pipeline auto-created
   - Service ready in 5-10 minutes

4. **Deploy Your Service**
   - Open Harness Console → Pipelines → `my-service-cd`
   - Click "Run Pipeline"
   - Enter image tag: `v1.0.0`
   - Click "Run"

**Done!** Service deployed to Kubernetes.

---

### For Platform Team: Update Configuration

1. **Update Catalog or Archetypes**
   ```bash
   vim kustomize/catalog/services.yaml
   # or
   vim kustomize/archetype/api/deployment.yaml
   ```

2. **Commit to Git**
   ```bash
   git add .
   git commit -m "Update API archetype resources"
   git push
   ```

3. **CI Auto-Runs**
   - Detects changes
   - Regenerates affected manifests
   - Commits to `generated/` directory

4. **Next Deployment Uses New Config**
   - Harness fetches latest from Git
   - No manual sync needed
   - GitOps auto-sync

## Structure

```
kustomize/
  cb-base/              # Organization-wide base configuration
  archetype/            # Workload type templates (api, listener, scheduler, streaming, job)
  components/           # Optional feature components
  envs/                 # Environment overlays (int-stable, pre-stable, prod)
  regions/              # Region overlays (euw1, euw2)
  catalog/              # Service catalog and configuration metadata
  kustomizeconfig/      # Kustomize configuration (varreference)

scripts/
  generate-kz.sh        # Generator script for creating per-service kustomizations
  gar.sh                # GAR image tag resolution utility

artifacts/              # Generated manifests and deployment records (gitignored)
```

## Quick Start

### Generate a Kustomize workspace for a service

```bash
./scripts/generate-kz.sh <SERVICE> <ENV> <REGION> [TAG]
```

Example:
```bash
./scripts/generate-kz.sh account-service int-stable euw1
```

### Build and validate

```bash
cd tmp/account-service/int-stable/euw1
kustomize build . > out.yaml
kubeconform -strict -summary out.yaml
```

### Apply to cluster

```bash
kubectl apply -f namespace.yaml
kubectl apply -f out.yaml
kubectl -n <namespace> rollout status deploy/account-service
```

## Catalog Files

- `catalog/services.yaml` - Service definitions and per-environment overrides
- `catalog/channels.yaml` - Channel to Git ref mapping
- `catalog/env-pins.yaml` - Environment to Git ref pinning
- `catalog/regions.yaml` - Region metadata and keys
- `catalog/region-pins.yaml` - Optional region-specific ref pinning
- `catalog/policies.yaml` - Validation guardrails

## Components

Available components:
- `ingress` - Ingress and routing configuration
- `retry` - HTTP retry policies
- `circuit-breaker` - Circuit breaker and outlier detection
- `mtls` - Mutual TLS configuration
- `hpa` - Horizontal Pod Autoscaler
- `security-hardening` - Enhanced security settings
- `serviceaccount-rbac` - Extended RBAC
- `network-policy` - Network policy rules
- `pdb` - Pod Disruption Budget
- `topology` - Topology spread and affinity
- `config` - ConfigMap generators
- `secrets` - Secret generators

## Multi-Region Support

The system supports failover-only multi-region deployments:
- Primary region (euw1) receives traffic normally
- DR region (euw2) is deployed but receives traffic only during failover
- Traffic routing is managed externally (e.g., Apigee)

## Versioning

Configuration is versioned using Git refs (tags/commits):
- Channels map to refs (stable, next)
- Environments can be pinned to specific refs
- Regions can optionally override environment pins

## License

[Your License Here]

