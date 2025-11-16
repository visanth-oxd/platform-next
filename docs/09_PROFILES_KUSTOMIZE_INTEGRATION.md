# Cost & Monitoring Profiles Integration with Kustomize

**Status**: ACTIVE - Integration Guide

**Document Type**: Technical Integration Specification

**Audience**: Platform engineers implementing profile expansion, CI/CD maintainers

**Date**: 2025-11-16

---

## Executive Summary

This document describes how **cost profiles** and **monitoring profiles** integrate with the Kustomize-based manifest generation system in platform-next. Both profiles use the same expansion pattern and are injected into generated manifests during CI/CD.

**Key Integration Points**:
1. ✅ **Profile Expansion** - Expand profiles at validation time (CI/CD)
2. ✅ **Label Injection** - Cost labels injected into `commonLabels` in kustomization.yaml
3. ✅ **Resource Generation** - Monitoring resources (ServiceMonitor, PrometheusRule) generated as separate files
4. ✅ **Unified Workflow** - Single script handles both cost and monitoring expansion

---

## 1. Integration Architecture

### 1.1 Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Service Catalog (services.yaml)                              │
├─────────────────────────────────────────────────────────────┤
│ - name: payment-service                                      │
│   costProfile: standard-api-cost                             │
│   cost:                                                       │
│     costCenter: "CC-12345"                                    │
│     businessUnit: "retail-banking"                           │
│     costOwner: "alice@company.com"                            │
│   monitoringProfile: api-observability                       │
│   monitoring:                                                 │
│     prometheus: true                                          │
│     dynatrace: true                                           │
│     overrides:                                                │
│       prod:                                                   │
│         sloAvailability: 99.99                                │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Profile Expansion Engine (CI/CD - Python Script)             │
├─────────────────────────────────────────────────────────────┤
│ 1. Load service from catalog                                 │
│ 2. Load cost profile (cost-profiles.yaml)                    │
│ 3. Load monitoring profile (monitoring-profiles.yaml)        │
│ 4. Expand cost config:                                        │
│    - Calculate budgets: base × size-multiplier               │
│    - Substitute variables: {service}, {costOwner}             │
│    - Apply overrides (service, environment)                  │
│ 5. Expand monitoring config:                                 │
│    - Calculate thresholds: base × size-multiplier           │
│    - Substitute variables: {SERVICE}, {TEAM}                 │
│    - Apply environment overrides                              │
│ 6. Generate expanded config (JSON/YAML)                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Manifest Generation Script (generate-kz.sh - Enhanced)      │
├─────────────────────────────────────────────────────────────┤
│ For each service/environment/region:                         │
│                                                              │
│ 1. Load expanded config (from expansion engine)              │
│ 2. Generate kustomization.yaml:                             │
│    - Include cost labels in commonLabels                    │
│    - Include monitoring labels in commonLabels              │
│ 3. Generate monitoring resources:                           │
│    - ServiceMonitor.yaml (Prometheus scrape config)         │
│    - PrometheusRule-recording.yaml (recording rules)        │
│    - PrometheusRule-alerts.yaml (alert rules)               │
│    - Dynatrace-app-config.yaml (Dynatrace config)           │
│    - Grafana-dashboard.yaml (dashboard ConfigMap)             │
│ 4. Write all files to tmp/{SERVICE}/{ENV}/{REGION}/          │
│ 5. Run: kustomize build tmp/.../                             │
│ 6. Output: generated/{SERVICE}/{ENV}/{REGION}/manifests.yaml │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Generated Manifests (Git - Versioned)                        │
├─────────────────────────────────────────────────────────────┤
│ generated/payment-service/prod/euw1/                         │
│ ├── manifests.yaml (all resources)                           │
│ │   ├── Namespace (with cost labels)                         │
│ │   ├── Deployment (with cost labels)                        │
│ │   ├── Service (with cost labels)                            │
│ │   ├── ServiceMonitor (Prometheus)                          │
│ │   ├── PrometheusRule (recording)                           │
│ │   ├── PrometheusRule (alerts)                              │
│ │   └── ConfigMap (Dynatrace, Grafana)                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Harness Deployment                                           │
├─────────────────────────────────────────────────────────────┤
│ - Fetches manifests.yaml from Git                            │
│ - Injects image tag                                          │
│ - Deploys to Kubernetes                                      │
│ - All resources have cost labels                            │
│ - Monitoring resources active                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Enhanced Manifest Generation Script

