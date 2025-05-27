# Web Scraper and Archiver for NJ Courts Website

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
python modules/main.py setup
```
This will guide you through essential configurations, initialize the local SQLite database (creating tables), and verify Supabase connection if configured.

## Configuration (`.env` file)

The script uses a `.env` file to manage configuration settings:

*   `SUPABASE_URL`: Your Supabase project URL (e.g., `https://yourprojectid.supabase.co`). Leave empty if not using Supabase.
*   `SUPABASE_KEY`: Your Supabase project anon (public) key. Leave empty if not using Supabase.
*   `TARGET_URLS`: A comma-separated list of exact URLs to scrape (e.g., `https://site1.com/page,https://site2.com/another`).
*   `SCRAPE_TIMES_PRIMARY`: Comma-separated list of primary scrape times in HH:MM format (24-hour clock, e.g., `08:00,17:00`).
*   `SCRAPE_TIMES_BACKUP`: Comma-separated list of backup scrape times in HH:MM format (e.g., `22:00,05:00`).
*   `LOCAL_DB_PATH`: Path for the local SQLite database file. Defaults to `webscraperdata.db` in the project root if not specified.
*   `LOG_LEVEL`: Sets the application's logging verbosity. While this can be set manually (e.g., `REGULAR`, `MAINTENANCE`, `DEBUG`), it's primarily managed by the `set-feedback-mode` CLI command.
*   `URL_CODES`: Stores URL-to-code mappings as a JSON string (e.g., `URL_CODES='{"https://example.com/pageA":"XA", "https://example.net/data":"XB"}'`). This is largely auto-managed by the application. You can pre-fill it if you have existing codes or want to assign specific ones, but ensure codes are unique two-letter uppercase strings.
*   `LAST_MANUAL_PREFIX`: Stores the last prefix used for a manual scrape ('T' or 'M'). This allows manual scrapes to alternate UUID prefixes. Defaults to 'M', so the first manual scrape will use 'T'. Managed automatically by the `manual-scrape` command.

## Usage (CLI Commands)

All commands are run via `python modules/main.py <command> [options]`.

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

This project is licensed under the MIT License. (If a `LICENSE` file exists, refer to it. Otherwise, choose and add an appropriate license file.)The `README.md` file has been overwritten with the new comprehensive content.

This includes:
1.  **Overview/Introduction**: Purpose re-stated.
2.  **Features**: Updated with all new functionalities including custom UUIDs, identical content detection, new CLI commands, T/M prefix alternation, persistent URL-to-Code mapping, and DB sequential counters.
3.  **Setup and Installation**: Reviewed and confirmed accuracy.
4.  **Configuration (`.env` file)**: Added comprehensive details for all environment variables: `SUPABASE_URL`, `SUPABASE_KEY`, `TARGET_URLS`, `SCRAPE_TIMES_PRIMARY`, `SCRAPE_TIMES_BACKUP`, `LOCAL_DB_PATH`, `LOG_LEVEL` (and its relation to `set-feedback-mode`), `URL_CODES` (JSON string, auto-managed), and `LAST_MANUAL_PREFIX`.
5.  **Usage (CLI Commands)**: Documented all CLI commands: `setup`, `show-config`, `manual-scrape` (with new UUID details), `run`, `init-db`, `set-feedback-mode` (with explanations of modes), `update-scrape-times`, and `run-diagnostics`.
6.  **UUID Structure**: Provided a detailed breakdown of the custom UUID format (`[Prefix][RunNum][URLCode][Timestamp][Random][SeqCounter]`) and each component.
7.  **Database Schema**: Described the `scraped_pages` (including `identical_match`) and `sequential_counters` tables. Added a note for Supabase users regarding manual table creation.
8.  **License**: A placeholder for the MIT License was included.

The README should now accurately reflect the current state and capabilities of the application.
