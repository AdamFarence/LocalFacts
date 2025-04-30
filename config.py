import os
from dotenv import load_dotenv

load_dotenv()

LEGISCAN_API_KEY  = os.getenv("LEGISCAN_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")
# … any other API keys …

# Base directory of this config.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# If DATA_DIR isn’t set in the environment, default to a local subfolder.
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "legiscan_data")
DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)

# Make sure the folder exists (optional but handy)
os.makedirs(DATA_DIR, exist_ok=True)

# Place your SQLite file inside DATA_DIR by default,
# but still allow a full override with DB_FILE.
DB_FILE = os.getenv(
    "DB_FILE",
    os.path.join(DATA_DIR, "legislation.db")
)

TOPIC_CATEGORIES = [
    "Healthcare", "Education", "Economy", "National Security", "Infrastructure",
    "Criminal Justice", "Social Issues", "Environment", "International Relations",
    "Civil Rights", "Inflation", "Immigration", "Groceries", "Taxes", "Housing", "Transportation",
    "Energy", "Agriculture", "Labor", "Veterans", "Science", "Technology",
    "Digital Rights", "Privacy", "Miscellaneous"
]
