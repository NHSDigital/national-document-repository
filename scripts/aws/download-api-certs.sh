#!/bin/bash
set -euo pipefail

# Usage: ./download-api-certs.sh <env>
ENVIRONMENT="$1"
echo "selected environment3: $ENVIRONMENT"
# All sandbox envs map to ndr-dev for certs
if [[ "$ENVIRONMENT" == ndr* ]]; then
    PERSISTENT_ENVIRONMENT="ndr-dev"
else    
    PERSISTENT_ENVIRONMENT="$ENVIRONMENT"
fi

echo "Using persistent environment: $PERSISTENT_ENVIRONMENT"

REGION="eu-west-2"
TRUSTSTOREBUCKETNAME="${PERSISTENT_ENVIRONMENT}-ndr-truststore"
CA_PATH="ndr-truststore.pem"

LOCAL_CERT_DIR="lambdas/mtls_env_certs/${ENVIRONMENT}"
mkdir -p "$LOCAL_CERT_DIR"

# Download CA cert from S3
aws s3 cp "s3://${TRUSTSTOREBUCKETNAME}/${CA_PATH}" "${LOCAL_CERT_DIR}/cacert.pem"

# Determine SSM paths
CERT_PATH="/ndr/${PERSISTENT_ENVIRONMENT}/external_client_cert"
CERT_KEY="/ndr/${PERSISTENT_ENVIRONMENT}/external_client_key"

# Download client cert and key from SSM
aws ssm get-parameter --name "${CERT_PATH}" --with-decryption | jq -r '.Parameter.Value' > "${LOCAL_CERT_DIR}/client.crt"
aws ssm get-parameter --name "${CERT_KEY}" --with-decryption | jq -r '.Parameter.Value' > "${LOCAL_CERT_DIR}/client.key"

# Verify cert
openssl verify -CAfile "${LOCAL_CERT_DIR}/cacert.pem" "${LOCAL_CERT_DIR}/client.crt"
# shellcheck disable=SC2181 # - Ignored Check exit code directly as required nested ifs to work with above logic
if [[ $? -eq 0 ]]; then
    echo "The downloaded cert matches the Truststore PEM file"
else
    echo "The downloaded cert doesnt match the Truststore PEM file"
    exit 1
fi