import json
import logging

from utils.request_context import request_context


class LoggingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:

        auth = "No Auth"
        if request_context.authorization is not None:
            auth = request_context.authorization

        logging.info(f"auth: {auth}")
        s = super().format(record)
        d = {
            "correlation_id": request_context.request_id,
            "auth": auth
            **record.__dict__.get("custom_args", {}),
            "Message": s,
        }
        logging.info(f"d: {json.dumps(d)}")
        return json.dumps(d)
