#!/bin/bash
PROJECT_ID=$(yq eval '.project_id' config.yml)
REGION=$(yq eval '.region' config.yml)
SERVICE_NAME=$(yq eval '.service_name' config.yml)
BUCKET_NAME_TEMPLATE=$(yq eval '.bucket_name' config.yml)

BUCKET_NAME=${BUCKET_NAME_TEMPLATE/\$\{timestamp\}/$(date +%s)}

gcloud config set project $PROJECT_ID

gcloud services enable storage.googleapis.com run.googleapis.com

gsutil mb -l $REGION gs://$BUCKET_NAME

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars BUCKET_NAME=$BUCKET_NAME

echo "Deployment complete. Service URL: https://$SERVICE_NAME-$PROJECT_ID-uc.a.run.app"