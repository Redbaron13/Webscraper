set -eux
cd /app # Ensure we are in the /app directory where the project root is
export PIP_BREAK_SYSTEM_PACKAGES=1

# Install Chromium browser (NOTE: This may still time out in an unstable environment, but it seems to have worked this time)
sudo apt-get update -y
sudo apt-get install -y chromium-browser

# Create the .env file with correct key=value format and proper quoting
# Ensure this entire block is present in your script, including the 'EOF' line at the end.
cat <<EOF > /app/.env
SUPABASE_URL="https://ekllcdhbxgdblwtralha.supabase.co"
SUPABASE_KEY="YOUR_SUPABASE_KEY"
TARGET_URLS="https://www.njcourts.gov/attorneys/opinions/expected,https://www.njcourts.gov/attorneys/opinions/unpublished-appellate,https://www.njcourts.gov/attorneys/opinions/published-appellate,https://www.njcourts.gov/attorneys/opinions/supreme,https://www.njcourts.gov/attorneys/opinions/published-trial,https://www.njcourts.gov/attorneys/opinions/unpublished-trial,https://www.njcourts.gov/courts/supreme/appeals,https://www.njcourts.gov/courts/appellate/argument-schedule,https://www.njcourts.gov/courts/appellate"
SCRAPE_TIMES_PRIMARY="08:00,17:00"
SCRAPE_TIMES_BACKUP="22:00,05:00"
LOCAL_DB_PATH="app/data/webscraper/localdata/webscraperdata.db"
URL_CODES='{"https://www.njcourts.gov/attorneys/opinions/expected":"EO", "https://www.njcourts.gov/attorneys/opinions/unpublished-appellate":"UA", "https://www.njcourts.gov/attorneys/opinions/published-appellate":"PA", "https://www.njcourts.gov/attorneys/opinions/supreme":"SC", "https://www.njcourts.gov/attorneys/opinions/published-trial":"PT", "https://www.njcourts.gov/attorneys/opinions/unpublished-trial":"UT", "https://www.njcourts.gov/courts/supreme/appeals":"SA", "https://www.njcourts.gov/courts/appellate/argument-schedule":"AS", "https://www.njcourts.gov/courts/appellate":"XA"}'
LAST_MANUAL_PREFIX="M"
LOG_LEVEL="DEBUG" # Set to DEBUG for maximum setup feedback
EOF

# Install Python dependencies
files=$(find . -maxdepth 2 -type f -wholename "*requirements*.txt") && python -m pip install $(echo "$files" | xargs -I {{}} echo -r {{}}) || true

echo "--- Starting post-installation setup and diagnostics ---"

# Initialize databases: Creates SQLite tables and verifies Supabase connection
# IMPORTANT CHANGE: Use 'python -m modules.main' instead of 'python modules/main.py'
python -m modules.main init-db

# Set feedback mode to DEBUG for verbose output during diagnostics
# IMPORTANT CHANGE: Use 'python -m modules.main'
python -m modules.main set-feedback-mode debug

# Run comprehensive diagnostics
# IMPORTANT CHANGE: Use 'python -m modules.main'
python -m modules.main run-diagnostics

echo "--- Initial setup and diagnostics complete ---"
