import base64
import json
import os

from tests.e2e.conftest import APIM_ENDPOINT

from lambdas.tests.e2e.api.fhir.conftest import (
    MTLS_ENDPOINT,
    PDM_SNOMED,
    create_mtls_session,
    fetch_with_retry_mtls,
)


def create_upload_payload(pdm_record):
    sample_payload = {
        "resourceType": "DocumentReference",
        "type": {
            "coding": [
                {
                    "system": "https://snomed.info/sct",
                    "code": f"{PDM_SNOMED}",
                    "display": "Confidential patient data",
                }
            ]
        },
        "subject": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/nhs-number",
                "value": pdm_record["nhs_number"],
            }
        },
        "author": [
            {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": pdm_record["ods"],
                }
            }
        ],
        "custodian": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": pdm_record["ods"],
            }
        },
        "content": [
            {
                "attachment": {
                    "creation": "2023-01-01",
                    "contentType": "application/pdf",
                    "language": "en-GB",
                    "title": "1of1_pdm_record_[Paula Esme VESEY]_[9730153973]_[22-01-1960].pdf",
                }
            }
        ],
    }

    if "data" in pdm_record:
        sample_payload["content"][0]["attachment"]["data"] = pdm_record["data"]
    return json.dumps(sample_payload)


def test_create_document_base64(test_data):
    pdm_record = {}
    pdm_record["ods"] = "H81109"
    pdm_record["nhs_number"] = "9449303304"
    sample_pdf_path = os.path.join(os.path.dirname(__file__), "files", "dummy.pdf")
    with open(sample_pdf_path, "rb") as f:
        pdm_record["data"] = base64.b64encode(f.read()).decode("utf-8")

    payload = create_upload_payload(pdm_record)
    url = f"https://{MTLS_ENDPOINT}/DocumentReference"
    headers = {"Authorization": "Bearer 123"}

    # Use mTLS
    session = create_mtls_session()
    retrieve_response = session.post(url, headers=headers, data=payload)
    upload_response = retrieve_response.json()
    pdm_record["id"] = upload_response["id"].split("~")[1]
    test_data.append(pdm_record)

    retrieve_url = f"https://{MTLS_ENDPOINT}/DocumentReference/{upload_response['id']}"

    raw_retrieve_response = fetch_with_retry_mtls(session, retrieve_url, headers)
    retrieve_response = raw_retrieve_response.json()

    attachment_url = upload_response["content"][0]["attachment"]["url"]
    assert (
        f"https://{APIM_ENDPOINT}/national-document-repository/DocumentReference/{PDM_SNOMED}~"
        in attachment_url
    )
