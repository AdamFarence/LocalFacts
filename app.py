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
    """Generate an AI summary only if it doesn’t exist in the database."""
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
    """Fetch recent legislations, filtering by AI-classified topics."""
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
                v.date, v.vote_text, 
                b.bill_id, b.bill_number, b.title, b.description, b.summary, b.topic, b.status, b.url
            FROM votes v
            JOIN bills b ON v.bill_id = b.bill_id
            WHERE v.people_id = ?
            AND b.status IN (4, 5, 6)
        """

        params = [people_id]

        if topic:
            sql_query += " AND (b.topic LIKE ? OR b.topic LIKE ? OR b.title LIKE ? OR b.description LIKE ?)"
            params.extend([f"%{topic}%", f"%,{topic},%", f"%{topic}%", f"%{topic}%"])

        sql_query += " GROUP BY b.bill_id ORDER BY v.date DESC LIMIT 5;"
        cursor.execute(sql_query, params)

        results = cursor.fetchall()
        conn.close()

        return {
            "people_id": people_id,
            "district": district,
            "bills": [
                {
                    "date": row[0],
                    "vote_text": row[1],
                    "bill": {
                        "bill_id": row[2],
                        "bill_number": row[3],
                        "title": row[4],
                        "description": row[5],
                        "summary": row[6],
                        "topic": row[7],  
                        "status": row[8],
                        "url": row[9]
                    }
                }
                for row in results
            ]
        }

    except Exception as e:
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
        topic = data.get("topic")  # ✅ Get optional topic from user input

        if not address:
            return jsonify({"error": "Address is required"}), 400

        # 🌎 Step 1: Get lat/lon from address
        location, error = geocode_address(address)
        if error:
            return jsonify({"error": error}), 400

        # 🏛️ Step 2: Find representatives using FiveCalls API
        reps, error = get_representatives(*location)
        if error:
            return jsonify({"error": error}), 400

        # 📜 Step 3: Fetch legislative activity with optional topic filter
        rep_legislation = {}
        for rep in reps:
            fivecalls_id = rep.get("id")
            if fivecalls_id:
                rep_legislation[rep["name"]] = get_legislation_for_rep(fivecalls_id, topic)

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
