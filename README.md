ff# Web Scraper and Archiver for NJ Courts Website

This script is designed to scrape specified pages from the New Jersey courts website (njcourts.gov) and other target URLs. It runs multiple times a day (configurable), storing a full HTML copy of each page. This allows for historical tracking of website content, which is particularly useful as sites update frequently and may not offer a public API for accessing historical data.

The scraped data is saved locally in an SQLite database and can also be mirrored to a Supabase project for cloud storage and accessibility.

## Features

*   Scheduled and manual scraping of multiple URLs.
*   Storage of full HTML content.
*   Dual database support: local SQLite and remote Supabase.
*   **Custom UUID Generation**: Unique identification for scrape events using the format `[Prefix][RunNum][URLCode][Timestamp][Random][SeqCounter]`.
    *   `P`/`B` prefixes for Primary/Backup scheduled scrapes, `T`/`M` (alternating) for Manual scrapes.
    *   Run numbers `01-09` for scheduled, `99` for manual.
    *   Persistent URL-to-Code mapping (`URL_CODES` in `.env`, auto-managed).
    *   Sequential counters per URL Code and Prefix, stored in the database.
*   **Identical HTML Content Detection**: Flags scrapes if the HTML content is identical to a previous scrape for the same URL, helping to avoid redundant processing by downstream tools.
*   **Configurable Feedback/Logging Modes**:
    *   Regular: Standard operational logs.
    *   Enhanced: More detailed operational logs.
    *   Debug: Most verbose logs for troubleshooting.
*   **Command-Line Interface (CLI)** for:
    *   Interactive setup.
    *   Displaying current configuration.
    *   Performing manual scrapes.
    *   Running scheduled scrapes (indefinitely or for a set duration).
    *   Initializing database tables.
    *   Setting feedback/logging modes.
    *   Updating primary/backup scrape times.
    *   Running system diagnostics.

## Setup and Installation

### 1. Prerequisites
*   Python 3.8 or higher.
*   `pip` for installing Python packages.
*   Access to a terminal or command prompt.

### 2. Clone the Repository
```bash
git clone <your-repository-url> # Replace <your-repository-url> with the actual URL
cd <repository-directory-name>
```

### 3. Set up a Python Virtual Environment
It is highly recommended to use a virtual environment:
**On macOS and Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```
Your terminal prompt should now indicate the `(venv)` environment is active.

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the sample environment file and edit it:
```bash
cp .env.sample .env
```
Open the `.env` file in a text editor and fill in your details. See the "Configuration (.env file)" section below for details on each variable.

### 6. Initialize the Application (First-Time Setup)
Run the interactive setup command:
```bash
python main.py setup
```
This will guide you through essential configurations, initialize the local SQLite database (creating tables), and verify Supabase connection if configured.

## Configuration (`.env` file)

The script uses a `.env` file to manage configuration settings:

*   `SUPABASE_URL`= Your Supabase project URL (e.g., `https://yourprojectid.supabase.co`). Leave empty if not using Supabase.
*   `SUPABASE_KEY`= Your Supabase project anon (public) key. Leave empty if not using Supabase.
*   `TARGET_URLS`= A comma-separated list of exact URLs to scrape (e.g., `https://site1.com/page,https://site2.com/another`).
*   `SCRAPE_TIMES_PRIMARY`= Comma-separated list of primary scrape times in HH:MM format (24-hour clock, e.g., `08:00,17:00`).
*   `SCRAPE_TIMES_BACKUP`= Comma-separated list of backup scrape times in HH:MM format (e.g., `22:00,05:00`).
*   `LOCAL_DB_PATH`= Path for the local SQLite database file. Defaults to `data/webscraperdata.db` in the project root if not specified.
*   `LOG_LEVEL`= Sets the application's logging verbosity. While this can be set manually (e.g., `REGULAR`, `MAINTENANCE`, `DEBUG`), it's primarily managed by the `set-feedback-mode` CLI command.
*   `URL_CODES`= Stores URL-to-code mappings as a JSON string (e.g., `URL_CODES='{"https://example.com/pageA":"XA", "https://example.net/data":"XB"}'`). This is largely auto-managed by the application. You can pre-fill it if you have existing codes or want to assign specific ones, but ensure codes are unique two-letter uppercase strings.
*   `LAST_MANUAL_PREFIX`: Stores the last prefix used for a manual scrape ('T' or 'M'). This allows manual scrapes to alternate UUID prefixes. Defaults to 'M', so the first manual scrape will use 'T'. Managed automatically by the `manual-scrape` command.

