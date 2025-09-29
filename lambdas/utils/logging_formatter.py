import json
import logging

from utils.request_context import request_context


class LoggingFormatter(logging.Formatter):
    """
    A JSON formatter that automatically adds key information from the
    request context to log records.
    """

    CONTEXT_MAPPING = {
        "authorization": "Authorisation",
        "request_id": "Correlation Id",
        "patient_nhs_no": "Patient NHS number",
        "app_interaction": "App Interaction",
        "nhs_correlation_id": "NHSD-Correlation-ID",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record into a JSON string with context."""
        log_content = {"Message": record.getMessage()}

        for context_attr, log_key in self.CONTEXT_MAPPING.items():
            context_value = getattr(request_context, context_attr, None)
            if context_value:
                log_content[log_key] = context_value

        if record.__dict__.get("custom_args", {}) is not None:
            log_content.update(record.__dict__.get("custom_args", {}))

        return json.dumps(log_content)
