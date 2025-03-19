# TO DO:
Figure out what to do with the blank `bioguide_id` column in the `people` table. Might be easiest to drop it or set it equal to the `people_id`.

Set up the front end so that when the Five Calls API is triggered, the response from their API (their `bioguide_id`) variable, is referenced against the `people_id` column in the `people` table.

Try to get the most recent bill information for all the Congressional legislators displayed on the front end. Also include their contact information.

--------

Get the AI summaries back up and running. Classify the bills that only passed, failed or vetoed after coming up for a vote. Only summarize bills that are returned by the query. Make sure to store them for easy retrieval, and so we don't have to keep using the OpenAI API.

--------

Look for either....

State legislator geographic information

Data to layer in about specific areas.


# Done
March 19th, 2025
- Fixed database structure. Queries are working again. Voting records for legislators keeps succeeds, along with vote totals and bill status. Updated schema is in `initialize_database.py` I need to sit down and map out the data structures for Five Calls, then map out each structure for all of Legiscan's data, and clearly define the relationship between them all.

- After that, I need to restrucutre both the `initilize_database.py` and `load_data.py` files to make them easier to read and simplier to diganose.