import io
import uuid

from tests.e2e.helpers.pdm_data_helper import PdmDataHelper

from lambdas.tests.e2e.api.fhir.conftest import (
    MTLS_ENDPOINT,
    PDM_S3_BUCKET,
    PDM_SNOMED,
    create_mtls_session,
)

pdm_data_helper = PdmDataHelper()


def test_small_file(test_data, snapshot_json):
    lloyd_george_record = {}
    test_data.append(lloyd_george_record)

    lloyd_george_record["id"] = str(uuid.uuid4())
    lloyd_george_record["nhs_number"] = "9449305943"
    lloyd_george_record["data"] = io.BytesIO(b"Sample PDF Content")

    pdm_data_helper.create_metadata(lloyd_george_record)
    pdm_data_helper.create_resource(lloyd_george_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference/{PDM_SNOMED}~{lloyd_george_record['id']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 200

    # json = response.json()
    # assert json == snapshot_json(exclude=paths("date", "id"))


def test_large_file(test_data, snapshot_json):
    lloyd_george_record = {}
    test_data.append(lloyd_george_record)

    lloyd_george_record["id"] = str(uuid.uuid4())
    lloyd_george_record["nhs_number"] = "9449305943"
    lloyd_george_record["data"] = io.BytesIO(b"A" * (10 * 1024 * 1024))
    lloyd_george_record["size"] = 10 * 1024 * 1024 * 1024

    pdm_data_helper.create_metadata(lloyd_george_record)
    pdm_data_helper.create_resource(lloyd_george_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference/{PDM_SNOMED}~{lloyd_george_record['id']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }

    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 200

    json = response.json()
    expected_presign_uri = f"https://{PDM_S3_BUCKET}.s3.eu-west-2.amazonaws.com/{lloyd_george_record['nhs_number']}/{lloyd_george_record['id']}"
    assert expected_presign_uri in json["content"][0]["attachment"]["url"]

    # assert json == snapshot_json(
    #     exclude=paths("date", "id", "content.0.attachment.url")
    # )


def test_no_file_found(snapshot_json):
    lloyd_george_record = {}
    lloyd_george_record["id"] = str(uuid.uuid4())

    url = f"https://{MTLS_ENDPOINT}/DocumentReference/{PDM_SNOMED}~{lloyd_george_record['id']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }
    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 404

    # json = response.json()
    # assert json == snapshot_json


def test_preliminary_file(test_data, snapshot_json):
    lloyd_george_record = {}
    test_data.append(lloyd_george_record)

    lloyd_george_record["id"] = str(uuid.uuid4())
    lloyd_george_record["nhs_number"] = "9449305943"
    lloyd_george_record["data"] = io.BytesIO(b"Sample PDF Content")
    lloyd_george_record["doc_status"] = "preliminary"

    pdm_data_helper.create_metadata(lloyd_george_record)
    pdm_data_helper.create_resource(lloyd_george_record)

    url = f"https://{MTLS_ENDPOINT}/DocumentReference/{PDM_SNOMED}~{lloyd_george_record['id']}"
    headers = {
        "Authorization": "Bearer 123",
        "X-Correlation-Id": "1234",
    }

    # Use mTLS
    session = create_mtls_session()
    response = session.get(url, headers=headers)
    assert response.status_code == 200

    # json = response.json()
    # assert json == snapshot_json(exclude=paths("date", "id"))
