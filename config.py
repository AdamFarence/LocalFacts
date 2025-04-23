import os
from dotenv import load_dotenv

load_dotenv()

LEGISCAN_API_KEY = os.getenv("LEGISCAN_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

# Base directory of this config.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# If DATA_DIR isn’t set in the environment, default to a local subfolder.
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "legiscan_data")

# In prod (Render), set DATA_DIR=/data (the mounted Disk); locally it stays as ./legiscan_data
DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)

# Put your SQLite file on DATA_DIR in either case
DB_FILE = os.path.join(DATA_DIR, "legislation.db")

TOPIC_CATEGORIES = [
    "Healthcare", "Education", "Economy", "National Security", "Infrastructure",
    "Criminal Justice", "Social Issues", "Environment", "International Relations",
    "Civil Rights", "Inflation", "Immigration", "Groceries", "Taxes", "Housing", "Transportation",
    "Energy", "Agriculture", "Labor", "Veterans", "Science", "Technology",
    "Digital Rights", "Privacy", "Miscellaneous"
]
