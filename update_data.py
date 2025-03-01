import requests
import sqlite3
from config import LEGISCAN_API_KEY, DB_FILE

def update_recent_bills(state="NY"):
    """Fetch recent bills from LegiScan and update the database."""
    url = f"https://api.legiscan.com/?key={LEGISCAN_API_KEY}&op=getMasterList&state={state}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            bills = data["masterlist"]

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            for key, bill in bills.items():
                if key == "session":
                    continue
                
                cursor.execute("""
                    INSERT OR REPLACE INTO bills (bill_id, session_id, state, bill_number, title, description, status, last_action, last_action_date, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bill["bill_id"], bill["session_id"], bill["state"], bill["number"], bill["title"],
                    bill["description"], bill["status"], bill["last_action"], bill["last_action_date"], bill["url"]
                ))

            conn.commit()
            conn.close()
            print("✅ Recent bills updated in database")
