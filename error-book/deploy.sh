#!/bin/bash
set -e

echo "=== 1. 构建前端 ==="
cd frontend && npm install && npm run build && cd ..

echo "=== 2. 部署 SAM 后端 ==="
sam build
sam deploy --config-file samconfig.toml

echo "=== 3. 获取部署输出 ==="
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name error-book --query 'Stacks[0].Outputs')
API_URL=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='ApiEndpoint'))")
FRONTEND_URL=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='FrontendUrl'))")
USER_POOL_ID=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='UserPoolId'))")
CLIENT_ID=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='UserPoolClientId'))")
BUCKET=$(echo $STACK_OUTPUTS | python3 -c "import sys,json; o=json.load(sys.stdin); print(next(x['OutputValue'] for x in o if x['OutputKey']=='ImagesBucketName' or x['OutputKey']=='FrontendBucketName' or True))" 2>/dev/null || true)

echo "=== 4. 写入前端环境变量 ==="
cat > frontend/.env.local << EOF
VITE_USER_POOL_ID=$USER_POOL_ID
VITE_USER_POOL_CLIENT_ID=$CLIENT_ID
VITE_API_BASE_URL=$API_URL
EOF

echo "=== 5. 重新构建前端（含真实环境变量） ==="
cd frontend && npm run build && cd ..

echo "=== 6. 上传前端资源到 S3 ==="
FRONTEND_BUCKET=$(aws cloudformation describe-stacks --stack-name error-book --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text 2>/dev/null || \
  aws s3 ls | grep error-book-frontend | awk '{print $3}')
aws s3 sync frontend/dist/ s3://$FRONTEND_BUCKET --delete

echo ""
echo "✅ 部署完成！"
echo "🌐 前端地址: $FRONTEND_URL"
echo "🔗 API 地址: $API_URL"
