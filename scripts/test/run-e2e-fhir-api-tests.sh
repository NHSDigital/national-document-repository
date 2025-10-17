#!/bin/bash
set -euo pipefail

# Default environment/sandbox value (can be overridden with --workspace)
WORKSPACE="ndr-dev"

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --workspace) WORKSPACE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Selected workspace: $WORKSPACE"
# Set environment variables
source ./scripts/test/set-e2e-env-vars.sh $WORKSPACE

echo "Running FHIR api E2E tests with:"
echo "PDM_METADATA_TABLE=$PDM_METADATA_TABLE"
echo "PDM_S3_BUCKET=$PDM_S3_BUCKET"
echo "MTLS_ENDPOINT=$MTLS_ENDPOINT"
echo "CLIENT_CERT_PATH=$CLIENT_CERT_PATH"
echo "CLIENT_KEY_PATH=$CLIENT_KEY_PATH"


# Run the tests
cd ./lambdas
./venv/bin/python3 -m pytest tests/e2e/api/fhir -vv