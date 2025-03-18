# LocalLens
Bringing the locals together — Representatives, Data, People

# TO DO:
- Fix database structure. Getting voting records for legislators keeps failing. I need to sit down and map out the data structures for Five Calls, then map out each structure for all of Legiscan's data, and clearly define the relationship between them all.

- After that, I need to restrucutre both the `initilize_database.py` and `load_data.py` files to make them easier to read and simplier to diganose.

# Table of Contents:
### TKTK

# Files Descriptions

## app.py

Flask API backend that serves information related to representatives, legislation, and legislative activity. It integrates Google Maps, Five Calls, and OpenAI's APIs and uses SQLite for data storage. The primary use case allows users to input an address (and optionally a topic), find their representatives, and retrieve recent legislative activity related to those representatives, summarized using AI.

## classify.py

Classifies legislative bills into various predefined topics using natural language processing (NLP), storing results in a SQLite database. It leverages a zero-shot classification model from Hugging Face (facebook/bart-large-mnli) to automatically identify relevant topics from bill descriptions.

## initialize_database.py

Initializes a SQLite database designed to store and efficiently retrieve legislative data. It defines tables for managing bills, votes, and legislator information, establishes database constraints to ensure data integrity, and optimizes database performance with indexing.

## load_data.py

Loads bulk legislative data from JSON files into a SQLite database. It specifically processes bill details, legislative votes, and legislator information from structured JSON files, skipping any records already existing in the database to avoid redundancy.

## update_data.py

Fetches recent legislative bills from the LegiScan API for a specified state and stores or updates them in a local SQLite database. It's primarily designed to keep a database of bills up-to-date with the latest legislative actions.

## Potential Datasets
Legiscan Bulk Datasets

## Potential APIs
Google Air quality API: https://developers.google.com/maps/documentation/air-quality/overview

Google Pollen API: https://developers.google.com/maps/documentation/pollen?hl=en&_gl=1*1360p25*_ga*MTQxMzg2NDc5NC4xNzQwMTE3Mjky*_ga_NRWSTWS78N*MTc0MDE3NjQ1Ny4xLjEuMTc0MDE3NjQ4My4wLjAuMA..

