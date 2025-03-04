import sqlite3
from config import DB_FILE

def initialize_database():
    """Creates necessary tables in the SQLite database if they don't exist."""
    conn = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")  # ✅ Enable Write-Ahead Logging
    conn.execute("PRAGMA synchronous = FULL;")  # ✅ Ensure database writes are fully committed
    cursor = conn.cursor()

    # ✅ Enable Foreign Key Constraints for data integrity
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ✅ Create bills table (now with AI-generated summary and topic)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY,
        session_id INTEGER,
        state TEXT,
        bill_number TEXT,
        title TEXT,
        description TEXT,
        summary TEXT DEFAULT NULL,  -- ✅ AI-generated bill summary
        topic TEXT DEFAULT NULL,  -- ✅ AI-classified bill topics (comma-separated)
        status TEXT,
        last_action TEXT,
        last_action_date TEXT DEFAULT NULL,  -- ✅ Store as TEXT but allows DATE conversion
        url TEXT
    );
    """)

    # ✅ Create index for faster topic-based queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_topic ON bills (topic);")

    # ✅ Create votes table (now includes `vote_text`)
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
        FOREIGN KEY (bill_id) REFERENCES bills (bill_id) ON DELETE CASCADE,
        FOREIGN KEY (people_id) REFERENCES people (people_id) ON DELETE CASCADE,
        PRIMARY KEY (roll_call_id, people_id)  -- ✅ Each person votes once per roll call
    );
    """)

    # ✅ Indexes for faster queries on vote tracking
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_bill ON votes (bill_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_votes_people ON votes (people_id);")

    # ✅ Create people table (now with `bioguide_id`)
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
