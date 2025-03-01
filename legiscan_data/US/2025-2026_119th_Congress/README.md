# 🏛️ Legislative Lookup App

This web application allows users to **find their congressional representatives** by entering their address and **view their recent legislative activity**, including **passed, failed, or vetoed bills** and how they voted.

---

## **🚀 Features**
- 🔍 **Find representatives** by entering an address
- 🗳️ **View their votes** on recent bills
- 📜 **Displays passed, failed, or vetoed bills**
- 🏛 **Uses Google Maps API, FiveCalls API, and LegiScan API**
- 🏎️ **Optimized for fast performance**

---

## **📦 Prerequisites**
Before running the app, make sure you have:

- **Python 3.8+** installed ([Download here](https://www.python.org/downloads/))
- **SQLite3** installed ([SQLite installation guide](https://www.sqlite.org/download.html))
- **Node.js** (optional, for future frontend enhancements)
- API keys for:
  - **Google Maps Geocoding API**
  - **FiveCalls API**
  - **LegiScan API (Bulk Data Access)**

---

## **📥 Installation**
### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/YOUR_USERNAME/legislative-lookup.git
cd legislative-lookup


python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


pip install -r requirements.txt

GOOGLE_MAPS_GEOCODER_API_KEY=your-google-api-key
FIVE_CALLS_API_KEY=your-five-calls-api-key

python initialize_database.py

python load_data.py

SELECT COUNT(*) FROM people;
SELECT COUNT(*) FROM bills;
SELECT COUNT(*) FROM votes;
If counts are greater than 0, the database is ready!

python app.py
