#!/bin/bash
set -e

# Configuration
FUNCTION_NAME="oddjob-resy-booker"
REGION="us-east-1"
ROLE_NAME="oddjob-lambda-role"
SECRET_NAME="oddjob/resy-credentials"

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

# Step 1: Create IAM Role for Lambda (if it doesn't exist)
echo "Step 1: Setting up IAM role..."
ROLE_ARN=$(aws_cmd iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "  Creating IAM role..."

    # Trust policy for Lambda
    cat > /tmp/trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    aws_cmd iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --output text > /dev/null

    # Attach basic Lambda execution policy
    aws_cmd iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Attach Secrets Manager read policy
    aws_cmd iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

    ROLE_ARN=$(aws_cmd iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

    echo "  Waiting for role to propagate..."
    sleep 10
fi
echo "  Role ARN: $ROLE_ARN"

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
