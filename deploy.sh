#!/bin/bash
set -e

# Configuration
FUNCTION_NAME="oddjob-resy-booker"
REGION="us-east-1"
ROLE_NAME="oddjob-lambda-role"
SCHEDULER_ROLE_NAME="oddjob-scheduler-role"
SECRET_NAME="oddjob/resy-credentials"
SCHEDULE_GROUP="oddjob"

echo "=== OddJob Lambda Deployment ==="
echo ""

# Check for aws-vault
if ! command -v aws-vault &> /dev/null; then
    echo "Error: aws-vault not found. Please install it first."
    exit 1
fi

# Function to run AWS commands through aws-vault
aws_cmd() {
    aws-vault exec oddjob -- aws "$@"
}

# Step 1: IAM Role (created manually in AWS Console to avoid session token limitations)
ACCOUNT_ID="145713876007"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
SCHEDULER_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${SCHEDULER_ROLE_NAME}"
echo "Step 1: Using IAM roles..."
echo "  Lambda Role ARN:    $ROLE_ARN"
echo "  Scheduler Role ARN: $SCHEDULER_ROLE_ARN"

# Step 2: Package the Lambda function
echo ""
echo "Step 2: Packaging Lambda function..."

cd "$(dirname "$0")"
rm -rf build lambda.zip

# Create build directory
mkdir -p build

# Copy source files
cp -r src/api build/
cp src/cli.py build/
cp src/lambda_handler.py build/

# Install dependencies
source "$(dirname "$0")/venv/bin/activate"
pip install requests -t build/ --quiet

# Create zip
cd build
zip -r ../lambda.zip . -x "*.pyc" -x "__pycache__/*" > /dev/null
cd ..

echo "  Created lambda.zip ($(du -h lambda.zip | cut -f1))"

# Step 3: Create or update Lambda function
echo ""
echo "Step 3: Deploying Lambda function..."

FUNCTION_EXISTS=$(aws_cmd lambda get-function --function-name $FUNCTION_NAME 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "  Creating new function..."
    aws_cmd lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler lambda_handler.lambda_handler \
        --zip-file fileb://lambda.zip \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION \
        --output text > /dev/null
else
    echo "  Updating existing function..."
    aws_cmd lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda.zip \
        --region $REGION \
        --output text > /dev/null
fi

echo "  Function deployed: $FUNCTION_NAME"

# Step 4: Check if secrets exist
echo ""
echo "Step 4: Checking secrets..."

SECRET_EXISTS=$(aws_cmd secretsmanager describe-secret --secret-id $SECRET_NAME --region $REGION 2>/dev/null || echo "")

if [ -z "$SECRET_EXISTS" ]; then
    echo "  Secret not found. You need to create it:"
    echo ""
    echo "  Run this command with your Resy credentials:"
    echo ""
    echo "  aws-vault exec oddjob -- aws secretsmanager create-secret \\"
    echo "    --name $SECRET_NAME \\"
    echo "    --region $REGION \\"
    echo "    --secret-string '{\"api_key\": \"YOUR_API_KEY\", \"auth_token\": \"YOUR_AUTH_TOKEN\"}'"
    echo ""
else
    echo "  Secret exists: $SECRET_NAME"
fi

# Step 5: Create EventBridge Scheduler schedule group
echo ""
echo "Step 5: Checking schedule group..."

GROUP_EXISTS=$(aws_cmd scheduler get-schedule-group --name $SCHEDULE_GROUP --region $REGION 2>/dev/null || echo "")

if [ -z "$GROUP_EXISTS" ]; then
    echo "  Creating schedule group: $SCHEDULE_GROUP"
    aws_cmd scheduler create-schedule-group --name $SCHEDULE_GROUP --region $REGION
    echo "  Created."
else
    echo "  Schedule group exists: $SCHEDULE_GROUP"
fi

# Step 6: Check for scheduler IAM role
echo ""
echo "Step 6: Checking scheduler IAM role..."

SCHEDULER_ROLE_EXISTS=$(aws_cmd iam get-role --role-name $SCHEDULER_ROLE_NAME 2>/dev/null || echo "")

if [ -z "$SCHEDULER_ROLE_EXISTS" ]; then
    echo "  Scheduler role not found. Create it manually in the AWS Console:"
    echo ""
    echo "  Role name: $SCHEDULER_ROLE_NAME"
    echo "  Trusted entity: Custom trust policy:"
    echo '    {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"scheduler.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    echo ""
    echo "  Inline permission policy (allow invoking the Lambda):"
    echo "    {"
    echo "      \"Version\": \"2012-10-17\","
    echo "      \"Statement\": [{"
    echo "        \"Effect\": \"Allow\","
    echo "        \"Action\": \"lambda:InvokeFunction\","
    echo "        \"Resource\": \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}\""
    echo "      }]"
    echo "    }"
    echo ""
else
    echo "  Scheduler role exists: $SCHEDULER_ROLE_NAME"
fi

# Cleanup
rm -rf build

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "To test the function:"
echo ""
echo "aws-vault exec oddjob -- aws lambda invoke \\"
echo "  --function-name $FUNCTION_NAME \\"
echo "  --payload '{\"venue_id\": 25973, \"date\": \"2026-02-19\", \"party_size\": 2, \"best\": \"22:00\", \"earliest\": \"21:00\", \"latest\": \"23:00\"}' \\"
echo "  --cli-binary-format raw-in-base64-out \\"
echo "  /tmp/response.json && cat /tmp/response.json"
