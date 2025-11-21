import json
import gkeepapi

# -------------------------------
# Google account credentials
# -------------------------------
EMAIL = "ticketsdata5@gmail.com"
APP_PASSWORD = "Azerty12345!"  # needed if 2FA is ON

# -------------------------------
# Files
# -------------------------------
INPUT_FILE = "extracted_items.json"

# -------------------------------
# Login to Google Keep
# -------------------------------
keep = gkeepapi.Keep()
success = keep.authenticate(EMAIL, APP_PASSWORD)
if not success:
    raise Exception("Login failed. Check credentials or app password.")

# -------------------------------
# Load JSON and filter notes
# -------------------------------
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

notes_only = [item for item in data if item.get("category") == "note"]

# -------------------------------
# Publish notes to Google Keep
# -------------------------------
for item in notes_only:
    title = item.get("text", "")[:50]  # first 50 chars as title
    text = item.get("text", "")
    keep.createNote(title, text)

# Sync with Google Keep
keep.sync()

print(f"✅ {len(notes_only)} notes published to Google Keep!")
