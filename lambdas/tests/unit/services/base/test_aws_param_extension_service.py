from datetime import datetime

from services.base.ssm_service import SSMService

MOCK_SSM_PARAMETERS_RESPONSE = {
    "Parameters": [
        {
            "Name": "ssm_parameter_key",
            "Type": "SecureString",
            "Value": "string",
            "Version": 123,
            "Selector": "string",
            "SourceResult": "string",
            "LastModifiedDate": datetime(2015, 1, 1),
            "ARN": "string",
            "DataType": "string",
        },
        {
            "Name": "another_key",
            "Type": "SecureString",
            "Value": "string",
            "Version": 123,
            "Selector": "string",
            "SourceResult": "string",
            "LastModifiedDate": datetime(2015, 1, 1),
            "ARN": "string",
            "DataType": "string",
        },
    ],
}

MOCK_SSM_PARAMETER_RESPONSE = {
    "Parameter": {
        "Name": "ssm_parameter_key",
        "Type": "String",
        "Value": "string",
        "Version": 123,
        "Selector": "string",
        "SourceResult": "string",
        "LastModifiedDate": datetime(2015, 1, 1),
        "ARN": "string",
        "DataType": "string",
    }
}


def test_get_ssm_parameter(mocker):
    mocker.patch("boto3.client")
    service = SSMService()
    mock_get_parameter = mocker.patch.object(service.client, "get_parameter")
    mock_get_parameter.return_value = MOCK_SSM_PARAMETER_RESPONSE
    actual = service.get_ssm_parameter(parameter_key="ssm_parameter_key")

    mock_get_parameter.assert_called_once_with(
        Name="ssm_parameter_key", WithDecryption=False
    )
    assert actual == "string"


def test_get_ssm_parameters(mocker):
    mocker.patch("boto3.client")
    service = SSMService()
    mock_get_parameters = mocker.patch.object(service.client, "get_parameters")
    mock_get_parameters.return_value = MOCK_SSM_PARAMETERS_RESPONSE
    actual = service.get_ssm_parameters(
        parameters_keys=["ssm_parameter_key", "another_key"]
    )
    expected = {"ssm_parameter_key": "string", "another_key": "string"}

    mock_get_parameters.assert_called_once_with(
        Names=["ssm_parameter_key", "another_key"], WithDecryption=False
    )
    assert actual == expected


def test_update_ssm_parameter(mocker):
    mocker.patch("boto3.client")
    service = SSMService()
    mock_put_parameter = mocker.patch.object(service.client, "put_parameter")
    service.update_ssm_parameter(
        parameter_key="ssm_parameter_key",
        parameter_value="parameter_value",
        parameter_type="SecureString",
    )

    mock_put_parameter.assert_called_once_with(
        Name="ssm_parameter_key",
        Value="parameter_value",
        Type="SecureString",
        Overwrite=True,
    )
