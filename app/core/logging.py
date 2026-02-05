import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
import io

# Global logging configuration
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
LOGGING_MAX_BYTES = int(os.getenv("LOGGING_MAX_BYTES", 10_000_000))  # 10 MB
LOGGING_BACKUP_COUNT = int(os.getenv("LOGGING_BACKUP_COUNT", 5))
LOGGING_ENABLE_CONSOLE = (
    os.getenv("LOGGING_ENABLE_CONSOLE", "True").lower() == "true"
)
LOGGING_COMPONENT_FILTER = os.getenv("LOGGING_COMPONENT_FILTER", "ALL").upper().split(",")


class _StdoutTee(io.TextIOBase):
    """Mirror stdout/stderr to the bot logger without stacking wrappers."""

    def __init__(self, original_stream, logger_instance, level=logging.INFO):
        self.original_stream = original_stream
        self.logger_instance = logger_instance
        self.level = level

    def configure(self, logger_instance, level=logging.INFO):
        self.logger_instance = logger_instance
        self.level = level

    def write(self, message):
        if not isinstance(message, str):
            message = str(message)
        self.original_stream.write(message)
        stripped = message.strip()
        if stripped and self.logger_instance:
            self.logger_instance.log(self.level, stripped)
        return len(message)

    def flush(self):  # pragma: no cover - passthrough
        try:
            self.original_stream.flush()
        except Exception:
            pass


def setup_application_logging(log_dir):
    """Configure rotating file logging with optional console output and stdout capture."""
    import logging
    root_logger = logging.getLogger()
    if not log_dir:
        log_dir = os.path.join(os.getcwd(), "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        # In containerized environments, we may not have permission to create log directories
        # Continue with logging setup but warn that file logging may not work
        import logging
        logging.getLogger("ai_trading_bot").warning(f"Could not create log directory {log_dir}, file logging disabled")
        log_dir = None


    if log_dir is None:
        # File logging disabled due to permission issues
        root_logger = logging.getLogger()
        resolved_level = getattr(logging, LOGGING_LEVEL, logging.INFO)
        root_logger.setLevel(min(resolved_level, logging.DEBUG))
        
        if LOGGING_ENABLE_CONSOLE:
            console_handler = logging.StreamHandler(sys.__stdout__)
            console_handler.setLevel(resolved_level)
            console_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        logging.getLogger("werkzeug").setLevel(logging.WARNING)

        logger_instance = logging.getLogger("ai_trading_bot")

        if isinstance(sys.stdout, _StdoutTee):
            sys.stdout.configure(logger_instance, resolved_level)
        else:
            sys.stdout = _StdoutTee(sys.stdout, logger_instance, level=resolved_level)

        if isinstance(sys.stderr, _StdoutTee):
            sys.stderr.configure(logger_instance, logging.ERROR)
        else:
            sys.stderr = _StdoutTee(sys.stderr, logger_instance, level=logging.ERROR)

        logger_instance.info(
            "Logging initialized with console-only output (file logging disabled)",
            extra={
                "level": LOGGING_LEVEL,
                "console_enabled": LOGGING_ENABLE_CONSOLE,
                "file_logging_disabled": True,
            },
        )
        return logger_instance

    log_path = os.path.join(log_dir, "bot.log")
    debug_path = os.path.join(log_dir, "bot.debug.log")
    # Prevent duplicate handlers when reinitialising
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            continue

    resolved_level = getattr(logging, LOGGING_LEVEL, logging.INFO)
    root_logger.setLevel(min(resolved_level, logging.DEBUG))

    # Structured JSON formatter for better log analysis
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            # Add structured fields
            if not hasattr(record, "component"):
                record.component = getattr(record, "name", "unknown").split(".")[-1]

            # Create base log entry
            log_entry = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                "level": record.levelname,
                "component": getattr(record, "component", "unknown"),
                "message": record.getMessage(),
                "logger": record.name,
            }

            # Add extra fields if present
            if hasattr(record, "__dict__"):
                extra_fields = {
                    k: v
                    for k, v in record.__dict__.items()
                    if k
                    not in [
                        "name",
                        "msg",
                        "args",
                        "levelname",
                        "levelno",
                        "pathname",
                        "filename",
                        "module",
                        "exc_info",
                        "exc_text",
                        "stack_info",
                        "lineno",
                        "funcName",
                        "created",
                        "msecs",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "processName",
                        "process",
                        "message",
                    ]
                }
                if extra_fields:
                    log_entry.update(extra_fields)

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_entry, default=str)

    # Human-readable formatter for console
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Use structured formatter for files
    structured_formatter = StructuredFormatter()

    info_handler = RotatingFileHandler(
        log_path, maxBytes=LOGGING_MAX_BYTES, backupCount=LOGGING_BACKUP_COUNT
    )
    info_handler.setLevel(resolved_level)
    info_handler.setFormatter(structured_formatter)
    root_logger.addHandler(info_handler)

    debug_handler = RotatingFileHandler(
        debug_path, maxBytes=LOGGING_MAX_BYTES, backupCount=LOGGING_BACKUP_COUNT
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(structured_formatter)
    root_logger.addHandler(debug_handler)

    if LOGGING_ENABLE_CONSOLE:
        # Use sys.__stdout__ to avoid recursion loop with _StdoutTee wrapper
        console_handler = logging.StreamHandler(sys.__stdout__)
        console_handler.setLevel(resolved_level)
        console_handler.setFormatter(console_formatter)  # Human-readable for console
        root_logger.addHandler(console_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    logger_instance = logging.getLogger("ai_trading_bot")

    if isinstance(sys.stdout, _StdoutTee):
        sys.stdout.configure(logger_instance, resolved_level)
    else:
        sys.stdout = _StdoutTee(sys.stdout, logger_instance, level=resolved_level)

    if isinstance(sys.stderr, _StdoutTee):
        sys.stderr.configure(logger_instance, logging.ERROR)
    else:
        sys.stderr = _StdoutTee(sys.stderr, logger_instance, level=logging.ERROR)

    logger_instance.info(
        "Logging initialized",
        extra={
            "level": LOGGING_LEVEL,
            "log_dir": log_dir,
            "structured_logging": True,
            "console_enabled": LOGGING_ENABLE_CONSOLE,
        },
    )
    return logger_instance


bot_logger = logging.getLogger("ai_trading_bot")


def _should_emit_component(component):
    if not LOGGING_COMPONENT_FILTER:
        return True
    component_key = str(component or "GENERAL").upper()
    return (
        "ALL" in LOGGING_COMPONENT_FILTER or component_key in LOGGING_COMPONENT_FILTER
    )


def log_component_event(component, message, level=logging.INFO, details=None):
    if not _should_emit_component(component):
        return

    component_key = str(component or "GENERAL").upper()
    if details is not None:
        try:
            serialized_details = json.dumps(details, default=str)
        except TypeError:
            serialized_details = str(details)
        bot_logger.log(
            level, "[%s] %s | details=%s", component_key, message, serialized_details
        )
    else:
        bot_logger.log(level, "[%s] %s", component_key, message)


def log_component_debug(component, message, details=None):
    log_component_event(component, message, level=logging.DEBUG, details=details)



_ONCE_LOGGED_WARNINGS = set()


def log_warning_once(component, key, message, details=None):
    identifier = f"{component}:{key}"
    if identifier in _ONCE_LOGGED_WARNINGS:
        return
    _ONCE_LOGGED_WARNINGS.add(identifier)
    log_component_event(component, message, level=logging.WARNING, details=details)
