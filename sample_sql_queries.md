Sample SQL Queries:

SELECT
    bills.bill_id,
    bills.title,
    legislator_votes.vote_text,
    votes.date AS vote_date,
    votes.yea AS total_yea,
    votes.nay AS total_nay,
    votes.passed
FROM legislator_votes
JOIN votes ON legislator_votes.roll_call_id = votes.roll_call_id
JOIN bills ON votes.bill_id = bills.bill_id
JOIN people ON legislator_votes.people_id = people.people_id
WHERE
    people.people_id = 14906
ORDER BY votes.date DESC
LIMIT 5;

--------------------------------

SELECT
    bills.bill_id,s
    bills.title,
    legislator_votes.vote_text
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