#!/usr/bin/env bash
# YouTube Shorts Agent — AWS deployment script
# Prerequisites: aws CLI configured, docker running, claude login done
set -euo pipefail

# ─── Config ───────────────────────────────────────────────────────────────────
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
STACK_NAME="youtube-shorts-agent"
REPO_NAME="shorts-agent"
PEXELS_API_KEY="h3njwHn0ccEmMtn8v6Ud8NeECQXEeU9InPxUQrZSb3FCqCb1jEU9BDp0"
DEFAULT_NICHE="psychology"
SCHEDULE="cron(0 9 * * ? *)"   # Daily 9AM UTC — edit to change

# ─── Preflight checks ─────────────────────────────────────────────────────────
command -v aws    >/dev/null 2>&1 || { echo "ERROR: aws CLI not found. Install from https://aws.amazon.com/cli/"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. Install Docker Desktop."; exit 1; }
[ -d ~/.claude ]                  || { echo "ERROR: ~/.claude/ not found. Run 'claude login' first."; exit 1; }

echo "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  Account: $ACCOUNT_ID | Region: $REGION"

ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_URI="${ECR_REGISTRY}/${REPO_NAME}"

# ─── Step 1: ECR repository ───────────────────────────────────────────────────
echo ""
echo "[1/5] Creating ECR repository..."
aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" \
  --output text >/dev/null 2>&1 || \
  aws ecr create-repository \
    --repository-name "$REPO_NAME" \
    --region "$REGION" \
    --image-scanning-configuration scanOnPush=true \
    --output text >/dev/null
echo "  ECR: $ECR_URI"

# ─── Step 2: Stage Claude auth into build context ─────────────────────────────
echo ""
echo "[2/5] Staging Claude auth files..."
cp -r ~/.claude .claude
trap 'rm -rf .claude' EXIT   # Always clean up, even on error

# ─── Step 3: Build Docker image ───────────────────────────────────────────────
echo ""
echo "[3/5] Building Docker image (linux/amd64)..."
docker build --platform linux/amd64 -t "${REPO_NAME}:latest" .

# ─── Step 4: Push to ECR ──────────────────────────────────────────────────────
echo ""
echo "[4/5] Pushing image to ECR..."
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$ECR_REGISTRY"
docker tag "${REPO_NAME}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${ECR_URI}:latest" 2>/dev/null || echo "${ECR_URI}:latest")
echo "  Pushed: $IMAGE_DIGEST"

# ─── Step 5: Deploy CloudFormation stack ──────────────────────────────────────
echo ""
echo "[5/5] Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file aws-deploy.yaml \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --parameter-overrides \
    ImageUri="${ECR_URI}:latest" \
    PexelsApiKey="$PEXELS_API_KEY" \
    DefaultNiche="$DEFAULT_NICHE" \
    ScheduleExpression="$SCHEDULE"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "✅ Deployment complete!"
echo ""
LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" \
  --output text)
echo "  Lambda ARN : $LAMBDA_ARN"
echo "  Schedule   : Daily 9AM UTC (EventBridge)"
echo "  Region     : $REGION"
echo ""
echo "── YouTube OAuth setup (run once) ────────────────────────────────────────"
echo "  1. Go to console.cloud.google.com → Enable YouTube Data API v3"
echo "  2. Create OAuth 2.0 credentials (Desktop app) → Download client_secret.json"
echo "  3. pip install -r requirements.txt"
echo "  4. python setup_youtube_auth.py --secret /path/to/client_secret.json"
echo ""
echo "── Test the Lambda ───────────────────────────────────────────────────────"
echo "  aws lambda invoke \\"
echo "    --function-name youtube-shorts-agent \\"
echo "    --region $REGION \\"
echo "    --payload '{\"niche\":\"psychology\"}' \\"
echo "    /tmp/response.json && cat /tmp/response.json"
