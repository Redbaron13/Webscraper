# modules/diagnostics.py
import requests # For simple URL accessibility check
from .configmanager import get_config
from .databasemanager import get_supabase_client, DB_TABLE_NAME # To check Supabase client and connection
from .scraper import fetch_html # For a basic scrape test
from .logger import regular, maintenance, debug, warning, error as log_error

def check_supabase_connection() -> bool:
    """
    Checks if the Supabase client can be initialized and perform a lightweight query.
    """
    maintenance("Running Supabase connection check...")
    sb_client = get_supabase_client()
    if not sb_client:
        # get_supabase_client() already logs warnings/errors if not configured or init fails
        warning("Supabase client not configured or failed to initialize. Supabase check considered failed.")
        return False
    
    try:
        # Attempt a lightweight query to the scraped_pages table.
        # This confirms that the connection URL, key, and basic table access are working.
        response = sb_client.table(DB_TABLE_NAME).select("capture_uuid", count="exact").limit(0).execute()
        
        # For Supabase-py v2.x, APIError is typically raised for HTTP errors.
        # For older versions or non-HTTP errors, response might contain an error object.
        if hasattr(response, 'error') and response.error:
            log_error(f"Supabase test query failed with response error: {response.error}", error_obj=Exception(str(response.error)))
            return False
        
        maintenance("Supabase client initialized and test query successful. Supabase check passed.")
        return True
    except Exception as e:
        # This will catch APIError from v2.x or other exceptions during the query
        log_error("Supabase connection/query check failed during test query.", error_obj=e)
        return False

def check_url_accessibility(url: str) -> bool:
    """Checks if a URL is accessible using a HEAD request."""
    maintenance(f"Checking URL accessibility for: {url}...")
    try:
        response = requests.head(url, timeout=10, allow_redirects=True) # HEAD is lighter
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        maintenance(f"URL {url} is accessible (Status: {response.status_code}).")
        return True
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to access URL {url}.", error_obj=e)
        return False

def test_basic_scrape(url: str) -> bool:
    """Performs a basic scrape test for a URL without JS rendering."""
    maintenance(f"Performing basic scrape test for: {url}...")
    html_content = fetch_html(url, attempt_js_render=False) 
    if html_content and len(html_content) > 0:
        maintenance(f"Basic scrape for {url} successful (got {len(html_content)} bytes).")
        if "<body>" in html_content.lower():
            debug(f"Found <body> tag in scraped content for {url}.")
        else:
            warning(f"Did not find <body> tag in scraped content for {url}.")
        return True
    else:
        log_error(f"Basic scrape for {url} failed to retrieve content.")
        return False

def run_all_diagnostics():
    """Runs all defined diagnostic checks."""
    regular("Starting system diagnostics...")
    config = get_config()
    all_passed = True

    if config.get("SUPABASE_URL") and config.get("SUPABASE_KEY"):
        regular("--- Running Supabase Diagnostics ---")
        if not check_supabase_connection():
            all_passed = False
    else:
        maintenance("Supabase not configured. Skipping Supabase connection check.")

    target_urls = config.get("TARGET_URLS", [])
    if not target_urls:
        warning("No target URLs configured. Skipping URL and scrape diagnostics.")
    else:
        urls_to_test = target_urls[:1] # Test only the first URL for brevity
        for url in urls_to_test:
            regular(f"--- Diagnostics for URL: {url} ---")
            if not check_url_accessibility(url):
                all_passed = False
            if not test_basic_scrape(url):
                all_passed = False
    
    regular("--- System Diagnostics Summary ---")
    if all_passed:
        regular("All diagnostic checks passed successfully.")
    else:
        warning("Some diagnostic checks failed. Please review logs above for details.")
    return all_passed

if __name__ == '__main__':
    # This block is for direct testing of this module.
    print("Running diagnostics.py directly (requires configuration to be loaded)...")
    
    try:
        # This setup is simplified. For robust standalone testing, ensure .env is loaded
        # and paths are correctly configured for imports.
        from .configmanager import load_config, get_config
        from .logger import set_log_level
        
        load_config()
        current_log_level = get_config().get("LOG_LEVEL", "DEBUG")
        set_log_level(current_log_level)
        print(f"Log level set to {current_log_level} for direct diagnostic run.")

        run_all_diagnostics()
    except ImportError as e:
        print(f"ImportError: {e}. If running diagnostics.py directly, ensure Python can find other 'modules'. Try 'python -m modules.diagnostics' from project root.")
    except Exception as e:
        print(f"An error occurred during direct diagnostic run: {e}")

    print("Direct diagnostic run finished.")
