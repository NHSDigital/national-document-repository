#!/bin/bash
set -euo pipefail

# Default environment/sandbox value (can be overridden with --env)
ENVIRONMENT="ndr-dev"

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --env) ENVIRONMENT="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Selected environment: $ENVIRONMENT"
# Set environment variables
source ./scripts/test/set-e2e-env-vars.sh $ENVIRONMENT

echo "Running E2E tests with:" #todo output all vars here?
echo "LG_METADATA_TABLE=$LG_METADATA_TABLE"
echo "LG_UNSTITCHED_TABLE=$LG_UNSTITCHED_TABLE"
echo "BULK_REPORT_TABLE=$BULK_REPORT_TABLE"
echo "NDR_S3_BUCKET=$NDR_S3_BUCKET"
echo "NDR_API_ENDPOINT=$NDR_API_ENDPOINT"
echo "MTLS_ENDPOINT=$MTLS_ENDPOINT"


# Run the tests
cd ./lambdas
./venv/bin/python3 -m pytest tests/e2e/api -vv