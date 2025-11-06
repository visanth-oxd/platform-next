# Kustomize Config Management Repository

This repository contains the Kustomize-based configuration management system for deploying Kubernetes workloads across multiple environments and regions.

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

