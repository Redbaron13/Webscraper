import click
import os
import time
from .configmanager import ( # ADD A DOT HERE
    get_config,
    save_config_value,
    load_config,
    ENV_FILE,
    DEFAULT_PRIMARY_TIMES_STR,
    DEFAULT_BACKUP_TIMES_STR,
    DEFAULT_LOG_LEVEL_STR,
    parse_times, # Added parse_times here
)
from .databasemanager import initialize_databases, save_scrape_data, close_local_db_connection # ADD A DOT HERE
from .scraper import fetch_html # ADD A DOT HERE
from .scheduler import setup_schedules, run_pending_schedules, stop_scheduler_flag # ADD A DOT HERE
from .logger import regular, maintenance, debug, error as log_error, set_log_level as set_global_log_level, LOG_LEVELS # ADD A DOT HERE
# from utils import parse_times # Removed from here
from .diagnostics import run_all_diagnostics # This one is already correct



@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """
    Web Scraper and Archiver CLI.
    Manages configuration, manual scrapes, and scheduled scraping tasks.
    """
    load_config() # Ensure config is loaded at the start of any command

@cli.command()
@click.option('--url', prompt='Supabase Project URL', help='Your Supabase project URL.')
@click.option('--key', prompt='Supabase Anon Key', help='Your Supabase project anon (public) key.', hide_input=True)
@click.option('--target-urls', prompt='Target URLs (comma-separated)', help='URLs to scrape.', default="", show_default=False)
@click.option('--primary-times', prompt='Primary Scrape Times (HH:MM, comma-separated)', default=DEFAULT_PRIMARY_TIMES_STR, help='Times for primary scrapes.')
@click.option('--backup-times', prompt='Backup Scrape Times (HH:MM, comma-separated)', default=DEFAULT_BACKUP_TIMES_STR, help='Times for backup scrapes.')
@click.option('--log-level', prompt='Log Level', type=click.Choice(list(LOG_LEVELS.keys()), case_sensitive=False), default=DEFAULT_LOG_LEVEL_STR, help='Set the logging verbosity.')
def setup():
    """Interactively set up Supabase credentials, target URLs, and scrape times."""
    regular("Starting interactive setup...")

    save_config_value("SUPABASE_URL", click.prompt('Supabase Project URL', default=get_config().get("SUPABASE_URL", "")))
    save_config_value("SUPABASE_KEY", click.prompt('Supabase Anon Key', default=get_config().get("SUPABASE_KEY", ""), hide_input=True))
    
    current_urls = ",".join(get_config().get("TARGET_URLS", []))
    target_urls_str = click.prompt('Target URLs (comma-separated)', default=current_urls)
    save_config_value("TARGET_URLS", target_urls_str)

    current_primary_times = ",".join(get_config().get("SCRAPE_TIMES_PRIMARY", parse_times(DEFAULT_PRIMARY_TIMES_STR)))
    primary_times_str = click.prompt('Primary Scrape Times (HH:MM, comma-separated)', default=current_primary_times)
    if not parse_times(primary_times_str): # Validate input
        log_error("Invalid primary time format. Please use HH:MM, comma-separated.")
        primary_times_str = click.prompt('Re-enter Primary Scrape Times (HH:MM, comma-separated)', default=DEFAULT_PRIMARY_TIMES_STR)
    save_config_value("SCRAPE_TIMES_PRIMARY", primary_times_str)

    current_backup_times = ",".join(get_config().get("SCRAPE_TIMES_BACKUP", parse_times(DEFAULT_BACKUP_TIMES_STR)))
    backup_times_str = click.prompt('Backup Scrape Times (HH:MM, comma-separated)', default=current_backup_times)
    if not parse_times(backup_times_str): # Validate input
        log_error("Invalid backup time format. Please use HH:MM, comma-separated.")
        backup_times_str = click.prompt('Re-enter Backup Scrape Times (HH:MM, comma-separated)', default=DEFAULT_BACKUP_TIMES_STR)
    save_config_value("SCRAPE_TIMES_BACKUP", backup_times_str)
    
    current_log_level = get_config().get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    log_level_str = click.prompt('Log Level', type=click.Choice(list(LOG_LEVELS.keys()), case_sensitive=False), default=current_log_level)
    save_config_value("LOG_LEVEL", log_level_str)
    set_global_log_level(log_level_str) # Apply immediately

    regular(f"Configuration saved to {ENV_FILE}")
    
    if click.confirm("Do you want to initialize the databases now (create tables if they don't exist)?", default=True):
        initialize_databases()
    
    regular("Setup complete. You can now run 'main.py run' or 'main.py manual-scrape'.")

