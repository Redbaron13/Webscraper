# utils.py htmlscrape
# Created by Kevin Baron on 5/19/25.
# Edited Last by Kevin Baron on 5/20/25 @ 00:20:37
# web_scraper/utils.py

import uuid
from logger import regular, debug, error as log_error # aliased to avoid conflict

def generate_unique_id() -> str:
    """Generates a unique ID for a scrape instance."""
    unique_id = str(uuid.uuid4())
    debug(f"Generated unique ID: {unique_id}")
    return unique_id

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
        log_error(f"Error parsing time string '{time_str}': {e}", error_obj=e)
        return []
    except Exception as e:
        log_error(f"Unexpected error parsing time string '{time_str}': {e}", error_obj=e)
        return []


if __name__ == '__main__':
    # Example Usage
    from logger import set_log_level
    set_log_level("DEBUG")
    
    print(f"Generated ID: {generate_unique_id()}")
    
    valid_times = "08:00, 17:30,22:15"
    print(f"Parsed times for '{valid_times}': {parse_times(valid_times)}")

    invalid_times_format = "09:00,abc,14:00"
    print(f"Parsed times for '{invalid_times_format}': {parse_times(invalid_times_format)}")

    invalid_times_value = "25:00,12:60"
    print(f"Parsed times for '{invalid_times_value}': {parse_times(invalid_times_value)}")
    
    empty_times = ""
    print(f"Parsed times for empty string: {parse_times(empty_times)}")
    
    none_times = None
    # print(f"Parsed times for None: {parse_times(none_times)}") # This would cause an error, handle appropriately

