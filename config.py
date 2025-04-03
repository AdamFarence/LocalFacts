import os
from dotenv import load_dotenv

load_dotenv()  # Load API keys from .env file


LEGISCAN_API_KEY = os.getenv("LEGISCAN_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

# File paths
DB_FILE = "legislation.db"
DATA_DIR = "legiscan_data"

TOPIC_CATEGORIES = [
    "Healthcare", "Education", "Economy", "National Security", "Infrastructure",
    "Criminal Justice", "Social Issues", "Environment", "International Relations",
    "Civil Rights", "Inflation", "Immigration", "Groceries", "Taxes", "Housing", "Transportation",
    "Energy", "Agriculture", "Labor", "Veterans", "Science", "Technology",
    "Digital Rights", "Privacy", "Miscellaneous"
]