## Usage (CLI Commands)

All commands are run via `python main.py <command> [options]`.

*   **`setup`**:
    *   Guides you through an interactive setup of essential configurations (Supabase credentials, target URLs, scrape times, log level).
    *   Prompts to initialize database tables.
*   **`show-config`**:
    *   Displays the current application configuration loaded from the `.env` file and defaults.
*   **`manual-scrape <URL_TO_SCRAPE>`**:
    *   Performs a one-time, immediate scrape of the specified `<URL_TO_SCRAPE>`.
    *   The `scrape_type` column in the database for this entry will be 'manual'.
    *   The UUID for this scrape will use an alternating prefix ('T' or 'M', different from the last manual scrape) and the run number '99'.
*   **`run [--duration-days <days>]`**:
    *   Starts the scheduler for automated scraping based on `SCRAPE_TIMES_PRIMARY` and `SCRAPE_TIMES_BACKUP`.
    *   If `--duration-days` is provided, the scheduler will run for approximately that many days and then stop. Otherwise, it runs indefinitely until manually stopped (e.g., Ctrl+C).
*   **`init-db`**:
    *   Initializes the local SQLite database, creating the `scraped_pages` and `sequential_counters` tables if they don't exist.
*   **`set-feedback-mode <regular|enhanced|debug>`**:
    *   Sets the application's feedback and logging verbosity.
        *   `regular`: Standard operational logs (maps to `REGULAR` log level).
        *   `enhanced`: More detailed operational logs for closer monitoring (maps to `MAINTENANCE` log level). Suggests running `run-diagnostics`.
        *   `debug`: Most verbose logs, useful for troubleshooting (maps to `DEBUG` log level).
*   **`update-scrape-times --scrape-type <primary|backup> --times "HH:MM,..."`**:
    *   Updates or clears the scrape times for either primary or backup schedules.
    *   `--scrape-type`: Specify `primary` or `backup`.
    *   `--times`: Provide a comma-separated string of times in HH:MM format (e.g., `"09:00,14:30"`). To clear all times for the specified type, provide an empty string (e.g., `""`).
*   **`run-diagnostics`**:
    *   Runs a series of system health checks:
        *   Supabase connection and basic query (if configured).
        *   Accessibility of the first configured target URL.
        *   Basic scrape test (no JS rendering) of the first configured target URL.
    *   Reports if all checks passed or if any failed, with details in the logs.

## UUID Structure

Scrape events are identified by a custom UUID with the following format:
`[Prefix][RunNum][URLCode][Timestamp][Random][SeqCounter]`

**Example**: `P01XA20230520103000R4ND0M5TR001`

Components:
*   **Prefix (1 char)**:
    *   `P`: Primary scheduled scrape.
    *   `B`: Backup scheduled scrape.
    *   `T`/`M`: Manual scrape (alternates with each manual run).
*   **Run Number (2 chars)**:
    *   `01`-`09`: For `P` and `B` types, indicating the 1st to 9th scheduled time slot for that URL and type on a given day. (Currently supports up to 9 scheduled times per type per URL due to this format).
    *   `99`: For `T` and `M` (manual) types.
*   **URL Code (2 chars)**:
    *   A unique two-letter uppercase code automatically assigned to each distinct URL.
    *   Managed via the `URL_CODES` variable in the `.env` file and persisted in `configmanager`.
*   **Timestamp (14 chars)**:
    *   The UTC datetime of when the scrape was initiated, in `YYYYMMDDHHMMSS` format.
*   **Random Part (8 chars)**:
    *   An 8-character random alphanumeric string (uppercase letters and digits) to ensure overall UUID uniqueness even if all other parts were hypothetically identical (e.g. system clock error).
*   **Sequential Counter (3 chars)**:
    *   A zero-padded sequential number from `001` to `999`.
    *   This counter is unique for each combination of `URLCode` and `Prefix` (P, B, T, M).
    *   Managed by the `sequential_counters` table in the local SQLite database. It resets only if the table is cleared or a specific counter entry is removed.

## Database Schema

