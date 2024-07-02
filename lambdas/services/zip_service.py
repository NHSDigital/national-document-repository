import os
import shutil
import tempfile
import zipfile

from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService
from utils.exceptions import InvalidDocumentReferenceException
from utils.lambda_exceptions import DocumentManifestServiceException

logger = LoggingService(__name__)


class DocumentZipService:
    def __init__(self, zip_trace):
        self.s3_service = S3Service()
        self.dynamo_service = DynamoDBService()
        self.temp_output_dir = tempfile.mkdtemp()
        self.temp_downloads_dir = tempfile.mkdtemp()
        self.zip_trace_object = zip_trace
        self.zip_output_bucket = os.environ["ZIPPED_STORE_BUCKET_NAME"]
        self.zip_trace_table = os.environ["ZIPPED_STORE_DYNAMODB_NAME"]
        self.zip_file_name = f"patient-record-{zip_trace.job_id}.zip"
        self.zip_file_path = os.path.join(self.temp_output_dir, self.zip_file_name)

    def handle_zip_request(self):
        self.download_documents_to_be_zipped()
        self.zip_files()
        self.upload_zip_file()
        self.remove_temp_files()
        self.update_dynamo_with_zip_location()

    def download_documents_to_be_zipped(self):
        logger.info("Downloading documents to be zipped")
        documents = self.zip_trace_object.files_to_download
        for document_name, document_location in documents:
            self.download_file_from_s3(document_name, document_location)

    def download_file_from_s3(self, document_name, document_location):
        download_path = os.path.join(self.temp_downloads_dir, document_name)
        file_bucket, file_key = self.get_file_bucket_and_key(document_location)
        try:
            self.s3_service.download_file(file_bucket, file_key, download_path)
        except ClientError as e:
            msg = f"{file_key} may reference missing file in s3 bucket: {file_bucket}"
            logger.error(
                f"{LambdaError.ZipServiceClientError.to_str()} {msg + str(e)}",
                {"Result": "Failed to create document manifest"},
            )
            raise DocumentManifestServiceException(
                status_code=500, error=LambdaError.ZipServiceClientError
            )

    @staticmethod
    def get_file_bucket_and_key(file_location):
        try:
            file_bucket, file_key = file_location.replace("s3://", "").split("/", 1)
            return file_bucket, file_key
        except ValueError:
            raise InvalidDocumentReferenceException(
                "Failed to parse bucket from file location string"
            )

    def upload_zip_file(self):
        logger.info("Uploading zip file to s3")
        zip_file_name = "patient-record-{}.zip"

        try:
            self.s3_service.upload_file(
                file_name=self.zip_file_path,
                s3_bucket_name=self.zip_output_bucket,
                file_key=f"{zip_file_name}",
            )
        except ClientError as e:
            logger.error(e, {"Result": "Failed to create document manifest"})
            raise DocumentManifestServiceException(
                status_code=500, error=LambdaError.ZipServiceClientError
            )

    def zip_files(self):
        logger.info("Creating zip from files")
        with zipfile.ZipFile(self.zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.temp_downloads_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, self.temp_downloads_dir)
                    zipf.write(file_path, arc_name)

    def update_dynamo_with_zip_location(self):
        logger.info("Writing zip trace to db")
        self.zip_trace_object.zip_file_location = (
            f"s3://{self.zip_output_bucket}/{self.zip_file_name}",
        )
        self.zip_trace_object.status = "Complete"
        self.dynamo_service.update_item(
            self.zip_trace_table,
            self.zip_trace_object.id,
            self.zip_trace_object.model_dump(
                by_alias=True, include={"created", "status", "zip_file_location"}
            ),
        )

    def remove_temp_files(self):
        # Removes the parent of each removed directory until the parent does not exist or the parent is not empty
        shutil.rmtree(self.temp_downloads_dir)
        shutil.rmtree(self.temp_output_dir)
