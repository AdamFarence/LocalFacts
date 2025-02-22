import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

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
    """Finds matching LegiScan data for a given bioguide_id."""
    for record in PEOPLE_DATA:
        person = record.get("person", {})
        if person.get("bioguide_id") == bioguide_id:
            return person  # Returns full LegiScan person data
    return None


def find_voting_history(people_id):
    """Finds all votes for a given legislator using people_id."""
    votes = {"yea": [], "nay": []}

    for roll_call in VOTE_DATA:
        roll_call_info = roll_call.get("roll_call", {})
        vote_records = roll_call_info.get("votes", [])

        for vote in vote_records:
            if vote.get("people_id") == people_id:
                vote_text = vote.get("vote_text")
                bill_info = find_bill_details(roll_call_info.get("bill_id"))

                vote_data = {
                    "bill_id": roll_call_info.get("bill_id"),
                    "date": roll_call_info.get("date"),
                    "desc": roll_call_info.get("desc"),
                    "yea": roll_call_info.get("yea"),
                    "nay": roll_call_info.get("nay"),
                    "nv": roll_call_info.get("nv"),
                    "absent": roll_call_info.get("absent"),
                    "total": roll_call_info.get("total"),
                    "passed": roll_call_info.get("passed"),
                    "vote_text": vote_text,
                    "bill_details": bill_info
                }

                if vote_text == "Yea":
                    votes["yea"].append(vote_data)
                elif vote_text == "Nay":
                    votes["nay"].append(vote_data)

    return votes


def find_bill_details(bill_id):
    """Finds bill details for a given bill_id."""
    for bill_record in BILL_DATA:
        bill = bill_record.get("bill", {})
        if bill.get("bill_id") == bill_id:
            return {
                "year_start": bill["session"]["year_start"],
                "year_end": bill["session"]["year_end"],
                "session_title": bill["session"]["session_title"],
                "session_name": bill["session"]["session_name"],
                "url": bill["url"],
                "state_link": bill["state_link"],
                "title": bill["title"],
                "description": bill["description"]
            }
    return None


if __name__ == '__main__':
    app.run(debug=True)
