# Ensure gcloud is in PATH if installed in user AppData
$GCLOUD_PATH = "C:\Users\clw10\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
if ((Test-Path $GCLOUD_PATH) -and ($env:Path -notlike "*$GCLOUD_PATH*")) {
    $env:Path = "$GCLOUD_PATH;$env:Path"
}

$SERVICE_NAME = "alpaca-hedging-agent"
$REGION = "us-central1"
$PROJECT_ID = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else { "forecastagent-501722" }

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Deploying Alpaca AI Hedging Agent to Google Cloud Run" -ForegroundColor Cyan
Write-Host " Service: $SERVICE_NAME" -ForegroundColor Cyan
Write-Host " Region:  $REGION" -ForegroundColor Cyan
Write-Host " Project: $PROJECT_ID (521695902469)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# Set gcloud project
gcloud config set project $PROJECT_ID

# Load .env variables if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)\s*=\s*(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
}

$API_KEY = $env:APCA_API_KEY_ID
$API_SECRET = $env:APCA_API_SECRET_KEY
$BASE_URL = if ($env:APCA_API_BASE_URL) { $env:APCA_API_BASE_URL } else { "https://paper-api.alpaca.markets/v2" }
$FL_KEY = $env:FEATHERLESS_API_KEY
$FL_URL = if ($env:FEATHERLESS_BASE_URL) { $env:FEATHERLESS_BASE_URL } else { "https://api.featherless.ai/v1" }
$FL_MODEL = if ($env:FEATHERLESS_MODEL) { $env:FEATHERLESS_MODEL } else { "meta-llama/Meta-Llama-3.1-8B-Instruct" }

Write-Host "Deploying container image to Google Cloud Run..." -ForegroundColor Yellow

$IMAGE_URI = "us-central1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}:latest"

gcloud run deploy $SERVICE_NAME `
    --project $PROJECT_ID `
    --image $IMAGE_URI `
    --platform managed `
    --region $REGION `
    --port 8080 `
    --memory 2Gi `
    --cpu 2 `
    --min-instances 1 `
    --max-instances 5 `
    --no-cpu-throttling `
    --timeout 300 `
    --allow-unauthenticated `
    --set-env-vars "APCA_API_KEY_ID=$API_KEY,APCA_API_SECRET_KEY=$API_SECRET,APCA_API_BASE_URL=$BASE_URL,FEATHERLESS_API_KEY=$FL_KEY,FEATHERLESS_BASE_URL=$FL_URL,FEATHERLESS_MODEL=$FL_MODEL,INITIAL_PORTFOLIO_EQUITY=100000.0,MAX_DRAWDOWN_THRESHOLD=0.025,MCP_TRANSPORT=sse,LOG_LEVEL=INFO"

Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