### 2.1 Updated generate-kz.sh Structure

```bash
#!/usr/bin/env bash
set -euo pipefail

# Generate Kustomize workspace for a service
# Usage: generate-kz.sh <SERVICE> <ENV> <REGION> [TAG]

SERVICE="${1:-}"
ENV="${2:-}"
REGION="${3:-}"
TAG="${4:-}"

# ... existing setup code ...

# ================================================
# NEW: Load expanded profiles
# ================================================

# Load service from catalog
SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" "$CATALOG_DIR/services.yaml")

# Check if cost profile exists
COST_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.costProfile // ""' -)
if [[ -z "$COST_PROFILE" ]]; then
  echo "Error: Service '$SERVICE' must have costProfile defined"
  exit 1
fi

# Check if monitoring profile exists
MONITORING_PROFILE=$(echo "$SERVICE_DATA" | yq eval '.monitoringProfile // ""' -)
if [[ -z "$MONITORING_PROFILE" ]]; then
  echo "Error: Service '$SERVICE' must have monitoringProfile defined"
  exit 1
fi

# Expand profiles (calls Python expansion script)
EXPANDED_CONFIG=$(python3 "$SCRIPT_DIR/expand-profiles.py" \
  --service "$SERVICE" \
  --environment "$ENV" \
  --output /tmp/expanded-${SERVICE}-${ENV}.json)

# Extract expanded cost config
COST_LABELS=$(echo "$EXPANDED_CONFIG" | jq -r '.cost.labels')
COST_BUDGET=$(echo "$EXPANDED_CONFIG" | jq -r ".cost.budgets.${ENV}.monthly")

# Extract expanded monitoring config
MONITORING_ENABLED=$(echo "$EXPANDED_CONFIG" | jq -r '.monitoring.enabled')
PROMETHEUS_ENABLED=$(echo "$EXPANDED_CONFIG" | jq -r '.monitoring.prometheus.enabled')
DYNATRACE_ENABLED=$(echo "$EXPANDED_CONFIG" | jq -r '.monitoring.dynatrace.enabled')

# ================================================
# Generate kustomization.yaml with cost labels
# ================================================

cat > "$TMP_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/$TYPE
  - ../../../../kustomize/envs/$ENV
  - ../../../../kustomize/regions/$REGION
  - ./namespace.yaml
EOF

# Add monitoring resources if enabled
if [[ "$PROMETHEUS_ENABLED" == "true" ]]; then
  echo "  - ./monitoring/service-monitor.yaml" >> "$TMP_DIR/kustomization.yaml"
  echo "  - ./monitoring/prometheus-rules-recording.yaml" >> "$TMP_DIR/kustomization.yaml"
  echo "  - ./monitoring/prometheus-rules-alerts.yaml" >> "$TMP_DIR/kustomization.yaml"
fi

if [[ "$DYNATRACE_ENABLED" == "true" ]]; then
  echo "  - ./monitoring/dynatrace-app-config.yaml" >> "$TMP_DIR/kustomization.yaml"
fi

# Add components
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

components:
EOF

for COMP in $COMPONENTS; do
  echo "  - ../../../../kustomize/components/$COMP" >> "$TMP_DIR/kustomization.yaml"
done

# Add commonLabels with cost and monitoring labels
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

namespace: $NAMESPACE

commonLabels:
  app: $SERVICE
  env: $ENV
  region: $REGION
  tier: core
  
  # ================================================
  # COST LABELS (from expanded cost profile)
  # ================================================
EOF

# Inject cost labels from expanded config
echo "$COST_LABELS" | jq -r 'to_entries[] | "  cost.\(.key): \"\(.value)\""' >> "$TMP_DIR/kustomization.yaml"

cat >> "$TMP_DIR/kustomization.yaml" <<EOF
  cost.budget: "$COST_BUDGET"
  cost.profile: "$COST_PROFILE"
  
  # ================================================
  # MONITORING LABELS (from expanded monitoring profile)
  # ================================================
  monitoring.profile: "$MONITORING_PROFILE"
  monitoring.enabled: "$MONITORING_ENABLED"
EOF

if [[ "$PROMETHEUS_ENABLED" == "true" ]]; then
  cat >> "$TMP_DIR/kustomization.yaml" <<EOF
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
EOF
fi

# Add images and patches (existing code)
cat >> "$TMP_DIR/kustomization.yaml" <<EOF

images:
  - name: app
    newName: $IMAGE
    newTag: $TAG

patches:
EOF

# ... existing patch generation code ...

# ================================================
# NEW: Generate monitoring resources
# ================================================

if [[ "$MONITORING_ENABLED" == "true" ]]; then
  mkdir -p "$TMP_DIR/monitoring"
  
  # Generate ServiceMonitor
  if [[ "$PROMETHEUS_ENABLED" == "true" ]]; then
    python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
      --service "$SERVICE" \
      --environment "$ENV" \
      --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
      --output-dir "$TMP_DIR/monitoring" \
      --resource-type servicemonitor
    
    python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
      --service "$SERVICE" \
      --environment "$ENV" \
      --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
      --output-dir "$TMP_DIR/monitoring" \
      --resource-type prometheusrule-recording
    
    python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
      --service "$SERVICE" \
      --environment "$ENV" \
      --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
      --output-dir "$TMP_DIR/monitoring" \
      --resource-type prometheusrule-alerts
  fi
  
  # Generate Dynatrace config
  if [[ "$DYNATRACE_ENABLED" == "true" ]]; then
    python3 "$SCRIPT_DIR/generate-monitoring-resources.py" \
      --service "$SERVICE" \
      --environment "$ENV" \
      --expanded-config /tmp/expanded-${SERVICE}-${ENV}.json \
      --output-dir "$TMP_DIR/monitoring" \
      --resource-type dynatrace-config
  fi
fi

echo "Generated Kustomize workspace at: $TMP_DIR"
echo "Cost profile: $COST_PROFILE"
echo "Monitoring profile: $MONITORING_PROFILE"
```

