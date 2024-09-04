import importlib
import logging
import os.path
import sys
from typing import Dict

from pydantic import BaseModel, TypeAdapter
from services.base.dynamo_service import DynamoDBService

COLUMNS_TO_FETCH = "OdsCode,PdsOdsCode,UploaderOdsCode,ID"
ATTRIBUTE_TO_REMOVE = "OdsCode"
ATTRIBUTE_TO_ADD = "PdsOdsCode"
UPLOADER_ODS_CODE = "PlaceHolder"


class ProgressForDoc(BaseModel):
    ods_code: str = ""
    update_completed: bool = False


class BatchUpdate:
    def __init__(
        self,
        table_name: str,
        progress_store_file_path: str = "column_change_progress.json",
    ):
        self.progress_store = progress_store_file_path
        self.table_name = table_name
        self.dynamo_service = DynamoDBService()
        self.progress: Dict[str, ProgressForDoc] = {}

        self.logger = logging.getLogger("BatchUpdateOds")

    def main(self):
        self.logger.info("Starting batch update script")
        self.logger.info(f"Table to be updated: {self.table_name}")

        if self.found_previous_progress():
            self.logger.info("Resuming from previous job")
            self.resume_previous_progress()
        else:
            self.logger.info("Starting a new job")
            self.initialise_new_job()

        try:
            self.run_update()
        except Exception as e:
            self.logger.error(e)
            raise e

    def run_update(self):
        if len(self.progress) == 0:
            self.logger.info(
                f'No record found in local progress file. Please try removing the local progress file: "{self.progress}"'
            )
            exit(2)

        patients_to_be_updated = [
            doc
            for [doc, status] in self.progress.items()
            if not status.update_completed
        ]
        if not patients_to_be_updated:
            self.logger.info(
                "Already updated the ODS codes for all patients in previous run."
            )
            exit(2)

        self.update_patient_ods()

        self.logger.info("Finished updating all patient's ODS codes")
        exit(0)

    def update_patient_ods(self):
        for doc_id, document in self.progress.items():
            self.logger.info(f"Updated ODS code for {doc_id}")

            updated_fields = {
                ATTRIBUTE_TO_ADD: document.ods_code,
                "UploaderOdsCode": UPLOADER_ODS_CODE,
            }
            self.dynamo_service.update_item(
                table_name=self.table_name,
                key=doc_id,
                updated_fields=updated_fields,
            )
            self.logger.info(f"REMOVING {ATTRIBUTE_TO_REMOVE} for {doc_id}")
            self.dynamo_service.remove_attribute_from_item(
                table_name=self.table_name, key=doc_id, attribute=ATTRIBUTE_TO_REMOVE
            )
            self.logger.info(f"Updated ODS code for patient: {document}")

            self.progress[doc_id].update_completed = True
        self.save_progress()

    def initialise_new_job(self):
        all_entries = self.list_all_entries()
        if len(all_entries) == 0:
            self.logger.info(
                f"No records was found in table {self.table_name}. Please check the table name."
            )
            exit(1)

        self.progress = self.build_progress_dict(all_entries)

    def resume_previous_progress(self):
        try:
            with open(self.progress_store, "r") as f:
                json_str = f.read()
                self.progress = TypeAdapter(Dict[str, ProgressForDoc]).validate_json(
                    json_str
                )
        except FileNotFoundError:
            self.logger.info("Cannot find a progress file. Will start a new job.")
            self.initialise_new_job()

    def found_previous_progress(self) -> bool:
        return os.path.isfile(self.progress_store)

    def save_progress(self):
        with open(self.progress_store, "wb") as f:
            json_str = TypeAdapter(Dict[str, ProgressForDoc]).dump_json(self.progress)
            return f.write(json_str)

    def list_all_entries(self) -> list[dict]:
        self.logger.info("Fetching all records from dynamodb table...")

        table = DynamoDBService().get_table(self.table_name)
        results = []

        response = table.scan(ProjectionExpression=COLUMNS_TO_FETCH)

        # handle pagination
        while "LastEvaluatedKey" in response:
            results += response["Items"]
            response = table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"],
                ProjectionExpression=COLUMNS_TO_FETCH,
            )

        results += response["Items"]

        self.logger.info(f"Downloaded {len(results)} records from table")

        return results

    def build_progress_dict(self, dynamodb_records: list[dict]) -> dict:
        self.logger.info("Grouping the records according to ID...")

        progress_dict = {}
        for entry in dynamodb_records:
            ods_code = entry.get(ATTRIBUTE_TO_REMOVE)
            if ods_code is None:
                continue
            doc_ref_id = entry["ID"]

            progress_dict[doc_ref_id] = ProgressForDoc(ods_code=ods_code)

        self.logger.info(f"Totally {len(progress_dict)} patients found in record.")
        return progress_dict


def setup_logging_for_local_script():
    importlib.reload(logging)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%d/%b/%Y %H:%M:%S",
        stream=sys.stdout,
    )


if __name__ == "__main__":
    import argparse

    setup_logging_for_local_script()

    parser = argparse.ArgumentParser(
        prog="batch_update_ods_code.py",
        description="A utility script to update the ODS Codes for all patients in a dynamoDB doc reference table",
    )
    parser.add_argument("table_name", type=str, help="The name of dynamodb table")
    args = parser.parse_args()

    BatchUpdate(table_name=args.table_name).main()
