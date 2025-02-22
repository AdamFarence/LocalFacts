import os
import json
import zipfile

# Constants for data handling
DATA_FOLDER = "data"
ZIP_FOLDER = "zipped_legiscan_data"
COMBINED_VOTE_FILE = "combined_vote.json"
COMBINED_BILL_FILE = "combined_bill.json"
COMBINED_PEOPLE_FILE = "combined_people.json"

def extract_zip_files():
    """Extracts all ZIP files while keeping the folder structure."""
    if not os.path.exists(ZIP_FOLDER):
        print(f"❌ ERROR: The folder '{ZIP_FOLDER}' does not exist!")
        return

    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    zip_files = [f for f in os.listdir(ZIP_FOLDER) if f.endswith(".zip")]
    
    if not zip_files:
        print(f"⚠ WARNING: No ZIP files found in '{ZIP_FOLDER}'")
        return

    for zip_filename in zip_files:
        zip_path = os.path.join(ZIP_FOLDER, zip_filename)
        print(f"📦 Extracting {zip_path}...")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(DATA_FOLDER)
                print(f"✅ Successfully extracted: {zip_filename}")
        except zipfile.BadZipFile:
            print(f"❌ ERROR: Corrupt ZIP file: {zip_filename}")
        except Exception as e:
            print(f"❌ ERROR extracting {zip_filename}: {e}")

def merge_json_files():
    """Scans extracted files and merges bill, people, and vote JSON files separately."""
    all_vote_data = []
    all_bill_data = []
    all_people_data = []

    if not os.path.exists(DATA_FOLDER):
        print(f"❌ ERROR: The folder '{DATA_FOLDER}' does not exist!")
        return

    # Walk through subdirectories to locate JSON files
    for root, dirs, files in os.walk(DATA_FOLDER):
        for filename in files:
            if filename.endswith(".json"):
                file_path = os.path.join(root, filename)

                # Determine the category based on the folder structure
                if "vote" in root:
                    target_list = all_vote_data
                elif "bill" in root:
                    target_list = all_bill_data
                elif "people" in root:
                    target_list = all_people_data
                else:
                    continue  # Skip JSON files outside these categories

                # Load and merge JSON data
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            target_list.extend(data)
                        elif isinstance(data, dict):
                            target_list.append(data)
                        print(f"✅ Processed {file_path}")
                except json.JSONDecodeError:
                    print(f"❌ ERROR: Invalid JSON in {file_path}, skipping.")
                except Exception as e:
                    print(f"❌ ERROR reading {file_path}: {e}")

    # Save combined JSONs
    save_json(COMBINED_VOTE_FILE, all_vote_data)
    save_json(COMBINED_BILL_FILE, all_bill_data)
    save_json(COMBINED_PEOPLE_FILE, all_people_data)

def save_json(filename, data):
    """Helper function to write JSON data to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=2)
        print(f"✅ Saved {len(data)} records to {filename}")
    except Exception as e:
        print(f"❌ ERROR writing to {filename}: {e}")

# Run extraction and merging
extract_zip_files()
merge_json_files()
