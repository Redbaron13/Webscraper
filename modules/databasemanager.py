# modules/databasemanager.py
import sqlite3
import datetime
import json # Added for attributes serialization
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from postgrest.exceptions import APIError as SupabaseAPIError

from .logger import regular, maintenance, debug, error as log_error, critical, warning
from .configmanager import get_config, load_config, ENV_FILE # ENV_FILE needed for if __name__
from .utils import generate_custom_uuid
from .parser import parse_html_tags_from_list # Added parser import
from requests_html import HTML # Added for creating HTML object from string

# --- Database Schema ---
DB_TABLE_NAME = "scraped_pages"
HTML_TAG_DATA_TABLE_NAME = "html_tag_data" # New table for tag data

SQLITE_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {DB_TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_uuid TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    scrape_timestamp TEXT NOT NULL,
    scrape_type TEXT NOT NULL,
    html_content TEXT NOT NULL,
    identical_match INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1
);
"""

SQLITE_HTML_TAG_DATA_TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {HTML_TAG_DATA_TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_uuid TEXT NOT NULL,
    tag_type TEXT NOT NULL,
    content TEXT,
    location TEXT,
    attributes TEXT, -- Store as JSON string
    FOREIGN KEY (capture_uuid) REFERENCES {DB_TABLE_NAME}(capture_uuid) ON DELETE CASCADE
);
"""

