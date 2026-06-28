# backend/config.py
import os

tableName = os.environ["TABLE_NAME"]
imagesBucket = os.environ["IMAGES_BUCKET"]
cognitoUserPoolId = os.environ["COGNITO_USER_POOL_ID"]
awsRegion = os.environ.get("AWS_REGION", "us-east-1")
