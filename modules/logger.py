# logger.py
# Created by Kevin Baron on 5/19/25.
# Edited Last by Kevin Baron on 5/20/25 @ 00:20:37
# webscraper/logger.py
import datetime
import traceback
# from configmanager import ENV_FILE # Removed to break circular import

# Define log levels as a dictionary for easy lookup and comparison
LOG_LEVELS = {
    "DEBUG": 0,       # Detailed information, typically of interest only when diagnosing problems.
    "MAINTENANCE": 1, # More detailed than regular, for tracking operations closely.
    "REGULAR": 2,     # Confirmation that things are working as expected. Standard operational messages.
    "INFO": 2,        # Alias for REGULAR for common practice
    "WARNING": 3,     # An indication that something unexpected happened, or indicative of some problem in the near future.
    "ERROR": 4,       # Due to a more serious problem, the software has not been able to perform some function.
    "CRITICAL": 5     # A serious error, indicating that the program itself may be unable to continue running.
}

# Global variable to hold the current logging level, initialized to REGULAR
CURRENT_LOG_LEVEL = LOG_LEVELS["REGULAR"]

def set_log_level(level_name: str):
    """
    Sets the global log level for the application.
    Args:
        level_name (str): The desired log level (e.g., "DEBUG", "REGULAR", "ERROR").
                          Case-insensitive.
    """
    global CURRENT_LOG_LEVEL
    level_name_upper = level_name.upper()
    if level_name_upper in LOG_LEVELS:
        CURRENT_LOG_LEVEL = LOG_LEVELS[level_name_upper]
        # Log the change itself, using a fixed level (e.g., INFO or REGULAR)
        # to ensure it's seen if the new level is more restrictive.
        _log_internal(f"Log level set to {level_name_upper}", "INFO")
    else:
        _log_internal(f"Unknown log level: {level_name}. Keeping current log level.", "ERROR")

def _log_internal(message: str, level_name: str, error_obj: Exception = None, show_traceback: bool = False):
    """
    Internal logging function.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level_name_upper = level_name.upper()

    if level_name_upper not in LOG_LEVELS:
        # Handle unknown log levels gracefully
        print(f"{timestamp} [UNKNOWN LEVEL: {level_name_upper}] {message}")
        if error_obj:
            print(f"    Error details: {type(error_obj).__name__} - {error_obj}")
        return

    # Only print the message if its level is at or above the current global log level
    if LOG_LEVELS[level_name_upper] >= CURRENT_LOG_LEVEL:
        log_entry = f"{timestamp} [{level_name_upper}] {message}"
        print(log_entry)
        if error_obj:
            error_details = f"    Error Info: {type(error_obj).__name__} - {str(error_obj)}"
            print(error_details)
            # Show traceback if in DEBUG mode or explicitly requested for critical/error
            if show_traceback or (CURRENT_LOG_LEVEL == LOG_LEVELS["DEBUG"] and LOG_LEVELS[level_name_upper] >= LOG_LEVELS["ERROR"]):
                # traceback.print_exc() prints to stderr by default, which is fine.
                # Or, format it as a string if you want to print it to stdout:
                # tb_str = traceback.format_exc()
                # print(f"    Traceback:\n{tb_str}")
                traceback.print_exc()


def debug(message: str, error: Exception = None):
    """Logs a message with DEBUG level."""
    _log_internal(message, "DEBUG", error)

def maintenance(message: str, error: Exception = None):
    """Logs a message with MAINTENANCE level."""
    _log_internal(message, "MAINTENANCE", error)

def regular(message: str, error: Exception = None):
    """Logs a message with REGULAR level."""
    _log_internal(message, "REGULAR", error)

def info(message: str, error: Exception = None):
    """Logs a message with INFO level (alias for REGULAR)."""
    _log_internal(message, "INFO", error)

def warning(message: str, error_obj: Exception = None):
    """Logs a message with WARNING level."""
    _log_internal(message, "WARNING", error_obj)

def error(message: str, error_obj: Exception = None):
    """Logs a message with ERROR level. Includes traceback in DEBUG mode."""
    _log_internal(message, "ERROR", error_obj, show_traceback=True)

def critical(message: str, error_obj: Exception = None):
    """Logs a message with CRITICAL level. Includes traceback."""
    _log_internal(message, "CRITICAL", error_obj, show_traceback=True)


if __name__ == '__main__':
    # Example Usage and Demonstration of logger functionalities

    print("--- Default Log Level (REGULAR) ---")
    debug("This is a debug message. (Should not be visible)")
    maintenance("This is a maintenance message. (Should not be visible)")
    regular("This is a regular message. (Should be visible)")
    info("This is an info message. (Should be visible)")
    warning("This is a warning message. (Should be visible)")
    error("This is an error message. (Should be visible)")
    critical("This is a critical message. (Should be visible)")

    print("\n--- Setting Log Level to DEBUG ---")
    set_log_level("DEBUG")
    debug("This is a debug message. (Now visible)")
    maintenance("This is a maintenance message. (Now visible)")
    regular("This is a regular message. (Visible)")
    try:
        x = 1 / 0
    except ZeroDivisionError as e:
        error("An error occurred during calculation (DEBUG mode).", error_obj=e)
        # Traceback will be printed because log level is DEBUG and error level is ERROR

    print("\n--- Setting Log Level to MAINTENANCE ---")
    set_log_level("MAINTENANCE")
    debug("This debug message won't show now.")
    maintenance("This maintenance message will show.")
    regular("This regular message will show.")
    warning("This warning message will show.")


    print("\n--- Setting Log Level to WARNING ---")
    set_log_level("WARNING")
    regular("Regular messages are now hidden.")
    warning("This is a warning message. (Visible)")
    error("This is an error message. (Visible)")


    print("\n--- Setting Log Level to ERROR ---")
    set_log_level("ERROR")
    warning("Warning messages are now hidden.")
    error("This is an error message. (Visible)")
    critical("This is a critical message. (Visible)")
    try:
        collections.namedtuple("Test", "field1 field2") # NameError: name 'collections' is not defined
    except NameError as e:
        # Even if not in DEBUG mode, error() with show_traceback=True will print it
        error("A NameError occurred.", error_obj=e)


    print("\n--- Testing invalid log level ---")
    set_log_level("SUPERDEBUG") # This is not a valid level
    # The logger should report an error about the invalid level itself.

    print("\n--- Logger test complete ---")

