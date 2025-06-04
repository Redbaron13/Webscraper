# scheduler.py htmlscrape
# Created by Kevin Baron on 5/19/25.
# Edited Last by Kevin Baron on 5/20/25 @ 00:20:37
# Webscraper/scheduler.py
import schedule
import time
import datetime
from .scraper import fetch_html # ADD A DOT HERE
from .databasemanager import save_scrape_data, close_local_db_connection # ADD A DOT HERE
from .configmanager import get_config # ADD A DOT HERE
from .logger import regular, maintenance, debug, error as log_error, critical # ADD A DOT HERE

# --- Global state for stopping the scheduler ---
_stop_scheduler = False

def stop_scheduler_flag():
    """Sets a flag to stop the scheduler loop gracefully."""
    global _stop_scheduler
    _stop_scheduler = True
    regular("Scheduler stop request received. Will stop after current job cycle if running.")

def perform_scrape(url: str, scrape_type: str, run_index: int):
    """
    Fetches HTML for a given URL and saves it to the databases.
    This is the job function that will be scheduled.
    """
    maintenance(f"Scheduler: Starting {scrape_type} scrape for {url} at {datetime.datetime.now()} (Run index: {run_index})")
    
    prefix_char = 'P' if scrape_type == 'primary' else 'B'
    # run_index is 0-based, UUID run_number should be 1-based (01-09)
    run_number_str = f"{run_index + 1:02d}" 

    html_content = fetch_html(url)
    if html_content:
        # Pass prefix_char and run_number_str to save_scrape_data
        save_scrape_data(url, html_content, scrape_type, prefix_char, run_number_str)
        regular(f"Scheduler: Completed {scrape_type} scrape for {url} (UUID: {prefix_char}{run_number_str}...)")
    else:
        log_error(f"Scheduler: Failed to fetch HTML for {url} during {scrape_type} scrape.")

def setup_schedules():
    """
    Sets up the scraping schedules based on the configuration.
    Clears any existing schedules before setting new ones.
    """
    schedule.clear() # Clear any previously defined jobs
    config = get_config()
    urls = config.get("TARGET_URLS", [])
    primary_times = config.get("SCRAPE_TIMES_PRIMARY", [])
    backup_times = config.get("SCRAPE_TIMES_BACKUP", [])

    if not urls:
        regular("No target URLs configured. Scheduler will not set up any jobs.")
        return

    for url in urls:
        if not url.startswith("http://") and not url.startswith("https://"):
            log_error(f"Invalid URL format (missing http/https): {url}. Skipping this URL for scheduling.")
            continue

        for idx, t in enumerate(primary_times):
            try:
                if idx >= 9: 
                    warning(f"Too many primary times specified for {url}. Only first 9 will get unique run numbers (01-09). Skipping time: {t}")
                    continue
                schedule.every().day.at(t).do(perform_scrape, url=url, scrape_type="primary", run_index=idx)
                maintenance(f"Scheduled PRIMARY scrape for {url} at {t} with run_index {idx}")
            except Exception as e: # Catches errors from schedule.every().day.at(t) e.g. invalid time format
                log_error(f"Failed to schedule PRIMARY scrape for {url} at {t}", error_obj=e)
        
        for idx, t in enumerate(backup_times):
            try:
                if idx >= 9:
                    warning(f"Too many backup times specified for {url}. Only first 9 will get unique run numbers (01-09). Skipping time: {t}")
                    continue
                schedule.every().day.at(t).do(perform_scrape, url=url, scrape_type="backup", run_index=idx)
                maintenance(f"Scheduled BACKUP scrape for {url} at {t} with run_index {idx}")
            except Exception as e:
                log_error(f"Failed to schedule BACKUP scrape for {url} at {t}", error_obj=e)
    
    if schedule.jobs:
        regular(f"Scheduler setup complete. {len(schedule.jobs)} jobs scheduled.")
        debug(f"Current jobs: {schedule.jobs}")
    else:
        regular("Scheduler setup complete. No jobs were scheduled (check URLs and times).")


