set -eux
cd /app # Ensure we are in the /app directory where the project root is
export PIP_BREAK_SYSTEM_PACKAGES=1

# Install Chromium browser (NOTE: This may still time out in an unstable environment)
sudo apt-get update -y
sudo apt-get install -y chromium-browser

# Install SQLite3 system-level utilities and libraries
sudo apt-get install -y sqlite3 

# Create the .env file with correct key=value format and proper quoting
cat <<EOF > /app/.env
SUPABASE_URL="https://ekllcdhbxgdblwtralha.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVrbGxjZGhieGdkYmx3dHJhbGhhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwMjQ5MTMsImV4cCI6MjA2MjYwMDkxM30.H4ukO2ucPPzJDL43igD_tks9pjW03McpzPKRyi1tMRE"
TARGET_URLS="https://www.njcourts.gov/attorneys/opinions/expected,https://www.njcourts.gov/attorneys/opinions/unpublished-appellate,https://www.njcourts.gov/attorneys/opinions/published-appellate,https://www.njcourts.gov/attorneys/opinions/supreme,https://www.njcourts.gov/attorneys/opinions/published-trial,https://www.njcourts.gov/attorneys/opinions/unpublished-trial,https://www.njcourts.gov/courts/supreme/appeals,https://www.njcourts.gov/courts/appellate/argument-schedule,https://www.njcourts.gov/courts/appellate"
SCRAPE_TIMES_PRIMARY="08:00,17:00"
SCRAPE_TIMES_BACKUP="22:00,05:00"
LOCAL_DB_PATH="data/webscraperdata.db" # UPDATED PATH HERE
URL_CODES='{"https://www.njcourts.gov/attorneys/opinions/expected":"EO", "https://www.njcourts.gov/attorneys/opinions/unpublished-appellate":"UA", "https://www.njcourts.gov/attorneys/opinions/published-appellate":"PA", "https://www.njcourts.gov/attorneys/opinions/supreme":"SC", "https://www.njcourts.gov/attorneys/opinions/published-trial":"PT", "https://www.njcourts.gov/attorneys/opinions/unpublished-trial":"UT", "https://www.njcourts.gov/courts/supreme/appeals":"SA", "https://www.njcourts.gov/courts/appellate/argument-schedule":"AS", "https://www.njcourts.gov/courts/appellate":"XA"}'
LAST_MANUAL_PREFIX="M"
LOG_LEVEL="DEBUG" # Set to DEBUG for maximum setup feedback
EOF

# Install Python dependencies
files=$(find . -maxdepth 2 -type f -wholename "*requirements*.txt") && python -m pip install $(echo "$files" | xargs -I {{}} echo -r {{}}) || true

echo "--- Starting post-installation setup and diagnostics ---"

# Create the directory for the local SQLite database
# UPDATED: Create only the 'data' directory at the root
mkdir -p /app/data/

# Initialize databases: Creates SQLite tables and verifies Supabase connection
python -m modules.main init-db

# Set feedback mode to DEBUG for verbose output during diagnostics
python -m modules.main set-feedback-mode debug

# Run comprehensive diagnostics
python -m modules.main run-diagnostics

echo "--- Initial setup and diagnostics complete ---"
