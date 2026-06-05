# YouTube Shorts Agent — Windows PowerShell deployment script
# Prerequisites: aws CLI configured, Docker Desktop running, pip available
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ── Config ────────────────────────────────────────────────────────────────────
$Region        = $env:AWS_DEFAULT_REGION ?? "us-east-1"
$StackName     = "youtube-shorts-agent"
$RepoName      = "shorts-agent"
$PexelsApiKey  = "h3njwHn0ccEmMtn8v6Ud8NeECQXEeU9InPxUQrZSb3FCqCb1jEU9BDp0"
$DefaultNiche  = "psychology"
$Schedule      = "cron(0 9 * * ? *)"   # Daily 9AM UTC

# ── Preflight ─────────────────────────────────────────────────────────────────
Write-Host "Verifying AWS credentials..."
$AccountId = (aws sts get-caller-identity --query Account --output text)
if ($LASTEXITCODE -ne 0) { throw "AWS credentials not configured. Run 'aws configure' first." }
Write-Host "  Account: $AccountId | Region: $Region"

$EcrRegistry = "${AccountId}.dkr.ecr.${Region}.amazonaws.com"
$EcrUri      = "${EcrRegistry}/${RepoName}"

# ── [1/4] ECR repository ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[1/4] Creating ECR repository..."
$repoExists = aws ecr describe-repositories --repository-names $RepoName --region $Region 2>$null
if ($LASTEXITCODE -ne 0) {
    aws ecr create-repository `
        --repository-name $RepoName `
        --region $Region `
        --image-scanning-configuration scanOnPush=true | Out-Null
}
Write-Host "  ECR: $EcrUri"

# ── [2/4] Build Docker image ──────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Building Docker image (linux/amd64)..."
docker build --platform linux/amd64 -t "${RepoName}:latest" .
if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }

# ── [3/4] Push to ECR ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[3/4] Pushing image to ECR..."
aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin $EcrRegistry
docker tag "${RepoName}:latest" "${EcrUri}:latest"
docker push "${EcrUri}:latest"
if ($LASTEXITCODE -ne 0) { throw "Docker push failed." }

# ── [4/4] CloudFormation ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Deploying CloudFormation stack..."
aws cloudformation deploy `
    --template-file aws-deploy.yaml `
    --stack-name $StackName `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $Region `
    --parameter-overrides `
        ImageUri="${EcrUri}:latest" `
        PexelsApiKey="$PexelsApiKey" `
        DefaultNiche="$DefaultNiche" `
        ScheduleExpression="$Schedule"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Deployment complete!"
Write-Host ""
$LambdaArn = (aws cloudformation describe-stacks `
    --stack-name $StackName --region $Region `
    --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" `
    --output text)
Write-Host "  Lambda ARN : $LambdaArn"
Write-Host "  Schedule   : Daily 9AM UTC (EventBridge)"
Write-Host ""
Write-Host "── Next steps ──────────────────────────────────────────────────────"
Write-Host "  1. Store Claude auth (free, one-time):"
Write-Host "     pip install -r requirements.txt"
Write-Host "     python setup_claude_auth.py"
Write-Host ""
Write-Host "  2. Store YouTube OAuth (one-time):"
Write-Host "     python setup_youtube_auth.py --secret C:\path\to\client_secret.json"
Write-Host ""
Write-Host "  3. Test the Lambda:"
Write-Host "     aws lambda invoke --function-name youtube-shorts-agent --region $Region --payload '{\"niche\":\"psychology\"}' response.json"
Write-Host "     Get-Content response.json"