@cli.command()
def show_config():
    """Displays the current configuration from the .env file."""
    config = get_config()
    regular("Current Configuration:")
    if not os.path.exists(ENV_FILE) and not any(config.values()):
        regular(f"No .env file found at {ENV_FILE} and no default values set. Run 'setup' command first.")
        return

    for key, value in config.items():
        if key == "SUPABASE_KEY" and value:
            click.echo(f"  {key}: {'*' * len(value) if value else 'Not set'}")
        elif isinstance(value, list):
             click.echo(f"  {key}: {', '.join(value) if value else 'Not set'}")
        else:
            click.echo(f"  {key}: {value if value else 'Not set'}")
    
    if not config.get("SUPABASE_URL") or not config.get("SUPABASE_KEY"):
        regular("\nWarning: Supabase URL or Key is not set. Supabase integration will be disabled.")
    if not config.get("TARGET_URLS"):
        regular("\nWarning: No target URLs are set. The scheduler will not run any scrapes.")

@cli.command()
@click.argument('url', required=True)
@click.option('--scrape-type', type=click.Choice(['primary', 'backup', 'manual'], case_sensitive=False), default='manual', help="Type of scrape.")
def manual_scrape(url: str, scrape_type: str):
    """Performs a one-time scrape of the given URL and saves the data."""
    if not url.startswith("http://") and not url.startswith("https://"):
        log_error("Invalid URL. Please include http:// or https://")
        return
        
    regular(f"Starting manual scrape for: {url} (Type: {scrape_type})")
    set_global_log_level(get_config().get("LOG_LEVEL", "REGULAR")) # Ensure log level is set

    # Initialize DBs in case they haven't been, or if schema changed
    # It's good practice to ensure tables exist before trying to write.
    if click.confirm("Ensure database tables are initialized before scraping?", default=False):
        initialize_databases()

    html_content = fetch_html(url)
    if html_content:
        config = get_config()
        last_manual_prefix = config.get("LAST_MANUAL_PREFIX", "M")
        current_manual_prefix = 'T' if last_manual_prefix == 'M' else 'M'
        
        # Save the newly used prefix back to config (and .env)
        # This will also trigger a reload of config in memory due to how save_config_value works
        save_config_value("LAST_MANUAL_PREFIX", current_manual_prefix)
        
        run_number_str = "99" # Manual scrapes use "99"
        
        # The scrape_type variable from click option is passed as the general scrape_type
        # The current_manual_prefix and run_number_str are for the UUID generation specifically
        save_scrape_data(url, html_content, scrape_type, current_manual_prefix, run_number_str)
        regular(f"Manual scrape for {url} completed and data saved (UUID Prefix: {current_manual_prefix}{run_number_str}).")
    else:
        log_error(f"Manual scrape for {url} failed to fetch HTML.")
    
    close_local_db_connection() # Close DB after manual operation

@cli.command()
@click.option('--duration-days', type=int, default=None, help="Optional: Number of days to run the scheduler. Runs indefinitely if not set.")
def run(duration_days: int | None):
    """
    Starts the scheduled scraping process.
    The script will run in the foreground. For background operation, use 'screen' or 'nohup'.
    """
    regular("Preparing to run scheduled scrapes...")
    set_global_log_level(get_config().get("LOG_LEVEL", "REGULAR"))

    if not get_config().get("TARGET_URLS"):
        log_error("No target URLs configured. Cannot start scheduler. Run 'setup' or edit .env file.")
        return

    initialize_databases() # Ensure DBs are ready
    setup_schedules()

    if not schedule.jobs:
        regular("No jobs were scheduled. Check your URL and time configurations.")
        return

    regular("Scheduler is starting. To run in the background, you can use 'screen':")
    regular("  1. Install screen: `sudo apt-get install screen` (or equivalent for your OS)")
    regular("  2. Create a new screen session: `screen -S Webscraper`")
    regular(f"  3. Inside the screen, run this script: `python {os.path.basename(__file__)} run`")
    if duration_days:
        regular(f"     (or `python {os.path.basename(__file__)} run --duration-days {duration_days}`)")
    regular("  4. Detach from screen: Press Ctrl+A then D")
    regular("  5. To reattach later: `screen -r Webscraper`")
    regular("  6. To list screens: `screen -ls`")
    regular("  7. To kill a screen session: `screen -X -S Webscraper quit`")
    
    run_pending_schedules(run_duration_days=duration_days)
    regular("Scheduler process finished.")
    close_local_db_connection() # Ensure DB is closed when scheduler stops

