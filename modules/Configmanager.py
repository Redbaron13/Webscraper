# web_scraper/config_manager.py
import os
from dotenv import load_dotenv, find_dotenv, set_key, unset_key
from logger import regular, maintenance, debug, error as log_error, warning, set_log_level as set_global_log_level
from utils import parse_times


# --- Constants ---
# Attempt to find .env. If not found, default to creating '.env' in the current working directory.
# This makes it more robust if the script is run from different subdirectories of a project.
_ENV_FILE_PATH = find_dotenv(usecwd=True) if find_dotenv(usecwd=True) else os.path.join(os.getcwd(), ".env")

# Public constant for modules importing it (though _ENV_FILE_PATH is used internally for most operations)
ENV_FILE = _ENV_FILE_PATH

DEFAULT_LOCAL_DB_NAME = "web_scraper_data.db"
DEFAULT_PRIMARY_TIMES_STR = "08:00,17:00"
DEFAULT_BACKUP_TIMES_STR = "22:00,05:00"
DEFAULT_LOG_LEVEL_STR = "REGULAR"

# --- Configuration Storage (Loaded from .env or defaults) ---
# This dictionary holds the application's configuration.
# It's populated by load_config().
CONFIG = {
    "SUPABASE_URL": None,
    "SUPABASE_KEY": None,
    "TARGET_URLS": [],  # List of URL strings
    "SCRAPE_TIMES_PRIMARY": [], # List of "HH:MM" strings
    "SCRAPE_TIMES_BACKUP": [],  # List of "HH:MM" strings
    "LOCAL_DB_PATH": DEFAULT_LOCAL_DB_NAME,
    "LOG_LEVEL": DEFAULT_LOG_LEVEL_STR
}

def _ensure_env_file_exists():
    """Ensures the .env file exists, creating an empty one if necessary."""
    if not os.path.exists(_ENV_FILE_PATH):
        try:
            with open(_ENV_FILE_PATH, 'w') as f:
                f.write("# Auto-generated .env file by Web Scraper\n")
            maintenance(f".env file created at {_ENV_FILE_PATH}")
        except IOError as e:
            log_error(f"Failed to create .env file at {_ENV_FILE_PATH}", error_obj=e)
            # If we can't create it, operations like set_key will fail.
            # The script might still run with defaults if load_dotenv doesn't find it.

def load_config() -> dict:
    """
    Loads configuration from the .env file into the global CONFIG dictionary.
    If .env doesn't exist, it attempts to create one.
    Applies defaults for any missing values.
    Sets the global log level based on the loaded configuration.

    Returns:
        dict: The loaded configuration.
    """
    global CONFIG
    _ensure_env_file_exists() # Make sure .env exists for load_dotenv and set_key
    
    # load_dotenv will read the .env file and set environment variables.
    # It returns True if a .env file was found and loaded, False otherwise.
    # We use override=True so that if this function is called multiple times,
    # it reloads values from the .env file, overriding any os.environ values
    # that might have been set by a previous load_dotenv call without override.
    load_dotenv(dotenv_path=_ENV_FILE_PATH, override=True)
    maintenance(f"Attempting to load configuration from: {_ENV_FILE_PATH}")

    CONFIG["SUPABASE_URL"] = os.getenv("SUPABASE_URL")
    CONFIG["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY")
    
    target_urls_str = os.getenv("TARGET_URLS", "")
    CONFIG["TARGET_URLS"] = [url.strip() for url in target_urls_str.split(',') if url.strip()]
    
    primary_times_str = os.getenv("SCRAPE_TIMES_PRIMARY", DEFAULT_PRIMARY_TIMES_STR)
    CONFIG["SCRAPE_TIMES_PRIMARY"] = parse_times(primary_times_str)

    backup_times_str = os.getenv("SCRAPE_TIMES_BACKUP", DEFAULT_BACKUP_TIMES_STR)
    CONFIG["SCRAPE_TIMES_BACKUP"] = parse_times(backup_times_str)
    
    CONFIG["LOCAL_DB_PATH"] = os.getenv("LOCAL_DB_PATH", DEFAULT_LOCAL_DB_NAME)
    CONFIG["LOG_LEVEL"] = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL_STR).upper()

    # Apply the loaded log level to the global logger settings
    set_global_log_level(CONFIG["LOG_LEVEL"])
    
    maintenance("Configuration loaded/reloaded.")
    debug(f"Current effective config: {CONFIG}")
    
    # Warnings for common misconfigurations
    if not CONFIG["SUPABASE_URL"] or not CONFIG["SUPABASE_KEY"]:
        warning("Supabase URL or Key is not set in the configuration. Supabase features will be disabled.")
    if not CONFIG["TARGET_URLS"]:
        warning("No target URLs are configured. The scraper will not have any sites to process.")

    return CONFIG

