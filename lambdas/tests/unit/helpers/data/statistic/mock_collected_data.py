from datetime import datetime, timedelta

from models.statistics import (
    ApplicationData,
    OrganisationData,
    RecordStoreData,
    StatisticData,
)
from tests.unit.helpers.data.statistic.mock_dynamodb_and_s3_records import (
    TOTAL_FILE_SIZE_FOR_H81109,
    TOTAL_FILE_SIZE_FOR_Y12345,
)
from tests.unit.helpers.data.statistic.mock_logs_query_results import (
    HASHED_USER_ID_1_WITH_ADMIN_ROLE,
    HASHED_USER_ID_1_WITH_PCSE_ROLE,
    HASHED_USER_ID_2_WITH_CLINICAL_ROLE,
)
from unit.conftest import TEST_UUID

START_DATE = datetime(2024, 5, 28, 10, 25, 0)
END_DATE = datetime(2024, 6, 4, 10, 25, 0)
START_DATE_STR = START_DATE.strftime("%Y%m%d")
END_DATE_STR = END_DATE.strftime("%Y%m%d")

MOCK_RECORD_STORE_DATA = [
    RecordStoreData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="H81109",
        total_number_of_records=6,
        number_of_document_types=2,
        total_size_of_records_in_megabytes=TOTAL_FILE_SIZE_FOR_H81109,
        average_size_of_documents_per_patient_in_megabytes=TOTAL_FILE_SIZE_FOR_H81109
        / 2,
    ),
    RecordStoreData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="Y12345",
        total_number_of_records=2,
        number_of_document_types=2,
        total_size_of_records_in_megabytes=TOTAL_FILE_SIZE_FOR_Y12345,
        average_size_of_documents_per_patient_in_megabytes=TOTAL_FILE_SIZE_FOR_Y12345,
    ),
]

MOCK_ORGANISATION_DATA = [
    OrganisationData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="H81109",
        number_of_patients=2,
        average_records_per_patient=3,
        daily_count_stored=4,
        daily_count_viewed=40,
        daily_count_downloaded=20,
        daily_count_deleted=2,
        daily_count_searched=30,
    ),
    OrganisationData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="Y12345",
        number_of_patients=1,
        average_records_per_patient=2,
        daily_count_stored=2,
        daily_count_viewed=20,
        daily_count_downloaded=10,
        daily_count_deleted=1,
        daily_count_searched=50,
    ),
]

MOCK_APPLICATION_DATA = [
    ApplicationData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="H81109",
        active_user_ids_hashed=[
            HASHED_USER_ID_1_WITH_ADMIN_ROLE,
            HASHED_USER_ID_2_WITH_CLINICAL_ROLE,
        ],
    ),
    ApplicationData(
        statistic_id=TEST_UUID,
        date=START_DATE_STR,
        ods_code="Y12345",
        active_user_ids_hashed=[HASHED_USER_ID_1_WITH_PCSE_ROLE],
    ),
]

ALL_MOCK_DATA = MOCK_RECORD_STORE_DATA + MOCK_ORGANISATION_DATA + MOCK_APPLICATION_DATA
ALL_MOCK_DATA_AS_JSON_LIST = list(
    map(lambda data: data.model_dump(by_alias=True), ALL_MOCK_DATA)
)


def get_weekly_data(statistics: list[StatisticData]):
    weekly_data = []
    for i in range(7):
        for record in statistics:
            new_record = record.model_copy()
            new_date = datetime.strptime(record.date, "%Y%m%d")
            new_record.date = (new_date + timedelta(days=i)).strftime("%Y%m%d")
            weekly_data.append(new_record)
    return weekly_data


MOCK_WEEKLY_ORGANISATION_DATA = get_weekly_data(MOCK_ORGANISATION_DATA)
MOCK_WEEKLY_APPLICATION_DATA = get_weekly_data(MOCK_APPLICATION_DATA)
ALL_MOCK_WEEKLY_DATA = (
    MOCK_RECORD_STORE_DATA
    + MOCK_WEEKLY_APPLICATION_DATA
    + MOCK_WEEKLY_ORGANISATION_DATA
)
