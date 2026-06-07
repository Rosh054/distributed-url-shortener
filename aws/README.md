# AWS Deployment Guide

Optional Terraform and scripts to deploy the distributed URL shortener on AWS.

## Architecture (AWS)

```text
Internet -> ALB -> ECS Fargate (API)
                      |
                      +--> RDS PostgreSQL (url mappings, click events)
                      +--> ElastiCache Redis (cache, rate limit, click queue)
                 ECS Fargate (Analytics worker)
                      |
                 CloudWatch logs, dashboard, alarms
```

## Resources

| Resource | Purpose |
|----------|---------|
| ECR (`url-shortener-api`, `url-shortener-worker`) | Container images |
| ECS cluster + services | API and analytics worker |
| ALB | Public ingress for redirects and API |
| RDS PostgreSQL | Persistent URL and analytics data |
| ElastiCache Redis | Cache-aside, rate limiting, click queue |
| CloudWatch | Logs, dashboard, alarms |

## Prerequisites

- AWS account with ECS, ECR, RDS, ElastiCache, VPC, IAM, CloudWatch permissions
- AWS CLI configured
- Terraform >= 1.5
- Docker

## Quick start

```bash
chmod +x aws/scripts/provision.sh aws/scripts/teardown.sh
./aws/scripts/provision.sh

cd aws/terraform
terraform init
terraform apply

# Build and push images (replace ACCOUNT_ID)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker build -f Dockerfile.api -t ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/url-shortener-api:latest .
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/url-shortener-api:latest
docker build -f Dockerfile.worker -t ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/url-shortener-worker:latest .
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/url-shortener-worker:latest
```

Wire ECS task definitions with environment variables:

- `DATABASE_URL` from RDS endpoint
- `REDIS_URL` from ElastiCache endpoint
- `BASE_URL` from ALB DNS name
- `IP_HASH_SALT` from Secrets Manager

## CloudWatch alarms

| Alarm | Trigger |
|-------|---------|
| `url-shortener-api-5xx` | ALB target 5xx count > 5/min |
| `url-shortener-high-latency` | ALB p95 target response time > threshold |
| `url-shortener-worker-failures` | Custom metric `FailedClickEvents` > 10 / 5 min |
| `url-shortener-redis-connection-errors` | Custom metric `RedisConnectionErrors` > 5/min |

Publish custom worker/cache metrics from the application or a sidecar for full alarm coverage.

## Cost warning

RDS, ElastiCache, ALB, and ECS running 24/7 can cost **$80–200+/month** depending on sizing and region. Run `./aws/scripts/teardown.sh` and `terraform destroy` when not benchmarking.

## What remains for full production

- ECS task definitions, services, and IAM roles wired in Terraform
- Secrets Manager for DB password and `IP_HASH_SALT`
- HTTPS (ACM certificate + ALB listener)
- Multi-AZ RDS and Redis replication group
- WAF on ALB
- Custom metric publisher for cache hit rate and worker failures

The Terraform skeleton provides VPC, ALB, ECR, RDS, ElastiCache, log groups, dashboard, and alarms.
