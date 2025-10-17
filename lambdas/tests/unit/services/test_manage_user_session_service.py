from unittest.mock import call

import pytest
from services.manage_user_session_access import ManageUserSessionAccess
from tests.unit.conftest import AUTH_SESSION_TABLE_NAME, TEST_NHS_NUMBER, TEST_UUID
from tests.unit.services.test_authoriser_service import (
    MOCK_CURRENT_SESSION,
    MOCK_SESSION_ID,
)
from utils.exceptions import AuthorisationException
from utils.request_context import request_context


@pytest.fixture(scope="function")
def mock_service(set_env, request, mocker):
    request_context.authorization = {"ndr_session_id": TEST_UUID}
    service = ManageUserSessionAccess()
    mocker.patch.object(service, "db_service")
    return service


@pytest.fixture()
def mock_permitted_search(mocker, mock_service):
    return mocker.patch.object(
        mock_service, "update_auth_session_with_permitted_search"
    )


@pytest.fixture()
def mock_find_login_session(mocker, mock_service):
    return mocker.patch.object(mock_service, "find_login_session")


@pytest.fixture()
def mock_updated_permitted_search_fields(mocker, mock_service):
    return mocker.patch.object(mock_service, "create_updated_permitted_search_fields")


@pytest.fixture()
def mock_update_auth_session_table_with_new_nhs_number(mocker, mock_service):
    return mocker.patch.object(
        mock_service, "update_auth_session_table_with_new_nhs_number"
    )


def test_update_auth_session_with_permitted_search_with_previous_search(
    mock_service, mock_updated_permitted_search_fields, mock_find_login_session
):

    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [TEST_NHS_NUMBER],
    }
    mock_service.update_auth_session_with_permitted_search(
        TEST_NHS_NUMBER, False, "GP_ADMIN"
    )

    mock_updated_permitted_search_fields.assert_not_called()
    mock_service.db_service.update_item.assert_not_called()


def test_update_auth_session_with_permitted_search_with_new_search_deceased_patient(
    mock_service,
    mock_update_auth_session_table_with_new_nhs_number,
    mock_find_login_session,
):
    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [],
    }

    mock_service.update_auth_session_with_permitted_search(
        TEST_NHS_NUMBER, True, "PCSE"
    )
    expected_calls = [
        call(
            field_name="DeceasedNHSNumbers",
            nhs_number=TEST_NHS_NUMBER,
            existing_nhs_numbers=[],
            ndr_session_id=TEST_UUID,
        ),
        call(
            field_name="AllowedNHSNumbers",
            nhs_number=TEST_NHS_NUMBER,
            existing_nhs_numbers=[],
            ndr_session_id=TEST_UUID,
        ),
    ]
    mock_update_auth_session_table_with_new_nhs_number.assert_has_calls(expected_calls)


def test_update_auth_session_with_permitted_search_with_new_search(
    mock_service,
    mock_update_auth_session_table_with_new_nhs_number,
    mock_find_login_session,
):
    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [],
    }
    mock_service.update_auth_session_with_permitted_search(
        TEST_NHS_NUMBER, False, "GP_ADMIN"
    )

    expected_calls = [
        call(
            field_name="AllowedNHSNumbers",
            nhs_number=TEST_NHS_NUMBER,
            existing_nhs_numbers=[],
            ndr_session_id=TEST_UUID,
        )
    ]
    mock_update_auth_session_table_with_new_nhs_number.assert_has_calls(expected_calls)


def test_update_auth_session_with_permitted_search_with_new_search_with_deceased_patient(
    mock_service,
    mock_update_auth_session_table_with_new_nhs_number,
    mock_find_login_session,
):
    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [],
    }

    mock_service.update_auth_session_with_permitted_search(
        TEST_NHS_NUMBER, True, "GP_ADMIN"
    )

    expected_calls = [
        call(
            field_name="DeceasedNHSNumbers",
            nhs_number=TEST_NHS_NUMBER,
            existing_nhs_numbers=[],
            ndr_session_id=TEST_UUID,
        )
    ]
    mock_update_auth_session_table_with_new_nhs_number.assert_has_calls(expected_calls)


