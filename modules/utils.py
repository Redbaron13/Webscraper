# utils.py htmlscrape
# Created by Kevin Baron on 5/19/25.
# Edited Last by Kevin Baron on 5/20/25 @ 00:20:37
# Webscraper/utils.py

import uuid
from datetime import datetime
import random
import string
from .configmanager import get_or_assign_url_code
# Use relative import for logger if utils.py is considered part of the 'modules' package
from .logger import debug, error as log_error, warning, regular


# def generate_unique_id() -> str:
#     """Generates a unique ID for a scrape instance."""
#     unique_id = str(uuid.uuid4())
#     debug(f"Generated unique ID: {unique_id}")
#     return unique_id

def generate_custom_uuid(prefix_char: str, run_number_str: str, url: str, get_next_sequence_func: callable) -> str | None:
    """
    Generates a custom UUID for a scrape event.
    Format: prefix_char + run_number_str + url_code + timestamp_str + random_part_str + sequence_str
    Example: "P01AB20230520103000R4ND0M5TR001"
    """
    # Validate inputs
    valid_prefixes = ['P', 'B', 'T', 'M']
    if prefix_char not in valid_prefixes:
        log_error(f"Invalid prefix_char: '{prefix_char}'. Must be one of {valid_prefixes}.")
        return None
    
    if not (isinstance(run_number_str, str) and len(run_number_str) == 2 and run_number_str.isdigit()):
        log_error(f"Invalid run_number_str: '{run_number_str}'. Must be a 2-digit string.")
        return None
        
    if not url:
        log_error("URL cannot be empty for custom UUID generation.")
        return None
        
    if not callable(get_next_sequence_func):
        log_error("get_next_sequence_func must be a callable function.")
        return None

    # Get URL Code
    url_code = get_or_assign_url_code(url)
    if url_code is None:
        log_error(f"Could not get or assign URL code for URL: {url}")
        return None

    # Get Timestamp
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")

    # Generate Random Part
    # 8-character random alphanumeric string (uppercase letters and digits)
    random_part_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Get Sequential Counter
    sequence_int = get_next_sequence_func(url_code, prefix_char)
    if sequence_int is None or sequence_int < 0:
        log_error(f"Failed to get a valid sequence number for url_code '{url_code}', prefix '{prefix_char}'. Received: {sequence_int}")
        return None
    
    if sequence_int > 999:
        warning(f"Sequence number {sequence_int} for url_code '{url_code}', prefix '{prefix_char}' exceeds 999. Capping at 999.")
        sequence_int = 999
    sequence_str = f"{sequence_int:03d}"

    # Assemble UUID
    custom_uuid = f"{prefix_char}{run_number_str}{url_code}{timestamp_str}{random_part_str}{sequence_str}"
    debug(f"Generated custom UUID: {custom_uuid} for URL: {url}")
    return custom_uuid

# parse_times has been moved to configmanager.py to break circular dependencies.

if __name__ == '__main__':
    # The following code was used for testing generate_custom_uuid directly from utils.py.
    # It has been commented out as it's for development/testing purposes only.
    # To re-enable, ensure logger and configmanager are correctly imported and initialized.

    # from modules.logger import set_log_level 
    # from modules.configmanager import load_config, get_or_assign_url_code # get_or_assign_url_code needed for capping test
    
    # print("Initializing logger and config for testing utils.py...")
    # set_log_level("DEBUG") 
    # load_config() # Needed for get_or_assign_url_code to interact with .env
    
    # # --- Dummy function for testing generate_custom_uuid ---
    # _test_counters = {}
    # def _dummy_get_next_sequence(url_code, prefix_char):
    #     key = (url_code, prefix_char)
    #     if key not in _test_counters:
    #         _test_counters[key] = 0
    #     _test_counters[key] += 1
    #     if _test_counters[key] > 1000 and prefix_char == "T": # Specific condition for capping test
    #         return 1001 
    #     return _test_counters[key]
    # # --- End Dummy function ---

    # print("\n--- Testing Custom UUID Generation ---")
    # test_url_uuid_A = "https://www.example.com/pageA_utils_test" # Unique URL for this test run
    # test_url_uuid_B = "https://www.example.com/pageB_utils_test" # Unique URL for this test run

    # uuid1 = generate_custom_uuid("P", "01", test_url_uuid_A, _dummy_get_next_sequence)
    # print(f"UUID 1 (P01 for {test_url_uuid_A}): {uuid1}")
    
    # uuid2 = generate_custom_uuid("P", "01", test_url_uuid_A, _dummy_get_next_sequence)
    # print(f"UUID 2 (P01 for {test_url_uuid_A}, next sequence): {uuid2}")
    
    # uuid3 = generate_custom_uuid("M", "99", test_url_uuid_A, _dummy_get_next_sequence)
    # print(f"UUID 3 (M99 for {test_url_uuid_A}): {uuid3}")
    
    # uuid4 = generate_custom_uuid("P", "01", test_url_uuid_B, _dummy_get_next_sequence)
    # print(f"UUID 4 (P01 for {test_url_uuid_B}): {uuid4}")

    # print("\n--- Testing Invalid Inputs for Custom UUID ---")
    # print(f"UUID (invalid prefix 'X'): {generate_custom_uuid('X', '01', test_url_uuid_A, _dummy_get_next_sequence)}")
    # print(f"UUID (invalid run_number '1'): {generate_custom_uuid('P', '1', test_url_uuid_A, _dummy_get_next_sequence)}")
    # print(f"UUID (invalid run_number 'A1'): {generate_custom_uuid('P', 'A1', test_url_uuid_A, _dummy_get_next_sequence)}")
    # print(f"UUID (empty URL): {generate_custom_uuid('P', '01', '', _dummy_get_next_sequence)}")
    # print(f"UUID (non-callable sequence func): {generate_custom_uuid('P', '01', test_url_uuid_A, 'not_callable')}")

    # print("\n--- Testing Sequence Capping ---")
    # # For this specific test to work as intended, get_or_assign_url_code must be operational
    # # to create a consistent url_code for test_url_uuid_A.
    # url_code_for_cap_test = get_or_assign_url_code(test_url_uuid_A) 
    # if url_code_for_cap_test:
    #     key_for_cap_test = (url_code_for_cap_test, "T") 
    #     _test_counters[key_for_cap_test] = 998 # Setup counter just before cap
        
    #     uuid_cap1 = generate_custom_uuid("T", "05", test_url_uuid_A, _dummy_get_next_sequence)
    #     print(f"UUID Cap Test 1 (seq 999): {uuid_cap1}")
    #     uuid_cap2 = generate_custom_uuid("T", "05", test_url_uuid_A, _dummy_get_next_sequence)
    #     print(f"UUID Cap Test 2 (seq 1000, capped to 999 by dummy): {uuid_cap2}")
    #     uuid_cap3 = generate_custom_uuid("T", "05", test_url_uuid_A, _dummy_get_next_sequence) 
    #     print(f"UUID Cap Test 3 (seq 1001, capped to 999 by dummy): {uuid_cap3}")
    # else:
    #     print("Skipping sequence capping test as URL code could not be obtained.")
    
    print("\n--- Utils test block (commented out) ---")

