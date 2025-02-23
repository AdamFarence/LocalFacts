import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS
import redis
import sqlite3
import subprocess
import requests

# GitHub raw file URLs (Replace YOUR_GITHUB_USERNAME and REPO_NAME)
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/AdamFarence/LocalLens/main"

FILES_TO_DOWNLOAD = [
    "combined_people.json",
    "combined_vote.json",
    "combined_bill.json"
]

def download_json_files():
    """Downloads JSON files from GitHub if they don't exist."""
    for file in FILES_TO_DOWNLOAD:
        if not os.path.exists(file):
            print(f"📥 Downloading {file} from GitHub...")
            url = f"{GITHUB_RAW_BASE_URL}/{file}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                with open(file, "wb") as f:
                    f.write(response.content)
                print(f"✅ {file} downloaded successfully!")
            except requests.exceptions.RequestException as e:
                print(f"❌ ERROR: Failed to download {file}: {e}")

# Ensure JSON files are present
download_json_files()

# Ensure Git LFS files are downloaded
print("📥 Checking Git LFS files...")
try:
    subprocess.run(["git", "lfs", "pull"], check=True)
    print("✅ Git LFS files downloaded successfully!")
except subprocess.CalledProcessError as e:
    print(f"❌ ERROR: Git LFS download failed: {e}")

# Ensure database exists on startup
DB_FILE = "data.db"

if not os.path.exists(DB_FILE):
    print("⚠️  Database not found! Running setup_db.py to generate it...")
    try:
        subprocess.run(["python", "setup_db.py"], check=True)
        print("✅ Database created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: Failed to create database: {e}")

# Check if running locally
if os.getenv("RENDER") is None:
    from dotenv import load_dotenv
    load_dotenv()  # Only load .env locally

app = Flask(__name__)
CORS(app)

# API Keys
GOOGLE_MAPS_GEOCODER_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

# Load LegiScan People, Vote & Bill Data
try:
    with open("combined_people.json", "r", encoding="utf-8") as f:
        PEOPLE_DATA = json.load(f)
    with open("combined_vote.json", "r", encoding="utf-8") as f:
        VOTE_DATA = json.load(f)
    with open("combined_bill.json", "r", encoding="utf-8") as f:
        BILL_DATA = json.load(f)
    print("✅ JSON files loaded successfully!")
except Exception as e:
    print(f"❌ ERROR loading JSON files: {e}")
    PEOPLE_DATA, VOTE_DATA, BILL_DATA = [], [], []

@app.before_request
def log_request():
    """Logs incoming requests for debugging."""
    print(f"🔍 REQUEST: {request.method} {request.path}")

@app.route('/')
def index():
    """Serves the HTML frontend."""
    return render_template('index.html')

@app.route('/api/representatives', methods=['POST'])
def get_representatives():
    """Fetches representatives using Five Calls API & adds voting history from LegiScan."""
    data = request.get_json()
    address = data.get("address")

    if not address:
        print("❌ ERROR: No address provided")
        return jsonify({"error": "Address is required"}), 400

    print(f"📍 Address received: {address}")

    # Step 1: Convert Address to Coordinates
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

    # Step 2: Fetch Representatives from Five Calls API
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

    # Step 3: Attach LegiScan District & Voting Information
    for rep in representatives["representatives"]:
        bioguide_id = rep.get("id")  # Use `id` from Five Calls API (this matches `bioguide_id` in LegiScan)
        legiscan_data = find_legiscan_data(bioguide_id)

        if legiscan_data:
            people_id = legiscan_data.get("people_id", None)
            district = legiscan_data.get("district", "Unknown")
            rep["people_id"] = people_id
            rep["district"] = district

            # Step 4: Find Voting History with Bill Details
            if people_id:
                rep["votes"] = find_voting_history(people_id)
        else:
            rep["people_id"] = None
            rep["district"] = "Unknown"
            rep["votes"] = []

    print("✅ Final API Response:", json.dumps(representatives, indent=2))
    return jsonify(representatives), 200


def find_legiscan_data(bioguide_id):
    """Finds legislator details from SQLite database."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT people_id, name, district, party FROM people WHERE bioguide_id = ?", (bioguide_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"people_id": result[0], "name": result[1], "district": result[2], "party": result[3]}
    
    return None



def find_voting_history(people_id):
    """Finds all votes for a legislator using people_id (SQLite)."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM votes WHERE people_id = ?", (people_id,))
    results = cursor.fetchall()
    conn.close()

    votes = {"yea": [], "nay": []}

    for row in results:
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
            "vote_text": row[10],
            "bill_details": find_bill_details(row[1])
        }
        if row[10] == "Yea":
            votes["yea"].append(vote_data)
        elif row[10] == "Nay":
            votes["nay"].append(vote_data)

    return votes



def find_bill_details(bill_id):
    """Finds bill details for a given bill_id (SQLite)."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "year_start": result[1],
            "year_end": result[2],
            "session_title": result[3],
            "session_name": result[4],
            "url": result[5],
            "state_link": result[6],
            "title": result[7],
            "description": result[8]
        }
    return None



if __name__ == '__main__':
    app.run(debug=True)
