#!/bin/bash
set -euo pipefail

# Usage: ./download-api-certs.sh <env>
RAW_ENVIRONMENT="$1"

# All sandbox envs map to ndr-dev for certs
if [[ "$RAW_ENVIRONMENT" == ndr* ]]; then
    ENVIRONMENT="ndr-dev"
else    
    ENVIRONMENT="$RAW_ENVIRONMENT"
fi

REGION="eu-west-2"
TRUSTSTOREBUCKETNAME="${ENVIRONMENT}-ndr-truststore"
CA_PATH="ndr-truststore.pem"

CERT_DIR="lambdas/mtls_env_certs/${ENVIRONMENT}" # todo change name dev?
mkdir -p "$CERT_DIR"

# Download CA cert from S3
aws s3 cp "s3://${TRUSTSTOREBUCKETNAME}/${CA_PATH}" "${CERT_DIR}/cacert.pem"

# Determine SSM paths
CERT_PATH="/ndr/${ENVIRONMENT}/external_client_cert"
CERT_KEY="/ndr/${ENVIRONMENT}/external_client_key"

# Download client cert and key from SSM
aws ssm get-parameter --name "${CERT_PATH}" --with-decryption | jq -r '.Parameter.Value' > "${CERT_DIR}/client.crt"
aws ssm get-parameter --name "${CERT_KEY}" --with-decryption | jq -r '.Parameter.Value' > "${CERT_DIR}/client.key"

# Verify cert
openssl verify -CAfile "${CERT_DIR}/cacert.pem" "${CERT_DIR}/client.crt"
# shellcheck disable=SC2181 # - Ignored Check exit code directly as required nested ifs to work with above logic
if [[ $? -eq 0 ]]; then
    echo "The downloaded cert matches the Truststore PEM file"
else
    echo "The downloaded cert doesnt match the Truststore PEM file"
    exit 1
fi