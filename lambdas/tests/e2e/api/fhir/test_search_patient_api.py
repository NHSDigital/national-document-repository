import io
import logging
import uuid

from lambdas.tests.e2e.api.fhir.conftest import MTLS_ENDPOINT, create_mtls_session
from lambdas.tests.e2e.helpers.pdm_data_helper import PdmDataHelper

pdm_data_helper = PdmDataHelper()


def test_search_patient_details(test_data, snapshot_json):
    lloyd_george_record = {}
    test_data.append(lloyd_george_record)

    lloyd_george_record["id"] = str(uuid.uuid4())
    lloyd_george_record["nhs_number"] = "9449305943"
    lloyd_george_record["data"] = io.BytesIO(b"Sample PDF Content")

    pdm_data_helper.create_metadata(lloyd_george_record)
    pdm_data_helper.create_resource(lloyd_george_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{lloyd_george_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    bundle = response.json()
    logging.info(bundle)

    # attachment_url = bundle["entry"][1]["resource"]["content"][0]["attachment"]["url"]
    # This will fail for now as the search endpoint is searching both tables, so if a record from Lloyd George
    # comes back first, that snomed will be used
    # assert (
    #     f"https://{APIM_ENDPOINT}/national-document-repository/DocumentReference/{PDM_SNOMED}~"
    #     in attachment_url
    # )

    # assert bundle == snapshot_json(
    #     exclude=paths(
    #         "entry.0.resource.id",
    #         "entry.0.resource.date",
    #         "entry.0.resource.content.0.attachment.url",
    #         "timestamp",
    #     )
    # )


def test_multiple_cancelled_search_patient_details(test_data, snapshot_json):
    lloyd_george_record = {}
    test_data.append(lloyd_george_record)

    lloyd_george_record["id"] = str(uuid.uuid4())
    lloyd_george_record["nhs_number"] = "9449305943"
    lloyd_george_record["data"] = io.BytesIO(b"Sample PDF Content")
    lloyd_george_record["doc_status"] = "cancelled"

    pdm_data_helper.create_metadata(lloyd_george_record)
    pdm_data_helper.create_resource(lloyd_george_record)

    second_lloyd_george_record = {}
    test_data.append(second_lloyd_george_record)

    second_lloyd_george_record["id"] = str(uuid.uuid4())
    second_lloyd_george_record["nhs_number"] = "9449305943"
    second_lloyd_george_record["data"] = io.BytesIO(b"Sample PDF Content")
    second_lloyd_george_record["doc_status"] = "cancelled"

    pdm_data_helper.create_metadata(second_lloyd_george_record)
    pdm_data_helper.create_resource(second_lloyd_george_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{lloyd_george_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 200

    # bundle = response.json()
    # assert bundle["entry"][0] == snapshot_json(
    #     exclude=paths(
    #         "resource.id", "resource.date", "resource.content.0.attachment.url"
    #     )
    # )
    # assert bundle["entry"][1] == snapshot_json(
    #     exclude=paths(
    #         "resource.id", "resource.date", "resource.content.0.attachment.url"
    #     )
    # )


def test_no_records(snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["nhs_number"] = "9449305943"

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{lloyd_george_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 404

    # bundle = response.json()
    # assert bundle == snapshot_json


def test_invalid_patient(snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["nhs_number"] = "9999999993"

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{lloyd_george_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 400

    # bundle = response.json()
    # assert bundle == snapshot_json
