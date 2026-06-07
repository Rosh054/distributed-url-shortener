#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-url-shortener}"
REGION="${AWS_REGION:-us-east-1}"

echo "Creating ECR repositories and CloudWatch log groups for ${PROJECT} in ${REGION}..."

aws ecr create-repository --repository-name "${PROJECT}-api" --region "$REGION" 2>/dev/null || true
aws ecr create-repository --repository-name "${PROJECT}-worker" --region "$REGION" 2>/dev/null || true

aws logs create-log-group --log-group-name "/ecs/${PROJECT}-api" --region "$REGION" 2>/dev/null || true
aws logs create-log-group --log-group-name "/ecs/${PROJECT}-worker" --region "$REGION" 2>/dev/null || true

echo "Provision script complete. Next: cd aws/terraform && terraform init && terraform apply"
