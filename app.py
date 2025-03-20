import os
import json
import requests
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
from config import DB_FILE

# Load API keys from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
def summarize_bill(bill_id, description):
    """Generate an AI summary only if it doesn't exist in the database."""
    if not description or len(description) < 20:
        return "No summary available."

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ✅ Check if a summary already exists
    cursor.execute("SELECT summary FROM bills WHERE bill_id = ?", (bill_id,))
    existing_summary = cursor.fetchone()

    if existing_summary and existing_summary[0]:
        conn.close()
        return existing_summary[0]

    openai.api_key = OPENAI_API_KEY

    max_length = 2000  # Truncate long descriptions to avoid exceeding OpenAI limits
    short_description = description[:max_length]

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the following legislation in simple terms for the general public. Keep it concise."},
                {"role": "user", "content": short_description}
            ]
        )
        summary = response.choices[0].message.content.strip()

        # ✅ Store the AI-generated summary in the database
        cursor.execute("UPDATE bills SET summary = ? WHERE bill_id = ?", (summary, bill_id))
        conn.commit()
        conn.close()

        return summary

    except Exception as e:
        print(f"⚠️ AI Summarization Error: {e}")
        return "Summary not available due to AI rate limits."

# ----------------------------
# 📜 Step 4: Fetch Legislative Activity
# ----------------------------
def get_legislation_for_rep(fivecalls_id, topic=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT people_id, name, party, district FROM people WHERE bioguide_id = ?", (fivecalls_id,))
        person = cursor.fetchone()
        if not person:
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

        if topic:
            sql_query += """
                AND (
                    bills.title LIKE ?
                    OR bills.description LIKE ?
                )
            """
            topic_param = f"%{topic}%"
            params.extend([topic_param, topic_param])

        sql_query += """
            GROUP BY bills.bill_id
            ORDER BY bills.status_date DESC
            LIMIT 5;
        """

        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        conn.close()

        # Return results keyed by legislator name for frontend compatibility
        return {
            name: {
                "people_id": people_id,
                "district": district,
                "bills": [
                    {
                        "bill": {
                            "bill_id": row[0],
                            "bill_number": row[0],  # If no bill_number, repeat bill_id
                            "title": row[1],
                            "description": row[2],
                            "status": row[3],
                            "status_date": row[4],
                            "url": row[5],
                            "summary": "",  # Placeholder if not yet implemented
                            "topic": ""     # Placeholder if not yet implemented
                        },
                        "vote_text": row[6],
                        "most_recent_vote_date": row[7],
                        "total_yea": row[8],
                        "total_nay": row[9],
                        "passed": bool(row[10])
                    }
                    for row in results
                ]
            }
        }

    except Exception as e:
        conn.close()
        return {"error": "Database error", "details": str(e)}



# ----------------------------
# 🛠️ API Route: Find Representatives
# ----------------------------
@app.route('/api/representatives', methods=['POST'])
def representatives():
    """Fetch representatives and their legislative activity based on an address and optional topic."""
    try:
        data = request.get_json()
        address = data.get("address")
        topic = data.get("topic")  # Optional user input

        if not address:
            return jsonify({"error": "Address is required"}), 400

        # Step 1: Geocode address
        location, error = geocode_address(address)
        if error:
            return jsonify({"error": error}), 400

        # Step 2: Find representatives using FiveCalls API
        reps, error = get_representatives(*location)
        if error:
            return jsonify({"error": error}), 400

        # Debug: Print Five Calls IDs and match status clearly
        print("\n📝 Five Calls ID check:")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        rep_legislation = {}
        for rep in reps:
            fivecalls_id = rep.get("id", "UNKNOWN")
            name = rep.get("name", "Unknown")

            # Print the Five Calls ID for debugging
            print(f" - {rep['name']} (Five Calls ID: {fivecalls_id})")

            # Check if legislator is in your database
            cursor.execute("SELECT people_id, name FROM people WHERE bioguide_id = ?", (fivecalls_id,))
            person = cursor.fetchone()

            if person:
                print(f"  ✅ Found {rep['name']} in DB with people_id {person[0]}")
                legislation = get_legislation_for_rep(fivecalls_id, topic)
                rep_legislation[name] = legislation
            else:
                print(f"❌ Legislator {rep['name']} (Five Calls ID: {fivecalls_id}) not found in database.")
                rep_legislation[rep["name"]] = {"error": "Legislator not found in database"}

        conn.close()

        return jsonify({"representatives": reps, "legislation": rep_legislation})

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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