SEQUENTIAL_COUNTERS_TABLE_NAME = "sequential_counters"
SQLITE_SEQUENTIAL_COUNTERS_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {SEQUENTIAL_COUNTERS_TABLE_NAME} (
    url_code TEXT NOT NULL,
    prefix_char TEXT NOT NULL,
    last_sequence INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (url_code, prefix_char)
);
"""

_local_db_connection: sqlite3.Connection | None = None

def get_local_db_connection() -> sqlite3.Connection | None:
    global _local_db_connection
    if _local_db_connection is None:
        config = get_config()
        db_path = config.get("LOCAL_DB_PATH", "default_scraper.db")
        try:
            _local_db_connection = sqlite3.connect(db_path, check_same_thread=False)
            _local_db_connection.row_factory = sqlite3.Row
            maintenance(f"Successfully connected to local SQLite database: {db_path}")
        except sqlite3.Error as e:
            critical(f"CRITICAL: Error connecting to SQLite database at {db_path}", error_obj=e)
            _local_db_connection = None
    return _local_db_connection

def close_local_db_connection():
    global _local_db_connection
    if _local_db_connection:
        try:
            _local_db_connection.close()
            _local_db_connection = None
            maintenance("Closed local SQLite database connection.")
        except sqlite3.Error as e:
            log_error("Error closing SQLite database connection", error_obj=e)

_supabase_client: Client | None = None

def get_supabase_client() -> Client | None:
    global _supabase_client
    if _supabase_client is None:
        config = get_config()
        supabase_url = config.get("SUPABASE_URL")
        supabase_key = config.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            debug("Supabase URL or Key not configured. Supabase client will not be initialized.")
            return None
        try:
            options = ClientOptions()
            _supabase_client = create_client(supabase_url, supabase_key, options=options)
            maintenance("Successfully initialized Supabase client.")
        except Exception as e:
            critical("CRITICAL: Error initializing Supabase client. Check URL/Key and network.", error_obj=e)
            _supabase_client = None
    return _supabase_client

def initialize_databases():
    regular("Initializing databases...")
    conn = get_local_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.executescript(SQLITE_TABLE_SCHEMA)
            regular(f"SQLite table '{DB_TABLE_NAME}' ensured/created successfully.")
            
            cursor.executescript(SQLITE_HTML_TAG_DATA_TABLE_SCHEMA) # Create new tag data table
            regular(f"SQLite table '{HTML_TAG_DATA_TABLE_NAME}' ensured/created successfully.")

            cursor.executescript(SQLITE_SEQUENTIAL_COUNTERS_SCHEMA)
            regular(f"SQLite table '{SEQUENTIAL_COUNTERS_TABLE_NAME}' ensured/created successfully.")
            
            conn.commit()
        except sqlite3.Error as e:
            log_error(f"Error creating/ensuring SQLite tables ('{DB_TABLE_NAME}', '{HTML_TAG_DATA_TABLE_NAME}', '{SEQUENTIAL_COUNTERS_TABLE_NAME}')", error_obj=e)
    else:
        log_error("Failed to initialize SQLite database: No connection could be established.")

    sb_client = get_supabase_client()
    if sb_client:
        try:
            # Check main scraped_pages table
            response_main = sb_client.table(DB_TABLE_NAME).select("capture_uuid", count="exact").limit(0).execute()
            if hasattr(response_main, 'error') and response_main.error:
                warning(f"Supabase table '{DB_TABLE_NAME}' might not exist or be accessible. Please create it. Error: {response_main.error}")
            elif response_main.count is not None:
                regular(f"Supabase table '{DB_TABLE_NAME}' is accessible.")
            
            # Check new html_tag_data table
            response_tags = sb_client.table(HTML_TAG_DATA_TABLE_NAME).select("id", count="exact").limit(0).execute() # Check for 'id' or any column
            if hasattr(response_tags, 'error') and response_tags.error:
                warning(f"Supabase table '{HTML_TAG_DATA_TABLE_NAME}' might not exist or be accessible. Please create it. Error: {response_tags.error}")
            elif response_tags.count is not None:
                regular(f"Supabase table '{HTML_TAG_DATA_TABLE_NAME}' is accessible.")

        except SupabaseAPIError as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                warning(
                    f"One or more Supabase tables ('{DB_TABLE_NAME}', '{HTML_TAG_DATA_TABLE_NAME}', '{SEQUENTIAL_COUNTERS_TABLE_NAME}') may not exist. "
                    f"Please create them via the Supabase dashboard (SQL Editor). "
                    f"Expected schema for '{DB_TABLE_NAME}': id (auto PK), capture_uuid (TEXT/UUID UNIQUE), url (TEXT), "
                    f"scrape_timestamp (TIMESTAMPTZ), scrape_type (TEXT), html_content (TEXT), "
                    f"identical_match (INTEGER), version (INTEGER)."
                    f"Expected schema for '{HTML_TAG_DATA_TABLE_NAME}': id (auto PK), capture_uuid (TEXT/UUID, FK to {DB_TABLE_NAME}), "
                    f"tag_type (TEXT), content (TEXT), location (TEXT), attributes (JSON/JSONB)."
                    f"Expected schema for '{SEQUENTIAL_COUNTERS_TABLE_NAME}': url_code (TEXT), prefix_char (TEXT), "
                    f"last_sequence (INTEGER), PRIMARY KEY (url_code, prefix_char)."
                )
            else:
                log_error(f"Supabase API error while checking tables. Ensure they are created and accessible.", error_obj=e)
        except Exception as e:
            log_error(f"Unexpected error while checking Supabase tables.", error_obj=e)
    else:
        debug("Supabase not configured. Skipping Supabase table check.")
    maintenance("Database initialization/verification process complete.")

def get_next_sequence(url_code: str, prefix_char: str) -> int | None:
    conn = get_local_db_connection()
    if not conn:
        log_error("Cannot get next sequence: No database connection.")
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE {SEQUENTIAL_COUNTERS_TABLE_NAME} SET last_sequence = last_sequence + 1 WHERE url_code = ? AND prefix_char = ?", (url_code, prefix_char))
        if cursor.rowcount == 0:
            cursor.execute(f"INSERT INTO {SEQUENTIAL_COUNTERS_TABLE_NAME} (url_code, prefix_char, last_sequence) VALUES (?, ?, 1)", (url_code, prefix_char))
            conn.commit()
            debug(f"Initialized sequence for ({url_code}, {prefix_char}) to 1.")
            return 1
        else:
            cursor.execute(f"SELECT last_sequence FROM {SEQUENTIAL_COUNTERS_TABLE_NAME} WHERE url_code = ? AND prefix_char = ?", (url_code, prefix_char))
            row = cursor.fetchone()
            conn.commit()
            if row:
                new_sequence = row['last_sequence']
                debug(f"Incremented sequence for ({url_code}, {prefix_char}) to {new_sequence}.")
                return new_sequence
            else:
                log_error(f"Failed to retrieve sequence for ({url_code}, {prefix_char}) after update/insert.")
                conn.rollback()
                return None
    except sqlite3.Error as e:
        log_error(f"Database error in get_next_sequence for ({url_code}, {prefix_char})", error_obj=e)
        if conn: conn.rollback()
        return None

def save_scrape_data(url: str, html_content: str, scrape_type: str, prefix_char: str, run_number_str: str, version: int = 1) -> str | None:
    if not html_content:
        log_error(f"No HTML content provided for URL: {url}. Skipping save operation.")
        return None

    capture_id = generate_custom_uuid(prefix_char, run_number_str, url, get_next_sequence)
    if capture_id is None:
        log_error(f"Failed to generate custom UUID for URL: {url}. Skipping save operation.")
        return None

    timestamp_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp_iso = timestamp_utc.isoformat()

    conn = get_local_db_connection()
    identical_match_value = 0
    if conn:
        try:
            cursor_check = conn.cursor()
            cursor_check.execute(f"SELECT 1 FROM {DB_TABLE_NAME} WHERE url = ? AND html_content = ? LIMIT 1", (url, html_content))
            if cursor_check.fetchone():
                identical_match_value = 1
                debug(f"Identical HTML content found for {url}. Flagging as identical_match=1.")
        except sqlite3.Error as e:
            log_error(f"Error checking for identical HTML for {url}. Defaulting identical_match to 0.", error_obj=e)
    else:
        log_error("No SQLite connection for identical HTML check. Defaulting identical_match to 0.")

    data_to_insert_main = {
        "capture_uuid": capture_id, "url": url, "scrape_timestamp": timestamp_iso,
        "scrape_type": scrape_type, "html_content": html_content,
        "identical_match": identical_match_value, "version": version
    }
    
    maintenance(f"Preparing to save scrape data for {url} (Capture UUID: {capture_id}, Type: {scrape_type}, Identical: {identical_match_value})")
    saved_locally = False

    if conn:
        tag_data_list = [] # Initialize tag_data_list to ensure it's always defined
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {DB_TABLE_NAME} (capture_uuid, url, scrape_timestamp, scrape_type, html_content, identical_match, version)
                VALUES (:capture_uuid, :url, :scrape_timestamp, :scrape_type, :html_content, :identical_match, :version)
            """, data_to_insert_main)
            # Do not commit yet, include tag data in the same transaction for SQLite

            # --- Begin: Parse and save HTML tag data ---
            debug(f"Attempting to parse and save tag data for {capture_id}.")
            html_doc_for_parsing = HTML(html=html_content) # Create HTML object from the string
            all_elements = html_doc_for_parsing.find('*') # Get all elements

            if all_elements:
                tag_data_list = parse_html_tags_from_list(all_elements)
                debug(f"Parsed {len(tag_data_list)} tags from HTML content for {capture_id}.")

                if tag_data_list:
                    for tag_info in tag_data_list:
                        try:
                            attributes_json = json.dumps(tag_info['attributes'])
                            cursor.execute(f"""
                                INSERT INTO {HTML_TAG_DATA_TABLE_NAME}
                                (capture_uuid, tag_type, content, location, attributes)
                                VALUES (?, ?, ?, ?, ?)
                            """, (capture_id, tag_info['tag_type'], tag_info['content'], tag_info['location'], attributes_json))
                        except Exception as e_tag_insert: # Catch errors during individual tag insert
                            log_error(f"Error inserting a specific tag ({tag_info.get('tag_type')}, loc: {tag_info.get('location')}) for {capture_id} into SQLite.", error_obj=e_tag_insert)
                    maintenance(f"Attempted to save {len(tag_data_list)} parsed tags to SQLite for {capture_id}.")
            else:
                # tag_data_list remains [] if no elements found
                debug(f"No elements found by html_doc.find('*') for {capture_id}. Skipping tag data save.")
            # --- End: Parse and save HTML tag data ---

            conn.commit() # Commit main page data and tag data together for SQLite
            regular(f"Successfully saved main scrape and associated tag data for {url} to SQLite. UUID: {capture_id}")
            saved_locally = True
        except sqlite3.IntegrityError as e:
            log_error(f"SQLite IntegrityError for {url} (UUID: {capture_id}). This might be due to duplicate UUID or other constraint. Rolling back.", error_obj=e)
            if conn: conn.rollback()
        except Exception as e: # Catch broader errors like issues with HTML parsing itself or other DB errors
            log_error(f"Error saving scrape data (main or tags) for {url} to SQLite. Rolling back.", error_obj=e)
            if conn: conn.rollback()
    else:
        log_error("Cannot save to SQLite: No database connection available.")

    # Supabase saving (main page data only for now, tag data for Supabase is a TODO)
    sb_client = get_supabase_client()
    if sb_client and saved_locally: # Only try Supabase if local save was successful
        try:
            response = sb_client.table(DB_TABLE_NAME).insert(data_to_insert_main).execute()
            if hasattr(response, 'error') and response.error:
                log_error(f"Error saving main scrape data for {url} to Supabase: {response.error}", error_obj=Exception(str(response.error)))
            elif response.data:
                regular(f"Successfully saved main scrape data for {url} to Supabase.")

            # --- Begin: Save HTML tag data to Supabase ---
            if tag_data_list: # Check if there's any tag data to save
                maintenance(f"Attempting to save {len(tag_data_list)} parsed tags to Supabase table {HTML_TAG_DATA_TABLE_NAME} for {capture_id}.")
                tags_saved_to_supabase_count = 0
                for tag_info in tag_data_list:
                    try:
                        supabase_tag_payload = {
                            "capture_uuid": capture_id,
                            "tag_type": tag_info['tag_type'],
                            "content": tag_info['content'],
                            "location": tag_info['location'],
                            "attributes": tag_info['attributes'] # Pass dict directly
                        }
                        response_tag_sb = sb_client.table(HTML_TAG_DATA_TABLE_NAME).insert(supabase_tag_payload).execute()
                        if hasattr(response_tag_sb, 'error') and response_tag_sb.error:
                            log_error(f"Error saving tag to Supabase for {capture_id}: {response_tag_sb.error}", error_obj=Exception(str(response_tag_sb.error)))
                        else:
                            tags_saved_to_supabase_count += 1
                    except Exception as e_sb_tag:
                        log_error(f"Unexpected error saving tag to Supabase for {capture_id}", error_obj=e_sb_tag)

                if tags_saved_to_supabase_count > 0:
                    regular(f"Successfully saved {tags_saved_to_supabase_count} tags to Supabase for {capture_id}.")
                if tags_saved_to_supabase_count < len(tag_data_list):
                    warning(f"Only {tags_saved_to_supabase_count} out of {len(tag_data_list)} tags were saved to Supabase for {capture_id} due to errors.")
            else:
                debug(f"No tag data to save to Supabase for {capture_id}.")
            # --- End: Save HTML tag data to Supabase ---

        except SupabaseAPIError as e:
            log_error(f"Supabase API error saving main scrape data for {url} to Supabase", error_obj=e)
        except Exception as e:
            log_error(f"Unexpected error saving main scrape data for {url} to Supabase", error_obj=e)
    elif not saved_locally:
        debug(f"Skipping Supabase save for {url} because local save failed or was skipped.")
    else: # sb_client is None
        debug("Supabase not configured. Skipping save to Supabase.")

    return capture_id if saved_locally else None


