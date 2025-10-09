import datetime
import os

from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service


class LloydGeorgeDataHelper:
    def __init__(self):
        self.lloydgeorge_dynamo_table = os.environ.get("LG_METADATA_TABLE") or ""
        self.s3_bucket = os.environ.get("NDR_S3_BUCKET") or ""
        self.dynamo_service = DynamoDBService()
        self.s3_service = S3Service()

    def create_metadata(self, lloyd_george_details):
        dynamo_item = {
            "ID": lloyd_george_details["id"],
            "ContentType": "application/pdf",
            "Created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "CurrentGpOds": "H81109",
            "Custodian": "H81109",
            "DocStatus": lloyd_george_details.get("doc_status", "final"),
            "DocumentScanCreation": "2023-01-01",
            "FileLocation": f"s3://{self.s3_bucket}/{lloyd_george_details['nhs_number']}/{lloyd_george_details['id']}",
            "FileName": f"1of1_Lloyd_George_Record_[Holly Lorna MAGAN]_[{lloyd_george_details['nhs_number']}]_[29-05-2006].pdf",
            "FileSize": lloyd_george_details.get("size", "12345"),
            "LastUpdated": 1743177202,
            "NhsNumber": lloyd_george_details["nhs_number"],
            "Status": "current",
            "DocumentSnomedCode": "16521000000101",
            "Uploaded": True,
            "Uploading": False,
            "Version": "1",
            "VirusScannerResult": "Clean",
        }
        self.dynamo_service.create_item(self.lloydgeorge_dynamo_table, dynamo_item)

    def create_resource(self, lloyd_george_record):
        self.s3_service.upload_file_obj(
            file_obj=lloyd_george_record["data"],
            s3_bucket_name=self.s3_bucket,
            file_key=f"{lloyd_george_record['nhs_number']}/{lloyd_george_record['id']}",
        )

    def tidyup(self, lloyd_george_record):
        self.dynamo_service.delete_item(
            table_name=self.lloydgeorge_dynamo_table,
            key={"ID": lloyd_george_record["id"]},
        )
        self.s3_service.delete_object(
            self.s3_bucket,
            f"{lloyd_george_record['nhs_number']}/{lloyd_george_record['id']}",
        )
