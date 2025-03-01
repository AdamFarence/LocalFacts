import zipfile
import os
from config import DATA_DIR

ZIPPED_DIR = "zipped_legiscan_data"  # Directory where ZIP files are stored

def extract_all_legiscan_zips():
    """Extracts all ZIP files from 'zipped_legiscan_data' into 'DATA_DIR'."""
    
    if not os.path.exists(ZIPPED_DIR):
        print(f"❌ Directory '{ZIPPED_DIR}' not found!")
        return

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    zip_files = [f for f in os.listdir(ZIPPED_DIR) if f.endswith(".zip")]

    if not zip_files:
        print("❌ No ZIP files found in 'zipped_legiscan_data'")
        return

    for zip_file in zip_files:
        zip_path = os.path.join(ZIPPED_DIR, zip_file)
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(DATA_DIR)
            print(f"✅ Extracted '{zip_file}' to {DATA_DIR}")
        except zipfile.BadZipFile:
            print(f"❌ ERROR: '{zip_file}' is not a valid ZIP file.")

    print("🎉 All ZIP files extracted successfully!")

# Run the function
if __name__ == "__main__":
    extract_all_legiscan_zips()
