# web_scraper/config_manager.py
import os
import json
import random
import string
from dotenv import load_dotenv, find_dotenv, set_key, unset_key
from .logger import regular, maintenance, debug, error as log_error, warning, set_log_level as set_global_log_level

# --- Utility function moved here from utils.py to break circular import ---
def parse_times(time_str: str) -> list:
    """
    Parses a comma-separated string of HH:MM times into a list.
    Returns empty list if input is invalid or empty.
    """
    if not time_str:
        return []
    try:
        times = [t.strip() for t in time_str.split(',') if t.strip()]
        # Basic validation for HH:MM format
        for t in times:
            if not (len(t) == 5 and t[2] == ':' and t[0:2].isdigit() and t[3:5].isdigit()):
                raise ValueError(f"Invalid time format: {t}")
            hour, minute = int(t[0:2]), int(t[3:5])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"Invalid time value: {t}")
        return times
    except ValueError as e:
        # Use logger if available, otherwise print (during early init)
        try:
            log_error(f"Error parsing time string '{time_str}': {e}", error_obj=e)
        except NameError: # If logger not yet fully initialized
            print(f"Error parsing time string '{time_str}': {e}")
        return []
    except Exception as e:
        try:
            log_error(f"Unexpected error parsing time string '{time_str}': {e}", error_obj=e)
        except NameError:
             print(f"Unexpected error parsing time string '{time_str}': {e}")
        return []

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
    "URL_CODES": {},  # Stores URL to two-letter code mappings
    "LAST_MANUAL_PREFIX": "M", # Default so first manual run uses 'T'
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
    CONFIG["SCRAPE_TIMES_PRIMARY"] = parse_times(primary_times_str) # parse_times is now local

    backup_times_str = os.getenv("SCRAPE_TIMES_BACKUP", DEFAULT_BACKUP_TIMES_STR)
    CONFIG["SCRAPE_TIMES_BACKUP"] = parse_times(backup_times_str) # parse_times is now local
    
    CONFIG["LOCAL_DB_PATH"] = os.getenv("LOCAL_DB_PATH", DEFAULT_LOCAL_DB_NAME)
    CONFIG["LOG_LEVEL"] = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL_STR).upper()
    CONFIG["LAST_MANUAL_PREFIX"] = os.getenv("LAST_MANUAL_PREFIX", "M") # Load from .env, default to "M"

    url_codes_str = os.getenv("URL_CODES", "{}") # Default to an empty JSON object string
    try:
        CONFIG["URL_CODES"] = json.loads(url_codes_str)
        if not isinstance(CONFIG["URL_CODES"], dict):
            warning(f"URL_CODES from .env is not a valid JSON object (dictionary). Using empty default. Found: {url_codes_str}")
            CONFIG["URL_CODES"] = {}
    except json.JSONDecodeError:
        warning(f"Failed to parse URL_CODES from .env as JSON. Using empty default. Found: {url_codes_str}")
        CONFIG["URL_CODES"] = {}

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

    if key_upper == "URL_CODES":
        if isinstance(value, dict):
            set_key(_ENV_FILE_PATH, key_upper, json.dumps(value))
            regular(f"Saved {key_upper} as JSON string to .env file.")
        elif value is None:
            unset_key(_ENV_FILE_PATH, key_upper)
            CONFIG[key_upper] = {} # Reset in-memory
            regular(f"Removed {key_upper} from .env file.")
        else:
            log_error(f"Failed to save {key_upper}: value must be a dictionary or None.")
            return
    elif value is None:
        # Remove the key from .env file
        unset_key(_ENV_FILE_PATH, key_upper)
        # Also remove from current os.environ if it exists, so load_dotenv doesn't see stale value
        if key_upper in os.environ:
            del os.environ[key_upper]
        regular(f"Removed {key_upper} from .env file and active environment variables.")
        
        # Reset to default or empty for in-memory representation.
        # load_config() will be called shortly and will establish the definitive state
        # based on the (now modified) .env and cleaned os.environ.
        # parse_times is now local
        if key_upper == "TARGET_URLS": CONFIG[key_upper] = []
        elif key_upper == "SCRAPE_TIMES_PRIMARY": CONFIG[key_upper] = parse_times(DEFAULT_PRIMARY_TIMES_STR)
        elif key_upper == "SCRAPE_TIMES_BACKUP": CONFIG[key_upper] = parse_times(DEFAULT_BACKUP_TIMES_STR)
        elif key_upper == "LOG_LEVEL": CONFIG[key_upper] = DEFAULT_LOG_LEVEL_STR
        elif key_upper == "LOCAL_DB_PATH": CONFIG[key_upper] = DEFAULT_LOCAL_DB_NAME
        elif key_upper == "LAST_MANUAL_PREFIX": CONFIG[key_upper] = "M" # Reset to default
        else: CONFIG[key_upper] = None
    else:
        # Save the key-value pair to the .env file
        # set_key will create the file if it doesn't exist, or update the key if it does.
        set_key(_ENV_FILE_PATH, key_upper, str(value)) # Ensure value is string for other keys
        regular(f"Saved {key_upper}='{str(value) if key_upper != 'SUPABASE_KEY' else '********'}' to .env file.")
    
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

