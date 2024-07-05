import os
from typing import Callable

from enums.lambda_error import LambdaError
from utils.audit_logging_setup import LoggingService
from utils.exceptions import MissingEnvVarException
from utils.lambda_response import ApiGatewayResponse

logger = LoggingService(__name__)


def ensure_environment_variables(names: list[str]) -> Callable:
    """A decorator for lambda handler.
    Verify that the lambda environment got a set of specific environment variables.
    If not, returns a 500 Internal server error response and log the missing env var.

    Usage:
    @ensure_environment_variables(names=["LLOYD_GEORGE_BUCKET_NAME", "LLOYD_GEORGE_DYNAMODB_NAME"])
    def lambda_handler(event, context):
        ...
    """

    def wrapper(lambda_func: Callable):
        def interceptor(event, context):
            for name in names:
                if name not in os.environ:
                    logger.info(f"missing env var: '{name}'")
                    error_body = LambdaError.EnvMissing.create_error_body(
                        {"name": name}
                    )
                    return ApiGatewayResponse(
                        500, error_body, event.get("httpMethod", "GET")
                    ).create_api_gateway_response()

            # Validation done. Return control flow to original lambda handler
            return lambda_func(event, context)

        return interceptor

    return wrapper


def ensure_environment_variables_for_non_webapi(names: list[str]) -> Callable:
    """A decorator for lambda handler.
    Verify that the lambda environment got a set of specific environment variables.
    If not, log and throw an error.
    Use for lambdas that are NOT supposed to be integrated with API Gateway.

    Usage:
    @ensure_environment_variables_for_non_webapi(names=["LLOYD_GEORGE_BUCKET_NAME", "LLOYD_GEORGE_DYNAMODB_NAME"])
    def lambda_handler(event, context):
        ...
    """

    def wrapper(lambda_func: Callable):
        def interceptor(event, context):
            missing_env_vars = set(names) - set(os.environ)
            if missing_env_vars:
                missing_env_vars_in_string = ", ".join(sorted(missing_env_vars))
                error_body = LambdaError.EnvMissing.create_error_body(
                    {"name": missing_env_vars_in_string}
                )
                logger.error(error_body, {"Result": "Failed to run lambda"})
                raise MissingEnvVarException(error_body)

            # Validation done. Return control flow to original lambda handler
            return lambda_func(event, context)

        return interceptor

    return wrapper
