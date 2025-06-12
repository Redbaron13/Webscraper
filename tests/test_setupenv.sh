#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.
echo "--- Starting Environment Setup Test ---"

# Run the setup script
echo "--- Running setupenv.sh ---"
sh setupenv.sh
echo "--- setupenv.sh finished ---"

echo "--- Verifying setup ---"

echo "--- Checking system dependencies ---"
if ! command -v chromium-browser > /dev/null; then
  echo "Error: chromium-browser is not installed or not in PATH."
  exit 1
fi
echo "chromium-browser: OK"

if ! command -v sqlite3 > /dev/null; then
  echo "Error: sqlite3 is not installed or not in PATH."
  exit 1
fi
echo "sqlite3: OK"
echo "--- System dependencies check passed ---"

echo "--- Checking .env file ---"
ENV_FILE="/app/.env"
expected_keys=(
  "SUPABASE_URL"
  "SUPABASE_KEY"
  "TARGET_URLS"
  "SCRAPE_TIMES_PRIMARY"
  "SCRAPE_TIMES_BACKUP"
  "LOCAL_DB_PATH"
  "URL_CODES"
  "LAST_MANUAL_PREFIX"
  "LOG_LEVEL"
)

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE."
  exit 1
fi
echo ".env file found: OK"

for key in "${expected_keys[@]}"; do
  if ! grep -q "^\s*$key=" "$ENV_FILE"; then
    echo "Error: Key $key not found in $ENV_FILE."
    exit 1
  fi
done
echo "All expected keys found in .env file: OK"

# Check specific value for LOCAL_DB_PATH
# The path in .env is app/data/webscraper/localdata/webscraperdata.db
expected_db_path="app/data/webscraper/localdata/webscraperdata.db"
actual_db_path=$(grep "^\s*LOCAL_DB_PATH=" "$ENV_FILE" | cut -d '=' -f2 | tr -d '"' | tr -d "'") # Remove single and double quotes

if [ "$actual_db_path" != "$expected_db_path" ]; then
  echo "Error: LOCAL_DB_PATH in $ENV_FILE is \"$actual_db_path\", expected \"$expected_db_path\"."
  exit 1
fi
echo "LOCAL_DB_PATH is correctly set to \"$expected_db_path\": OK"
echo "--- .env file check passed ---"

echo "--- Checking Python dependencies ---"
REQ_FILE="/app/requirements.txt" # Assuming requirements.txt is in /app

if [ ! -f "$REQ_FILE" ]; then
  echo "Error: $REQ_FILE not found."
  # Attempt to find any requirements file if the primary is missing
  REQ_FILE=$(find /app -maxdepth 1 -name "*requirements*.txt" -print -quit)
  if [ -z "$REQ_FILE" ] || [ ! -f "$REQ_FILE" ]; then
    echo "Error: No requirements file found in /app."
    exit 1
  else
    echo "Found requirements file: $REQ_FILE"
  fi
fi

# Read each line, ignoring comments and empty lines
grep -v "^\s*#" "$REQ_FILE" | grep -v "^\s*$" | while IFS= read -r package_line || [ -n "$package_line" ];
do
  # Extract package name (before any version specifiers, comments, or extras like [html_clean])
  package_name=$(echo "$package_line" | sed -e "s/\s*#.*//" -e "s/\s*[=<>!~].*//" -e "s/\[.*\]//")
  if [ -z "$package_name" ]; then
    continue # Skip empty lines after processing
  fi

  echo "Checking for Python package: $package_name"
  if ! python -m pip show "$package_name" > /dev/null 2>&1; then
    echo "Error: Python package $package_name is not installed."
    exit 1
  fi
  echo "$package_name: OK"
done
echo "--- Python dependencies check passed ---"

echo "--- Checking data directory and database file ---"
# Path configured in .env and used by setupenv.sh and init-db
DATA_DIR="/app/app/data/webscraper/localdata"
DB_FILE="$DATA_DIR/webscraperdata.db"

if [ ! -d "$DATA_DIR" ]; then
  echo "Error: Data directory $DATA_DIR not found."
  exit 1
fi
echo "Data directory $DATA_DIR found: OK"

# The setupenv.sh script calls 'python -m modules.main init-db'
# This command should create the database file using LOCAL_DB_PATH from .env
if [ ! -f "$DB_FILE" ]; then
  echo "Error: Database file $DB_FILE not found after init-db."
  exit 1
fi
echo "Database file $DB_FILE found: OK"
echo "--- Data directory and database file check passed ---"

# Verify Chromium browser installation
echo "Checking for Chromium browser..."
if ! command -v chromium-browser &> /dev/null
then
    echo "Chromium browser could not be found"
    exit 1
fi
echo "Chromium browser found."

echo "--- Environment Setup Test Completed Successfully ---"