def run_pending_schedules(run_duration_days: int | None = None):
    """
    Runs the scheduler loop.
    
    Args:
        run_duration_days (int | None): Optional. If provided, the scheduler will run for
                                        this many days and then stop. If None, runs indefinitely.
    """
    global _stop_scheduler
    _stop_scheduler = False # Reset stop flag

    if not schedule.jobs:
        regular("No jobs scheduled. Scheduler will not start.")
        return

    regular("Starting scheduler... Press Ctrl+C to stop manually if running in foreground.")
    
    start_time = datetime.datetime.now()
    end_time = None
    if run_duration_days is not None and run_duration_days > 0:
        end_time = start_time + datetime.timedelta(days=run_duration_days)
        regular(f"Scheduler will run for {run_duration_days} days, until approximately {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    else:
        regular("Scheduler will run indefinitely until stopped.")

    try:
        while not _stop_scheduler:
            schedule.run_pending()
            time.sleep(1) # Check every second

            if end_time and datetime.datetime.now() >= end_time:
                regular(f"Scheduler has reached the configured run duration of {run_duration_days} days. Stopping.")
                break
            
            if _stop_scheduler: # Check flag again after sleep
                regular("Scheduler stopping as per flag.")
                break
                
    except KeyboardInterrupt:
        regular("\nScheduler stopped by user (KeyboardInterrupt).")
    except Exception as e:
        critical("An unexpected error occurred in the scheduler loop.", error_obj=e)
    finally:
        regular("Scheduler has stopped.")
        # Clean up resources like database connections if they are managed globally
        # and not per-transaction. For SQLite, it's good to close when done.
        close_local_db_connection() 
        regular("Local database connection closed by scheduler.")

if __name__ == '__main__':
    from configmanager import load_config, save_config_value
    from logger import set_log_level
    
    set_log_level("DEBUG")
    load_config() # Ensure config is loaded

    # --- Test Setup ---
    # You might need to create/update your .env file for this to work meaningfully
    # Example: set TARGET_URLS and SCRAPE_TIMES_PRIMARY/BACKUP in .env
    # Or, use save_config_value for a temporary test (will modify .env)
    # save_config_value("TARGET_URLS", "https://httpbin.org/html")
    # save_config_value("SCRAPE_TIMES_PRIMARY", datetime.datetime.now().strftime("%H:%M:%S")) # Schedule for now
    
    print("--- Setting up schedules based on current config ---")
    setup_schedules()

    if schedule.jobs:
        print(f"Jobs scheduled: {len(schedule.jobs)}")
        for job in schedule.jobs:
            print(f"  - {job}")
        
        # Run for a very short duration for testing (e.g., 10 seconds then stop)
        # This won't actually run for "days", but will exit the loop.
        # To test actual scheduling, you'd run it for longer or set specific times.
        print("\n--- Running scheduler for a short period (approx 10 seconds) ---")
        
        # Create a temporary job that runs in a few seconds for quick testing
        test_url = get_config().get("TARGET_URLS", ["https://httpbin.org/html"])[0]
        if test_url:
            now = datetime.datetime.now()
            # Schedule a job to run 5 seconds from now
            # schedule_time = (now + datetime.timedelta(seconds=5)).strftime("%H:%M:%S")
            # schedule.every().day.at(schedule_time).do(perform_scrape, url=test_url, scrape_type="test_immediate")
            # print(f"Added temporary immediate job for {test_url} at {schedule_time}")
            
            # Instead of scheduling for a specific time for a short test,
            # we can just call the job directly for testing the perform_scrape function.
            print(f"Manually triggering 'perform_scrape' for {test_url} for testing purposes...")
            # For scheduler's perform_scrape, run_index needs to be provided.
            # Using 0 for a direct test call.
            perform_scrape(url=test_url, scrape_type="test_manual_trigger", run_index=0) 
            print("Manual trigger test complete.")

        # To test the actual scheduler loop, you would run this:
        # print("\n--- Running scheduler indefinitely (Press Ctrl+C to stop) ---")
        # run_pending_schedules()
        
        # For a timed run test:
        # print("\n--- Running scheduler for 0.0001 days (approx 8 seconds) ---")
        # run_pending_schedules(run_duration_days=0.0001) # Very short duration
        
    else:
        print("No jobs scheduled. Make sure TARGET_URLS and SCRAPE_TIMES are set in your .env or config.")

    print("\nScheduler test complete.")
    close_local_db_connection() # Ensure connection is closed after test

