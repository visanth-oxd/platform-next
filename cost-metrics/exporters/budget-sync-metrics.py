#!/usr/bin/env python3
"""
Budget Sync Metrics Exporter

Exports Prometheus metrics from the Cloud Function that syncs service budgets to Apptio.
Metrics include sync duration, success/failure rates, and service count.

Usage:
  python3 budget-sync-metrics.py --port 9090
"""

import time
import logging
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, start_http_server
from google.cloud import functions_v1, secretmanager
import google.cloud.logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
google_logger = google.cloud.logging.Client().logger("budget-sync-metrics")

# ========================================
# METRIC DEFINITIONS
# ========================================

# Histogram: Time to complete budget sync
budget_sync_duration_seconds = Histogram(
    'budget_sync_duration_seconds',
    'Time taken to sync budgets to Apptio',
    ['status'],  # success, failure, timeout
    buckets=(1, 5, 10, 15, 30, 60, 120, 300)  # 1s to 5m
)

# Counter: Total sync attempts
budget_sync_total = Counter(
    'budget_sync_total',
    'Total number of budget sync operations',
    ['status']  # success, failure, timeout
)

# Gauge: Number of services synced
budget_sync_services_count = Gauge(
    'budget_sync_services_count',
    'Number of services synced in last operation',
    ['environment']  # int-stable, pre-stable, prod
)

# Gauge: Last sync timestamp
budget_sync_last_timestamp = Gauge(
    'budget_sync_last_timestamp',
    'Unix timestamp of last successful sync'
)

# Counter: Budget creation success/failure
budget_creation_total = Counter(
    'budget_creation_total',
    'Total number of budget creation attempts in Apptio',
    ['status']  # success, failure
)

# Counter: Alert configuration success/failure
alert_config_total = Counter(
    'alert_config_total',
    'Total number of alert configuration attempts',
    ['status']  # success, failure
)

# Histogram: Apptio API response time
apptio_api_request_duration_seconds = Histogram(
    'apptio_api_request_duration_seconds',
    'Apptio API request duration',
    ['endpoint', 'method', 'status'],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60)
)

# Counter: Apptio API requests
apptio_api_request_total = Counter(
    'apptio_api_request_total',
    'Total Apptio API requests',
    ['endpoint', 'method', 'status']
)

# Gauge: Services with completed sync
budget_sync_completed_services = Gauge(
    'budget_sync_completed_services',
    'Number of services with successfully synced budgets',
    ['environment']
)

# Gauge: Services with failed sync
budget_sync_failed_services = Gauge(
    'budget_sync_failed_services',
    'Number of services that failed to sync',
    ['environment']
)

# Gauge: Catalog version synced
budget_sync_catalog_version = Gauge(
    'budget_sync_catalog_version',
    'Version/timestamp of catalog that was synced'
)

# ========================================
# METRIC COLLECTION FUNCTIONS
# ========================================

def record_sync_operation(
    duration_seconds: float,
    status: str,
    services_synced: dict,
    budgets_created: int,
    budgets_failed: int,
    alerts_configured: int,
    alerts_failed: int
):
    """
    Record metrics for a sync operation
    
    Args:
        duration_seconds: Time taken for sync
        status: 'success', 'failure', or 'timeout'
        services_synced: {'int-stable': 5, 'pre-stable': 10, 'prod': 15}
        budgets_created: Number of successfully created budgets
        budgets_failed: Number of failed budget creations
        alerts_configured: Number of successfully configured alerts
        alerts_failed: Number of failed alert configurations
    """
    
    # Record duration
    budget_sync_duration_seconds.labels(status=status).observe(duration_seconds)
    
    # Record success/failure
    budget_sync_total.labels(status=status).inc()
    
    # Record service counts by environment
    for env, count in services_synced.items():
        budget_sync_services_count.labels(environment=env).set(count)
        budget_sync_completed_services.labels(environment=env).set(count)
    
    # Record budget creation results
    budget_creation_total.labels(status='success').inc(budgets_created)
    budget_creation_total.labels(status='failure').inc(budgets_failed)
    
    # Record alert configuration results
    alert_config_total.labels(status='success').inc(alerts_configured)
    alert_config_total.labels(status='failure').inc(alerts_failed)
    
    # Update last sync timestamp if successful
    if status == 'success':
        budget_sync_last_timestamp.set(time.time())
    
    # Log summary
    logger.info(f"Sync operation completed: status={status}, duration={duration_seconds}s, "
                f"services={sum(services_synced.values())}, "
                f"budgets={budgets_created}/{budgets_created + budgets_failed}, "
                f"alerts={alerts_configured}/{alerts_configured + alerts_failed}")


def record_apptio_api_call(
    endpoint: str,
    method: str,
    status_code: int,
    duration_seconds: float
):
    """
    Record metrics for an Apptio API call
    
    Args:
        endpoint: API endpoint (e.g., '/budgets', '/alerts')
        method: HTTP method (GET, POST, PUT, DELETE)
        status_code: HTTP status code (200, 201, 400, 401, 500, 429)
        duration_seconds: Request duration
    """
    
    # Convert status code to label
    if 200 <= status_code < 300:
        status = 'success'
    elif 400 <= status_code < 500:
        status = 'client_error'
    elif 500 <= status_code < 600:
        status = 'server_error'
    elif status_code == 429:
        status = 'rate_limited'
    else:
        status = 'unknown'
    
    # Record duration
    apptio_api_request_duration_seconds.labels(
        endpoint=endpoint,
        method=method,
        status=status
    ).observe(duration_seconds)
    
    # Record request count
    apptio_api_request_total.labels(
        endpoint=endpoint,
        method=method,
        status=status
    ).inc()