def test_update_auth_session_table_with_new_nhs_number(
    mock_service, mock_updated_permitted_search_fields, mock_find_login_session
):
    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [TEST_NHS_NUMBER],
    }
    mock_updated_permitted_search_fields.return_value = {
        "AllowedNHSNumbers": TEST_NHS_NUMBER
    }

    mock_service.update_auth_session_table_with_new_nhs_number(
        "AllowedNHSNumbers", TEST_NHS_NUMBER, "", TEST_UUID
    )

    mock_updated_permitted_search_fields.assert_called_once_with(
        field_name="AllowedNHSNumbers",
        nhs_number=TEST_NHS_NUMBER,
        existing_nhs_numbers="",
    )
    mock_service.db_service.update_item.assert_called_once_with(
        table_name=AUTH_SESSION_TABLE_NAME,
        key_pair={"NDRSessionId": TEST_UUID},
        updated_fields={"AllowedNHSNumbers": TEST_NHS_NUMBER},
    )


def test_update_auth_session_with_permitted_search_with_new_search_existing_list_of_allows(
    mock_service, mock_updated_permitted_search_fields, mock_find_login_session
):
    existing_nhs_number_search = "9000000000"
    expected_list = f"{existing_nhs_number_search},{TEST_NHS_NUMBER}"
    mock_find_login_session.return_value = {
        "DeceasedNHSNumbers": [],
        "AllowedNHSNumbers": [existing_nhs_number_search],
    }
    mock_updated_permitted_search_fields.return_value = {
        "AllowedNHSNumbers": expected_list
    }

    mock_service.update_auth_session_with_permitted_search(
        TEST_NHS_NUMBER, False, "GP_ADMIN"
    )

    mock_updated_permitted_search_fields.assert_called_once_with(
        field_name="AllowedNHSNumbers",
        nhs_number=TEST_NHS_NUMBER,
        existing_nhs_numbers=[existing_nhs_number_search],
    )
    mock_service.db_service.update_item.assert_called_once_with(
        table_name=AUTH_SESSION_TABLE_NAME,
        key_pair={"NDRSessionId": TEST_UUID},
        updated_fields={
            "AllowedNHSNumbers": f"{existing_nhs_number_search},{TEST_NHS_NUMBER}"
        },
    )


@pytest.mark.parametrize(
    ["nhs_number", "allowed_nhs_numbers", "expected"],
    [
        (
            "9000000001",
            "9000000000",
            {"AllowedNHSNumbers": "9000000000,9000000001"},
        ),
        (
            "9000000000",
            "",
            {"AllowedNHSNumbers": "9000000000"},
        ),
    ],
)
def test_create_updated_permitted_search_fields(
    mock_service, nhs_number, allowed_nhs_numbers, expected
):
    actual = mock_service.create_updated_permitted_search_fields(
        field_name="AllowedNHSNumbers",
        nhs_number=nhs_number,
        existing_nhs_numbers=allowed_nhs_numbers,
    )
    assert actual == expected


def test_find_login_session(mocker, mock_service):
    expected = MOCK_CURRENT_SESSION
    valid_session_record = [
        {
            "NDRSessionId": "test_session_id",
            "sid": "test_cis2_session_id",
            "Subject": "test_cis2_user_id",
            "TimeToExist": 12345678960,
            "AllowedNHSNumbers": "12,34,12,534",
        }
    ]
    dynamo_service = mocker.patch.object(mock_service.db_service, "query_table")
    dynamo_service.return_value = valid_session_record

    actual = mock_service.find_login_session(MOCK_SESSION_ID)

    assert expected == actual


def test_find_login_session_raises_auth_exception(mocker, mock_service):
    invalid_session_record = []
    dynamo_service = mocker.patch.object(mock_service.db_service, "query_table")
    dynamo_service.return_value = invalid_session_record

    with pytest.raises(AuthorisationException):
        mock_service.find_login_session("test session id")
