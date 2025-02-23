import sqlite3
import json

DB_FILE = "data.db"

def create_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            people_id INTEGER PRIMARY KEY,
            name TEXT,
            district TEXT,
            party TEXT,
            bioguide_id TEXT
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


def insert_people(cursor, data):
    for record in data:
        person = record.get("person", {})
        cursor.execute("""
            INSERT OR IGNORE INTO people (people_id, name, district, party, bioguide_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            person.get("people_id"),
            person.get("name"),
            person.get("district"),
            person.get("party"),
            person.get("bioguide_id")
        ))


def insert_votes(cursor, data):
    for roll_call in data:
        roll_call_info = roll_call.get("roll_call", {})
        for vote in roll_call_info.get("votes", []):
            cursor.execute("""
                INSERT INTO votes (people_id, bill_id, date, desc, yea, nay, nv, absent, total, passed, vote_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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


def insert_bills(cursor, data):
    for record in data:
        bill = record.get("bill", {})
        cursor.execute("""
            INSERT INTO bills (bill_id, year_start, year_end, session_title, session_name, url, state_link, title, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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


def load_json_to_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    create_tables(cursor)

    with open("combined_people.json", "r", encoding="utf-8") as f:
        people_data = json.load(f)
        insert_people(cursor, people_data)

    with open("combined_vote.json", "r", encoding="utf-8") as f:
        vote_data = json.load(f)
        insert_votes(cursor, vote_data)

    with open("combined_bill.json", "r", encoding="utf-8") as f:
        bill_data = json.load(f)
        insert_bills(cursor, bill_data)

    conn.commit()
    conn.close()
    print("✅ Database setup complete!")


if __name__ == "__main__":
    load_json_to_db()