class BudgetSyncMetricsCollector:
    """
    Collects metrics from the budget-sync Cloud Function logs
    Parses logs and exports metrics to Prometheus
    """
    
    def __init__(self):
        self.registry = CollectorRegistry()
    
    def collect_from_cloud_function_logs(self):
        """
        Query Cloud Logging for budget-sync execution logs
        Extract metrics and record them
        """
        
        from google.cloud import logging as cloud_logging
        
        client = cloud_logging.Client()
        
        # Query for last sync execution
        filter_str = (
            'resource.type="cloud_function" AND '
            'resource.labels.function_name="budget-sync" AND '
            'severity="INFO" AND '
            'textPayload=~"Sync operation completed"'
        )
        
        entries = client.list_entries(filter_=filter_str, max_results=10)
        
        for entry in entries:
            self._parse_log_entry(entry)
    
    def _parse_log_entry(self, log_entry):
        """Parse a log entry and record metrics"""
        
        text = log_entry.payload
        
        # Example log format:
        # "Sync operation completed: status=success, duration=15.2s, 
        #  services={int-stable: 5, pre-stable: 10, prod: 15}, 
        #  budgets=20/20, alerts=20/20"
        
        import re
        
        try:
            status = re.search(r'status=(\w+)', text).group(1)
            duration = float(re.search(r'duration=([\d.]+)s', text).group(1))
            
            # Extract service counts
            services_match = re.search(r'services=\{([^}]+)\}', text)
            services_synced = {}
            if services_match:
                for env_count in services_match.group(1).split(','):
                    env, count = env_count.strip().split(':')
                    services_synced[env.strip()] = int(count.strip())
            
            # Extract budget results
            budgets_match = re.search(r'budgets=(\d+)/(\d+)', text)
            if budgets_match:
                budgets_created = int(budgets_match.group(1))
                budgets_total = int(budgets_match.group(2))
                budgets_failed = budgets_total - budgets_created
            else:
                budgets_created = budgets_failed = 0
            
            # Extract alert results
            alerts_match = re.search(r'alerts=(\d+)/(\d+)', text)
            if alerts_match:
                alerts_configured = int(alerts_match.group(1))
                alerts_total = int(alerts_match.group(2))
                alerts_failed = alerts_total - alerts_configured
            else:
                alerts_configured = alerts_failed = 0
            
            # Record metrics
            record_sync_operation(
                duration_seconds=duration,
                status=status,
                services_synced=services_synced,
                budgets_created=budgets_created,
                budgets_failed=budgets_failed,
                alerts_configured=alerts_configured,
                alerts_failed=alerts_failed
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse log entry: {e}")


# ========================================
# HTTP SERVER
# ========================================

def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics HTTP server"""
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")


# ========================================
# EXAMPLE USAGE (for testing)
# ========================================

def example_sync_operation():
    """Example: Record a successful sync operation"""
    
    record_sync_operation(
        duration_seconds=15.2,
        status='success',
        services_synced={
            'int-stable': 5,
            'pre-stable': 10,
            'prod': 15
        },
        budgets_created=30,
        budgets_failed=0,
        alerts_configured=30,
        alerts_failed=0
    )
    
    # Record some API calls
    record_apptio_api_call('/budgets', 'POST', 201, 0.5)
    record_apptio_api_call('/budgets', 'POST', 201, 0.3)
    record_apptio_api_call('/alerts', 'POST', 201, 0.4)
    record_apptio_api_call('/alerts', 'POST', 201, 0.6)


def example_failed_sync():
    """Example: Record a failed sync operation"""
    
    record_sync_operation(
        duration_seconds=5.1,
        status='failure',
        services_synced={'int-stable': 2},  # Partial
        budgets_created=2,
        budgets_failed=3,
        alerts_configured=0,
        alerts_failed=3
    )
    
    # Record API errors
    record_apptio_api_call('/budgets', 'POST', 500, 0.5)
    record_apptio_api_call('/budgets', 'POST', 500, 0.4)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Budget Sync Metrics Exporter')
    parser.add_argument('--port', type=int, default=9090, help='Port for metrics server')
    parser.add_argument('--example', action='store_true', help='Run example metrics')
    args = parser.parse_args()
    
    # Start server
    start_metrics_server(args.port)
    
    # Record example metrics if requested
    if args.example:
        example_sync_operation()
        example_failed_sync()
        logger.info("Example metrics recorded. Visit http://localhost:9090/metrics")
    
    # Keep running
    try:
        while True:
            time.sleep(60)
            # In production, periodically collect metrics from Cloud Logging
            collector = BudgetSyncMetricsCollector()
            collector.collect_from_cloud_function_logs()
    except KeyboardInterrupt:
        logger.info("Shutting down")
