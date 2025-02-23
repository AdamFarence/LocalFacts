import sqlite3
import json
import os

DB_FILE = "data.db"

# Batch size for inserting data (Adjust based on available memory)
BATCH_SIZE = 500

def create_tables(cursor):
    """Creates necessary database tables if they don't already exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            people_id INTEGER PRIMARY KEY,
            name TEXT,
            district TEXT,
            party TEXT,
            bioguide_id TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            people_id INTEGER,
            bill_id INTEGER,
            date TEXT,
            desc TEXT,
            yea INTEGER,
            nay INTEGER,
            nv INTEGER,
            absent INTEGER,
            total INTEGER,
            passed INTEGER,
            vote_text TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            bill_id INTEGER PRIMARY KEY,
            year_start INTEGER,
            year_end INTEGER,
            session_title TEXT,
            session_name TEXT,
            url TEXT,
            state_link TEXT,
            title TEXT,
            description TEXT
        )
    """)


def insert_people_in_batches(cursor, filename):
    """Inserts people data in batches to prevent memory overload."""
    print(f"📥 Processing {filename}...")
    batch = []

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

        for record in data:
            person = record.get("person", {})
            batch.append((
                person.get("people_id"),
                person.get("name"),
                person.get("district"),
                person.get("party"),
                person.get("bioguide_id")
            ))

            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT OR IGNORE INTO people (people_id, name, district, party, bioguide_id)
                    VALUES (?, ?, ?, ?, ?)
                """, batch)
                batch = []  # Clear batch

        if batch:  # Insert remaining records
            cursor.executemany("""
                INSERT OR IGNORE INTO people (people_id, name, district, party, bioguide_id)
                VALUES (?, ?, ?, ?, ?)
            """, batch)

    print("✅ People data inserted successfully!")


def insert_votes_in_batches(cursor, filename):
    """Inserts vote data in batches."""
    print(f"📥 Processing {filename}...")
    batch = []

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

        for roll_call in data:
            roll_call_info = roll_call.get("roll_call", {})
            for vote in roll_call_info.get("votes", []):
                batch.append((
                    vote.get("people_id"),
                    roll_call_info.get("bill_id"),
                    roll_call_info.get("date"),
                    roll_call_info.get("desc"),
                    roll_call_info.get("yea"),
                    roll_call_info.get("nay"),
                    roll_call_info.get("nv"),
                    roll_call_info.get("absent"),
                    roll_call_info.get("total"),
                    roll_call_info.get("passed"),
                    vote.get("vote_text")
                ))

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany("""
                        INSERT INTO votes (people_id, bill_id, date, desc, yea, nay, nv, absent, total, passed, vote_text)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    batch = []

        if batch:  # Insert remaining records
            cursor.executemany("""
                INSERT INTO votes (people_id, bill_id, date, desc, yea, nay, nv, absent, total, passed, vote_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)

    print("✅ Votes data inserted successfully!")


def insert_bills_in_batches(cursor, filename):
    """Inserts bill data in batches."""
    print(f"📥 Processing {filename}...")
    batch = []

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

        for record in data:
            bill = record.get("bill", {})
            batch.append((
                bill.get("bill_id"),
                bill["session"]["year_start"],
                bill["session"]["year_end"],
                bill["session"]["session_title"],
                bill["session"]["session_name"],
                bill.get("url"),
                bill.get("state_link"),
                bill.get("title"),
                bill.get("description")
            ))

            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO bills (bill_id, year_start, year_end, session_title, session_name, url, state_link, title, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                batch = []

        if batch:  # Insert remaining records
            cursor.executemany("""
                INSERT INTO bills (bill_id, year_start, year_end, session_title, session_name, url, state_link, title, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)

    print("✅ Bills data inserted successfully!")


def load_json_to_db():
    """Creates tables and loads data into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("🔧 Creating tables...")
    create_tables(cursor)

    print("📂 Loading data into database...")
    insert_people_in_batches(cursor, "combined_people.json")
    insert_votes_in_batches(cursor, "combined_vote.json")
    insert_bills_in_batches(cursor, "combined_bill.json")

    conn.commit()
    conn.close()
    print("✅ Database setup complete!")


if __name__ == "__main__":
    if os.path.exists(DB_FILE):
        print("⚠️ Database already exists! Deleting and recreating...")
        os.remove(DB_FILE)

    load_json_to_db()