---

## 3. Profile Expansion Script

### 3.1 expand-profiles.py

```python
#!/usr/bin/env python3
"""
Expand cost and monitoring profiles for a service.

Usage:
    expand-profiles.py --service <SERVICE> --environment <ENV> --output <FILE>
"""

import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, Any

def load_catalog(catalog_dir: Path) -> Dict[str, Any]:
    """Load services catalog."""
    with open(catalog_dir / "services.yaml") as f:
        return yaml.safe_load(f)

def load_cost_profiles(catalog_dir: Path) -> Dict[str, Any]:
    """Load cost profiles catalog."""
    with open(catalog_dir / "cost-profiles.yaml") as f:
        return yaml.safe_load(f)

def load_monitoring_profiles(catalog_dir: Path) -> Dict[str, Any]:
    """Load monitoring profiles catalog."""
    with open(catalog_dir / "monitoring-profiles.yaml") as f:
        return yaml.safe_load(f)

def load_sizes(catalog_dir: Path) -> Dict[str, Any]:
    """Load size definitions."""
    with open(catalog_dir / "sizes.yaml") as f:
        return yaml.safe_load(f)

def expand_cost_profile(
    service: Dict[str, Any],
    profile: Dict[str, Any],
    sizes: Dict[str, Any],
    environment: str
) -> Dict[str, Any]:
    """
    Expand cost profile for a service.
    
    Returns:
        Expanded cost configuration with budgets, labels, alerts
    """
    service_name = service["name"]
    service_size = service.get("size", "medium")
    cost_config = service.get("cost", {})
    
    # Get size multiplier
    size_multiplier = sizes[service_size].get("costMultiplier", 1.0)
    
    # Calculate budgets per environment
    budgets = {}
    for env in ["int-stable", "pre-stable", "prod"]:
        env_budget = profile["budgets"][env]
        base = env_budget["base"]
        scaling = env_budget.get("scaling", 1.0)
        
        # Calculate: base × scaling × size_multiplier
        monthly = base * scaling * size_multiplier
        
        # Apply service-level override if present
        if "overrides" in cost_config:
            if "service" in cost_config["overrides"]:
                service_mult = cost_config["overrides"]["service"].get("budgetMultiplier", 1.0)
                monthly *= service_mult
            
            if "environment" in cost_config["overrides"]:
                if env in cost_config["overrides"]["environment"]:
                    env_mult = cost_config["overrides"]["environment"][env].get("budgetMultiplier", 1.0)
                    monthly *= env_mult
        
        budgets[env] = {
            "monthly": round(monthly),
            "base": base,
            "scaling": scaling,
            "sizeMultiplier": size_multiplier
        }
    
    # Generate cost labels
    labels = {
        "service": service_name,
        "team": service.get("team", "unknown"),
        "environment": environment,
        "costCenter": cost_config.get("costCenter", ""),
        "businessUnit": cost_config.get("businessUnit", ""),
        "owner": cost_config.get("costOwner", ""),
        "budget": str(budgets[environment]["monthly"])
    }
    
    # Substitute variables in alerts
    alerts = []
    for alert_template in profile.get("alerts", []):
        alert = alert_template.copy()
        
        # Substitute variables in channels
        if "channels" in alert:
            channels = alert["channels"]
            if "teams" in channels:
                channels["teams"] = [
                    ch.replace("{service}", service_name)
                    for ch in channels["teams"]
                ]
            if "email" in channels:
                channels["email"] = [
                    email.replace("{costOwner}", cost_config.get("costOwner", ""))
                    for email in channels["email"]
                ]
        
        alerts.append(alert)
    
    return {
        "budgets": budgets,
        "labels": labels,
        "alerts": alerts,
        "optimization": profile.get("optimization", {})
    }

def expand_monitoring_profile(
    service: Dict[str, Any],
    profile: Dict[str, Any],
    sizes: Dict[str, Any],
    environment: str
) -> Dict[str, Any]:
    """
    Expand monitoring profile for a service.
    
    Returns:
        Expanded monitoring configuration with thresholds, SLOs, rules
    """
    service_name = service["name"]
    service_size = service.get("size", "medium")
    monitoring_config = service.get("monitoring", {})
    
    # Get size multiplier for resource thresholds
    size_multiplier = sizes[service_size].get("monitoringMultiplier", 1.0)
    
    # Calculate resource thresholds
    resource_thresholds = {}
    if "resourceThresholds" in profile:
        for resource, config in profile["resourceThresholds"].items():
            base = config["base"]
            scaled = config.get("scaled", True)
            
            if scaled:
                threshold = base * size_multiplier
            else:
                threshold = base
            
            resource_thresholds[resource] = {
                "threshold": threshold,
                "warningPercent": config.get("warningPercent", 80),
                "criticalPercent": config.get("criticalPercent", 95)
            }
    
    # Get SLOs (with environment overrides)
    slos = profile.get("slos", {}).copy()
    
    # Apply environment overrides from profile
    if "environmentOverrides" in profile:
        if environment in profile["environmentOverrides"]:
            env_overrides = profile["environmentOverrides"][environment]
            if "slos" in env_overrides:
                slos.update(env_overrides["slos"])
    
    # Apply service-level overrides
    if "overrides" in monitoring_config:
        if environment in monitoring_config["overrides"]:
            service_overrides = monitoring_config["overrides"][environment]
            if "sloAvailability" in service_overrides:
                slos["availability"] = service_overrides["sloAvailability"]
            if "sloErrorRate" in service_overrides:
                slos["errorRate"] = service_overrides["sloErrorRate"]
            if "sloLatencyP95ms" in service_overrides:
                slos["latency"]["p95Baseline"] = service_overrides["sloLatencyP95ms"]
    
    # Substitute variables in Prometheus rules
    prometheus_config = profile.get("prometheus", {}).copy()
    
    if "recordingRules" in prometheus_config:
        for rule in prometheus_config["recordingRules"]:
            rule["expr"] = rule["expr"].replace("{SERVICE}", service_name)
            rule["expr"] = rule["expr"].replace("{TEAM}", service.get("team", "unknown"))
            rule["expr"] = rule["expr"].replace("{ENVIRONMENT}", environment)
    
    if "alertRules" in prometheus_config:
        for rule in prometheus_config["alertRules"]:
            rule["expr"] = rule["expr"].replace("{SERVICE}", service_name)
            rule["expr"] = rule["expr"].replace("{TEAM}", service.get("team", "unknown"))
            rule["expr"] = rule["expr"].replace("{ENVIRONMENT}", environment)
            
            # Substitute threshold variables
            if "ERROR_RATE_THRESHOLD" in rule["expr"]:
                error_rate = slos.get("errorRate", {}).get("baselineProd", 0.1)
                rule["expr"] = rule["expr"].replace("{ERROR_RATE_THRESHOLD}", str(error_rate / 100))
            
            if "LATENCY_THRESHOLD_SECONDS" in rule["expr"]:
                latency_p95 = slos.get("latency", {}).get("p95Baseline", 500)
                rule["expr"] = rule["expr"].replace("{LATENCY_THRESHOLD_SECONDS}", str(latency_p95 / 1000))
            
            if "MEMORY_THRESHOLD_BYTES" in rule["expr"]:
                memory_mb = resource_thresholds.get("memory", {}).get("threshold", 512)
                memory_bytes = memory_mb * 1024 * 1024
                rule["expr"] = rule["expr"].replace("{MEMORY_THRESHOLD_BYTES}", str(memory_bytes))
            
            if "CPU_THRESHOLD_CORES" in rule["expr"]:
                cpu_m = resource_thresholds.get("cpu", {}).get("threshold", 500)
                cpu_cores = cpu_m / 1000
                rule["expr"] = rule["expr"].replace("{CPU_THRESHOLD_CORES}", str(cpu_cores))
            
            # Substitute variables in channels
            if "channels" in rule:
                if "teams" in rule["channels"]:
                    rule["channels"]["teams"] = [
                        ch.replace("{SERVICE}", service_name)
                        for ch in rule["channels"]["teams"]
                    ]
    
    # Substitute variables in Dynatrace config
    dynatrace_config = profile.get("dynatrace", {}).copy()
    
    if "requestAttributes" in dynatrace_config.get("application", {}):
        for attr in dynatrace_config["application"]["requestAttributes"]:
            if "source" in attr and "kubernetesLabel" in attr["source"]:
                # Labels will be available at runtime
                pass
    
    return {
        "enabled": monitoring_config.get("prometheus", False) or monitoring_config.get("dynatrace", False),
        "prometheus": {
            "enabled": monitoring_config.get("prometheus", False),
            "serviceMonitor": prometheus_config.get("serviceMonitor", {}),
            "recordingRules": prometheus_config.get("recordingRules", []),
            "alertRules": prometheus_config.get("alertRules", [])
        },
        "dynatrace": {
            "enabled": monitoring_config.get("dynatrace", False),
            "application": dynatrace_config.get("application", {})
        },
        "slos": slos,
        "resourceThresholds": resource_thresholds
    }

def main():
    parser = argparse.ArgumentParser(description="Expand cost and monitoring profiles")
    parser.add_argument("--service", required=True, help="Service name")
    parser.add_argument("--environment", required=True, help="Environment (int-stable, pre-stable, prod)")
    parser.add_argument("--output", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    # Load catalogs
    repo_root = Path(__file__).parent.parent
    catalog_dir = repo_root / "kustomize" / "catalog"
    
    catalog = load_catalog(catalog_dir)
    cost_profiles = load_cost_profiles(catalog_dir)
    monitoring_profiles = load_monitoring_profiles(catalog_dir)
    sizes = load_sizes(catalog_dir)
    
    # Find service
    service = next((s for s in catalog["services"] if s["name"] == args.service), None)
    if not service:
        raise ValueError(f"Service '{args.service}' not found in catalog")
    
    # Expand cost profile
    cost_profile_name = service.get("costProfile")
    if not cost_profile_name:
        raise ValueError(f"Service '{args.service}' missing costProfile")
    
    cost_profile = cost_profiles["costProfiles"][cost_profile_name]
    expanded_cost = expand_cost_profile(service, cost_profile, sizes, args.environment)
    
    # Expand monitoring profile
    monitoring_profile_name = service.get("monitoringProfile")
    if not monitoring_profile_name:
        raise ValueError(f"Service '{args.service}' missing monitoringProfile")
    
    monitoring_profile = monitoring_profiles["monitoringProfiles"][monitoring_profile_name]
    expanded_monitoring = expand_monitoring_profile(service, monitoring_profile, sizes, args.environment)
    
    # Combine expanded configs
    expanded_config = {
        "service": args.service,
        "environment": args.environment,
        "cost": expanded_cost,
        "monitoring": expanded_monitoring
    }
    
    # Write output
    with open(args.output, "w") as f:
        json.dump(expanded_config, f, indent=2)
    
    print(f"✅ Expanded profiles for {args.service} in {args.environment}")
    print(f"   Cost budget: ${expanded_cost['budgets'][args.environment]['monthly']}/month")
    print(f"   Monitoring: {'enabled' if expanded_monitoring['enabled'] else 'disabled'}")

if __name__ == "__main__":
    main()
```

