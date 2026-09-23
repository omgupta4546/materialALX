# System Monitoring and Observability

This document defines the metrics, logs, and health indicators tracked by the platform to ensure high availability and rapid incident response.

## Core Observability Pillars

### 1. Centralized Logging
- **Structured Logs**: All backend application logs are structured as JSON for ingestion into SIEM or log aggregators (e.g., ELK, Datadog).
- **Request Tracing**: A unique `X-Request-ID` is generated for every incoming HTTP request. This ID is injected into the response headers and appended to every log entry emitted during that request lifecycle, enabling cross-service distributed tracing.

### 2. Application Health Checks
The platform exposes standardized endpoints to interface with Load Balancers and Container Orchestrators (Kubernetes).
- **`/health` (Liveness)**: Returns `200 OK` indicating the application process is running and capable of responding to requests.
- **`/ready` (Readiness)**: Performs a deep check by actively pinging PostgreSQL and Redis. If the DB is unreachable, it returns `503 Service Unavailable`, preventing the Load Balancer from sending traffic to an impaired node.

### 3. Key Performance Indicators (Metrics)
The following metrics must be actively monitored:
- **API Processing Latency**: P95 and P99 latency across core endpoints (especially matching and search).
- **AI Inference Latency**: Time taken specifically by the AI engine to generate embeddings or semantic matches.
- **Queue Depth**: Number of pending tasks in the Celery brokered queues. Sudden spikes trigger worker horizontal scaling.
- **Failed Jobs Rate**: The percentage of background jobs throwing uncaught exceptions.
- **Database Connection Pool**: The active vs idle connections in PostgreSQL to detect connection leaks.

## Incident Thresholds
Alerts will be triggered under the following conditions:
- **High Error Rate**: > 1% HTTP 5xx responses over a 5-minute window.
- **Latency Spike**: P95 API response time > 2 seconds.
- **Stale Queue**: Items waiting in the `migration_queue` > 10 minutes.
- **Database CPU**: Sustained DB CPU > 80% for 15 minutes.
