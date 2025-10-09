#!/bin/bash
set -euo pipefail

# Check for required argument
if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <ENVIRONMENT>"
    exit 1
fi

ENVIRONMENT="$1"

# Set environment variables
export LG_METADATA_TABLE="${ENVIRONMENT}_LloydGeorgeReferenceMetadata"
export LG_UNSTITCHED_TABLE="${ENVIRONMENT}_LloydGeorgeUnstitched"
export BULK_REPORT_TABLE="${ENVIRONMENT}_BulkReportMetadata"
export NDR_S3_BUCKET="${ENVIRONMENT}-lloyd-george-store"
export NDR_API_ENDPOINT="api-${ENVIRONMENT}.access-request-fulfilment.patient-deductions.nhs.uk"
export MTLS_ENDPOINT="mtls.${ENVIRONMENT}.access-request-fulfilment.patient-deductions.nhs.uk"

# Fetch API key from AWS API Gateway
API_KEY_ID=$(aws apigateway get-api-keys --name-query "${ENVIRONMENT}_pdm" --query "items[0].id" --output text)
if [[ -z "$API_KEY_ID" || "$API_KEY_ID" == "None" ]]; then
    echo "ERROR: API key ID not found for ${ENVIRONMENT}_pdm"
    exit 1
fi

API_KEY=$(aws apigateway get-api-key --api-key "$API_KEY_ID" --include-value --query 'value' --output text)
if [[ -z "$API_KEY" || "$API_KEY" == "None" ]]; then
    echo "ERROR: API key value not found for ID $API_KEY_ID"
    exit 1
fi

# Export the API key
export MTLS_NDR_API_KEY="$API_KEY"

# Ensure Client certificates in place
if ! make download-api-certs env="${ENVIRONMENT}"
then
  echo "Execution of 'make download-api-certs env=${ENVIRONMENT}' failed, exiting"
  exit 1
fi

# Set certificate paths in regards to where e2e tests are run from
export TESTING_CLIENT_CERT_PATH=./mtls_env_certs/"${ENVIRONMENT}"/client.crt
export TESTING_CLIENT_KEY_PATH=./mtls_env_certs/"${ENVIRONMENT}"/client.key

# if [[ ! -f "$TESTING_CLIENT_CERT_PATH" ]]; then
#     echo "ERROR: Certificate file not found at $TESTING_CLIENT_CERT_PATH"
#     exit 1
# fi

echo "Environment variables set for ENVIRONMENT=${ENVIRONMENT}"
