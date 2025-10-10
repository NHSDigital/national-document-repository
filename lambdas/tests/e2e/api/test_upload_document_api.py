import base64
import json
import logging
import os

import requests
from syrupy.filters import paths
from tests.e2e.conftest import (
    APIM_ENDPOINT,
    LLOYD_GEORGE_S3_BUCKET,
    LLOYD_GEORGE_SNOMED,
    MTLS_ENDPOINT,
    fetch_with_retry_mtls,
)
from tests.e2e.helpers.lloyd_george_data_helper import LloydGeorgeDataHelper

from lambdas.tests.e2e.conftest import create_mtls_session

data_helper = LloydGeorgeDataHelper()


def create_upload_payload(lloyd_george_record):
    sample_payload = {
        "resourceType": "DocumentReference",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": f"{LLOYD_GEORGE_SNOMED}",
                    "display": "Lloyd George record folder",
                }
            ]
        },
        "subject": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/nhs-number",
                "value": lloyd_george_record["nhs_number"],
            }
        },
        "author": [
            {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": lloyd_george_record["ods"],
                }
            }
        ],
        "custodian": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": lloyd_george_record["ods"],
            }
        },
        "content": [
            {
                "attachment": {
                    "creation": "2023-01-01",
                    "contentType": "application/pdf",
                    "language": "en-GB",
                    "title": "1of1_Lloyd_George_Record_[Paula Esme VESEY]_[9730153973]_[22-01-1960].pdf",
                }
            }
        ],
    }

    if "data" in lloyd_george_record:
        sample_payload["content"][0]["attachment"]["data"] = lloyd_george_record["data"]
    return json.dumps(sample_payload)


def test_create_document_base64(test_data, snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["ods"] = "H81109"
    lloyd_george_record["nhs_number"] = "9449303304"
    sample_pdf_path = os.path.join(os.path.dirname(__file__), "files", "dummy.pdf")
    with open(sample_pdf_path, "rb") as f:
        lloyd_george_record["data"] = base64.b64encode(f.read()).decode("utf-8")

    payload = create_upload_payload(lloyd_george_record)
    url = f"https://{MTLS_ENDPOINT}/DocumentReference"
    headers = {"Authorization": "Bearer 123"}

    # Use mTLS
    session = create_mtls_session()
    retrieve_response = session.post(url, headers=headers, data=payload)

    upload_response = retrieve_response.json()
    lloyd_george_record["id"] = upload_response["id"].split("~")[1]
    test_data.append(lloyd_george_record)

    retrieve_url = f"https://{MTLS_ENDPOINT}/DocumentReference/{upload_response['id']}"

    def condition(response_json):
        logging.info(response_json)
        return response_json["content"][0]["attachment"].get("data", False)

    raw_retrieve_response = fetch_with_retry_mtls(
        session, retrieve_url, condition, headers
    )
    retrieve_response = raw_retrieve_response.json()

    attachment_url = upload_response["content"][0]["attachment"]["url"]
    assert (
        f"https://{APIM_ENDPOINT}/national-document-repository/DocumentReference/{LLOYD_GEORGE_SNOMED}~"
        in attachment_url
    )

    base64_data = retrieve_response["content"][0]["attachment"]["data"]
    assert base64.b64decode(base64_data, validate=True)

    assert upload_response == snapshot_json(
        exclude=paths("id", "date", "content.0.attachment.url")
    )
    assert retrieve_response == snapshot_json(
        exclude=paths("id", "date", "content.0.attachment.data")
    )


def test_create_document_presign(test_data, snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["ods"] = "H81109"
    lloyd_george_record["nhs_number"] = "9449303304"

    payload = create_upload_payload(lloyd_george_record)
    url = f"https://{MTLS_ENDPOINT}/DocumentReference"
    headers = {"Authorization": "Bearer 123"}

    # Use mTLS
    session = create_mtls_session()
    retrieve_response = session.post(url, headers=headers, data=payload)

    upload_response = retrieve_response.json()
    lloyd_george_record["id"] = upload_response["id"].split("~")[1]
    test_data.append(lloyd_george_record)
    presign_uri = upload_response["content"][0]["attachment"]["url"]
    del upload_response["content"][0]["attachment"]["url"]

    sample_pdf_path = os.path.join(os.path.dirname(__file__), "files", "big-dummy.pdf")
    with open(sample_pdf_path, "rb") as f:
        files = {"file": f}
        presign_response = requests.put(presign_uri, files=files)
        assert presign_response.status_code == 200

    retrieve_url = f"https://{MTLS_ENDPOINT}/DocumentReference/{upload_response['id']}"

    def condition(response_json):
        logging.info(response_json)
        return response_json["content"][0]["attachment"].get("url", False)

    raw_retrieve_response = fetch_with_retry_mtls(
        session, retrieve_url, condition, headers
    )
    retrieve_response = raw_retrieve_response.json()

    expected_presign_uri = f"https://{LLOYD_GEORGE_S3_BUCKET}.s3.eu-west-2.amazonaws.com/{lloyd_george_record['nhs_number']}/{lloyd_george_record['id']}"
    assert expected_presign_uri in retrieve_response["content"][0]["attachment"]["url"]

    assert isinstance(retrieve_response["content"][0]["attachment"]["size"], (int))

    assert upload_response == snapshot_json(exclude=paths("id", "date"))
    assert retrieve_response == snapshot_json(
        exclude=paths(
            "id", "date", "content.0.attachment.url", "content.0.attachment.size"
        )
    )


def test_create_document_virus(test_data, snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["ods"] = "H81109"

    lloyd_george_record["nhs_number"] = "9730154260"

    payload = create_upload_payload(lloyd_george_record)
    url = f"https://{MTLS_ENDPOINT}/DocumentReference"
    headers = {"Authorization": "Bearer 123"}

    # Use mTLS
    session = create_mtls_session()
    retrieve_response = session.post(url, headers=headers, data=payload)
    upload_response = retrieve_response.json()
    lloyd_george_record["id"] = upload_response["id"].split("~")[1]
    test_data.append(lloyd_george_record)
    presign_uri = upload_response["content"][0]["attachment"]["url"]
    del upload_response["content"][0]["attachment"]["url"]

    sample_pdf_path = os.path.join(os.path.dirname(__file__), "files", "dummy.pdf")
    with open(sample_pdf_path, "rb") as f:
        files = {"file": f}
        presign_response = requests.put(presign_uri, files=files)
        assert presign_response.status_code == 200

    retrieve_url = f"https://{MTLS_ENDPOINT}/DocumentReference/{upload_response['id']}"

    def condition(response_json):
        logging.info(response_json)
        return response_json.get("docStatus", False) == "cancelled"

    raw_retrieve_response = fetch_with_retry_mtls(
        session, retrieve_url, condition, headers
    )
    retrieve_response = raw_retrieve_response.json()

    assert upload_response == snapshot_json(exclude=paths("id", "date"))
    assert retrieve_response == snapshot_json(exclude=paths("id", "date"))