---

## 4. Monitoring Resource Generation

### 4.1 generate-monitoring-resources.py

```python
#!/usr/bin/env python3
"""
Generate Kubernetes monitoring resources from expanded monitoring config.

Usage:
    generate-monitoring-resources.py --service <SERVICE> --environment <ENV> \
        --expanded-config <FILE> --output-dir <DIR> --resource-type <TYPE>
"""

import argparse
import json
import yaml
from pathlib import Path

def generate_service_monitor(service: str, env: str, config: dict, output_dir: Path):
    """Generate ServiceMonitor resource."""
    prometheus = config["monitoring"]["prometheus"]
    
    servicemonitor = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": f"{service}-monitor",
            "namespace": f"{env}-{service}-{env}",
            "labels": {
                "app": service,
                "monitoring.profile": config.get("monitoringProfile", ""),
                "environment": env
            }
        },
        "spec": {
            "selector": {
                "matchLabels": {
                    "app": service
                }
            },
            "endpoints": [{
                "port": prometheus["serviceMonitor"].get("port", "http"),
                "path": prometheus["serviceMonitor"].get("path", "/metrics"),
                "interval": prometheus["serviceMonitor"].get("scrapeInterval", "30s"),
                "scrapeTimeout": prometheus["serviceMonitor"].get("scrapeTimeout", "10s")
            }]
        }
    }
    
    with open(output_dir / "service-monitor.yaml", "w") as f:
        yaml.dump(servicemonitor, f, default_flow_style=False)

def generate_prometheus_rules_recording(service: str, env: str, config: dict, output_dir: Path):
    """Generate PrometheusRule with recording rules."""
    prometheus = config["monitoring"]["prometheus"]
    
    rules = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": f"{service}-recording-rules",
            "namespace": f"{env}-{service}-{env}",
            "labels": {
                "app": service,
                "prometheus": "kube-prometheus",
                "role": "recording"
            }
        },
        "spec": {
            "groups": [{
                "name": f"{service}_recording",
                "interval": "30s",
                "rules": prometheus["recordingRules"]
            }]
        }
    }
    
    with open(output_dir / "prometheus-rules-recording.yaml", "w") as f:
        yaml.dump(rules, f, default_flow_style=False)

def generate_prometheus_rules_alerts(service: str, env: str, config: dict, output_dir: Path):
    """Generate PrometheusRule with alert rules."""
    prometheus = config["monitoring"]["prometheus"]
    
    rules = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": f"{service}-alert-rules",
            "namespace": f"{env}-{service}-{env}",
            "labels": {
                "app": service,
                "prometheus": "kube-prometheus",
                "role": "alerting"
            }
        },
        "spec": {
            "groups": [{
                "name": f"{service}_alerts",
                "interval": "30s",
                "rules": prometheus["alertRules"]
            }]
        }
    }
    
    with open(output_dir / "prometheus-rules-alerts.yaml", "w") as f:
        yaml.dump(rules, f, default_flow_style=False)

def generate_dynatrace_config(service: str, env: str, config: dict, output_dir: Path):
    """Generate Dynatrace application config ConfigMap."""
    dynatrace = config["monitoring"]["dynatrace"]
    
    app_config = {
        "metadata": {
            "name": service,
            "environment": env,
            "team": config.get("team", "unknown")
        },
        "monitoring": dynatrace["application"]
    }
    
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{service}-dynatrace-config",
            "namespace": f"{env}-{service}-{env}",
            "labels": {
                "app": service,
                "monitoring.profile": config.get("monitoringProfile", "")
            }
        },
        "data": {
            "application.json": json.dumps(app_config, indent=2)
        }
    }
    
    with open(output_dir / "dynatrace-app-config.yaml", "w") as f:
        yaml.dump(configmap, f, default_flow_style=False)

def main():
    parser = argparse.ArgumentParser(description="Generate monitoring resources")
    parser.add_argument("--service", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--expanded-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resource-type", required=True,
                       choices=["servicemonitor", "prometheusrule-recording",
                               "prometheusrule-alerts", "dynatrace-config"])
    
    args = parser.parse_args()
    
    # Load expanded config
    with open(args.expanded_config) as f:
        config = json.load(f)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate requested resource
    if args.resource_type == "servicemonitor":
        generate_service_monitor(args.service, args.environment, config, output_dir)
    elif args.resource_type == "prometheusrule-recording":
        generate_prometheus_rules_recording(args.service, args.environment, config, output_dir)
    elif args.resource_type == "prometheusrule-alerts":
        generate_prometheus_rules_alerts(args.service, args.environment, config, output_dir)
    elif args.resource_type == "dynatrace-config":
        generate_dynatrace_config(args.service, args.environment, config, output_dir)
    
    print(f"✅ Generated {args.resource_type} for {args.service}")

if __name__ == "__main__":
    main()
```