if __name__ == '__main__':
    # This test script will now also test creation of html_tag_data table
    # and saving of parsed tags for the first successful scrape.
    load_config()
    from .logger import set_log_level
    set_log_level("DEBUG")

    regular("Starting databasemanager test script (with tag parsing)...")
    
    import os
    config_values = get_config()
    db_path_for_test = config_values.get("LOCAL_DB_PATH", "web_scraper_data.db")
    
    # Ensure current connection is closed before deleting file
    close_local_db_connection()
    
    if os.path.exists(db_path_for_test):
        try:
            os.remove(db_path_for_test)
            maintenance(f"TESTING: Removed existing database file: {db_path_for_test}")
        except OSError as e:
            critical(f"TESTING: Error removing database file {db_path_for_test}: {e}. Tests might be affected.", error_obj=e)

    print("\n--- Initializing Databases (creates tables if they don't exist) ---")
    initialize_databases() # This will now create html_tag_data table as well

    print("\n--- Testing Save Operation (with custom UUIDs, identical_match, and tag parsing) ---")
    test_url_1 = "http://example.com/dbm_testpage1_tags"
    test_html_content_1 = "<html><head><title>Tag Test</title></head><body><h1>Main Title</h1><p>A paragraph with <span>some text</span> and <a href='#'>a link</a>.</p></body></html>"
    
    print(f"\nSaving first version of {test_url_1} with tags...")
    # Use a known prefix and run number for predictability if needed for other tests
    capture_uuid_1 = save_scrape_data(test_url_1, test_html_content_1, "primary", "P", "01", version=1)
    if capture_uuid_1:
        print(f"Save 1 for {test_url_1} (UUID: {capture_uuid_1}) successful.")
    else:
        print(f"Save 1 for {test_url_1} FAILED.")
    assert capture_uuid_1 is not None

    print("\n--- Verifying SQLite Data (Manual Query) ---")
    conn_verify = get_local_db_connection() # Re-establish connection if closed by reset
    if conn_verify:
        try:
            cursor = conn_verify.cursor()
            # Check main table
            cursor.execute(f"SELECT capture_uuid, url, identical_match FROM {DB_TABLE_NAME} WHERE capture_uuid = ?", (capture_uuid_1,))
            main_row = cursor.fetchone()
            if main_row:
                print(f"Main data for {capture_uuid_1}: URL: {main_row['url']}, Identical: {main_row['identical_match']}")
            else:
                print(f"No main data found for {capture_uuid_1}")

            # Check tag data table
            cursor.execute(f"SELECT tag_type, content, location, attributes FROM {HTML_TAG_DATA_TABLE_NAME} WHERE capture_uuid = ?", (capture_uuid_1,))
            tag_rows = cursor.fetchall()
            if tag_rows:
                print(f"Found {len(tag_rows)} tags for {capture_uuid_1}:")
                for row_data in tag_rows[:3]: # Print first 3 tags
                    attrs = json.loads(row_data['attributes']) if row_data['attributes'] else {}
                    print(f"  Tag: {row_data['tag_type']}, Loc: {row_data['location']}, Content: '{row_data['content']}', Attrs: {attrs}")
            else:
                print(f"No tag data found for {capture_uuid_1}. This is unexpected if parsing worked.")
            assert len(tag_rows) > 0, "Expected tag data to be saved"

        except sqlite3.Error as e:
            log_error("Error querying SQLite for verification during test", error_obj=e)
        except json.JSONDecodeError as e:
            log_error("Error decoding JSON attributes from DB during test", error_obj=e)
    else:
        print("Could not connect to SQLite to verify data during test.")
    
    close_local_db_connection()
    print("\nDatabase manager test script (with tag parsing) complete.")
