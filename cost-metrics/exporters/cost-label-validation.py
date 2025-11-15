#!/usr/bin/env python3
"""
Cost Label Validation Job

Daily job that validates cost labels on all Kubernetes resources.
Exports metrics about label coverage and correctness.

Runs as a Kubernetes CronJob that pushes metrics to Prometheus Pushgateway.

Usage:
  python3 cost-label-validation.py --pushgateway http://prometheus-pushgateway:9091
"""

import os
import re
import logging
from datetime import datetime
from kubernetes import client, config
from prometheus_client import CollectorRegistry, Gauge, Counter, push_to_gateway

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# METRIC DEFINITIONS
# ========================================

registry = CollectorRegistry()

# Gauge: Pods missing cost labels
pods_missing_cost_label = Gauge(
    'pods_missing_cost_label',
    'Number of pods without required cost labels',
    ['label_type'],  # cost.service, cost.team, cost.costCenter, etc.
    registry=registry
)

# Gauge: Deployments missing cost labels
deployments_missing_cost_label = Gauge(
    'deployments_missing_cost_label',
    'Number of deployments without required cost labels',
    ['label_type'],
    registry=registry
)

# Gauge: Total pods with valid cost labels
pods_with_valid_labels = Gauge(
    'pods_with_valid_labels',
    'Number of pods with all required cost labels correctly formatted',
    registry=registry
)

# Gauge: Total deployments with valid cost labels
deployments_with_valid_labels = Gauge(
    'deployments_with_valid_labels',
    'Number of deployments with all required cost labels',
    registry=registry
)

# Counter: Invalid label formats detected
invalid_label_format_total = Counter(
    'invalid_label_format_total',
    'Number of resources with incorrectly formatted cost labels',
    ['label_type', 'reason'],  # reason: invalid_format, invalid_value, etc.
    registry=registry
)

# Gauge: Label completeness ratio
cost_label_completeness_ratio = Gauge(
    'cost_label_completeness_ratio',
    'Ratio of resources with complete and valid cost labels',
    ['resource_type'],  # pod, deployment, service, etc.
    registry=registry
)

# Gauge: Pods by environment
pods_by_environment = Gauge(
    'pods_by_environment',
    'Total number of pods by environment',
    ['environment'],
    registry=registry
)

# Gauge: Last validation timestamp
cost_label_validation_timestamp = Gauge(
    'cost_label_validation_timestamp',
    'Unix timestamp of last validation run',
    registry=registry
)

# ========================================
# VALIDATION FUNCTIONS
# ========================================

REQUIRED_COST_LABELS = [
    'cost.service',
    'cost.team',
    'cost.environment',
    'cost.costCenter',
    'cost.businessUnit'
]

def validate_cost_center_format(value: str) -> bool:
    """Validate cost center format: CC-XXXXX"""
    return bool(re.match(r'^CC-\d{5}$', value))

def validate_business_unit_format(value: str) -> bool:
    """Validate business unit is not empty"""
    return len(value) > 0

def validate_environment_format(value: str) -> bool:
    """Validate environment is one of known values"""
    return value in ['int-stable', 'pre-stable', 'prod']

def validate_label_value(label_key: str, label_value: str) -> tuple[bool, str]:
    """
    Validate a cost label value
    
    Returns:
        (is_valid, reason_if_invalid)
    """
    
    if not label_value:
        return (False, 'empty_value')
    
    if label_key == 'cost.costCenter':
        if not validate_cost_center_format(label_value):
            return (False, 'invalid_cc_format')
    
    elif label_key == 'cost.environment':
        if not validate_environment_format(label_value):
            return (False, 'invalid_environment')
    
    elif label_key == 'cost.businessUnit':
        if not validate_business_unit_format(label_value):
            return (False, 'empty_business_unit')
    
    return (True, '')

def validate_pod_labels(pod) -> tuple[bool, list]:
    """
    Validate all cost labels on a pod
    
    Returns:
        (has_all_labels, missing_labels)
    """
    
    labels = pod.metadata.labels or {}
    missing_labels = []
    invalid_labels = []
    
    for required_label in REQUIRED_COST_LABELS:
        if required_label not in labels:
            missing_labels.append(required_label)
        else:
            # Validate the value
            is_valid, reason = validate_label_value(
                required_label,
                labels[required_label]
            )
            if not is_valid:
                invalid_labels.append((required_label, reason))
    
    has_all_valid = len(missing_labels) == 0 and len(invalid_labels) == 0
    
    # Record invalid labels
    for label_key, reason in invalid_labels:
        invalid_label_format_total.labels(
            label_type=label_key,
            reason=reason
        ).inc()
    
    return (has_all_valid, missing_labels + [f"{k} ({r})" for k, r in invalid_labels])