The script uses a local SQLite database. Key tables include:

*   **`scraped_pages`**: Stores the actual scrape data.
    *   `id` (INTEGER PRIMARY KEY AUTOINCREMENT): Local DB primary key.
    *   `capture_uuid` (TEXT UNIQUE NOT NULL): The custom UUID for the scrape event.
    *   `url` (TEXT NOT NULL): The URL that was scraped.
    *   `scrape_timestamp` (TEXT NOT NULL): UTC timestamp in ISO 8601 format.
    *   `scrape_type` (TEXT NOT NULL): General type of scrape (e.g., 'primary', 'backup', 'manual'). Note: This is the general category, the specific UUID prefix (P,B,T,M) gives more granular detail.
    *   `html_content` (TEXT NOT NULL): The full HTML content of the page.
    *   `identical_match` (INTEGER DEFAULT 0): Flag (1 or 0) indicating if this content is identical to a previous scrape for the same URL.
    *   `version` (INTEGER DEFAULT 1): Version number for the scrape data structure (for future schema evolutions).
*   **`sequential_counters`**: Manages sequential numbers for UUID generation.
    *   `url_code` (TEXT NOT NULL): The two-letter code for the URL.
    *   `prefix_char` (TEXT NOT NULL): The UUID prefix (P, B, T, or M).
    *   `last_sequence` (INTEGER NOT NULL DEFAULT 0): The last used sequence number for this `url_code` and `prefix_char` combination.
    *   PRIMARY KEY (`url_code`, `prefix_char`).

**Note for Supabase Users**:
If you are using Supabase for remote storage, you need to manually create the `scraped_pages` and `sequential_counters` tables in your Supabase project's SQL editor. The schema should generally correspond to the SQLite structure described above.
*   For `scraped_pages`, ensure columns like `capture_uuid`, `url`, `scrape_timestamp` (use `TIMESTAMPTZ`), `scrape_type`, `html_content`, `identical_match` (can be `INTEGER` or `BOOLEAN`), and `version` are present.
*   For `sequential_counters`, ensure `url_code` (TEXT), `prefix_char` (TEXT), and `last_sequence` (INTEGER) are present, with a composite primary key on (`url_code`, `prefix_char`).

## Development

(This section can be expanded with details about contributing, coding standards, running tests, etc.)

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Background Running (Windows)

To run the web scraper continuously or on a schedule in the background on Windows, here are a couple of recommended methods:

### 1. Using Windows Task Scheduler (Recommended for most users)

Windows Task Scheduler allows you to automate the execution of scripts at specific times or system events (like startup).

**Steps:**

