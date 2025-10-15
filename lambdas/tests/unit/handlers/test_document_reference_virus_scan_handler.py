from unittest.mock import call

import pytest
from handlers.document_reference_virus_scan_handler import lambda_handler


@pytest.fixture
def mocked_service(set_env, mocker):
    mocked_class = mocker.patch(
        "handlers.document_reference_virus_scan_handler.UploadDocumentReferenceService"
    )
    mocked_service = mocked_class.return_value
    yield mocked_service


def test_lambda_handler_returns_200(mocked_service, context):
    object_key = "user_upload/test_file.pdf"
    file_size = 104857
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "staging-bulk-store"},
                    "object": {"key": object_key, "size": file_size},
                }
            }
        ]
    }

    lambda_handler(event, context)

    mocked_service.handle_upload_document_reference_request.assert_called_once_with(
        object_key, file_size
    )


def test_lambda_handler_returns_200_multiple_objects(mocked_service, context):
    object_key_1 = "user_upload/test_file.pdf"
    object_key_2 = "user_upload/test_file2.pdf"

    file_size = 104857
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "staging-bulk-store"},
                    "object": {"key": object_key_1, "size": file_size},
                }
            },
            {
                "s3": {
                    "bucket": {"name": "staging-bulk-store"},
                    "object": {"key": object_key_2, "size": file_size},
                }
            },
        ]
    }

    lambda_handler(event, context)

    mocked_service.handle_upload_document_reference_request.assert_has_calls(
        [call(object_key_1, file_size), call(object_key_2, file_size)]
    )
