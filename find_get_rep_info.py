import os
import json
import requests
import sqlite3
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)

# Allow frontend requests from any domain (change for security in production)
CORS(app, resources={r"/*": {"origins": os.getenv("FRONTEND_URL", "*")}})

# -----------------------------------------------
# 📌 Configuration
# -----------------------------------------------
GITHUB_RELEASE_URL = "https://github.com/AdamFarence/LocalLens/releases/download/v1.0"

FILES_TO_DOWNLOAD = ["combined_people.json", "combined_vote.json", "combined_bill.json"]
DB_FILE = "data.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# Load environment variables (only for local development)
if os.getenv("RENDER") is None:
    load_dotenv()

# API Keys
GOOGLE_MAPS_GEOCODER_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")

# -----------------------------------------------
# 📥 Ensure Required Files Exist
# -----------------------------------------------
def download_file(filename):
    """Downloads a file from GitHub Releases if it's missing."""
    if not os.path.exists(filename):
        print(f"📥 Downloading {filename}...")
        url = f"{GITHUB_RELEASE_URL}/{filename}"
        try:
            response = requests.get(url, headers=HEADERS, stream=True)
            response.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ {filename} downloaded successfully!")
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: Failed to download {filename}: {e}")

if os.getenv("RENDER") is None:
    for file in FILES_TO_DOWNLOAD + [DB_FILE]:
        download_file(file)

# -----------------------------------------------
# 🌎 Flask Routes
# -----------------------------------------------
@app.before_request
def log_request():
    """Logs all incoming requests for debugging."""
    print(f"🔍 REQUEST: {request.method} {request.path}")

@app.route('/')
def index():
    """Serves the HTML frontend."""
    return render_template('index.html')

@app.route('/api/representatives', methods=['POST'])
def get_representatives():
    """Fetches representatives using Five Calls API & adds voting history."""
    data = request.get_json()
    address = data.get("address")

    if not address:
        return jsonify({"error": "Address is required"}), 400

    # Step 1: Convert Address to Coordinates (Geolocation)
    google_url = "https://maps.googleapis.com/maps/api/geocode/json"
    google_params = {"address": address, "key": GOOGLE_MAPS_GEOCODER_API_KEY}

    try:
        geo_response = requests.get(google_url, params=google_params, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if geo_data.get("status") != "OK" or not geo_data.get("results"):
            return jsonify({"error": "Invalid address"}), 400

        location = geo_data["results"][0]["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Google Maps API error"}), 500

    # Step 2: Fetch Representatives from Five Calls API
    five_calls_url = "https://api.5calls.org/v1/representatives"
    five_calls_params = {"location": f"{lat},{lng}"}
    headers = {"X-5Calls-Token": FIVE_CALLS_API_KEY}

    try:
        five_calls_response = requests.get(five_calls_url, params=five_calls_params, headers=headers, timeout=5)
        five_calls_response.raise_for_status()
        representatives = five_calls_response.json()

        if "representatives" not in representatives or not representatives["representatives"]:
            return jsonify({"error": "No representatives found"}), 404

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Five Calls API error"}), 500

    return jsonify(representatives), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
