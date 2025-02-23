import sqlite3

DB_FILE = "data.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM people;")
result = cursor.fetchone()

conn.close()

print(f"✅ Total People Records: {result[0]}")