@cli.command()
def init_db():
    """Initializes the databases (creates tables if they don't exist)."""
    regular("Initializing databases...")
    set_global_log_level(get_config().get("LOG_LEVEL", "REGULAR"))
    initialize_databases()
    regular("Database initialization complete.")
    close_local_db_connection()

# --- Feedback Mode Mapping ---
FEEDBACK_MODE_TO_LOG_LEVEL = {
    "regular": "REGULAR",
    "enhanced": "MAINTENANCE", 
    "debug": "DEBUG",
}

@cli.command(name="set-feedback-mode")
@click.argument('mode', type=click.Choice(list(FEEDBACK_MODE_TO_LOG_LEVEL.keys()), case_sensitive=False))
def set_feedback_mode(mode: str):
    """Sets the application's feedback verbosity mode."""
    log_level_to_set = FEEDBACK_MODE_TO_LOG_LEVEL[mode.lower()]
    save_config_value("LOG_LEVEL", log_level_to_set) # Save to .env
    set_global_log_level(log_level_to_set) # Apply immediately
    regular(f"Feedback mode set to '{mode}'. Log level is now '{log_level_to_set}'.")
    if mode == "enhanced":
        maintenance("Enhanced mode logging activated. More detailed logs will be shown.")
        regular("Consider running 'main.py run-diagnostics' to perform system checks.") # Updated message

@cli.command(name="update-scrape-times")
@click.option('--scrape-type', 'config_scrape_type', type=click.Choice(['primary', 'backup'], case_sensitive=False), required=True, help="The type of scrape schedule to update (primary or backup).")
@click.option('--times', 'times_str', required=True, help="Comma-separated list of scrape times in HH:MM format (e.g., '08:00,17:00'). To clear times, provide an empty string ''.")
def update_scrape_times(config_scrape_type: str, times_str: str):
    """Updates the scrape times for primary or backup schedules."""
    
    # If times_str is empty, parse_times will return [], which is valid for clearing times.
    # If times_str is not empty but contains invalid format, parse_times will return [].
    parsed_times = parse_times(times_str)
    
    if times_str and not parsed_times: # Non-empty input string resulted in empty list of times -> invalid format
        log_error(f"Invalid time format: '{times_str}'. Please use HH:MM, comma-separated. No changes made.")
        return

    validated_times_str = ",".join(parsed_times) # Join back, will be empty if parsed_times is []

    config_key = ""
    if config_scrape_type == 'primary':
        config_key = "SCRAPE_TIMES_PRIMARY"
    elif config_scrape_type == 'backup':
        config_key = "SCRAPE_TIMES_BACKUP"
    # No else needed as Click choice validation handles invalid config_scrape_type

    save_config_value(config_key, validated_times_str)
    if validated_times_str:
        regular(f"Successfully updated {config_scrape_type} scrape times to: {validated_times_str}.")
    else:
        regular(f"Successfully cleared {config_scrape_type} scrape times.")
    maintenance("The new schedule will apply the next time the scheduler is started or reconfigured (e.g., via 'run' command).")

@cli.command(name="run-diagnostics")
def cli_run_diagnostics():
    """Runs a series of checks to ensure the scraper and its integrations are working."""
    # Log level for diagnostics will be based on the currently set LOG_LEVEL in config.
    # If users want more detailed diagnostic output, they should first set feedback mode to debug or enhanced.
    maintenance("Starting diagnostic process via CLI command...")
    all_passed = run_all_diagnostics()
    if all_passed:
        regular("CLI: All diagnostics passed.")
    else:
        log_error("CLI: Some diagnostics failed. Please review output above.")
    # No need to restore log level, as it's based on current config.

if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        # This is a top-level catch for unexpected errors in the CLI itself.
        critical(f"An unexpected critical error occurred in the CLI: {e}", error_obj=e)
    finally:
        # Ensure any resources like DB connections are closed if not handled by specific commands
        # This is a fallback. Ideally, each command manages its own resources.
        close_local_db_connection()
        maintenance("CLI execution finished. Final resource cleanup attempted.")
