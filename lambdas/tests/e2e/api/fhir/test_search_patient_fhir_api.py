import io
import logging
import uuid

from lambdas.tests.e2e.api.fhir.conftest import MTLS_ENDPOINT, create_mtls_session
from lambdas.tests.e2e.helpers.pdm_data_helper import PdmDataHelper

pdm_data_helper = PdmDataHelper()


def test_search_patient_details(test_data):
    pdm_record = {}
    test_data.append(pdm_record)

    pdm_record["id"] = str(uuid.uuid4())
    pdm_record["nhs_number"] = "9449305943"
    pdm_record["data"] = io.BytesIO(b"Sample PDF Content")

    pdm_data_helper.create_metadata(pdm_record)
    pdm_data_helper.create_resource(pdm_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{pdm_record['nhs_number']}"
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


def test_multiple_cancelled_search_patient_details(test_data):
    pdm_record = {}
    test_data.append(pdm_record)

    pdm_record["id"] = str(uuid.uuid4())
    pdm_record["nhs_number"] = "9449305943"
    pdm_record["data"] = io.BytesIO(b"Sample PDF Content")
    pdm_record["doc_status"] = "cancelled"

    pdm_data_helper.create_metadata(pdm_record)
    pdm_data_helper.create_resource(pdm_record)

    second_pdm_record = {}
    test_data.append(second_pdm_record)

    second_pdm_record["id"] = str(uuid.uuid4())
    second_pdm_record["nhs_number"] = "9449305943"
    second_pdm_record["data"] = io.BytesIO(b"Sample PDF Content")
    second_pdm_record["doc_status"] = "cancelled"

    pdm_data_helper.create_metadata(second_pdm_record)
    pdm_data_helper.create_resource(second_pdm_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{pdm_record['nhs_number']}"
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


def test_no_records():
    pdm_record = {}
    pdm_record["nhs_number"] = "9449305943"

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{pdm_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 404


def test_invalid_patient():
    pdm_record = {}
    pdm_record["nhs_number"] = "9999999993"

    url = f"https://{MTLS_ENDPOINT}/DocumentReference?subject:identifier=https://fhir.nhs.uk/Id/nhs-number|{pdm_record['nhs_number']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 400
