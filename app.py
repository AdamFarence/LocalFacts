import os
import json
import requests
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
from config import DB_FILE, TOPIC_CATEGORIES
import logging
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    filename="ai_summarization.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# Load API keys from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not all([GOOGLE_MAPS_API_KEY, FIVE_CALLS_API_KEY, OPENAI_API_KEY, NEWS_API_KEY]):
    raise ValueError("One or more API keys are missing. Please set them in your environment variables.")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow frontend requests

# ----------------------------
# 📍 Step 1: Geocode Address
# ----------------------------
def geocode_address(address):
    """Convert an address into latitude/longitude using Google Maps API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200 or "results" not in data or not data["results"]:
        return None, "Geocoding failed. Invalid address."

    location = data["results"][0]["geometry"]["location"]
    return (location["lat"], location["lng"]), None

# ----------------------------
# 🏛️ Step 2: Find Representatives
# ----------------------------
def get_representatives(lat, lng):
    """Fetch representatives based on latitude/longitude using Five Calls API."""
    url = "https://api.5calls.org/v1/representatives"
    params = {"location": f"{lat},{lng}"}
    headers = {"X-5Calls-Token": FIVE_CALLS_API_KEY}

    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        return None, "Five Calls API error."

    data = response.json()
    if "representatives" not in data or not data["representatives"]:
        return None, "No representatives found."

    return data["representatives"], None

# ----------------------------
# 📝 Step 3: Use AI to Summarize Bills
# ----------------------------
def summarize_and_store_bill(bill_id, vote_text=None, outcome=None, topic=None, legislator=None):
    """Summarize a full bill using chunked summarization if needed."""
    MAX_CHUNKS = 30
    MAX_CHUNKS_FOR_FINAL_SUMMARY = 20
    MAX_FINAL_SUMMARY_LENGTH = 8000  # characters

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT summary, full_text, title, description FROM bills WHERE bill_id = ?", (bill_id,))
    row = cursor.fetchone()
    if not row:
        logging.warning(f"Bill {bill_id} not found in DB.")
        conn.close()
        return "Bill not found."

    summary, full_text, title, description = row

    if summary:
        logging.info(f"📄 Summary for bill {bill_id} reused for legislator: {legislator.get('name') if legislator else 'Unknown'}")
        conn.close()
        return summary

    if not full_text or len(full_text.strip()) < 100:
        logging.warning(f"❌ No usable full text found for bill {bill_id}.")
        conn.close()
        return "No full text available for summarization."

    try:
        # Step 1: Chunk the full text
        chunks = chunk_text(full_text, max_chunk_size=1500)
        logging.info(f"✂️ Bill {bill_id} split into {len(chunks)} chunks.")

        if len(chunks) > MAX_CHUNKS:
            logging.warning(f"⚠️ Truncating bill {bill_id} to {MAX_CHUNKS} chunks.")
            chunks = chunks[:MAX_CHUNKS]

        client = openai.OpenAI(api_key=openai.api_key)
        chunk_summaries = []

        # Step 2: Summarize each chunk
        for i, chunk in enumerate(chunks):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Summarize this section of a legislative bill clearly and concisely."},
                    {"role": "user", "content": chunk}
                ]
            )
            chunk_summary = response.choices[0].message.content.strip()
            chunk_summaries.append(chunk_summary)
            logging.info(f"✅ Bill {bill_id} chunk {i+1}/{len(chunks)} summarized.")

        # Step 3: Prepare combined summary
        limited_summaries = chunk_summaries[:MAX_CHUNKS_FOR_FINAL_SUMMARY]
        combined_summary_text = "\n".join(limited_summaries)
        outcome_text = outcome or "This bill received a final vote."
        vote_line = f"The legislator voted: {vote_text}." if vote_text else ""

        # Step 4: Ensure topic classification
        if not topic or not topic.strip():
            logging.info(f"🏷️ Bill {bill_id} has no topic. Attempting classification...")
            topic = classify_bill_if_needed(
                bill_id=bill_id,
                title=title,
                description=description,
                full_text=full_text,
                existing_topic=topic
            )

        # Step 5: Final AI summary
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": (
                        f"Combine the following section summaries into a single, plain-English summary of the bill. "
                        f"{outcome_text} "
                        f"The bill is categorized under the topic(s): {topic}. "
                        f"Explain the bill's intended purpose and how it could affect these topics. "
                        f"Then, briefly highlight potential benefits, as well as possible downsides or tradeoffs, in a way that's accessible to regular voters. "
                        f"Be concise, informative, and maintain a neutral tone."
                    )},
                    {"role": "user", "content": combined_summary_text[:MAX_FINAL_SUMMARY_LENGTH]}
                ]
            )
            final_summary = response.choices[0].message.content.strip()
            final_summary = " ".join(final_summary.split())  # optional whitespace cleanup
            logging.info(f"🧠 Final AI summary created for bill {bill_id}.")

        except Exception as e:
            logging.error(f"⚠️ Final summary failed for bill {bill_id}: {e}")
            final_summary = combined_summary_text[:MAX_FINAL_SUMMARY_LENGTH] + "\n\n(Note: Full summary truncated due to token limits or errors)"

        # Step 6: Store final summary
        cursor.execute("UPDATE bills SET summary = ? WHERE bill_id = ?", (final_summary, bill_id))
        conn.commit()
        conn.close()

        return final_summary

    except Exception as e:
        logging.error(f"⚠️ AI summarization failed for bill {bill_id}: {e}")
        cursor.execute("UPDATE bills SET summary = ? WHERE bill_id = ?", (
            "Summary unavailable: this bill may be too long or triggered an API error.",
            bill_id
        ))
        conn.commit()
        conn.close()
        return "AI failed to summarize."

    
def chunk_text(text, max_chunk_size=1500):
    """Split long text into manageable chunks."""
    return [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]


# ----------------------------
# 📜 Step 4: Fetch Legislative Activity
# ----------------------------
def get_legislation_for_rep(fivecalls_id, topics=None, match_behavior="any"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT people_id, name, party, district FROM people WHERE bioguide_id = ?", (fivecalls_id,))
    person = cursor.fetchone()
    if not person:
        conn.close()
        return {"bioguide_id": fivecalls_id, "error": "No matching legislator found"}

    people_id, name, party, district = person

    sql_query = """
        SELECT
            bills.bill_id,
            bills.title,
            bills.description,
            bills.status,
            bills.status_date,
            bills.url,
            bills.summary,
            bills.topic,
            bills.full_text,
            legislator_votes.vote_text AS legislator_vote,
            MAX(votes.date) AS most_recent_vote_date,
            MAX(votes.yea) AS total_yea,
            MAX(votes.nay) AS total_nay,
            MAX(votes.passed) AS passed
        FROM legislator_votes
        JOIN votes ON legislator_votes.roll_call_id = votes.roll_call_id
        JOIN bills ON votes.bill_id = bills.bill_id
        WHERE legislator_votes.people_id = ?
          AND bills.status IN (4, 5, 6)
    """

    params = [people_id]

    if topics:
        topics = [t.strip() for t in topics]

        if match_behavior == "all":
            topic_condition = ' AND '.join(["bills.topic LIKE ?"] * len(topics))
        else:
            topic_condition = ' OR '.join(["bills.topic LIKE ?"] * len(topics))

        sql_query += f" AND ({topic_condition})"
        params.extend([f'%{topic}%' for topic in topics])

    sql_query += """
        GROUP BY bills.bill_id
        ORDER BY bills.status_date DESC
        LIMIT 2;
    """

    cursor.execute(sql_query, params)
    results = cursor.fetchall()

    legislation_results = []
    for row in results:
        bill_data = {
            "bill": {
                "bill_id": row[0],
                "title": row[1],
                "description": row[2],
                "status": row[3],
                "status_date": row[4],
                "url": row[5],
                "summary": summarize_and_store_bill(
                    bill_id=row[0],
                    vote_text=row[9],
                    outcome=outcome_from_status(row[3]),
                    topic=row[7],
                    legislator={
                        "name": name,
                        "party": party,
                        "district": district
                    }
                ),
                "topic": row[7],
                "full_text": row[8]
            },
            "vote_text": row[9],
            "most_recent_vote_date": row[10],
            "total_yea": row[11],
            "total_nay": row[12],
            "passed": bool(row[13])
        }
        legislation_results.append(bill_data)

    conn.close()

    return {
        "people_id": people_id,
        "district": district,
        "bills": legislation_results
    }

def outcome_from_status(status):
    if status == 4:
        return "✅ This bill passed."
    elif status == 5:
        return "🛑 This bill was vetoed."
    elif status == 6:
        return "❌ This bill failed."
    else:
        return "This bill received a final vote."

# ----------------------------
# 🛠️ API Route: Find Representatives
# ----------------------------
@app.route('/api/representatives', methods=['POST'])
def representatives():
    data = request.get_json()
    address = data.get("address", "").strip()
    topics = data.get("topics", [])
    match_behavior = data.get("matchBehavior", "any")  # "any" (OR) or "all" (AND)

    if not address and not topics:
        return jsonify({"error": "Provide at least one topic or an address."}), 400

    reps = []
    if address:
        location, error = geocode_address(address)
        if error:
            return jsonify({"error": error}), 400

        reps, error = get_representatives(*location)
        if error:
            return jsonify({"error": error}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    rep_legislation = {}

    if not reps:
        rep_legislation["Bills Matching Selected Topics"] = get_bills_by_topics(cursor, topics, match_behavior)
    else:
        for rep in reps:
            fivecalls_id = rep.get("id", "UNKNOWN")
            cursor.execute("SELECT people_id FROM people WHERE bioguide_id = ?", (fivecalls_id,))
            person = cursor.fetchone()

            if person:
                legislation = get_legislation_for_rep(fivecalls_id, topics if topics else None, match_behavior)
                rep_legislation[rep["name"]] = legislation
            else:
                rep_legislation[rep["name"]] = {"error": "Legislator not found in database"}

    conn.close()

    return jsonify({"representatives": reps, "legislation": rep_legislation})

# Helper function to fetch bills by topic (when no address is provided)
def get_bills_by_topics(cursor, topics, match_behavior):
    if not topics:
        return []

    # Clean whitespace just in case
    topics = [topic.strip() for topic in topics]

    if match_behavior == "all":
        condition = ' AND '.join(["bills.topic LIKE ?"] * len(topics))
    else:
        condition = ' OR '.join(["bills.topic LIKE ?"] * len(topics))

    params = [f'%{topic}%' for topic in topics]

    query = f"""
        SELECT bill_id, title, description, summary, topic, url
        FROM bills WHERE {condition}
        ORDER BY status_date DESC LIMIT 10;
    """

    cursor.execute(query, params)
    results = cursor.fetchall()

    return [{
        "bill": {
            "bill_id": row[0],
            "title": row[1],
            "description": row[2],
            "summary": row[3],
            "topic": row[4],
            "url": row[5]
        }
    } for row in results]


# Load once at module level to avoid reloading on each request
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# ----------------------------
# 🎨 Classify bills, if needed
# ----------------------------

def classify_bill_if_needed(bill_id, title=None, description=None, full_text=None, existing_topic=None):
    """Run AI classification using full_text if available. Save results in DB."""

    if existing_topic and existing_topic.strip():
        return existing_topic

    base_text = full_text if full_text and len(full_text.strip()) > 100 else description
    if not base_text or len(base_text.strip()) < 20:
        topic_str = "Miscellaneous"
        score_json = json.dumps({"Miscellaneous": 1.0})
    else:
        input_text = f"Title: {title}\n{base_text[:2000]}"

        try:
            result = classifier(input_text, TOPIC_CATEGORIES, multi_label=True)
            topics = [label for label, score in zip(result["labels"], result["scores"]) if score > 0.6]
            if not topics:
                topics = [result["labels"][0]]  # fallback to best match

            topic_str = ", ".join(topics)
            score_json = json.dumps(dict(zip(result["labels"], result["scores"])))

        except Exception as e:
            logging.warning(f"⚠️ Failed to classify bill {bill_id}: {e}")
            topic_str = "Miscellaneous"
            score_json = json.dumps({"Miscellaneous": 1.0})

    # ✅ Save topic and scores to DB
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE bills SET topic = ?, topic_scores = ? WHERE bill_id = ?", (topic_str, score_json, bill_id))
        conn.commit()
        conn.close()
        logging.info(f"🏷️ Bill {bill_id} classified as: {topic_str}")
    except Exception as e:
        logging.error(f"❌ DB error while saving topic for bill {bill_id}: {e}")

    return topic_str

# ----------------------------
# Get news articles for a representative
# ----------------------------
def fetch_news_for_representative(name, state=None, district=None):
    """
    Query NewsAPI for the 5 most recent English‐language articles that:
      • contain the exact phrase `name`, and
      • contain one of our office keywords (Rep, Representative, Sen, Senator, etc.),
      • (optionally) mention the state or district as extra context.
    """
    url = "https://newsapi.org/v2/everything"

    # build office filter
    office_terms = ["Rep", "Representative", "Sen", "Senator", "Congressman", "Congresswoman"]
    office_filter = " OR ".join(office_terms)

    # build the boolean query
    # e.g.:  '"John Smith" AND (Rep OR Representative OR Sen OR Senator) AND TX AND "CA-10"'
    parts = [f'"{name}"', f'({office_filter})']
    if state:
        parts.append(state)
    if district:
        parts.append(f'"{district}"')
    query = " AND ".join(parts)

    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "pageSize": 5,
        "sortBy": "publishedAt",
        "language": "en",
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()

    articles = resp.json().get("articles", [])
    return {
        "name": name,
        "district": district,
        "articles": [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a["source"]["name"],
                "publishedAt": a["publishedAt"],
                "description": a.get("description"),
            }
            for a in articles
        ]
    }

@app.route('/api/representative-news', methods=['POST'])
def representative_news():
    """
    Expects JSON:
      { "representatives": [ { "name": "Rep Name", ... }, … ] }
    Returns:
      { "news": [ { "name": "...", "articles": […] }, … ] }
    """
    reps = request.get_json().get("representatives", [])
    names = [r["name"] for r in reps]

    results = []
    # Parallelize up to 5 concurrent NewsAPI calls
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = { pool.submit(fetch_news_for_representative, nm): nm for nm in names }
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({ "name": futures[fut], "error": str(e) })

    return jsonify({ "news": results })

# ----------------------------
# 🎨 Serve Frontend
# ----------------------------
@app.route('/')
def index():
    """Serves the frontend."""
    return render_template('index.html')

# ----------------------------
# 🚀 Start Flask App
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