---

## 5. Example Generated kustomization.yaml

### 5.1 Complete Example with Cost and Monitoring

```yaml
# generated/payment-service/prod/euw1/kustomization.yaml

apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/api
  - ../../../../kustomize/envs/prod
  - ../../../../kustomize/regions/euw1
  - ./namespace.yaml
  
  # Monitoring resources (generated from monitoring profile)
  - ./monitoring/service-monitor.yaml
  - ./monitoring/prometheus-rules-recording.yaml
  - ./monitoring/prometheus-rules-alerts.yaml
  - ./monitoring/dynatrace-app-config.yaml

components:
  - ../../../../kustomize/components/ingress
  - ../../../../kustomize/components/hpa
  - ../../../../kustomize/components/pdb
  - ../../../../kustomize/components/mtls

namespace: prod-payment-service-euw1-stable

commonLabels:
  # Functional labels
  app: payment-service
  env: prod
  region: euw1
  tier: core
  
  # ================================================
  # COST LABELS (from expanded cost profile)
  # ================================================
  cost.service: payment-service
  cost.team: payments-team
  cost.environment: prod
  cost.costCenter: CC-12345
  cost.businessUnit: retail-banking
  cost.owner: alice@company.com
  cost.budget: "6000"
  cost.profile: standard-api-cost
  
  # ================================================
  # MONITORING LABELS (from expanded monitoring profile)
  # ================================================
  monitoring.profile: api-observability
  monitoring.enabled: "true"
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"

images:
  - name: app
    newName: gcr.io/project/payment-service
    newTag: v2.3.1

patches:
  - path: resources-patch.yaml
  - path: hpa-patch.yaml
  - path: ingress-patch.yaml
```

