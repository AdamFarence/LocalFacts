Sample SQL Queries:

-- This query reveals the most recent vote cast for a bill
-- that went onto become law, was vetoed, or otherwise failed

SELECT
    bills.bill_id,
    bills.title,
    legislator_votes.vote_text AS legislator_vote,
    MAX(votes.date) AS most_recent_vote_date,
    MAX(votes.yea) AS total_yea,
    MAX(votes.nay) AS total_nay,
    MAX(votes.passed) AS passed,
    bills.status,
    bills.status_date
FROM legislator_votes
JOIN votes ON legislator_votes.roll_call_id = votes.roll_call_id
JOIN bills ON votes.bill_id = bills.bill_id
JOIN people ON legislator_votes.people_id = people.people_id
WHERE
    people.people_id = 14906
    AND bills.status IN (4, 5, 6)  -- 4: Passed, 5: Vetoed, 6: Failed
GROUP BY bills.bill_id
ORDER BY bills.status_date DESC
LIMIT 5;


--------------------------------

SELECT
    bills.bill_id,
    bills.title,
    legislator_votes.vote_text,
FROM legislator_votes
JOIN votes ON legislator_votes.roll_call_id = votes.roll_call_id
JOIN bills ON votes.bill_id = bills.bill_id
JOIN people ON legislator_votes.people_id = people.people_id
WHERE
    people.people_id = 14906
LIMIT 5;

--------------------------------

SELECT * FROM people WHERE bioguide_id = 'P000605';

--------------------------------

SELECT * FROM legislator_votes WHERE people_id = 14906 LIMIT 5;

--------------------------------

SELECT * FROM legislator_votes WHERE people_id = 14906 LIMIT 5;

--------------------------------

SELECT * FROM votes WHERE roll_call_id = [roll_call_id];

--------------------------------

SELECT * FROM bills WHERE bill_id = [bill_id];

--------------------------------
Removes AI summaries

UPDATE bills 
SET summary = NULL 
WHERE summary IS NOT NULL;


UPDATE bills
SET summary = NULL,
    topic = NULL
WHERE status IN (4, 5, 6);
