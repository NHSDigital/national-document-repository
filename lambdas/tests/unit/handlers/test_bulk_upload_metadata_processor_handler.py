import pytest
from handlers.bulk_upload_metadata_processor_handler import lambda_handler
from services.bulk_upload_metadata_processor_service import (
    BulkUploadMetadataProcessorService,
)


@pytest.fixture
def mock_metadata_service(mocker):
    mocked_instance = mocker.patch(
        "handlers.bulk_upload_metadata_processor_handler.BulkUploadMetadataProcessorService",
        spec=BulkUploadMetadataProcessorService,
    ).return_value
    return mocked_instance


def test_metadata_processor_lambda_handler_valid_event(
    set_env, context, mock_metadata_service
):
    lambda_handler({"practiceDirectory": "test"}, context)

    mock_metadata_service.process_metadata.assert_called_once()


def test_metadata_processor_lambda_handler_empty_event(
    set_env, context, mock_metadata_service
):
    lambda_handler({}, context)

    mock_metadata_service.process_metadata.assert_not_called()
