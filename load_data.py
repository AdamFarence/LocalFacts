import json
import glob
import os
import sqlite3
import time
from config import DB_FILE, DATA_DIR

def load_bulk_data():
    """Loads extracted LegiScan JSON files into the SQLite database without classification, skipping already uploaded bills."""
    start_time = time.time()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()

    us_path = os.path.join(DATA_DIR, "US")
    if not os.path.exists(us_path):
        print(f"❌ No 'US' directory found inside {DATA_DIR}!")
        return

    session_dirs = [d for d in os.listdir(us_path) if os.path.isdir(os.path.join(us_path, d))]

    if not session_dirs:
        print("❌ No Congressional session directories found in legiscan_data/US!")
        return

    for session in session_dirs:
        session_path = os.path.join(us_path, session)
        print(f"📂 Processing session: {session}")

        # ------------------------------
        # 🏛️ Load and Insert Bills (Skipping Existing Bills)
        # ------------------------------
        bill_path = os.path.join(session_path, "bill")
        bill_files = glob.glob(os.path.join(bill_path, "*.json"))

        if not bill_files:
            print(f"⚠ No bill files found in {bill_path}")

        batch = []

        for file in bill_files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                bill = data["bill"]

                bill_id = bill.get("bill_id")

                # ✅ Check if bill already exists in the database
                cursor.execute("SELECT 1 FROM bills WHERE bill_id = ? LIMIT 1;", (bill_id,))
                exists = cursor.fetchone()
                if exists:
                    print(f"🔹 Skipping already uploaded Bill {bill_id}")
                    continue  # ✅ Skip this bill, it's already in the database

                session_id = bill.get("session_id")
                state = bill.get("state")
                bill_number = bill.get("bill_number")
                title = bill.get("title", "")
                description = bill.get("description", "")
                status = bill.get("status")
                last_action = bill.get("last_action")
                last_action_date = bill.get("last_action_date")
                url = bill.get("url")

                # ✅ Add bill to batch for database insertion
                batch.append((bill_id, session_id, state, bill_number, title, description, status, last_action, last_action_date, url))

                if len(batch) >= 50:  # ✅ Insert in bulk for better performance
                    cursor.executemany("""
                        INSERT INTO bills 
                        (bill_id, session_id, state, bill_number, title, description, status, last_action, last_action_date, url) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    batch = []

        if batch:  # ✅ Insert remaining bills
            cursor.executemany("""
                INSERT INTO bills 
                (bill_id, session_id, state, bill_number, title, description, status, last_action, last_action_date, url) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()

        # ------------------------------
        # 🗳️ Load Votes (Skipping Existing Votes)
        # ------------------------------
        vote_path = os.path.join(session_path, "vote")
        vote_files = glob.glob(os.path.join(vote_path, "*.json"))

        if not vote_files:
            print(f"⚠ No vote files found in {vote_path}")

        for file in vote_files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                roll_call = data["roll_call"]

                roll_call_id = roll_call["roll_call_id"]

                # ✅ Check if vote already exists in the database
                cursor.execute("SELECT 1 FROM votes WHERE roll_call_id = ? LIMIT 1;", (roll_call_id,))
                exists = cursor.fetchone()
                if exists:
                    print(f"🔹 Skipping already uploaded Vote {roll_call_id}")
                    continue  # ✅ Skip this vote, it's already in the database

                cursor.execute("""
                    INSERT INTO votes 
                    (roll_call_id, bill_id, date, description, yea, nay, nv, absent, total, passed, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    roll_call_id,
                    roll_call["bill_id"],
                    roll_call["date"],
                    roll_call["desc"],
                    roll_call["yea"],
                    roll_call["nay"],
                    roll_call["nv"],
                    roll_call["absent"],
                    roll_call["total"],
                    roll_call["passed"],
                    roll_call.get("url", "No URL")
                ))
                conn.commit()

        # ------------------------------
        # 👥 Load Legislators (Fixing UNIQUE Constraint Issue)
        # ------------------------------
        people_path = os.path.join(session_path, "people")
        people_files = glob.glob(os.path.join(people_path, "*.json"))

        if not people_files:
            print(f"⚠ No people files found in {people_path}")

        for file in people_files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                person = data["person"]

                people_id = person.get("people_id")
                bioguide_id = person.get("bioguide_id", "UNKNOWN")
                name = person.get("name")
                party = person.get("party")
                district = person.get("district")

                # ✅ Check if legislator already exists by `bioguide_id`
                cursor.execute("SELECT people_id FROM people WHERE bioguide_id = ? LIMIT 1;", (bioguide_id,))
                exists = cursor.fetchone()

                if exists:
                    print(f"🔹 Skipping already uploaded Legislator {people_id} (Bioguide ID: {bioguide_id})")
                    continue  # ✅ Skip this legislator

                # ✅ Insert or replace to ensure uniqueness
                cursor.execute("""
                    INSERT OR REPLACE INTO people 
                    (people_id, bioguide_id, name, party, district)
                    VALUES (?, ?, ?, ?, ?)
                """, (people_id, bioguide_id, name, party, district))
                conn.commit()

    conn.close()
    end_time = time.time()
    print(f"✅ Bulk data loaded into database in {round(end_time - start_time, 2)} seconds.")

# ✅ Run the function
if __name__ == "__main__":
    load_bulk_data()