---

## 6. CI/CD Integration

### 6.1 Updated GitHub Actions Workflow

```yaml
# .github/workflows/generate-manifests.yml

name: Generate K8s Manifests with Profiles

on:
  push:
    branches: [main]
    paths:
      - 'kustomize/catalog/services.yaml'
      - 'kustomize/catalog/cost-profiles.yaml'
      - 'kustomize/catalog/monitoring-profiles.yaml'
      - 'kustomize/archetype/**'
      - 'kustomize/components/**'

jobs:
  validate-profiles:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pyyaml jsonschema
      
      - name: Validate cost profiles
        run: |
          python scripts/validate-cost-profiles.py \
            --catalog kustomize/catalog/services.yaml \
            --profiles kustomize/catalog/cost-profiles.yaml
      
      - name: Validate monitoring profiles
        run: |
          python scripts/validate-monitoring-profiles.py \
            --catalog kustomize/catalog/services.yaml \
            --profiles kustomize/catalog/monitoring-profiles.yaml
  
  generate-manifests:
    needs: validate-profiles
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
        environment: ['int-stable', 'pre-stable', 'prod']
        region: ['euw1', 'euw2']
      max-parallel: 20
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pyyaml
      
      - name: Expand profiles
        run: |
          python scripts/expand-profiles.py \
            --service ${{ matrix.service }} \
            --environment ${{ matrix.environment }} \
            --output /tmp/expanded-${{ matrix.service }}-${{ matrix.environment }}.json
      
      - name: Generate Kustomize workspace
        run: |
          ./scripts/generate-kz.sh \
            ${{ matrix.service }} \
            ${{ matrix.environment }} \
            ${{ matrix.region }}
      
      - name: Build manifests
        run: |
          OUTPUT_DIR="generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}"
          mkdir -p $OUTPUT_DIR
          
          cd tmp/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}
          kustomize build . > $GITHUB_WORKSPACE/$OUTPUT_DIR/manifests.yaml
      
      - name: Validate manifests
        run: |
          kubeconform --strict \
            generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}/manifests.yaml
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: manifests-${{ matrix.service }}-${{ matrix.environment }}-${{ matrix.region }}
          path: generated/${{ matrix.service }}/${{ matrix.environment }}/${{ matrix.region }}/
  
  commit:
    needs: generate-manifests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/download-artifact@v3
        with:
          path: generated/
      
      - name: Commit manifests
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          
          git add generated/
          git commit -m "🤖 Generated manifests with cost & monitoring profiles" || exit 0
          
          git push
```

