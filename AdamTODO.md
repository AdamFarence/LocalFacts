# TO DO:

Clean up the requirements.txt and deploy on render

Figure out a cost-effective, yet accurate way to use AI to summarize the language of the bills.

Figure out how to use the LegiScan API to pull down bill progress, without having to re-download the zip files.

Pull in news feed data -- stories written about the legislators queried.

Pull in location-specific data about quality of life issues.

--------

# Done
April 22nd, 2025

Added in the news API. Might have to swtich to a custom Google Search -- I'm getting some duplicates in the results.


April 2nd, 2025
Added in a run_pipeline.py file to delete and rebuild the entire thing except the AI summarizer. Right now, the file deletes the existing database and logs, and rebuilds the database, then collects full bill text, then classifies them.

Added in a way to tag and classify bills when they're requested. The summary and classifiers now use the full bill text instead of just the description. The AI summary now uses the tags to help craft the summary. The prompt was also set to weight the pros and cons.

April 1st, 2025
Noted that LegiScan bulk download doesn't contain the full text of the bill. So I built in logic to use the API to add the full bill text to the database. I also added in additional functionality so users can:

- Search only by tag
- Search for multiple tags (both separate and together. For example, if user can select the tags "veterans" and "healthcare" to see bills tagged with either one, or with both)
- Search for how their representatives voted combined with the tag functionality above.


March 31st, 2025
Got the AI summaries back up and running. Currently classifying the bills that only passed, failed or vetoed after coming up for a vote. Only bills returned by the query are summarized. They are stored back into the database so we don't have to keep using the OpenAI API.

Fixed the UI so it successfully retrives legislation information along with legislator information. Right now, it just prints the JSON file without any formatting to the page. We'll make it look pretty later... 

March 20th, 2025
Figured out what the issue was with the blank `bioguide_id` column in the `people` table. Might be easiest to drop it or set it equal to the `people_id`. Looks like `bioguide_id` was a relatively new data addition. Earlier iterations of the data simply didn't have the field, so it default to `None`. Since the database initilization script didn't upsert the data, it didn't appear. This has been fixed now.

Set up the front end so that when the Five Calls API is triggered, the response from their API (their `bioguide_id`) variable, is referenced against the `people_id` column in the `people` table.

Try to get the most recent bill information for all the Congressional legislators displayed on the front end. Also include their contact information.


-------------------------------------
March 19th, 2025
- Fixed database structure. Queries are working again. Voting records for legislators keeps succeeds, along with vote totals and bill status. Updated schema is in `initialize_database.py` I need to sit down and map out the data structures for Five Calls, then map out each structure for all of Legiscan's data, and clearly define the relationship between them all.

- After that, I need to restrucutre both the `initilize_database.py` and `load_data.py` files to make them easier to read and simplier to diganose.