def validate_deployment_labels(deployment) -> tuple[bool, list]:
    """Validate cost labels on a deployment template"""
    
    labels = deployment.spec.template.metadata.labels or {}
    missing_labels = []
    
    for required_label in REQUIRED_COST_LABELS:
        if required_label not in labels:
            missing_labels.append(required_label)
    
    return (len(missing_labels) == 0, missing_labels)

# ========================================
# VALIDATION JOB
# ========================================

def run_validation():
    """Run the validation job"""
    
    logger.info("Starting cost label validation")
    start_time = datetime.now()
    
    try:
        # Load Kubernetes config
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        logger.info("Not in cluster, using local kubeconfig")
        config.load_kube_config()
    
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    
    # ========================================
    # VALIDATE PODS
    # ========================================
    
    logger.info("Validating pods...")
    
    pods_missing_by_label = {}
    pods_with_valid = 0
    pods_by_env = {}
    
    for required_label in REQUIRED_COST_LABELS:
        pods_missing_by_label[required_label] = 0
    
    try:
        all_pods = v1.list_pod_for_all_namespaces()
        total_pods = len(all_pods.items)
        
        for pod in all_pods.items:
            # Track by environment
            env = pod.metadata.labels.get('cost.environment', 'unknown') if pod.metadata.labels else 'unknown'
            pods_by_env[env] = pods_by_env.get(env, 0) + 1
            
            # Check for cost labels
            has_all_labels, missing = validate_pod_labels(pod)
            
            if has_all_labels:
                pods_with_valid += 1
            else:
                for missing_label in missing:
                    # Extract just the label key
                    if '(' in missing_label:
                        label_key = missing_label.split(' (')[0]
                    else:
                        label_key = missing_label
                    
                    if label_key in pods_missing_by_label:
                        pods_missing_by_label[label_key] += 1
        
        # Record pod metrics
        for label_key, count in pods_missing_by_label.items():
            pods_missing_cost_label.labels(label_type=label_key).set(count)
        
        pods_with_valid_labels.set(pods_with_valid)
        
        for env, count in pods_by_env.items():
            pods_by_environment.labels(environment=env).set(count)
        
        # Calculate completeness ratio
        if total_pods > 0:
            completeness = pods_with_valid / total_pods
        else:
            completeness = 1.0
        
        cost_label_completeness_ratio.labels(resource_type='pod').set(completeness)
        
        logger.info(f"Pods: {total_pods} total, {pods_with_valid} valid ({completeness*100:.1f}%)")
        
    except Exception as e:
        logger.error(f"Error validating pods: {e}")
    
    # ========================================
    # VALIDATE DEPLOYMENTS
    # ========================================
    
    logger.info("Validating deployments...")
    
    deployments_missing_by_label = {}
    deployments_with_valid = 0
    
    for required_label in REQUIRED_COST_LABELS:
        deployments_missing_by_label[required_label] = 0
    
    try:
        all_deployments = apps_v1.list_deployment_for_all_namespaces()
        total_deployments = len(all_deployments.items)
        
        for deployment in all_deployments.items:
            has_all_labels, missing = validate_deployment_labels(deployment)
            
            if has_all_labels:
                deployments_with_valid += 1
            else:
                for missing_label in missing:
                    if missing_label in deployments_missing_by_label:
                        deployments_missing_by_label[missing_label] += 1
        
        # Record deployment metrics
        for label_key, count in deployments_missing_by_label.items():
            deployments_missing_cost_label.labels(label_type=label_key).set(count)
        
        deployments_with_valid_labels.set(deployments_with_valid)
        
        # Calculate completeness ratio
        if total_deployments > 0:
            completeness = deployments_with_valid / total_deployments
        else:
            completeness = 1.0
        
        cost_label_completeness_ratio.labels(resource_type='deployment').set(completeness)
        
        logger.info(f"Deployments: {total_deployments} total, {deployments_with_valid} valid ({completeness*100:.1f}%)")
        
    except Exception as e:
        logger.error(f"Error validating deployments: {e}")
    
    # ========================================
    # RECORD COMPLETION
    # ========================================
    
    cost_label_validation_timestamp.set(datetime.now().timestamp())
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"Validation completed in {duration:.1f}s")
    
    return True

# ========================================
# PROMETHEUS EXPORT
# ========================================

def push_metrics(pushgateway: str, job_name: str = 'cost-label-validation'):
    """Push metrics to Prometheus Pushgateway"""
    
    try:
        push_to_gateway(
            pushgateway,
            job=job_name,
            registry=registry
        )
        logger.info(f"Metrics pushed to {pushgateway}")
    except Exception as e:
        logger.error(f"Failed to push metrics: {e}")

# ========================================
# MAIN
# ========================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cost Label Validation Job')
    parser.add_argument('--pushgateway', default='http://prometheus-pushgateway:9091',
                        help='Prometheus Pushgateway URL')
    args = parser.parse_args()
    
    # Run validation
    if run_validation():
        # Push metrics
        push_metrics(args.pushgateway)
        logger.info("Done")
    else:
        logger.error("Validation failed")
        exit(1)
