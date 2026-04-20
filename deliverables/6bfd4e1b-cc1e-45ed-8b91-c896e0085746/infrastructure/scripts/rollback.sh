#!/usr/bin/env bash
# rollback.sh - Emergency Rollback Script
set -euo pipefail

PROJECT="ai-org"
SERVICE="${1:-backend}"

echo "⚠️  Rolling back $SERVICE in $PROJECT..."
aws ecs update-service \
  --cluster "$PROJECT-production-cluster" \
  --service "$PROJECT-production-$SERVICE" \
  --task-definition "$(
    aws ecs describe-task-definition \
      --task-definition "$PROJECT-production-$SERVICE" \
      --query "taskDefinition.taskDefinitionArn" \
      --output text
  )" \
  --force-new-deployment

echo "✅ Rollback initiated. Monitor in CloudWatch."