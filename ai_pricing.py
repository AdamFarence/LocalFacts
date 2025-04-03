import sqlite3
import tiktoken
from config import DB_FILE

# Set model and prices
MODEL = "gpt-4"
ENCODING = tiktoken.encoding_for_model(MODEL)

COST_PER_1K_INPUT = 0.03  # USD
COST_PER_1K_OUTPUT = 0.06  # USD

MAX_CHUNK_SIZE = 1500
CHUNK_PROMPT = "Summarize this section of a legislative bill clearly and concisely."
FINAL_PROMPT_TEMPLATE = (
    "Combine the following section summaries into a final, plain-English summary of the bill. "
    "Explain how it affects the topics in a way that's accessible to regular voters."
)

def count_tokens(text):
    return len(ENCODING.encode(text))

def estimate_tokens_and_cost_for_text(text):
    chunks = [text[i:i + MAX_CHUNK_SIZE] for i in range(0, len(text), MAX_CHUNK_SIZE)]

    total_input_tokens = 0
    total_output_tokens = 0

    for chunk in chunks:
        prompt_tokens = count_tokens(CHUNK_PROMPT + chunk)
        total_input_tokens += prompt_tokens
        total_output_tokens += 150  # assume ~150 tokens output per chunk summary

    combined_summary_text = "\n".join(["..." for _ in chunks])  # placeholder text
    final_prompt = FINAL_PROMPT_TEMPLATE + combined_summary_text

    final_input_tokens = count_tokens(final_prompt)
    final_output_tokens = 300  # estimate ~300 tokens for final summary

    total_input_tokens += final_input_tokens
    total_output_tokens += final_output_tokens

    input_cost = (total_input_tokens / 1000) * COST_PER_1K_INPUT
    output_cost = (total_output_tokens / 1000) * COST_PER_1K_OUTPUT
    total_cost = input_cost + output_cost

    return total_input_tokens, total_output_tokens, total_cost

def run_estimate(limit=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bill_id, full_text FROM bills
        WHERE summary IS NULL AND full_text IS NOT NULL AND status IN (4, 5, 6)
        ORDER BY status_date DESC
        LIMIT ?""" if limit else """
        SELECT bill_id, full_text FROM bills
        WHERE summary IS NULL AND full_text IS NOT NULL AND status IN (4, 5, 6)
    """, (limit,) if limit else ())

    rows = cursor.fetchall()
    conn.close()

    grand_total_input = 0
    grand_total_output = 0
    grand_total_cost = 0

    for bill_id, full_text in rows:
        input_tokens, output_tokens, cost = estimate_tokens_and_cost_for_text(full_text)
        grand_total_input += input_tokens
        grand_total_output += output_tokens
        grand_total_cost += cost

    print("📊 Token and Cost Estimate")
    print(f"🧾 Bills analyzed: {len(rows)}")
    print(f"📥 Total input tokens: {grand_total_input:,}")
    print(f"📤 Total output tokens: {grand_total_output:,}")
    print(f"💸 Estimated total cost: ${grand_total_cost:.2f}")

if __name__ == "__main__":
    run_estimate()  # Adjust or remove limit as needed
