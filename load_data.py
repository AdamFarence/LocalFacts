import json
import glob
import os
import sqlite3
from config import DB_FILE, DATA_DIR

def load_bulk_data():
    """Loads extracted LegiScan JSON files into SQLite, handling missing fields flexibly."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    us_path = os.path.join(DATA_DIR, "US")
    if not os.path.exists(us_path):
        print(f"❌ No 'US' directory found inside {DATA_DIR}!")
        return

    # Get all session directories inside "US"
    session_dirs = [d for d in os.listdir(us_path) if os.path.isdir(os.path.join(us_path, d))]
    
    if not session_dirs:
        print("❌ No Congressional session directories found in legiscan_data/US!")
        return

    for session in session_dirs:
        session_path = os.path.join(us_path, session)
        print(f"📂 Processing session: {session}")

        # ------------------------------
        # 🏛️ Load Bills
        # ------------------------------
        bill_path = os.path.join(session_path, "bill")
        bill_files = glob.glob(os.path.join(bill_path, "*.json"))
        if not bill_files:
            print(f"⚠ No bill files found in {bill_path}")
        for file in bill_files:
            print(f"   🔹 Loading {file}")
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                bill = data["bill"]

                # Extract last action dynamically
                last_action = None
                last_action_date = bill.get("status_date", None)
                if "history" in bill and isinstance(bill["history"], list) and bill["history"]:
                    last_history_entry = bill["history"][-1]
                    last_action = last_history_entry.get("action", None)
                    last_action_date = last_history_entry.get("date", last_action_date)

                # Insert into bills table
                cursor.execute("""
                    INSERT OR REPLACE INTO bills (bill_id, session_id, state, bill_number, title, description, status, last_action, last_action_date, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bill.get("bill_id"),
                    bill.get("session_id"),
                    bill.get("state"),
                    bill.get("bill_number"),
                    bill.get("title"),
                    bill.get("description"),
                    bill.get("status"),
                    last_action,
                    last_action_date,
                    bill.get("url")
                ))

        # ------------------------------
        # 🗳️ Load Votes (Including Legislator Votes)
        # ------------------------------
        vote_path = os.path.join(session_path, "vote")
        vote_files = glob.glob(os.path.join(vote_path, "*.json"))
        if not vote_files:
            print(f"⚠ No vote files found in {vote_path}")
        for file in vote_files:
            print(f"   🗳 Loading {file}")
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                roll_call = data["roll_call"]

                # Insert roll call summary
                cursor.execute("""
                    INSERT OR REPLACE INTO votes 
                    (roll_call_id, bill_id, date, description, yea, nay, nv, absent, total, passed, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    roll_call["roll_call_id"],
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

                # Insert individual legislator votes
                for vote in roll_call["votes"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO votes
                        (roll_call_id, bill_id, people_id, vote_text)
                        VALUES (?, ?, ?, ?)
                    """, (
                        roll_call["roll_call_id"],
                        roll_call["bill_id"],
                        vote["people_id"],
                        vote["vote_text"]
                    ))

        # ------------------------------
        # 👥 Load People (Legislators)
        # ------------------------------
        people_path = os.path.join(session_path, "people")
        people_files = glob.glob(os.path.join(people_path, "*.json"))
        if not people_files:
            print(f"⚠ No people files found in {people_path}")
        for file in people_files:
            print(f"   👥 Loading {file}")
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                person = data["person"]

                cursor.execute("""
                    INSERT OR REPLACE INTO people (people_id, bioguide_id, name, party, district)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    person.get("people_id"),
                    person.get("bioguide_id", "UNKNOWN"),  # ✅ Ensure this is stored in the database
                    person.get("name"),
                    person.get("party"),
                    person.get("district")
                ))



    conn.commit()
    conn.close()
    print("✅ Bulk data loaded into database")

# Run the function
if __name__ == "__main__":
    load_bulk_data()
