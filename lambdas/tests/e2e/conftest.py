import os
import time

import pytest
import requests
from tests.e2e.helpers.lloyd_george_data_helper import LloydGeorgeDataHelper

data_helper = LloydGeorgeDataHelper()

LLOYD_GEORGE_SNOMED = 16521000000101
API_ENDPOINT = os.environ.get("NDR_API_ENDPOINT")
API_KEY = os.environ.get("NDR_API_KEY")
LLOYD_GEORGE_S3_BUCKET = os.environ.get("NDR_S3_BUCKET") or ""


@pytest.fixture
def test_data():
    test_records = []
    yield test_records
    for record in test_records:
        data_helper.tidyup(record)


def fetch_with_retry(url, condition_func, max_retries=5, delay=10):
    retries = 0
    while retries < max_retries:
        headers = {"Authorization": "Bearer 123", "X-Api-Key": API_KEY}
        response = requests.get(url, headers=headers)
        if condition_func(response.json()):
            return response
        time.sleep(delay)
        retries += 1
    raise Exception("Condition not met within retry limit")
