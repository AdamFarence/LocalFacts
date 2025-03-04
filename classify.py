import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from transformers import pipeline
from config import DB_FILE

# ✅ Load NLP classification model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# ✅ Define possible bill topics
TOPIC_CATEGORIES = [
    "Healthcare", "Education", "Economy", "National Security", "Infrastructure",
    "Criminal Justice", "Social Issues", "Environment", "International Relations",
    "Civil Rights", "Inflation", "Groceries", "Taxes", "Housing", "Transportation",
    "Energy", "Agriculture", "Labor", "Veterans", "Science", "Technology",
    "Digital Rights", "Privacy", "Miscellaneous"
]

def classify_bills(batch_size=10, num_threads=4):
    """Continuously classifies bills with a final vote (status=4, 5, 6) until all are processed."""
    while True:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()

        # ✅ Fetch unclassified bills with final votes
        cursor.execute("""
            SELECT bill_id, title, description FROM bills 
            WHERE topic IS NULL AND status IN ('4', '5', '6') 
            LIMIT ?;
        """, (batch_size,))
        bills = cursor.fetchall()
        conn.close()  # ✅ Close connection after fetching

        if not bills:
            print("✅ All bills have been classified. Exiting...")
            break  # ✅ Stop execution when there are no more unclassified bills.

        print(f"🔍 Found {len(bills)} unclassified bills. Processing...")

        # ✅ Process batches in parallel (Each thread opens its own DB connection)
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            executor.map(classify_and_update, bills)

        time.sleep(2)  # ✅ Small delay before the next batch to avoid overloading CPU

def classify_and_update(bill):
    """Classifies a single bill and updates the database."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()

    bill_id, title, description = bill
    bill_text = f"Title: {title}\nDescription: {description[:1000]}"
    
    try:
        print(f"🔍 Classifying Bill {bill_id} with AI...")
        result = classifier(bill_text, TOPIC_CATEGORIES, multi_label=True)
        topics = [label for label, score in zip(result["labels"], result["scores"]) if score > 0.5]
        topic_str = ", ".join(topics) if topics else "Miscellaneous"

        print(f"📌 Bill {bill_id} classified as: {topic_str}")

        # ✅ Store classification result
        cursor.execute("UPDATE bills SET topic = ? WHERE bill_id = ?", (topic_str, bill_id))
        conn.commit()

    except Exception as e:
        print(f"⚠️ AI Classification Error for Bill {bill_id}: {e}")

    finally:
        conn.close()  # ✅ Close connection after processing

if __name__ == "__main__":
    classify_bills(batch_size=10, num_threads=4)
