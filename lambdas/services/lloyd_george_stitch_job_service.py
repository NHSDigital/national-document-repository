import os
import uuid
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError
from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.trace_status import TraceStatus
from models.stitch_trace import DocumentStitchJob, StitchTrace
from pydantic import ValidationError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.exceptions import FileUploadInProgress, NoAvailableDocument
from utils.lambda_exceptions import LGStitchServiceException
from utils.lloyd_george_validator import LGInvalidFilesException
from utils.utilities import format_cloudfront_url

logger = LoggingService(__name__)


class LloydGeorgeStitchJobService:
    def __init__(self):
        get_document_presign_url_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(
            custom_aws_role=get_document_presign_url_aws_role_arn
        )
        self.dynamo_service = DynamoDBService()
        self.document_service = DocumentService()
        self.stitch_trace_table = os.environ.get("STITCH_METADATA_DYNAMODB_NAME")
        self.lloyd_george_table_name = os.environ.get("LLOYD_GEORGE_DYNAMODB_NAME")
        self.cloudfront_table_name = os.environ.get("EDGE_REFERENCE_TABLE")
        self.cloudfront_url = os.environ.get("CLOUDFRONT_URL")
        self.lloyd_george_bucket_name = os.environ.get("LLOYD_GEORGE_BUCKET_NAME")

    def get_or_create_stitch_job(self, nhs_number: str) -> TraceStatus:
        try:
            self.check_lloyd_george_record_for_patient(nhs_number)
            stitch_trace_results = self.query_stitch_trace_with_nhs_number(nhs_number)

            if not stitch_trace_results:
                return self.update_dynamo_with_new_stitch_trace(nhs_number)

            latest_stitch_trace = self.get_latest_stitch_trace(stitch_trace_results)

            if latest_stitch_trace.job_status == TraceStatus.FAILED:
                return self.update_dynamo_with_new_stitch_trace(nhs_number)

            return latest_stitch_trace.job_status

        except ClientError as e:
            logger.error(
                f"{LambdaError.StitchNoService.to_str()}: {str(e)}",
                {"Result": "Creating Lloyd George stitching job failed"},
            )
            raise LGStitchServiceException(
                500,
                LambdaError.StitchNoService,
            )

    def update_dynamo_with_new_stitch_trace(
        self,
        nhs_number: str,
    ) -> TraceStatus:
        logger.info("Writing Document Stitch trace to db")

        expiration_time = self.get_expiration_time()

        stitch_trace = StitchTrace(nhs_number=nhs_number, expire_at=expiration_time)
        self.dynamo_service.create_item(
            self.stitch_trace_table, stitch_trace.model_dump(by_alias=True)
        )
        return stitch_trace.job_status

    def get_expiration_time(self):
        current_time = datetime.now()
        tomorrow = current_time + timedelta(days=1)
        tomorrow_1am = tomorrow.replace(hour=1, minute=0, second=0, microsecond=0)
        return int(tomorrow_1am.timestamp())

    def query_document_stitch_job(self, nhs_number: str):
        stitch_trace_response = self.query_stitch_trace_with_nhs_number(
            nhs_number=nhs_number
        )
        stitch_trace = self.get_latest_stitch_trace(stitch_trace_response)
        return self.process_stitch_trace_response(stitch_trace)

    def process_stitch_trace_response(self, stitch_trace: StitchTrace):
        match stitch_trace.job_status:
            case TraceStatus.FAILED:
                raise LGStitchServiceException(500, LambdaError.StitchNoService)
            case TraceStatus.PENDING:
                return DocumentStitchJob(jobStatus=TraceStatus.PENDING, presignedUrl="")

            case TraceStatus.PROCESSING:
                return DocumentStitchJob(
                    jobStatus=TraceStatus.PROCESSING, presignedUrl=""
                )
            case TraceStatus.COMPLETED:
                presigned_url = self.create_document_stitch_presigned_url(
                    stitch_trace.stitched_file_location
                )
                logger.info(
                    "User has viewed Lloyd George records",
                    {"Result": "Successful Stitching"},
                )

                return DocumentStitchJob(
                    jobStatus=TraceStatus.COMPLETED,
                    presignedUrl=presigned_url,
                    numberOfFiles=stitch_trace.number_of_files,
                    lastUpdated=stitch_trace.file_last_updated,
                    totalFileSizeInBytes=stitch_trace.total_file_size_in_bytes,
                )

    def validate_stitch_trace(
        self, stitch_trace_dynamo_response: list
    ) -> list[StitchTrace] | None:
        try:
            if not stitch_trace_dynamo_response:
                return None
            return [
                StitchTrace.model_validate(stitch_trace)
                for stitch_trace in stitch_trace_dynamo_response
            ]

        except ValidationError as e:
            logger.error(
                f"{LambdaError.StitchValidation.to_str()}: {str(e)}",
                {"Result": "Failed to create document manifest job"},
            )
            raise LGStitchServiceException(400, LambdaError.StitchValidation)

    def get_latest_stitch_trace(self, stitch_trace_items: list[StitchTrace]):
        latest_stitch_trace = stitch_trace_items[0]
        for stitch_trace in stitch_trace_items:
            if (
                stitch_trace.convert_created_to_datetime()
                > latest_stitch_trace.convert_created_to_datetime()
            ):
                latest_stitch_trace = stitch_trace
        return latest_stitch_trace

    def query_stitch_trace_with_nhs_number(self, nhs_number: str) -> list[StitchTrace]:
        filter_builder = DynamoQueryFilterBuilder()
        delete_filter_expression = filter_builder.add_condition(
            attribute="Deleted",
            attr_operator=AttributeOperator.EQUAL,
            filter_value=False,
        ).build()
        response = self.dynamo_service.query_table(
            table_name=self.stitch_trace_table,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=nhs_number,
            query_filter=delete_filter_expression,
        )
        return self.validate_stitch_trace(response)

    def create_document_stitch_presigned_url(self, stitched_file_location):
        presign_url_response = self.s3_service.create_download_presigned_url(
            s3_bucket_name=self.lloyd_george_bucket_name,
            file_key=stitched_file_location,
        )
        presigned_id = str(uuid.uuid4())
        deletion_date = datetime.now(timezone.utc)

        ttl_half_an_hour_in_seconds = self.s3_service.presigned_url_expiry
        dynamo_item_ttl = int(deletion_date.timestamp() + ttl_half_an_hour_in_seconds)
        self.dynamo_service.create_item(
            self.cloudfront_table_name,
            {
                "ID": presigned_id,
                "presignedUrl": presign_url_response,
                "TTL": dynamo_item_ttl,
            },
        )
        return format_cloudfront_url(presigned_id, self.cloudfront_url)

    def check_lloyd_george_record_for_patient(self, nhs_number) -> None:
        try:
            self.document_service.get_available_lloyd_george_record_for_patient(
                nhs_number
            )
        except ClientError as e:
            logger.error(
                f"{LambdaError.StitchDB.to_str()}: {str(e)}",
                {"Result": "Lloyd George stitching failed"},
            )
            raise LGStitchServiceException(500, LambdaError.StitchDB)
        except FileUploadInProgress as e:
            logger.error(
                f"{LambdaError.UploadInProgressError.to_str()}: {str(e)}",
                {"Result": "Lloyd George stitching failed"},
            )
            raise LGStitchServiceException(
                status_code=423, error=LambdaError.UploadInProgressError
            )
        except NoAvailableDocument as e:
            logger.error(
                f"{LambdaError.StitchNotFound.to_str()}: {str(e)}",
                {"Result": "Lloyd George stitching failed"},
            )
            raise LGStitchServiceException(
                status_code=404, error=LambdaError.StitchNotFound
            )
        except LGInvalidFilesException as e:
            logger.error(
                f"{LambdaError.IncompleteRecordError.to_str()}: {str(e)}",
                {"Result": "Lloyd George stitching failed"},
            )
            raise LGStitchServiceException(
                status_code=400, error=LambdaError.IncompleteRecordError
            )
