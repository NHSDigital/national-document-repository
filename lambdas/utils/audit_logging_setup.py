import logging
import sys
from utils.logging_formatter import LoggingFormatter


class LoggingService:
    _instances = {}

    def __new__(cls, name, *args, **kwargs):
        if name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name):
        if getattr(self, '_initialized', False):
            return

        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(LoggingFormatter())
            self.logger.addHandler(handler)

        self.logger.propagate = False

        self._initialized = True

    def info(self, message, custom_args: dict = None, *args, **kwargs):
        self.logger.info(message, extra={"custom_args": custom_args or {}}, *args, **kwargs)

    def error(self, message, custom_args: dict = None, *args, **kwargs):
        self.logger.error(message, extra={"custom_args": custom_args or {}}, *args, **kwargs)

    def warning(self, message, custom_args: dict = None, *args, **kwargs):
        self.logger.warning(message, extra={"custom_args": custom_args or {}}, *args, **kwargs)

    def debug(self, message, custom_args: dict = None, *args, **kwargs):
        self.logger.debug(message, extra={"custom_args": custom_args or {}}, *args, **kwargs)

    def exception(self, message, custom_args: dict = None, *args, exc_info=True, **kwargs):
        self.logger.exception(
            message, exc_info=exc_info, extra={"custom_args": custom_args or {}}, *args, **kwargs
        )

    def critical(self, message, custom_args: dict = None, *args, **kwargs):
        self.logger.critical(message, extra={"custom_args": custom_args or {}}, *args, **kwargs)