1.  **Prepare your script:**
    *   Ensure your Python environment is set up correctly and you can run the scraper manually (e.g., `python main.py run`).
    *   Make a note of the full path to your Python executable (e.g., `C:\Users\YourUser\venv\Scripts\python.exe` if using a virtual environment, or your system's Python path).
    *   Make a note of the full path to the `main.py` script in your project directory (e.g., `C:\Path\To\YourProject\main.py`).
    *   Decide on the arguments you want to use (e.g., `run` for indefinite scheduling, or `run --duration-days 30` for a limited time).

2.  **Open Task Scheduler:**
    *   Search for "Task Scheduler" in the Windows Start Menu and open it.

3.  **Create a Basic Task (or a regular Task for more options):**
    *   In the right-hand pane, click "Create Basic Task..." (or "Create Task..." for more control).
    *   **Name & Description:** Give your task a recognizable name (e.g., "WebScraperScheduler") and an optional description. Click Next.
    *   **Trigger:** Choose how often you want the task to run.
        *   For continuous running (restarting when the system boots), you might choose "When the computer starts".
        *   For daily runs at specific times, choose "Daily" and set the time.
        *   If the script's internal scheduler is preferred for timing, you might set it to run "When the computer starts" and let the Python script handle the specific scrape times. Click Next.
    *   **Action:** Select "Start a program". Click Next.
    *   **Start a Program:**
        *   **Program/script:** Enter the full path to your Python executable (e.g., `C:\Users\YourUser\venv\Scripts\python.exe`).
        *   **Add arguments (optional):** Enter the full path to your `main.py` script followed by the command. For example: `C:\Path\To\YourProject\main.py run`
        *   **Start in (optional):** Enter the full path to your project directory (the directory containing `main.py`). This ensures the script runs with the correct working directory, which is important for finding `.env` files, local databases, etc. For example: `C:\Path\To\YourProject\`
    *   Click Next.
    *   **Finish:** Review the settings and click "Finish".

4.  **Configure Advanced Settings (Optional but Recommended):**
    *   Find your newly created task in the Task Scheduler Library. Right-click it and select "Properties".
    *   **General Tab:**
        *   Consider selecting "Run whether user is logged on or not". You may need to enter your user credentials for this.
        *   Check "Run with highest privileges" if your script might need it (usually not necessary for this scraper unless writing to restricted locations).
    *   **Conditions Tab:**
        *   You might want to uncheck "Start the task only if the computer is on AC power" if running on a laptop.
    *   **Settings Tab:**
        *   "Allow task to be run on demand" is useful for testing.
        *   "Run task as soon as possible after a scheduled start is missed" can be helpful.
        *   "If the task fails, restart every:" can be configured (e.g., restart every 10 minutes, attempt 3 times). This provides some resilience.
        *   "Stop the task if it runs longer than:" - be cautious with this. If your `run` command is meant to run indefinitely, don't set this too short. You might set it to "1 day" and have the trigger run it daily if you want daily restarts.
    *   Click OK to save changes.

5.  **Testing:**
    *   You can manually run the task from Task Scheduler (right-click -> Run) to test it.
    *   Check your script's log files (as configured in `logger.py`) to ensure it's running and performing scrapes as expected.

### 2. Using NSSM (Non-Sucking Service Manager) (More Robust for "Always-On")

NSSM is a free utility that allows you to run any application as a Windows service. This is ideal if you want the scraper to run continuously in the background and automatically restart if it crashes.

**Steps:**

1.  **Download NSSM:**
    *   Go to the NSSM website (`https://nssm.cc/download`) and download the latest release.
    *   Extract `nssm.exe` (choose 32-bit or 64-bit based on your system) to a directory where you can easily access it (e.g., `C:\NSSM`). Ensure this directory is in your system's PATH or run `nssm.exe` using its full path.

2.  **Install the Service:**
    *   Open Command Prompt or PowerShell **as Administrator**.
    *   Navigate to the directory where you saved `nssm.exe` (if not in PATH).
    *   Run the command: `nssm.exe install WebScraperService` (you can choose any service name).
    *   This will open the NSSM GUI configurator.
    *   **Application Tab:**
        *   **Path:** Full path to your Python executable (e.g., `C:\Users\YourUser\venv\Scripts\python.exe`).
        *   **Startup directory:** Full path to your project directory (containing `main.py`).
        *   **Arguments:** Full path to your `main.py` script followed by the command (e.g., `C:\Path\To\YourProject\main.py run`).
    *   **Details Tab (Optional):**
        *   Set a Display name and Description for your service.
    *   **I/O Tab (Important for Logging):**
        *   If your script's own logging is not sufficient or you want to capture all stdout/stderr from the Python process itself, configure redirection here. For example:
            *   Output (stdout): `C:\Path\To\YourProject\logs\nssm_stdout.log`
            *   Error (stderr): `C:\Path\To\YourProject\logs\nssm_stderr.log`
            *(Ensure the `logs` directory exists.)*
    *   **Restart Tab:**
        *   Configure application restart options (e.g., restart delays, number of retries). NSSM's default restart behavior is usually quite good.
    *   Click "Install service".

3.  **Start the Service:**
    *   You can start the service from the Services management console (`services.msc`) or using NSSM:
        `nssm.exe start WebScraperService`

4.  **Manage the Service:**
    *   Use `nssm.exe stop WebScraperService`, `nssm.exe restart WebScraperService`, `nssm.exe status WebScraperService`.
    *   To edit the service configuration: `nssm.exe edit WebScraperService`
    *   To remove the service: `nssm.exe remove WebScraperService` (confirm in the GUI).

**Choosing a Method:**
*   If you prefer using built-in Windows tools and have straightforward scheduling needs, **Task Scheduler** is a good choice.
*   If you need the script to run robustly as a background service with automatic restarts and more control over service behavior, **NSSM** is highly recommended.

Remember to check the script's own log files (e.g., in `logs/scraper.log` or as configured) for operational details and any errors, regardless of the method chosen.
