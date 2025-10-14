#!/bin/bash
set -euo pipefail

# Check for required argument
if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <WORKSPACE>"
    exit 1
fi

WORKSPACE="$1"

# Set environment variables
export PDM_METADATA_TABLE="${WORKSPACE}_PDMDocumentMetadata"
export PDM_S3_BUCKET="${WORKSPACE}-pdm-document-store"
export MTLS_ENDPOINT="mtls.${WORKSPACE}.access-request-fulfilment.patient-deductions.nhs.uk"

# Ensure Client certificates in place
if ! make download-api-certs WORKSPACE="${WORKSPACE}"
then
  echo "Execution of 'make download-api-certs WORKSPACE=${WORKSPACE}' failed, exiting"
  exit 1
fi

# Set certificate paths in regards to where e2e tests are run from
export CLIENT_CERT_PATH=./mtls_env_certs/"${WORKSPACE}"/client.crt
export CLIENT_KEY_PATH=./mtls_env_certs/"${WORKSPACE}"/client.key

echo "Environment variables set for WORKSPACE ${WORKSPACE}"
