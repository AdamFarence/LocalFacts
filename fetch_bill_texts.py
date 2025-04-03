import os
import sqlite3
import requests
import base64
import tempfile
import pdfplumber
import time
from tqdm import tqdm
from config import DB_FILE
import logging

# 🧹 Silence noisy PDF messages
logging.getLogger("pdfminer").setLevel(logging.ERROR)


LEGISCAN_API_KEY = os.getenv("LEGISCAN_API_KEY")
SUCCESS_LOG = "fetched_bills.log"
FAILURE_LOG = "failed_bills.log"

# ----------------------------------------
# Log Handling
# ----------------------------------------
def load_logged_ids(filepath):
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r") as f:
        return set(line.strip() for line in f.readlines())

def log_bill(filepath, bill_id):
    with open(filepath, "a") as f:
        f.write(f"{bill_id}\n")

# ----------------------------------------
# Download + decode + extract PDF text
# ----------------------------------------
def fetch_and_extract_text_from_doc(doc_id):
    url = f"https://api.legiscan.com/?key={LEGISCAN_API_KEY}&op=getBillText&id={doc_id}"

    try:
        response = requests.get(url)
        data = response.json()

        doc = data.get("text", {}).get("doc")
        mime = data.get("text", {}).get("mime")

        if not doc or not mime:
            print("❌ No document or MIME type found.")
            return None

        decoded = base64.b64decode(doc)
        suffix = ".pdf" if "pdf" in mime else ".bin"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(decoded)
            temp_path = tmp.name

        if suffix == ".pdf":
            with pdfplumber.open(temp_path) as pdf:
                return "\n".join([page.extract_text() or "" for page in pdf.pages])
        else:
            print(f"⚠️ Unsupported MIME type: {mime}")
            return None

    except Exception as e:
        print(f"⚠️ Error fetching doc_id {doc_id}: {e}")
        return None

# ----------------------------------------
# Fetch and save to DB
# ----------------------------------------
def fetch_and_store_full_text(bill_id, doc_id):
    text = fetch_and_extract_text_from_doc(doc_id)
    if not text:
        print(f"❌ Skipped bill {bill_id} (no text)")
        log_bill(FAILURE_LOG, bill_id)
        return False

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bills 
        SET full_text = ?
        WHERE bill_id = ?
    """, (text, bill_id))
    conn.commit()
    conn.close()

    log_bill(SUCCESS_LOG, bill_id)
    print(f"✅ Stored text for bill {bill_id}")
    return True

# ----------------------------------------
# Main batch runner
# ----------------------------------------
def batch_fetch_and_store_texts(batch_limit=1000):
    completed = load_logged_ids(SUCCESS_LOG)
    failed = load_logged_ids(FAILURE_LOG)

    while True:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT bill_id, doc_id 
            FROM bills 
            WHERE status IN (4, 5, 6)
              AND doc_id IS NOT NULL 
              AND full_text IS NULL
        """)
        all_bills = cursor.fetchall()
        conn.close()

        bills_to_process = [
            (bid, did) for (bid, did) in all_bills
            if str(bid) not in completed and str(bid) not in failed
        ][:batch_limit]

        if not bills_to_process:
            print("✅ All eligible bills processed. Done!")
            break

        print(f"\n📦 Processing {len(bills_to_process)} more bills...")

        for bill_id, doc_id in tqdm(bills_to_process, desc="📚 Fetching bill texts", unit="bill"):
            try:
                fetch_and_store_full_text(bill_id, doc_id)
                completed.add(str(bill_id))  # Track in memory to avoid rechecking logs
            except Exception as e:
                print(f"❌ Error processing bill {bill_id}: {e}")
                log_bill(FAILURE_LOG, bill_id)
            time.sleep(1)


if __name__ == "__main__":
    batch_fetch_and_store_texts()
