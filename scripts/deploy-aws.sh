#!/usr/bin/env bash
# Deploy the KSERC Truing-Up Engine to AWS.
#   ./scripts/deploy-aws.sh [region]
# Needs: terraform, docker, aws CLI with credentials for the target account.
set -euo pipefail

REGION="${1:-ap-south-1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="terraform -chdir=$ROOT/infra/aws"
TAG="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date +%s)"

echo "▸ 1/4  Provisioning infrastructure in $REGION"
$TF init -input=false -upgrade >/dev/null
# First pass creates the registry; the service waits for an image (step 3).
$TF apply -input=false -auto-approve -var "region=$REGION" -var "image_tag=$TAG"

REPO="$($TF output -raw ecr_repository)"
BUCKET="$($TF output -raw docs_bucket)"
CLUSTER="$($TF output -raw cluster)"
SERVICE="$($TF output -raw service)"

echo "▸ 2/4  Building and pushing image $REPO:$TAG"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/amd64 -t "$REPO:$TAG" -t "$REPO:latest" "$ROOT"
docker push "$REPO:$TAG"
docker push "$REPO:latest"

echo "▸ 3/4  Uploading the regulatory corpus to s3://$BUCKET/documents/"
aws s3 sync "$ROOT/documents" "s3://$BUCKET/documents/" --region "$REGION" --only-show-errors

echo "▸ 4/4  Rolling out"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --force-new-deployment \
    --region "$REGION" >/dev/null
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION"

echo "✓ Live at $($TF output -raw url)"
