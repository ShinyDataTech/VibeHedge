#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run Deployment Script for Alpaca Autonomous Hedging Agent
# ==============================================================================
set -e

# Configuration
SERVICE_NAME="alpaca-hedging-agent"
REGION="us-central1"
PROJECT_ID=${GCP_PROJECT_ID:-"forecastagent-501722"}

echo "=================================================================="
echo " Deploying Alpaca AI Hedging Agent to Google Cloud Run"
echo " Service: $SERVICE_NAME"
echo " Region:  $REGION"
echo " Project: $PROJECT_ID (521695902469)"
echo "=================================================================="

# Set gcloud project
gcloud config set project "$PROJECT_ID"

# Load environment secrets if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Deploy container directly from source to Cloud Run
echo "Building and deploying multi-stage container to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --source . \
    --platform managed \
    --region "$REGION" \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 5 \
    --no-cpu-throttling \
    --timeout 300 \
    --allow-unauthenticated \
    --set-env-vars "APCA_API_KEY_ID=${APCA_API_KEY_ID},APCA_API_SECRET_KEY=${APCA_API_SECRET_KEY},APCA_API_BASE_URL=${APCA_API_BASE_URL},FEATHERLESS_API_KEY=${FEATHERLESS_API_KEY},FEATHERLESS_BASE_URL=${FEATHERLESS_BASE_URL},FEATHERLESS_MODEL=${FEATHERLESS_MODEL},INITIAL_PORTFOLIO_EQUITY=100000.0,MAX_DRAWDOWN_THRESHOLD=0.025,MCP_TRANSPORT=sse,LOG_LEVEL=INFO"

echo "=================================================================="
echo " Deployment Complete!"
echo " Service URL: $(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')"
echo " FastMCP SSE Endpoint: $(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')/sse"
echo "=================================================================="
