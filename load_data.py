import os
import json
import requests
import sqlite3
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
from config import DB_FILE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Load API keys from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Geocode Address
def geocode_address(address):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}

    logging.info(f"Geocoding address: {address}")
    response = requests.get(url, params=params)
    logging.info(f"Geocoder response status: {response.status_code}")

    data = response.json()

    if response.status_code != 200 or "results" not in data or not data["results"]:
        logging.error(f"Geocoding failed: {data}")
        return None, "Geocoding failed. Invalid address."

    location = data["results"][0]["geometry"]["location"]
    logging.info(f"Geocoded address '{address}' to lat/lng: {location}")

    return (location["lat"], location["lng"]), None

# Fetch Representatives
def get_representatives(lat, lng):
    url = "https://api.5calls.org/v1/representatives"
    params = {"location": f"{lat},{lng}"}
    headers = {"X-5Calls-Token": FIVE_CALLS_API_KEY}

    response = requests.get(url, params=params, headers=headers)
    logging.info(f"Five Calls response status: {response.status_code}")

    if response.status_code != 200:
        logging.error(f"Five Calls API error: {response.text}")
        return None, "Five Calls API error."

    data = response.json()
    if "representatives" not in data:
        logging.error(f"No representatives found: {data}")
        return None, "No representatives found."

    logging.info(f"Five Calls API returned {len(data['representatives'])} representatives")
    return data["representatives"], None

# Fetch Legislative Activity
def get_legislation_for_rep(fivecalls_id, topic=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT people_id, district FROM people WHERE bioguide_id = ?", (fivecalls_id,))
    person = cursor.fetchone()
    if not person:
        logging.warning(f"Legislator with ID {fivecalls_id} not found in database.")
        return {"error": "No matching legislator found"}

    people_id, district = person

    logging.info(f"Fetching legislation for people_id {people_id}")

    sql_query = """
        SELECT v.date, v.vote_text, b.bill_id, b.bill_number, b.title, b.description, b.summary, b.topic, b.status, b.url
        FROM votes v JOIN bills b ON v.bill_id = b.bill_id
        WHERE v.people_id = ? AND b.status IN (4, 5, 6)
        ORDER BY v.date DESC LIMIT 5;
    """

    cursor.execute(sql_query, (person[0],))
    results = cursor.fetchall()

    logging.info(f"Fetched {len(results)} bills for legislator {fivecalls_id}")
    conn.close()

    return {
        "people_id": person[0],
        "district": person[1],
        "bills": [
            {"date": row[0], "vote_text": row[1], "bill": {"bill_id": row[2], "bill_number": row[3], "title": row[4],
              "description": row[5], "summary": row[6], "topic": row[7], "status": row[8], "url": row[9]}
            }
            for row in cursor.fetchall()
        ]
    }

@app.route('/api/representatives', methods=['POST'])
def representatives():
    data = request.get_json()
    address = data.get("address")
    topic = data.get("topic")

    if not address:
        return jsonify({"error": "Address is required"}), 400

    location, error = geocode_address(address)
    if error:
        return jsonify({"error": error}), 400

    reps, error = get_representatives(*location)
    if error:
        return jsonify({"error": error}), 400

    rep_legislation = {}
    for rep in reps:
        fivecalls_id = rep.get("id")
        if fivecalls_id:
            legislation = get_legislation_for_rep(fivecalls_id, topic)
            rep_legislation[rep["name"]] = legislation

    return jsonify({"representatives": reps, "legislation": rep_legislation})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
