# [Purpose] Custom logging configuration for the KSERC ARA Backend
# [Source] Python logging best practices
# [Why] Provides consistent, configurable logging throughout the application

# [Library] logging - Python's built-in logging facility
# [Source] Python standard library
# [Why] Standard way to track events and debug issues in production
import logging

# [Library] sys - System-specific parameters and functions
# [Why] Used to write logs to stdout (console)
import sys

# [Library] os - Operating system interface
# [Why] Used to read environment variables for log configuration
import os

# [Library] datetime - Date and time handling
# [Why] Used for timestamp formatting in logs
from datetime import datetime

# [Library] typing - Type hints
# [Why] Better code documentation and IDE support
from typing import Optional


# [User Defined] Custom log formatter with detailed format
# [Source] Extended from logging.Formatter
# [Why] Provides consistent log format across application
class CustomFormatter(logging.Formatter):
    """
    [Purpose] Custom formatter for log messages with color coding (optional)
    [Source] User defined, extends logging.Formatter
    [Why] Makes logs more readable with consistent formatting
    
    [Format] [TIMESTAMP] [LEVEL] [MODULE] - MESSAGE
    """
    
    # [Comment] ANSI color codes for different log levels (for terminal output)
    # [Why] Visual distinction between log levels improves readability
    COLORS = {
        'DEBUG': '\033[36m',     # [Color] Cyan
        'INFO': '\033[32m',      # [Color] Green
        'WARNING': '\033[33m',   # [Color] Yellow
        'ERROR': '\033[31m',     # [Color] Red
        'CRITICAL': '\033[35m'   # [Color] Magenta
    }
    RESET = '\033[0m'  # [Comment] Reset color to default
    
    def __init__(self, use_colors: bool = True):
        """
        [Purpose] Initialize the formatter
        [Parameters]
        - use_colors: Whether to use colored output (default True)
        """
        # [Comment] Define log format string
        # [Format] [2024-02-18 10:30:45] [INFO] [pdf_ingestion] - Processing PDF
        super().__init__(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.use_colors = use_colors
    
    def format(self, record):
        """
        [Purpose] Format log record with optional colors
        [Source] Overrides logging.Formatter.format()
        [Why] Adds color coding for terminal output
        
        [Parameters]
        - record: LogRecord object
        
        [Returns]
        - str: Formatted log message
        """
        # [Comment] Get the base formatted message
        # [Library] super().format() - Call parent class method
        log_message = super().format(record)
        
        # [Comment] Add color if enabled and log level has color defined
        if self.use_colors and record.levelname in self.COLORS:
            # [Comment] Wrap message in color codes
            color = self.COLORS[record.levelname]
            log_message = f"{color}{log_message}{self.RESET}"
        
        return log_message


# [User Defined] Function to configure and get logger instance
# [Source] Logger factory pattern
# [Why] Centralized logger configuration ensures consistency
def get_logger(
    name: str,
    level: Optional[str] = None,
    log_to_file: bool = False,
    log_file_path: str = "logs/app.log"
) -> logging.Logger:
    """
    [Purpose] Creates and configures a logger instance
    [Source] User defined logger factory
    [Why] Provides consistent logging configuration across all modules
    
    [Parameters]
    - name: Logger name (typically __name__ of the module)
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - log_to_file: Whether to also log to a file
    - log_file_path: Path to log file if log_to_file is True
    
    [Returns]
    - logging.Logger: Configured logger instance
    
    [Usage]
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Processing started")
    """
    
    # [Library] logging.getLogger() - Get logger by name
    # [Why] Creates or retrieves existing logger with given name
    logger = logging.getLogger(name)
    
    # [Comment] Only configure if logger has no handlers (avoid duplicate handlers)
    # [Why] Prevents multiple handler attachment when logger is retrieved multiple times
    if not logger.handlers:
        
        # [Comment] Determine log level from parameter or environment variable
        # [Why] Allows configuration via environment variables
        if level is None:
            level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # [Library] logging.getLevelName() - Convert string to log level constant
        # [Why] Converts 'INFO' string to logging.INFO constant
        log_level = getattr(logging, level, logging.INFO)
        logger.setLevel(log_level)
        
        # [Comment] Create console handler (logs to stdout)
        # [Library] logging.StreamHandler() - Handler for stream output
        # [Why] Outputs logs to console/terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # [Comment] Create formatter and attach to console handler
        # [Why] Ensures consistent format for console logs
        console_formatter = CustomFormatter(use_colors=True)
        console_handler.setFormatter(console_formatter)
        
        # [Library] logger.addHandler() - Attach handler to logger
        # [Why] Makes logger output to console
        logger.addHandler(console_handler)
        
        # [Comment] Optionally add file handler
        # [Why] Persistent logs are useful for production debugging
        if log_to_file:
            # [Comment] Ensure log directory exists
            # [Library] os.makedirs() - Create directory if it doesn't exist
            # [Why] Prevents FileNotFoundError when writing logs
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # [Library] logging.FileHandler() - Handler for file output
            # [Why] Writes logs to persistent file
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(log_level)
            
            # [Comment] File logs don't need colors
            # [Why] Color codes would create garbage characters in text files
            file_formatter = CustomFormatter(use_colors=False)
            file_handler.setFormatter(file_formatter)
            
            # [Library] logger.addHandler() - Attach file handler
            logger.addHandler(file_handler)
        
        # [Comment] Prevent log propagation to root logger
        # [Why] Avoids duplicate log messages
        logger.propagate = False
    
    return logger


# [User Defined] Function to log exception with full traceback
# [Source] Exception logging helper
# [Why] Provides detailed error information for debugging
def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """
    [Purpose] Logs exception with full traceback
    [Source] User defined helper function
    [Why] Standardized way to log exceptions with context
    
    [Parameters]
    - logger: Logger instance to use
    - exception: Exception object to log
    - context: Additional context string (e.g., "while processing PDF")
    
    [Usage]
    try:
        risky_operation()
    except Exception as e:
        log_exception(logger, e, "while processing PDF")
    """
    # [Comment] Build error message with context
    error_msg = f"Exception occurred"
    if context:
        error_msg += f" {context}"
    error_msg += f": {str(exception)}"
    
    # [Library] logger.error() with exc_info=True
    # [Why] exc_info=True includes full stack trace in log
    logger.error(error_msg, exc_info=True)


# [User Defined] Function to log function entry/exit (decorator pattern)
# [Source] Decorator for function logging
# [Why] Helps track function call flow in production
def log_function_call(logger: logging.Logger):
    """
    [Purpose] Decorator to log function entry and exit
    [Source] User defined decorator pattern
    [Why] Automatic logging of function calls for debugging
    
    [Usage]
    @log_function_call(logger)
    def my_function(arg1, arg2):
        # function code
        return result
    """
    def decorator(func):
        """
        [Purpose] Actual decorator function
        [Source] Standard Python decorator pattern
        """
        def wrapper(*args, **kwargs):
            """
            [Purpose] Wrapper that adds logging around function call
            """
            # [Comment] Log function entry
            logger.debug(f"Entering function: {func.__name__}")
            
            try:
                # [Comment] Call the actual function
                result = func(*args, **kwargs)
                
                # [Comment] Log successful exit
                logger.debug(f"Exiting function: {func.__name__} (success)")
                
                return result
            
            except Exception as e:
                # [Comment] Log exception and re-raise
                logger.error(
                    f"Exception in function {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# [Comment] Example usage for testing (won't run when imported)
if __name__ == "__main__":
    # [Comment] Test logger configuration
    test_logger = get_logger(__name__, level="DEBUG")
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
    
    # [Comment] Test exception logging
    try:
        # [Comment] Intentional error for testing
        result = 1 / 0
    except Exception as e:
        log_exception(test_logger, e, "during test")