def save_config_value(key: str, value: str | None):
    """
    Saves a single key-value pair to the .env file and updates the in-memory CONFIG.
    If value is None, the key is removed from the .env file.

    Args:
        key (str): The configuration key (e.g., "SUPABASE_URL").
        value (str | None): The value to save. If None, the key is removed.
    """
    global CONFIG
    _ensure_env_file_exists() # Ensure .env file exists before writing
    
    key_upper = key.upper()

    if value is None:
        # Remove the key from .env file and update in-memory config
        unset_key(_ENV_FILE_PATH, key_upper)
        regular(f"Removed {key_upper} from .env file.")
        # Reset to default or empty for in-memory representation
        if key_upper == "TARGET_URLS": CONFIG[key_upper] = []
        elif key_upper == "SCRAPE_TIMES_PRIMARY": CONFIG[key_upper] = parse_times(DEFAULT_PRIMARY_TIMES_STR)
        elif key_upper == "SCRAPE_TIMES_BACKUP": CONFIG[key_upper] = parse_times(DEFAULT_BACKUP_TIMES_STR)
        elif key_upper == "LOG_LEVEL": CONFIG[key_upper] = DEFAULT_LOG_LEVEL_STR
        elif key_upper == "LOCAL_DB_PATH": CONFIG[key_upper] = DEFAULT_LOCAL_DB_NAME
        else: CONFIG[key_upper] = None
    else:
        # Save the key-value pair to the .env file
        # set_key will create the file if it doesn't exist, or update the key if it does.
        set_key(_ENV_FILE_PATH, key_upper, value)
        regular(f"Saved {key_upper}='{value if key_upper != 'SUPABASE_KEY' else '********'}' to .env file.")
    
    # After saving to .env, reload the entire config to ensure consistency
    # and to correctly parse complex types like lists of times or URLs.
    load_config()
    debug(f"Config reloaded after saving {key_upper}.")


def get_config() -> dict:
    """
    Returns the current configuration dictionary.
    Ensures configuration is loaded if it hasn't been already.
    """
    # Check a key that should be populated by load_config.
    # If LOG_LEVEL (which has a default) is still the initial default from CONFIG definition,
    # it implies load_config might not have run or fully populated.
    # A more robust check could be a dedicated flag.
    if CONFIG["LOG_LEVEL"] == DEFAULT_LOG_LEVEL_STR and not os.getenv("LOG_LEVEL"):
         debug("get_config() called, ensuring config is loaded.")
         load_config()
    return CONFIG

def get_env_file_path() -> str:
    """Returns the path to the .env file being used."""
    return ENV_FILE  # Use the public constant instead of _ENV_FILE_PATH

# Load configuration when the module is imported for the first time.
# This makes the config available immediately to other modules.
load_config()

if __name__ == '__main__':
    # Example Usage and Demonstration
    print(f"Using .env file at: {get_env_file_path()}")
    
    print("\n--- Initial Config (loaded on import) ---")
    initial_config = get_config()
    for k, v in initial_config.items():
        print(f"  {k}: {v}")

    print("\n--- Modifying and Saving Config Values ---")
    # Example: Change SUPABASE_URL and TARGET_URLS
    # Note: This will modify your actual .env file!
    current_supabase_url = initial_config.get("SUPABASE_URL")
    save_config_value("SUPABASE_URL", "https://test.supabase.co")
    save_config_value("TARGET_URLS", "https://example.com,https://test.com")
    save_config_value("LOG_LEVEL", "DEBUG") # This will also change global log level

    print("\n--- Config After Modifications ---")
    updated_config = get_config() # get_config() will reflect changes due to reload in save_config_value
    for k, v in updated_config.items():
        print(f"  {k}: {v}")
    
    # Test removing a key
    print("\n--- Removing TARGET_URLS ---")
    save_config_value("TARGET_URLS", None)
    config_after_removal = get_config()
    print(f"  TARGET_URLS after removal: {config_after_removal.get('TARGET_URLS')}")
    assert config_after_removal.get('TARGET_URLS') == []


    print("\n--- Restoring Previous SUPABASE_URL (if any) ---")
    # Restore original value if it existed, otherwise remove it
    save_config_value("SUPABASE_URL", current_supabase_url if current_supabase_url else None)
    # Restore other values to defaults or original state if necessary for testing
    save_config_value("TARGET_URLS", ",".join(initial_config.get("TARGET_URLS",[]))) # Restore original URLs
    save_config_value("LOG_LEVEL", initial_config.get("LOG_LEVEL", DEFAULT_LOG_LEVEL_STR)) # Restore original log level
    
    print("\n--- Final Config (should be close to initial or reflect restored values) ---")
    final_config = get_config()
    for k, v in final_config.items():
        print(f"  {k}: {v}")

    print("\nConfig manager test complete.")

# This module can be run directly to test the configuration management functionality.