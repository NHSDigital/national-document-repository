import datetime
import os

from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service


class PdmDataHelper:
    def __init__(self):
        self.pdm_dynamo_table = os.environ.get("PDM_METADATA_TABLE") or ""
        self.s3_bucket = os.environ.get("PDM_S3_BUCKET") or ""
        self.dynamo_service = DynamoDBService()
        self.s3_service = S3Service()

    def create_metadata(self, pdm_document_details):
        dynamo_item = {
            "ID": pdm_document_details["id"],
            "ContentType": "application/pdf",
            "Created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "CurrentGpOds": "H81109",  # maybe?
            "Custodian": "H81109",
            "DocStatus": pdm_document_details.get("doc_status", "final"),
            "DocumentScanCreation": "2023-01-01",
            "FileLocation": f"s3://{self.s3_bucket}/{pdm_document_details['nhs_number']}/{pdm_document_details['id']}",
            "FileName": f"1of1_pdm_record_[Holly Lorna MAGAN]_[{pdm_document_details['nhs_number']}]_[29-05-2006].pdf",
            "FileSize": pdm_document_details.get("size", "12345"),
            "LastUpdated": 1743177202,
            "NhsNumber": pdm_document_details["nhs_number"],
            "Status": "current",
            "DocumentSnomedCode": "717391000000106",
            "Uploaded": True,
            "Uploading": False,
            "Version": "1",
            "VirusScannerResult": "Clean",
        }
        self.dynamo_service.create_item(self.pdm_dynamo_table, dynamo_item)

    def create_resource(self, pdm_record):
        self.s3_service.upload_file_obj(
            file_obj=pdm_record["data"],
            s3_bucket_name=self.s3_bucket,
            file_key=f"{pdm_record['nhs_number']}/{pdm_record['id']}",
        )

    def tidyup(self, pdm_record):
        self.dynamo_service.delete_item(
            table_name=self.pdm_dynamo_table,
            key={"ID": pdm_record["id"]},
        )
        self.s3_service.delete_object(
            self.s3_bucket,
            f"{pdm_record['nhs_number']}/{pdm_record['id']}",
        )
