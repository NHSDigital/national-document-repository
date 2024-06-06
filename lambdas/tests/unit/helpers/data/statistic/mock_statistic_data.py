import random

from models.statistics import OrganisationData, RecordStoreData


def make_random_data(
    ods_code: str,
    date_range: list[str],
    field_names: set[str],
) -> list[dict]:
    results = []
    for date in date_range:
        random_data: dict[str, str | int] = {
            key: random.randint(0, 1000) for key in field_names
        }
        random_data.update({"date": date, "ods_code": ods_code})
        results.append(random_data)
    return results


def build_random_record_store_data(
    ods_code: str, date_range: list[str]
) -> list[RecordStoreData]:
    field_names = set(RecordStoreData.model_fields.keys()) - {
        "ods_code",
        "date",
        "statistic_id",
    }
    all_random_data = make_random_data(ods_code, date_range, field_names)
    return [RecordStoreData(**data) for data in all_random_data]


def build_random_organisation_data(
    ods_code: str, date_range: list[str]
) -> list[OrganisationData]:
    field_names = set(OrganisationData.model_fields.keys()) - {
        "ods_code",
        "date",
        "statistic_id",
    }
    all_random_data = make_random_data(ods_code, date_range, field_names)
    return [OrganisationData(**data) for data in all_random_data]
