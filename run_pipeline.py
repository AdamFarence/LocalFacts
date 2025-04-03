import os
import subprocess
import time
from dotenv import load_dotenv
import sys

load_dotenv()

DB_PATH = "legislation.db"

scripts = [
    "initialize_database.py",
    "fetch_bill_texts.py",
    "classify.py"
]

# Option 2: Python quick-fix
open("fetched_bills.log", "w").close()
open("failed_bills.log", "w").close()

# 🧹 Safely delete DB if it exists
if os.path.exists(DB_PATH):
    print(f"🧨 Removing {DB_PATH}...")
    os.remove(DB_PATH)
else:
    print(f"ℹ️ No existing {DB_PATH} found.")

# 🚀 Run pipeline
for script in scripts:
    print(f"🚀 Running {script}...")
    start = time.time()
    result = subprocess.run([sys.executable, script])
    end = time.time()

    if result.returncode != 0:
        print(f"❌ {script} failed (code {result.returncode}). Stopping pipeline.")
        break

    print(f"✅ Finished {script} in {end - start:.2f} seconds.\n")
    time.sleep(1)


# if __name__ == "__main__":
#     main()
