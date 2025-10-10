import os
import time

import pytest
import requests
from syrupy.extensions.json import JSONSnapshotExtension
from tests.e2e.helpers.lloyd_george_data_helper import LloydGeorgeDataHelper

data_helper = LloydGeorgeDataHelper()

LLOYD_GEORGE_SNOMED = 16521000000101
APIM_ENDPOINT = "internal-dev.api.service.nhs.uk"

# All config pulled from environment variables
LG_METADATA_TABLE = os.environ["LG_METADATA_TABLE"]
LG_UNSTITCHED_TABLE = os.environ["LG_UNSTITCHED_TABLE"]
BULK_REPORT_TABLE = os.environ["BULK_REPORT_TABLE"]
LLOYD_GEORGE_S3_BUCKET = os.environ["NDR_S3_BUCKET"]
API_ENDPOINT = os.environ["NDR_API_ENDPOINT"]
MTLS_ENDPOINT = os.environ["MTLS_ENDPOINT"]
CLIENT_CERT_PATH = os.environ["TESTING_CLIENT_CERT_PATH"]
CLIENT_KEY_PATH = os.environ["TESTING_CLIENT_KEY_PATH"]


@pytest.fixture
def test_data():
    test_records = []
    yield test_records
    for record in test_records:
        data_helper.tidyup(record)


def fetch_with_retry_mtls(
    session, url, condition_func, headers, max_retries=5, delay=10
):
    retries = 0
    while retries < max_retries:
        response = session.get(url, headers=headers)
        try:
            response_json = response.json()
        except ValueError:
            response_json = {}

        if condition_func(response_json):
            return response

        time.sleep(delay)
        retries += 1

    raise Exception("Condition not met within retry limit")


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.with_defaults(extension_class=JSONSnapshotExtension)


def create_mtls_session():
    session = requests.Session()
    session.cert = (CLIENT_CERT_PATH, CLIENT_KEY_PATH)
    return session
