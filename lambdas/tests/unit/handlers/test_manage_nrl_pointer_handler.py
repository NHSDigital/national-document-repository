import pytest
from enums.snomed_codes import SnomedCodes
from handlers.manage_nrl_pointer_handler import lambda_handler
from models.fhir.R4.fhir_document_reference import Attachment
from models.sqs.nrl_sqs_message import NrlSqsMessage
from utils.exceptions import NrlApiException

@pytest.fixture
def mock_service(mocker):
    mocked_class = mocker.patch("handlers.manage_nrl_pointer_handler.NrlApiService")
    mocked_instance = mocked_class.return_value
    mocked_class.return_value.end_user_ods_code = "NRL"
    return mocked_instance


def build_test_sqs_message(action="create"):
    doc_details = Attachment(url="https://example.org/my-doc.pdf", title="lg_record")
    sqs_message = NrlSqsMessage(
        nhs_number="123456789",
        action=action,
        snomed_code_doc_type=SnomedCodes.LLOYD_GEORGE.value,
        snomed_code_category=SnomedCodes.CARE_PLAN.value,
        attachment=doc_details,
    ).model_dump_json()
    return {
        "body": sqs_message,
        "eventSource": "aws:sqs",
    }


def test_process_event_with_one_message(mock_service, context, set_env):
    event = {"Records": [build_test_sqs_message("create")]}
    lambda_handler(event, context)

    mock_service.create_new_pointer.assert_called_once()


def test_process_delete_event_with_one_message(mock_service, context, set_env):
    event = {"Records": [build_test_sqs_message("delete")]}
    lambda_handler(event, context)
    mock_service.delete_pointer.assert_called_once()


def test_process_event_with_multiple_messages(mock_service, context, set_env):
    event = {
        "Records": [build_test_sqs_message("create"), build_test_sqs_message("delete")]
    }
    lambda_handler(event, context)
    mock_service.create_new_pointer.assert_called_once()
    mock_service.delete_pointer.assert_called_once()


def test_failed_to_create_a_pointer(mock_service, context, set_env, caplog):
    event = {"Records": [build_test_sqs_message("create")]}
    expected_log = "Failed to process current message due to error: test exception"
    mock_service.create_new_pointer.side_effect = NrlApiException("test exception")
    with pytest.raises(NrlApiException):
        lambda_handler(event, context)
    assert any(expected_log in record.message for record in caplog.records)
    mock_service.create_new_pointer.assert_called_once()


def test_process_event_with_invalid_action(mock_service, context, set_env, caplog):
    event = {"Records": [build_test_sqs_message("invalid_action")]}

    lambda_handler(event, context)

    mock_service.create_new_pointer.assert_not_called()
    mock_service.delete_pointer.assert_not_called()
