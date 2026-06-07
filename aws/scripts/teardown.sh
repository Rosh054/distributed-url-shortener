#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-url-shortener}"
REGION="${AWS_REGION:-us-east-1}"

echo "WARNING: This will destroy AWS resources and may delete data."
read -r -p "Type 'destroy' to continue: " confirm
if [ "$confirm" != "destroy" ]; then
  echo "Aborted."
  exit 1
fi

cd "$(dirname "$0")/../terraform"
terraform destroy

echo "Optional: delete ECR images manually for ${PROJECT}-api and ${PROJECT}-worker in ${REGION}"
