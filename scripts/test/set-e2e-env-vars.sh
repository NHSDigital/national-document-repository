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

echo "selected environment2: $ENVIRONMENT"

# Ensure Client certificates in place
if ! make download-api-certs env="${ENVIRONMENT}"
then
  echo "Execution of 'make download-api-certs env=${ENVIRONMENT}' failed, exiting"
  exit 1
fi

echo env="${ENVIRONMENT}"
# Set certificate paths in regards to where e2e tests are run from
export TESTING_CLIENT_CERT_PATH=./mtls_env_certs/"${ENVIRONMENT}"/client.crt
export TESTING_CLIENT_KEY_PATH=./mtls_env_certs/"${ENVIRONMENT}"/client.key

echo "Environment variables set for ENVIRONMENT=${ENVIRONMENT}"
