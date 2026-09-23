# Production Deployment Architecture

This document describes the cloud-agnostic deployment architecture for the National Material Intelligence Platform.

## System Topology

The platform consists of the following isolated tiers:
1. **Edge / Routing Tier**: API Gateway / Reverse Proxy (e.g., Nginx, Traefik, AWS ALB).
2. **Presentation Tier**: React SPA hosted on a CDN or static web server.
3. **Application Tier**: FastAPI backend and AI matching engine.
4. **Asynchronous Tier**: Celery Worker nodes for background processing.
5. **Data Tier**: PostgreSQL (with `pgvector`), Redis, and Object Storage (S3/MinIO).

## Reverse Proxy & HTTPS
- All traffic must pass through a Reverse Proxy/Load Balancer.
- **HTTPS Termination**: The API Gateway handles TLS 1.2+ termination. No internal services listen directly to external traffic.
- **Routing**:
  - `/api/v1/*` routes to the Backend application cluster.
  - `/` routes to the Frontend static asset bucket or Nginx server.
- **Security Headers**: HSTS, CSP, and X-Frame-Options are injected at the API Gateway level (and backed up by the application middleware).

## Deployments
### Frontend Deployment
- **Build**: `npm run build` outputs static assets.
- **Hosting**: Served via Nginx containers or cloud-native Object Storage (e.g., AWS S3 + CloudFront).

### Backend Deployment
- **Container**: `uvicorn` running FastAPI, managed by Docker.
- **Scaling**: Horizontally scalable. Scaled based on CPU usage and request latency.
- **Readiness**: Utilizes the `/ready` endpoint to ensure the database connection pool is warmed up before accepting traffic.

### AI Service Deployment
- **Hardware**: Strongly recommended to deploy on instances with hardware acceleration (GPU) if deep learning inference is localized.
- **Model Storage**: Model weights should be persisted in a shared persistent volume or loaded directly from Object Storage into a cache directory upon boot.

### Worker Deployment
- **Scaling**: Scaled independently based on Celery Queue Depth.
- **Resource Constraints**: High memory constraints for large batch normalization processes.

### Data Tier
- **PostgreSQL**: Must be deployed in a Highly Available (HA) configuration (e.g., AWS RDS Multi-AZ). Requires the `pgvector` extension.
- **Redis**: Clustered Redis for caching, rate limiting, and Celery message brokering.
- **Object Storage**: S3-compatible API for storing user uploads, migration mapping exports, and backups.

## Networking & Security
- **VPC Isolation**: The Data Tier and Asynchronous Tier should sit in private subnets with NO direct internet access.
- **Secrets Management**: Environment variables containing secrets MUST be injected via secure stores (e.g., AWS Secrets Manager, HashiCorp Vault), never hardcoded.
