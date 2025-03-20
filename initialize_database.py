import sqlite3
import json
import glob
import os
import logging
from config import DATA_DIR, DB_FILE

# Setup logging
logging.basicConfig(level=logging.INFO)

def initialize_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS people (
        people_id INTEGER PRIMARY KEY,
        bioguide_id TEXT,
        name TEXT,
        party TEXT,
        role TEXT,
        district TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY,
        session_title TEXT,
        session_name TEXT,
        state_link TEXT,
        url TEXT,
        status INTEGER,
        status_date TEXT,
        title TEXT,
        description TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS votes (
        roll_call_id INTEGER PRIMARY KEY,
        bill_id INTEGER,
        date TEXT,
        description TEXT,
        yea INTEGER,
        nay INTEGER,
        nv INTEGER,
        absent INTEGER,
        total INTEGER,
        passed INTEGER,
        url TEXT,
        FOREIGN KEY(bill_id) REFERENCES bills(bill_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS legislator_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_call_id INTEGER,
        people_id INTEGER,
        vote_text TEXT,
        FOREIGN KEY(roll_call_id) REFERENCES votes(roll_call_id)
    )''')

    conn.commit()
    conn.close()

def load_json_files():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Recursively search for all JSON files in the nested directories
    session_dirs = glob.glob(os.path.join(DATA_DIR, "**"), recursive=True)
    for session_dir in session_dirs:
        # Load people JSON files
        people_files = glob.glob(os.path.join(session_dir, "people", "*.json"))
        for file in people_files:
            with open(file, "r", encoding="utf-8") as f:
                person = json.load(f)["person"]

                print("DEBUG: ", person["name"],"bioguide_id", person.get("bioguide_id"))
                cursor.execute('''
                    INSERT INTO people (people_id, bioguide_id, name, party, role, district)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(people_id) DO UPDATE SET
                        bioguide_id=excluded.bioguide_id,
                        name=excluded.name,
                        party=excluded.party,
                        role=excluded.role,
                        district=excluded.district
                ''', (
                    person["people_id"],
                    person.get("bioguide_id"),
                    person["name"],
                    person["party"],
                    person["role"],
                    person["district"]
                ))

                # logging.info(f"Inserted person {person['name']}")

        # Bills
        bill_files = glob.glob(os.path.join(session_dir, "bill", "*.json"))
        for file in bill_files:
            with open(file, "r", encoding="utf-8") as f:
                bill_json = json.load(f)["bill"]
                cursor.execute('''
                    INSERT OR IGNORE INTO bills (
                        bill_id, session_title, session_name, state_link, url,
                        status, status_date, title, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    bill_json["bill_id"],
                    bill_json["session"]["session_title"],
                    bill_json["session"]["session_name"],
                    bill_json["state_link"],
                    bill_json["url"],
                    bill_json["status"],
                    bill_json["status_date"],
                    bill_json["title"],
                    bill_json["description"]
                ))
                # logging.info(f"Inserted bill {bill_json['bill_number']}")

        # Votes
        vote_files = glob.glob(os.path.join(session_dir, "vote", "*.json"))
        for file in vote_files:
            with open(file, "r", encoding="utf-8") as f:
                roll_call = json.load(f)["roll_call"]
                cursor.execute('''
                    INSERT OR IGNORE INTO votes (roll_call_id, bill_id, date, description, yea, nay, nv, absent, total, passed, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    roll_call["roll_call_id"],
                    roll_call["bill_id"],
                    roll_call["date"],
                    roll_call["desc"],
                    roll_call["yea"],
                    roll_call["nay"],
                    roll_call.get("nv", 0),
                    roll_call.get("absent", 0),
                    roll_call["total"],
                    roll_call["passed"],
                    roll_call.get("url", "")
                ))

            for voter in roll_call.get("votes", []):
                cursor.execute('''
                    INSERT OR IGNORE INTO legislator_votes (roll_call_id, people_id, vote_text)
                    VALUES (?, ?, ?)''', (
                    roll_call["roll_call_id"],
                    voter["people_id"],
                    voter["vote_text"]
                ))

            # logging.info(f"Inserted roll call {roll_call['roll_call_id']} into database")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_db()
    load_json_files()