_MAX_CODE_GENERATION_ATTEMPTS = 1000 # To prevent infinite loops

def get_or_assign_url_code(url: str) -> str | None:
    """
    Retrieves the two-letter code for a URL. If not found, generates a new one,
    saves it to the .env file, and updates the in-memory config.
    Returns the code, or None if a new code cannot be generated.
    """
    global CONFIG
    if not url:
        log_error("Cannot get or assign code for an empty URL.")
        return None

    # Ensure URL_CODES is loaded and is a dictionary
    if "URL_CODES" not in CONFIG or not isinstance(CONFIG["URL_CODES"], dict):
        warning("URL_CODES configuration is missing or invalid. Attempting to reload.")
        load_config() # Try to reload/initialize it
        if "URL_CODES" not in CONFIG or not isinstance(CONFIG["URL_CODES"], dict):
            log_error("URL_CODES configuration remains invalid after reload. Cannot assign URL code.")
            CONFIG["URL_CODES"] = {} # Reset to empty dict to avoid repeated errors on this call

    # Check if URL already has a code
    if url in CONFIG["URL_CODES"]:
        return CONFIG["URL_CODES"][url]

    # Generate a new unique two-letter code
    existing_codes = set(CONFIG["URL_CODES"].values())
    new_code = None
    for attempt in range(_MAX_CODE_GENERATION_ATTEMPTS):
        code = ''.join(random.choices(string.ascii_uppercase, k=2))
        if code not in existing_codes:
            new_code = code
            break
    
    if new_code is None:
        log_error(f"Failed to generate a unique two-letter code for URL: {url} after {_MAX_CODE_GENERATION_ATTEMPTS} attempts.")
        return None

    # Assign new code and save
    # Create a new dictionary for URL_CODES to ensure we are not modifying a shared mutable object directly
    # before it's correctly processed by save_config_value.
    updated_url_codes = CONFIG["URL_CODES"].copy()
    updated_url_codes[url] = new_code
    
    # Call save_config_value with the entire updated dictionary.
    # save_config_value will handle json.dumps for "URL_CODES".
    save_config_value("URL_CODES", updated_url_codes) 

    # After save_config_value, CONFIG["URL_CODES"] is updated by load_config()
    # so new_code should be accessible via CONFIG["URL_CODES"][url]
    # However, it's safer to return the new_code directly as it was generated.
    maintenance(f"Assigned new code '{new_code}' for URL '{url}'. Configuration updated.")
    return new_code

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
    
    # --- Test calls for get_or_assign_url_code were here during development ---
    # --- They have been removed after confirming functionality.          ---

    print("\nConfig manager test complete.")

# This module can be run directly to test the configuration management functionality.
