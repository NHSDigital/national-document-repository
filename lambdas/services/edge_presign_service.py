import re

from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.base.ssm_service import SSMService
from utils.audit_logging_setup import LoggingService
from utils.lambda_exceptions import CloudFrontEdgeException

logger = LoggingService(__name__)


class EdgePresignService:

    def __init__(self):
        self.dynamo_service = DynamoDBService()
        self.s3_service = S3Service()
        self.ssm_service = SSMService()
        self.table_name_ssm_param = "EDGE_REFERENCE_TABLE"

    def attempt_url_update(self, uri_hash, domain_name) -> None:
        try:
            environment = self.extract_environment_from_domain(domain_name)
            logger.info(f"Environment found: {environment}")
            base_table_name: str = self.ssm_service.get_ssm_parameter(
                self.table_name_ssm_param
            )
            formatted_table_name: str = self.extend_table_name(
                base_table_name, environment
            )
            logger.info(f"Table: {formatted_table_name}")
            self.dynamo_service.update_item(
                table_name=formatted_table_name,
                key=uri_hash,
                updated_fields={"IsRequested": True},
                condition_expression="attribute_not_exists(IsRequested) OR IsRequested = :false",
                expression_attribute_values={":false": False},
            )
        except ClientError as e:
            logger.error(f"{str(e)}", {"Result": LambdaError.EdgeNoClient.to_str()})
            raise CloudFrontEdgeException(400, LambdaError.EdgeNoClient)

    @staticmethod
    def extract_environment_from_domain(domain_name: str) -> str:
        match = re.match(r"([^-]+(?:-[^-]+)?)", domain_name)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def extend_table_name(base_table_name, environment) -> str:
        if environment:
            return f"{environment}_{base_table_name}"
        return base_table_name
