# import os
# import json
# import requests
# import sqlite3
# import logging
# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import openai
# from config import DB_FILE

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# # Load API keys from environment variables
# GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_GEOCODER_API_KEY")
# FIVE_CALLS_API_KEY = os.getenv("FIVE_CALLS_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# app = Flask(__name__)
# CORS(app, resources={r"/api/*": {"origins": "*"}})

# def summarize_bill(bill_id, description):
#     print(f"🛠️ summarize_bill called with bill_id={bill_id}")
    
#     if not description or len(description) < 20:
#         print(f"🚫 No description or too short: {description}")
#         return "No summary available."

#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     cursor.execute("SELECT summary FROM bills WHERE bill_id = ?", (bill_id,))
#     existing_summary = cursor.fetchone()

#     if existing_summary and existing_summary[0]:
#         print(f"✅ Existing summary found for bill_id={bill_id}")
#         conn.close()
#         return existing_summary[0]

#     print(f"🤖 Generating AI summary for bill_id={bill_id}")

#     openai.api_key = OPENAI_API_KEY
#     max_length = 2000
#     short_description = description[:max_length]

#     try:
#         client = openai.OpenAI(api_key=OPENAI_API_KEY)
#         response = client.chat.completions.create(
#             model="gpt-4",
#             messages=[
#                 {"role": "system", "content": "Summarize concisely."},
#                 {"role": "user", "content": short_description}
#             ]
#         )
#         summary = response.choices[0].message.content.strip()

#         cursor.execute("UPDATE bills SET summary = ? WHERE bill_id = ?", (summary, bill_id))
#         if cursor.rowcount == 0:
#             cursor.execute("INSERT INTO bills (bill_id, summary) VALUES (?, ?)", (bill_id, summary))

#         conn.commit()
#         conn.close()
#         print(f"🎉 Summary stored successfully for bill_id={bill_id}")
#         return summary

#     except Exception as e:
#         print(f"⚠️ AI summarization error for bill_id={bill_id}: {e}")
#         conn.close()
#         return "Summary not available."


# # Geocode Address
# def geocode_address(address):
#     url = "https://maps.googleapis.com/maps/api/geocode/json"
#     params = {"address": address, "key": GOOGLE_MAPS_API_KEY}

#     logging.info(f"Geocoding address: {address}")
#     response = requests.get(url, params=params)
#     logging.info(f"Geocoder response status: {response.status_code}")

#     data = response.json()

#     if response.status_code != 200 or "results" not in data or not data["results"]:
#         logging.error(f"Geocoding failed: {data}")
#         return None, "Geocoding failed. Invalid address."

#     location = data["results"][0]["geometry"]["location"]
#     logging.info(f"Geocoded address '{address}' to lat/lng: {location}")

#     return (location["lat"], location["lng"]), None

# # Fetch Representatives
# def get_representatives(lat, lng):
#     url = "https://api.5calls.org/v1/representatives"
#     params = {"location": f"{lat},{lng}"}
#     headers = {"X-5Calls-Token": FIVE_CALLS_API_KEY}

#     response = requests.get(url, params=params, headers=headers)
#     logging.info(f"Five Calls response status: {response.status_code}")

#     if response.status_code != 200:
#         logging.error(f"Five Calls API error: {response.text}")
#         return None, "Five Calls API error."

#     data = response.json()
#     if "representatives" not in data:
#         logging.error(f"No representatives found: {data}")
#         return None, "No representatives found."

#     logging.info(f"Five Calls API returned {len(data['representatives'])} representatives")
#     return data["representatives"], None

# # Fetch Legislative Activity
# def get_legislation_for_rep(fivecalls_id, topic=None):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     try:
#         cursor.execute("SELECT people_id, name, party, district FROM people WHERE bioguide_id = ?", (fivecalls_id,))
#         person = cursor.fetchone()
#         if not person:
#             return {"bioguide_id": fivecalls_id, "error": "No matching legislator found"}

#         people_id, name, party, district = person

#         sql_query = """
#             SELECT
#                 bills.bill_id,
#                 bills.title,
#                 bills.description,
#                 bills.status,
#                 bills.status_date,
#                 bills.url,
#                 bills.summary,
#                 legislator_votes.vote_text AS legislator_vote,
#                 MAX(votes.date) AS most_recent_vote_date,
#                 MAX(votes.yea) AS total_yea,
#                 MAX(votes.nay) AS total_nay,
#                 MAX(votes.passed) AS passed
#             FROM legislator_votes
#             JOIN votes ON legislator_votes.roll_call_id = votes.roll_call_id
#             JOIN bills ON votes.bill_id = bills.bill_id
#             WHERE legislator_votes.people_id = ?
#               AND bills.status IN (4, 5, 6)
#         """

#         params = [people_id]

#         if topic:
#             sql_query += """
#                 AND (
#                     bills.title LIKE ?
#                     OR bills.description LIKE ?
#                 )
#             """
#             topic_param = f"%{topic}%"
#             params.extend([topic_param, topic_param])

#         sql_query += """
#             GROUP BY bills.bill_id
#             ORDER BY bills.status_date DESC
#             LIMIT 5;
#         """

#         cursor.execute(sql_query, params)
#         results = cursor.fetchall()

#         legislation_results = []
#         for row in results:
#             bill_id = row[0]
#             description = row[2]
#             existing_summary = row[6]

#             # ✅ Check if summary exists, else summarize using AI
#             if existing_summary and len(existing_summary.strip()) > 0:
#                 summary = existing_summary
#                 print(f"✅ Using existing summary for bill_id {bill_id}")
#             else:
#                 print(f"🔄 Generating new summary for bill_id {bill_id}")
#                 summary = summarize_bill(bill_id, description)

#             bill_data = {
#                 "bill": {
#                     "bill_id": bill_id,
#                     "bill_number": bill_id,  # Adjust if you have a specific bill_number field
#                     "title": row[1],
#                     "description": description,
#                     "status": row[3],
#                     "status_date": row[4],
#                     "url": row[5],
#                     "summary": summary,
#                     "topic": topic or "Not categorized"
#                 },
#                 "vote_text": row[7],
#                 "most_recent_vote_date": row[8],
#                 "total_yea": row[9],
#                 "total_nay": row[10],
#                 "passed": bool(row[11])
#             }
#             legislation_results.append(bill_data)

#         conn.close()

#         # Return results keyed by legislator name for frontend compatibility
#         return {
#             name: {
#                 "people_id": people_id,
#                 "district": district,
#                 "bills": legislation_results
#             }
#         }

#     except Exception as e:
#         conn.close()
#         return {"error": "Database error", "details": str(e)}


# @app.route('/api/representatives', methods=['POST'])
# def representatives():
#     data = request.get_json()
#     address = data.get("address")
#     topic = data.get("topic")

#     if not address:
#         return jsonify({"error": "Address is required"}), 400

#     location, error = geocode_address(address)
#     if error:
#         return jsonify({"error": error}), 400

#     reps, error = get_representatives(*location)
#     if error:
#         return jsonify({"error": error}), 400

#     rep_legislation = {}
#     for rep in reps:
#         fivecalls_id = rep.get("id")
#         if fivecalls_id:
#             legislation = get_legislation_for_rep(fivecalls_id, topic)
#             rep_legislation[rep["name"]] = legislation

#     return jsonify({"representatives": reps, "legislation": rep_legislation})

# @app.route('/')
# def index():
#     return render_template('index.html')

# if __name__ == '__main__':
#     app.run(debug=True)
