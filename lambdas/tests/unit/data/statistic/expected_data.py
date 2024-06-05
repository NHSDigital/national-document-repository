from datetime import datetime

from models.statistics import ApplicationData, OrganisationData, RecordStoreData
from tests.unit.data.statistic.mock_logs_query_results import (
    HASHED_USER_ID_1,
    HASHED_USER_ID_2,
)
from unit.data.statistic.mock_dynamodb_and_s3_records import (
    TOTAL_FILE_SIZE_FOR_H81109,
    TOTAL_FILE_SIZE_FOR_Y12345,
)

TODAY_DATE = datetime.today().strftime("%Y%m%d")

MOCK_RECORD_STORE_DATA = [
    RecordStoreData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="H81109",
        total_number_of_records=6,
        number_of_document_types=2,
        total_size_of_records_in_megabytes=TOTAL_FILE_SIZE_FOR_H81109,
        average_size_of_documents_per_patient_in_megabytes=TOTAL_FILE_SIZE_FOR_H81109
        / 2,
    ),
    RecordStoreData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="Y12345",
        total_number_of_records=2,
        number_of_document_types=2,
        total_size_of_records_in_megabytes=TOTAL_FILE_SIZE_FOR_Y12345,
        average_size_of_documents_per_patient_in_megabytes=TOTAL_FILE_SIZE_FOR_Y12345,
    ),
]

MOCK_ORGANISATION_DATA = [
    OrganisationData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="H81109",
        number_of_patients=2,
        average_records_per_patient=3,
        daily_count_stored=4,
        daily_count_viewed=40,
        daily_count_downloaded=20,
        daily_count_deleted=2,
    ),
    OrganisationData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="Y12345",
        number_of_patients=1,
        average_records_per_patient=2,
        daily_count_stored=2,
        daily_count_viewed=20,
        daily_count_downloaded=10,
        daily_count_deleted=1,
    ),
]

MOCK_APPLICATION_DATA = [
    ApplicationData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="H81109",
        active_user_ids_hashed=[HASHED_USER_ID_1, HASHED_USER_ID_2],
    ),
    ApplicationData(
        statistic_id="mock_uuid",
        date=TODAY_DATE,
        ods_code="Y12345",
        active_user_ids_hashed=[HASHED_USER_ID_1],
    ),
]
