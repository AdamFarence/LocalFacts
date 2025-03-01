import os
from dotenv import load_dotenv

load_dotenv()  # Load API keys from .env file


LEGISCAN_API_KEY = os.getenv("LEGISCAN_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

# File paths
DB_FILE = "legislation.db"
DATA_DIR = "legiscan_data"
