#!/usr/bin/env bash
set -euo pipefail

# Generate Kustomize workspace for a service
# Usage: generate-kz.sh <SERVICE> <ENV> <REGION> [TAG]

SERVICE="${1:-}"
ENV="${2:-}"
REGION="${3:-}"
TAG="${4:-}"

if [[ -z "$SERVICE" || -z "$ENV" || -z "$REGION" ]]; then
  echo "Usage: $0 <SERVICE> <ENV> <REGION> [TAG]"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CATALOG_DIR="$REPO_ROOT/kustomize/catalog"
TMP_DIR="$REPO_ROOT/tmp/$SERVICE/$ENV/$REGION"

# Load catalog data
SERVICE_DATA=$(yq eval ".services[] | select(.name == \"$SERVICE\")" "$CATALOG_DIR/services.yaml")
if [[ -z "$SERVICE_DATA" ]]; then
  echo "Error: Service '$SERVICE' not found in catalog"
  exit 1
fi

TYPE=$(echo "$SERVICE_DATA" | yq eval '.type' -)
IMAGE=$(echo "$SERVICE_DATA" | yq eval '.image' -)
TAG_STRATEGY=$(echo "$SERVICE_DATA" | yq eval '.tagStrategy' -)
NAMESPACE_TEMPLATE=$(echo "$SERVICE_DATA" | yq eval '.namespaceTemplate' -)
COMPONENTS=$(echo "$SERVICE_DATA" | yq eval '.components[]' - | tr '\n' ' ')

# Resolve config ref
CHANNEL=$(echo "$SERVICE_DATA" | yq eval '.channel // ""' -)
if [[ -n "$CHANNEL" ]]; then
  CONFIG_REF=$(yq eval ".channels.$CHANNEL" "$CATALOG_DIR/channels.yaml")
else
  REGION_PIN=$(yq eval ".regionPins.$REGION.$ENV // \"\"" "$CATALOG_DIR/region-pins.yaml")
  if [[ -n "$REGION_PIN" ]]; then
    CONFIG_REF="$REGION_PIN"
  else
    CONFIG_REF=$(yq eval ".envPins.$ENV" "$CATALOG_DIR/env-pins.yaml")
  fi
fi

# Resolve image tag
if [[ -z "$TAG" ]]; then
  TAG=$("$SCRIPT_DIR/gar.sh" resolve --image "$IMAGE" --strategy "$TAG_STRATEGY")
fi

# Compute namespace
NAMESPACE=$(echo "$NAMESPACE_TEMPLATE" | sed "s/{env}/$ENV/g;s/{service}/$SERVICE/g;s/{region}/$REGION/g")

# Create temp workspace
mkdir -p "$TMP_DIR"

# Generate namespace.yaml
cat > "$TMP_DIR/namespace.yaml" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    app: $SERVICE
    env: $ENV
    region: $REGION
    tier: core
EOF

# Generate kustomization.yaml
cat > "$TMP_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../../../kustomize/cb-base
  - ../../../../kustomize/archetype/$TYPE
  - ../../../../kustomize/envs/$ENV
  - ../../../../kustomize/regions/$REGION
  - ./namespace.yaml

components:
EOF

for COMP in $COMPONENTS; do
  echo "  - ../../../../kustomize/components/$COMP" >> "$TMP_DIR/kustomization.yaml"
done

cat >> "$TMP_DIR/kustomization.yaml" <<EOF

namespace: $NAMESPACE

commonLabels:
  app: $SERVICE
  env: $ENV
  region: $REGION
  tier: core

images:
  - name: app
    newName: $IMAGE
    newTag: $TAG

patches:
EOF

# Generate patches based on service data
HPA_ENABLED=$(echo "$SERVICE_DATA" | yq eval '.hpa.enabled // false' -)
if [[ "$HPA_ENABLED" == "true" ]]; then
  MIN_REPLICAS=$(echo "$SERVICE_DATA" | yq eval ".hpa.minReplicas.overrides.$ENV // .hpa.minReplicas.defaults" -)
  MAX_REPLICAS=$(echo "$SERVICE_DATA" | yq eval ".hpa.maxReplicas.overrides.$ENV // .hpa.maxReplicas.defaults" -)
  CPU_TARGET=$(echo "$SERVICE_DATA" | yq eval '.hpa.metrics[0].resource.target.averageUtilization' -)
  
  cat > "$TMP_DIR/hpa-patch.yaml" <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: $SERVICE
