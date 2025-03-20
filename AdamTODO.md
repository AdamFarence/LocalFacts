# TO DO:


--------

Get the AI summaries back up and running. Classify the bills that only passed, failed or vetoed after coming up for a vote. Only summarize bills that are returned by the query. Make sure to store them for easy retrieval, and so we don't have to keep using the OpenAI API.

--------

Look for either....

State legislator geographic information

Data to layer in about specific areas.

--------

Fix the UI so it successfully retrives legislation information along with legislator information. Right now, it successfully finds the legislators based on the entered address. But it doesn't come up with the legislation. 


# Done
March 20th, 2025
Figured out what the issue was with the blank `bioguide_id` column in the `people` table. Might be easiest to drop it or set it equal to the `people_id`. Looks like `bioguide_id` was a relatively new data addition. Earlier iterations of the data simply didn't have the field, so it default to `None`. Since the database initilization script didn't upsert the data, it didn't appear. This has been fixed now.

Set up the front end so that when the Five Calls API is triggered, the response from their API (their `bioguide_id`) variable, is referenced against the `people_id` column in the `people` table.

Try to get the most recent bill information for all the Congressional legislators displayed on the front end. Also include their contact information.


-------------------------------------
March 19th, 2025
- Fixed database structure. Queries are working again. Voting records for legislators keeps succeeds, along with vote totals and bill status. Updated schema is in `initialize_database.py` I need to sit down and map out the data structures for Five Calls, then map out each structure for all of Legiscan's data, and clearly define the relationship between them all.

- After that, I need to restrucutre both the `initilize_database.py` and `load_data.py` files to make them easier to read and simplier to diganose.