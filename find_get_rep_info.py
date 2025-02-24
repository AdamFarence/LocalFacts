import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS
import sqlite3
import subprocess

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for API routes

# -----------------------------------------------
# 📌 Configuration
# -----------------------------------------------

# GitHub Release URL where large JSON files are hosted
GITHUB_RELEASE_URL = "https://github.com/AdamFarence/LocalLens/releases/download/v1.0"

# List of JSON files required for processing
FILES_TO_DOWNLOAD = [
    "combined_people.json",
    "combined_vote.json",
    "combined_bill.json"
]

# Headers to avoid request blocking due to missing User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# SQLite Database file
DB_FILE = "data.db"

# -----------------------------------------------
# 📥 JSON File Download Function
# -----------------------------------------------

def download_json_files():
    """Downloads missing JSON files from GitHub Releases and saves them locally."""
    for file in FILES_TO_DOWNLOAD:
        if not os.path.exists(file):  # Only download if missing
            print(f"📥 Downloading {file} from GitHub Releases...")
            url = f"{GITHUB_RELEASE_URL}/{file}"
            try:
                response = requests.get(url, headers=HEADERS, allow_redirects=True, stream=True)
                response.raise_for_status()  # Raise an error for HTTP issues

                # Save file in chunks to avoid memory overload
                with open(file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"✅ {file} downloaded successfully!")
            except requests.exceptions.RequestException as e:
                print(f"❌ ERROR: Failed to download {file}: {e}")

# Ensure necessary JSON files are available
# Only download JSON files if running locally
if os.getenv("RENDER") is None:
    download_json_files()
else:
    print("🛑 Skipping JSON download: Using prebuilt database in Render environment")


# -----------------------------------------------
# 🗄️ Database Setup (Ensures SQLite DB exists)
# -----------------------------------------------

if not os.path.exists(DB_FILE):
    print("📥 Downloading data.db from GitHub Releases...")
    url = f"{GITHUB_RELEASE_URL}/data.db"
    try:
        response = requests.get(url, headers=HEADERS, allow_redirects=True, stream=True)
        response.raise_for_status()
        with open(DB_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Database downloaded successfully!")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to download database: {e}")


# -----------------------------------------------
# 🌎 Flask App Setup
# -----------------------------------------------

# Load environment variables **ONLY** if running locally (not in Render)
if os.getenv("RENDER") is None:
    load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow ALL origins globally


# API Keys (Loaded from environment variables)
GOOGLE_MAPS_GEOCODER_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

@app.before_request
def log_request():
    """Logs all incoming requests for debugging."""
    print(f"🔍 REQUEST: {request.method} {request.path}")

@app.route('/')
def index():
    """Serves the HTML frontend."""
    return render_template('index.html')

# -----------------------------------------------
# 🏛️ Representative Lookup Route
# -----------------------------------------------

@app.route('/api/representatives', methods=['POST'])
def get_representatives():
    """Fetches representatives using Five Calls API & adds voting history from LegiScan."""
    
    data = request.get_json()
    address = data.get("address")

    if not address:
        print("❌ ERROR: No address provided")
        return jsonify({"error": "Address is required"}), 400

    print(f"📍 Address received: {address}")

    # 🗺️ Step 1: Convert Address to Coordinates (Geolocation)
    google_url = "https://maps.googleapis.com/maps/api/geocode/json"
    google_params = {"address": address, "key": GOOGLE_MAPS_GEOCODER_API_KEY}

    try:
        geo_response = requests.get(google_url, params=google_params, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if geo_data.get("status") != "OK" or not geo_data.get("results"):
            print("❌ ERROR: Geocoding API failed.")
            return jsonify({"error": "Invalid address"}), 400

        location = geo_data["results"][0]["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]
        print(f"📌 Geolocation: {lat}, {lng}")

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Google API failed: {e}")
        return jsonify({"error": "Google Maps API error"}), 500

    # 🏛️ Step 2: Fetch Representatives from Five Calls API
    five_calls_url = "https://api.5calls.org/v1/representatives"
    five_calls_params = {"location": f"{lat},{lng}"}
    headers = {"X-5Calls-Token": FIVE_CALLS_API_KEY}

    try:
        five_calls_response = requests.get(five_calls_url, params=five_calls_params, headers=headers, timeout=5)
        five_calls_response.raise_for_status()
        representatives = five_calls_response.json()

        print("✅ Five Calls API Response:", json.dumps(representatives, indent=2))

        if "representatives" not in representatives or not representatives["representatives"]:
            return jsonify({"error": "No representatives found"}), 404

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Five Calls API request failed: {e}")
        return jsonify({"error": "Five Calls API error"}), 500

    # 🔎 Step 3: Attach LegiScan Data (District & Voting History)
    for rep in representatives["representatives"]:
        bioguide_id = rep.get("id")  # `id` from Five Calls API matches `bioguide_id` in LegiScan
        legiscan_data = find_legiscan_data(bioguide_id)

        if legiscan_data:
            people_id = legiscan_data.get("people_id", None)
            rep["people_id"] = people_id
            rep["district"] = legiscan_data.get("district", "Unknown")

            # Step 4: Fetch Voting History
            if people_id:
                rep["votes"] = find_voting_history(people_id)
        else:
            rep["people_id"] = None
            rep["district"] = "Unknown"
            rep["votes"] = []

    print("✅ Final API Response:", json.dumps(representatives, indent=2))
    return jsonify(representatives), 200

# -----------------------------------------------
# 📊 Database Query Functions
# -----------------------------------------------

def find_legiscan_data(bioguide_id):
    """Finds legislator details from SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT people_id, name, district, party FROM people WHERE bioguide_id = ?", (bioguide_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"people_id": result[0], "name": result[1], "district": result[2], "party": result[3]}
    
    return None

def find_voting_history(people_id):
    """Finds all votes for a legislator using people_id (SQLite)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM votes WHERE people_id = ?", (people_id,))
    results = cursor.fetchall()
    conn.close()

    votes = {"yea": [], "nay": [], "other": []}  # Add an "other" category for unexpected values

    for row in results:
        vote_text = row[10]  # This is the vote type (e.g., "Yea", "Nay", "Absent", etc.)

        vote_data = {
            "bill_id": row[1],
            "date": row[2],
            "desc": row[3],
            "yea": row[4],
            "nay": row[5],
            "nv": row[6],
            "absent": row[7],
            "total": row[8],
            "passed": row[9],
            "vote_text": vote_text,
            "bill_details": find_bill_details(row[1])
        }

        # Ensure only "Yea" and "Nay" votes are categorized correctly
        if vote_text == "Yea":
            votes["yea"].append(vote_data)
        elif vote_text == "Nay":
            votes["nay"].append(vote_data)
        else:
            # Log and store unexpected vote types
            print(f"⚠️ Unexpected vote type: {vote_text} for people_id {people_id}")
            votes["other"].append(vote_data)

    return votes


def find_bill_details(bill_id):
    """Finds bill details for a given bill_id (SQLite)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    result = cursor.fetchone()
    conn.close()

    return None if not result else {"title": result[7], "description": result[8]}

if __name__ == '__main__':
    # # Determine the environment
    # render_env = os.getenv('RENDER')
    
    # if render_env:
    #     # Running on Render
    #     port = int(os.environ.get('PORT', 10000))  # Render uses port 10000 by default
    #     app.run(host='0.0.0.0', port=port)
    # else:
    #     # Running locally
        app.run(debug=True)


