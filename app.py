import os
import json
import requests
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from config import DB_FILE

# Load API keys from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

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
# 📜 Step 3: Fetch Legislative Activity
# ----------------------------
def get_legislation_for_rep(fivecalls_id):
    """Fetch the 5 most recent passed, failed, or vetoed legislations with legislator votes."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # 🚨 Step 1: Convert FiveCalls `id` to LegiScan `people_id`
        cursor.execute("""
            SELECT people_id, name, party, district 
            FROM people 
            WHERE bioguide_id = ?;
        """, (fivecalls_id,))
        
        person = cursor.fetchone()
        if not person:
            print(f"⚠️ No matching people_id found for FiveCalls id: {fivecalls_id}")
            return {"bioguide_id": fivecalls_id, "error": "No matching legislator found"}

        people_id, name, party, district = person

        # 🚨 Step 2: Fetch unique 5 most recent legislations (failed, passed, vetoed)
        cursor.execute("""
            SELECT 
                v.date, v.vote_text, 
                b.bill_id, b.bill_number, b.title, b.description AS bill_description, b.status, b.url
            FROM votes v
            JOIN bills b ON v.bill_id = b.bill_id
            WHERE v.people_id = ?
            AND b.status IN (4, 5, 6)  -- ✅ Only Passed (4), Vetoed (5), or Failed (6) bills
            GROUP BY b.bill_id  -- ✅ Ensures only 1 entry per bill
            ORDER BY v.date DESC
            LIMIT 5;  -- ✅ Fetch only the 5 most recent
        """, (people_id,))

        results = cursor.fetchall()
        conn.close()

        print(f"🛠️ DEBUG: Query returned {len(results)} unique bills for people_id {people_id}")

        if not results:
            return {"people_id": people_id, "district": district, "bills": []}

        rep_info = {
            "people_id": people_id,
            "name": name,
            "party": party,
            "district": district,
            "bills": []
        }

        for row in results:
            rep_info["bills"].append({
                "date": row[0],
                "vote_text": row[1],  # ✅ How the legislator voted
                "bill": {
                    "bill_id": row[2],
                    "bill_number": row[3],
                    "title": row[4],
                    "description": row[5],
                    "status": row[6],  # ✅ Show Passed, Failed, or Vetoed
                    "url": row[7]
                }
            })

        return rep_info

    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        return {"error": "Database error", "details": str(e)}


# ----------------------------
# 🛠️ API Route: Find Representatives
# ----------------------------
@app.route('/api/representatives', methods=['POST'])
def representatives():
    """Fetch representatives and their legislative activity."""
    try:
        data = request.get_json()
        address = data.get("address")

        if not address:
            return jsonify({"error": "Address is required"}), 400

        # Step 1: Get lat/lon from address
        location, error = geocode_address(address)
        if error:
            print(f"❌ Geocoding Error: {error}")
            return jsonify({"error": error}), 400

        # Step 2: Find reps using lat/lon
        reps, error = get_representatives(*location)
        if error:
            print(f"❌ Five Calls API Error: {error}")
            return jsonify({"error": error}), 400

        # Step 3: Fetch legislative activity for those reps using `id` (from FiveCalls API)
        rep_legislation = {}
        for rep in reps:
            fivecalls_id = rep.get("id")  # ✅ This is now correctly mapped
            if fivecalls_id:
                rep_legislation[rep["name"]] = get_legislation_for_rep(fivecalls_id)

        return jsonify({"representatives": reps, "legislation": rep_legislation})

    except Exception as e:
        print(f"❌ SERVER ERROR: {e}")
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
