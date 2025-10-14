from copy import deepcopy

from models.report.bulk_upload_report import BulkUploadReport
from tests.unit.conftest import TEST_UUID

TEST_UPLOADER_ODS_1 = "Y12345"
TEST_UPLOADER_ODS_2 = "Z12345"

MOCK_REPORT_ITEMS_FOR_UPLOADER_1 = [
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000000",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "SUSP",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000001",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Patient is deceased - INFORMAL",
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "DECE",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000002",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "REST",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000003",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000003",
        "FilePath": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Could not find the given patient on PDS",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000004",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000004",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000005",
        "FilePath": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Could not find the given patient on PDS",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000006",
        "FilePath": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Could not find the given patient on PDS",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000006",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Lloyd George file already exists",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000007",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_1,
        "Reason": "Lloyd George file already exists",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
]

MOCK_REPORT_ITEMS_FOR_UPLOADER_2 = [
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000009",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "SUSP",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000010",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "Reason": "Patient is deceased - FORMAL",
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "DECE",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000011",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "REST",
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000012",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000012",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_1,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000013",
        "FilePath": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of1_Lloyd_George_Record_[NAME]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "UploadStatus": "complete",
        "ID": TEST_UUID,
        "PdsOdsCode": "Z12345",
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000014",
        "FilePath": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "Reason": "Could not find the given patient on PDS",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
    {
        "Timestamp": 1688395681,
        "Date": "2012-01-13",
        "NhsNumber": "9000000015",
        "FilePath": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/1of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "Reason": "Could not find the given patient on PDS",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000015",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "Reason": "Lloyd George file already exists",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
    {
        "Timestamp": 1688395680,
        "Date": "2012-01-13",
        "NhsNumber": "9000000016",
        "FilePath": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "StoredFileName": "/0000000000/2of2_Lloyd_George_Record_[NAME_2]_[0000000000]_[DOB].pdf",
        "UploaderOdsCode": TEST_UPLOADER_ODS_2,
        "Reason": "Lloyd George file already exists",
        "UploadStatus": "failed",
        "ID": TEST_UUID,
        "PdsOdsCode": TEST_UPLOADER_ODS_2,
    },
]

MOCK_REPORT_RESPONSE_ALL = {
    "Items": MOCK_REPORT_ITEMS_FOR_UPLOADER_1 + MOCK_REPORT_ITEMS_FOR_UPLOADER_2,
    "Count": 4,
    "ScannedCount": 4,
}

MOCK_REPORT_RESPONSE_ALL_WITH_LAST_KEY = deepcopy(MOCK_REPORT_RESPONSE_ALL)
MOCK_REPORT_RESPONSE_ALL_WITH_LAST_KEY.update(
    {
        "LastEvaluatedKey": {
            "FilePath": "/9000000010/2of2_Lloyd_George_Record_[NAME_2]_[9000000010]_[DOB].pdf"
        }
    }
)

MOCK_REPORT_ITEMS_ALL = [
    BulkUploadReport.model_validate(item) for item in MOCK_REPORT_RESPONSE_ALL["Items"]
]

MOCK_REPORT_ITEMS_UPLOADER_1 = [
    BulkUploadReport.model_validate(item) for item in MOCK_REPORT_ITEMS_FOR_UPLOADER_1
]

MOCK_REPORT_ITEMS_UPLOADER_2 = [
    BulkUploadReport.model_validate(item) for item in MOCK_REPORT_ITEMS_FOR_UPLOADER_2
]
