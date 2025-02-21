import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Retrieve your API keys from environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
BALLOTPEDIA_API_KEY = os.environ.get("BALLOTPEDIA_API_KEY")

@app.route('/api/representatives', methods=['POST'])
def get_representatives():
    data = request.get_json()
    address = data.get("address")
    if not address:
        return jsonify({"error": "Address is required"}), 400

    # Step 1: Convert address to coordinates using Google Geocoding API
    google_url = "https://maps.googleapis.com/maps/api/geocode/json"
    google_params = {
        "address": address,
        "key": GOOGLE_API_KEY
    }
    geo_response = requests.get(google_url, params=google_params)
    if geo_response.status_code != 200:
        return jsonify({"error": "Error calling Google Geocoding API"}), 500

    geo_data = geo_response.json()
    if geo_data.get("status") != "OK":
        return jsonify({"error": "Geocoding API error", "details": geo_data}), 400

    location = geo_data["results"][0]["geometry"]["location"]
    lat = location["lat"]
    lng = location["lng"]

    # Step 2: Use the coordinates with Ballotpedia's API
    ballotpedia_url = "https://api.ballotpedia.org/vX/representatives"  # Replace vX with the correct version
    ballotpedia_params = {
        "lat": lat,
        "lon": lng,
        "api_key": BALLOTPEDIA_API_KEY,
        # Add any additional required parameters here
    }
    ballotpedia_response = requests.get(ballotpedia_url, params=ballotpedia_params)
    if ballotpedia_response.status_code != 200:
        return jsonify({"error": "Error calling Ballotpedia API"}), 500

    representatives = ballotpedia_response.json()

    # Combine and return the data
    return jsonify({
        "coordinates": {"lat": lat, "lng": lng},
        "representatives": representatives
    })

if __name__ == '__main__':
    app.run(debug=True)
