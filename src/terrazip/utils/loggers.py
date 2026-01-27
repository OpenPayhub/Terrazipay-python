import os
import sys
import loguru

# 1. It is recommended to keep this name consistent with your SDK package name
SDK_NAME = "src"

# 2. Disable log output by default to avoid interfering with the end-user's console
loguru.logger.disable(SDK_NAME)


def setup_logger(level="INFO", log_to_file=False, log_path="logs/sdk.log"):
    """
    User calls this function to configure and enable SDK logging.

    :param level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
    :param log_to_file: Boolean, whether to save logs to a local file
    :param log_path: File path for logs, defaults to 'logs/sdk.log' in the workspace
    """
    # Remove all default loguru handlers to prevent duplicate or unwanted formatting
    loguru.logger.remove()

    # Re-enable logging for this specific SDK module
    loguru.logger.enable(SDK_NAME)

    # Configure console (stdout/stderr) output
    loguru.logger.add(
        sys.stderr,
        backtrace=False,
        diagnose=True,
        level=level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Configure file logging if requested
    if log_to_file:
        # Ensure the target directory exists
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        loguru.logger.add(
            log_path,
            rotation="10 MB",  # Rotate file when it reaches 10MB
            retention="1 week",  # Keep logs for 7 days
            level=level,
            encoding="utf-8",
            enqueue=True,  # Ensure thread-safety for multi-threaded apps
        )


# 3. Export the bound logger instance
# Internal SDK modules should use: from .logger_config import sdk_logger
logger = loguru.logger.bind(name=SDK_NAME)