spec:
  minReplicas: $MIN_REPLICAS
  maxReplicas: $MAX_REPLICAS
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: $CPU_TARGET
EOF
  echo "  - path: hpa-patch.yaml" >> "$TMP_DIR/kustomization.yaml"
else
  REPLICAS=$(echo "$SERVICE_DATA" | yq eval ".replicas.overrides.$ENV // .replicas.defaults" -)
  cat > "$TMP_DIR/replicas-patch.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $SERVICE
spec:
  replicas: $REPLICAS
EOF
  echo "  - path: replicas-patch.yaml" >> "$TMP_DIR/kustomization.yaml"
fi

# Resources patch
CPU=$(echo "$SERVICE_DATA" | yq eval ".resources.overrides.$ENV.cpu // .resources.defaults.cpu" -)
MEM=$(echo "$SERVICE_DATA" | yq eval ".resources.overrides.$ENV.memory // .resources.defaults.memory" -)

cat > "$TMP_DIR/resources-patch.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $SERVICE
spec:
  template:
    spec:
      containers:
        - name: app
          resources:
            requests:
              cpu: "$CPU"
              memory: "$MEM"
            limits:
              cpu: "$CPU"
              memory: "$MEM"
EOF
echo "  - path: resources-patch.yaml" >> "$TMP_DIR/kustomization.yaml"

# Ingress patch (if ingress component is included)
if echo "$COMPONENTS" | grep -q "ingress"; then
  DOMAIN=$(echo "$SERVICE_DATA" | yq eval ".domains.$ENV // \"\"" -)
  if [[ -n "$DOMAIN" ]]; then
    cat > "$TMP_DIR/ingress-patch.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $SERVICE
spec:
  rules:
    - host: $DOMAIN
EOF
    echo "  - path: ingress-patch.yaml" >> "$TMP_DIR/kustomization.yaml"
  fi
fi

# Retry patch (if retry component is included)
if echo "$COMPONENTS" | grep -q "retry"; then
  ATTEMPTS=$(echo "$SERVICE_DATA" | yq eval '.retry.attempts' -)
  PER_TRY=$(echo "$SERVICE_DATA" | yq eval '.retry.perTryTimeout' -)
  RETRY_ON=$(echo "$SERVICE_DATA" | yq eval '.retry.retryOn' -)
  
  cat > "$TMP_DIR/retry-patch.yaml" <<EOF
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: $SERVICE
spec:
  http:
    - retries:
        attempts: $ATTEMPTS
        perTryTimeout: $PER_TRY
        retryOn: "$RETRY_ON"
EOF
  echo "  - path: retry-patch.yaml" >> "$TMP_DIR/kustomization.yaml"
fi

# Circuit breaker patch (if circuit-breaker component is included)
if echo "$COMPONENTS" | grep -q "circuit-breaker"; then
  MODE=$(echo "$SERVICE_DATA" | yq eval '.trafficPolicy.modeKey' -)
  CONSECUTIVE=$(echo "$SERVICE_DATA" | yq eval '.trafficPolicy.outlierDetection.consecutiveErrors' -)
  INTERVAL=$(echo "$SERVICE_DATA" | yq eval '.trafficPolicy.outlierDetection.interval' -)
  BASE_EJECTION=$(echo "$SERVICE_DATA" | yq eval '.trafficPolicy.outlierDetection.baseEjectionTime' -)
  MAX_EJECTION=$(echo "$SERVICE_DATA" | yq eval '.trafficPolicy.outlierDetection.maxEjectionPercent' -)
  
  cat > "$TMP_DIR/circuit-breaker-patch.yaml" <<EOF
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: $SERVICE
spec:
  trafficPolicy:
    tls:
      mode: $MODE
    outlierDetection:
      consecutiveErrors: $CONSECUTIVE
      interval: $INTERVAL
      baseEjectionTime: $BASE_EJECTION
      maxEjectionPercent: $MAX_EJECTION
EOF
  echo "  - path: circuit-breaker-patch.yaml" >> "$TMP_DIR/kustomization.yaml"
fi

echo "Generated Kustomize workspace at: $TMP_DIR"
echo "Config ref: $CONFIG_REF"
echo "Image: $IMAGE:$TAG"
echo "Namespace: $NAMESPACE"

