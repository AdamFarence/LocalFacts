import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from transformers import pipeline
from tqdm import tqdm
from config import DB_FILE, TOPIC_CATEGORIES
import json

# ✅ Classification config
BATCH_SIZE = 10
NUM_THREADS = 4
MAX_INPUT_CHARS = 2000

# ✅ Load classification model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def classify_bills(batch_size=BATCH_SIZE, num_threads=NUM_THREADS):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM bills WHERE topic IS NULL AND status IN ('4', '5', '6');
    """)
    total_bills = cursor.fetchone()[0]
    conn.close()

    if total_bills == 0:
        print("✅ No bills to classify.")
        return

    print(f"🔍 Total bills to classify: {total_bills}")

    with tqdm(total=total_bills, desc="Classifying Bills") as pbar:
        while True:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT bill_id, title, description, full_text FROM bills 
                WHERE topic IS NULL AND status IN ('4', '5', '6') 
                LIMIT ?;
            """, (batch_size,))
            bills = cursor.fetchall()
            conn.close()

            if not bills:
                break

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                executor.map(classify_and_update, bills)

            pbar.update(len(bills))
            time.sleep(1)

    print("✅ Classification complete.")

def classify_and_update(bill):
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()

    bill_id, title, description, full_text = bill
    base_text = full_text if full_text and len(full_text.strip()) > 100 else description

    if not base_text or len(base_text.strip()) < 20:
        topic_str = "Miscellaneous"
        score_json = json.dumps({"Miscellaneous": 1.0})
    else:
        input_text = f"Title: {title}\n{base_text[:MAX_INPUT_CHARS]}"

        try:
            result = classifier(input_text, TOPIC_CATEGORIES, multi_label=True)
            topics = [label for label, score in zip(result["labels"], result["scores"]) if score > 0.6]
            if not topics:
                topics = [result["labels"][0]]
            topic_str = ", ".join(topics)
            score_json = json.dumps(dict(zip(result["labels"], result["scores"])))
        except Exception as e:
            print(f"⚠️ Classification error for bill {bill_id}: {e}")
            topic_str = "Miscellaneous"
            score_json = json.dumps({"Miscellaneous": 1.0})

    try:
        cursor.execute("UPDATE bills SET topic = ?, topic_scores = ? WHERE bill_id = ?", (topic_str, score_json, bill_id))
        conn.commit()
    except Exception as e:
        print(f"❌ DB update failed for bill {bill_id}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    classify_bills()
