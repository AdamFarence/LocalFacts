import sqlite3
from config import DB_FILE

def initialize_database():
    """Creates necessary tables in the SQLite database if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create bills table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY,
        session_id INTEGER,
        state TEXT,
        bill_number TEXT,
        title TEXT,
        description TEXT,
        status TEXT,
        last_action TEXT,
        last_action_date TEXT,
        url TEXT
    );
    """)

    # Create votes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        roll_call_id INTEGER,
        bill_id INTEGER,
        people_id INTEGER,  -- ✅ Added people_id
        date TEXT,
        description TEXT,
        vote_text TEXT,  -- ✅ Store "Yea", "Nay", "NV"
        yea INTEGER,
        nay INTEGER,
        nv INTEGER,
        absent INTEGER,
        total INTEGER,
        passed INTEGER,
        url TEXT,
        FOREIGN KEY (bill_id) REFERENCES bills (bill_id),
        FOREIGN KEY (people_id) REFERENCES people (people_id),
        PRIMARY KEY (roll_call_id, people_id)  -- ✅ Each person votes once per roll call
    );
    """)


    # Create people table (now with bioguide_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS people (
        people_id INTEGER PRIMARY KEY,
        bioguide_id TEXT UNIQUE,  -- ✅ Added bioguide_id to match FiveCalls API
        name TEXT,
        party TEXT,
        district TEXT
    );
    """)


    conn.commit()
    conn.close()
    print("✅ Database initialized with necessary tables.")

if __name__ == "__main__":
    initialize_database()