---

## 7. Summary

### Integration Checklist

- [x] **Profile Expansion Script** - `expand-profiles.py` expands both cost and monitoring profiles
- [x] **Enhanced generate-kz.sh** - Injects cost labels and generates monitoring resources
- [x] **Monitoring Resource Generator** - Creates ServiceMonitor, PrometheusRule, Dynatrace configs
- [x] **CI/CD Integration** - Validates and generates manifests with profiles
- [x] **Label Injection** - Cost labels in `commonLabels`, monitoring labels for Prometheus
- [x] **Resource Generation** - Monitoring resources as separate YAML files included in kustomization

### Key Files

1. **`scripts/expand-profiles.py`** - Expands cost and monitoring profiles
2. **`scripts/generate-kz.sh`** - Enhanced to handle profiles
3. **`scripts/generate-monitoring-resources.py`** - Generates monitoring K8s resources
4. **`kustomize/catalog/cost-profiles.yaml`** - Cost profile definitions
5. **`kustomize/catalog/monitoring-profiles.yaml`** - Monitoring profile definitions

### Result

Every service deployment includes:
- ✅ Cost labels for GCP billing allocation
- ✅ Monitoring resources (ServiceMonitor, PrometheusRule)
- ✅ Both configured via profile templates (DRY principle)
- ✅ Environment-specific overrides applied
- ✅ Size-aware thresholds and budgets

---

**Document Status**: ✅ Complete Integration Guide

**Related Documents**:
- [07_COST_MANAGEMENT_WITH_PROFILES.md](./07_COST_MANAGEMENT_WITH_PROFILES.md) - Cost profile design
- [08_MONITORING_METRICS_PROFILES.md](./08_MONITORING_METRICS_PROFILES.md) - Monitoring profile design
- [02_KUSTOMIZE_CONFIG_MANAGEMENT.md](./02_KUSTOMIZE_CONFIG_MANAGEMENT.md) - Kustomize architecture

