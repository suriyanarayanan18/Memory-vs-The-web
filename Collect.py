# collection script: runs each query several times and saves the raw AI responses
# raw responses go to a jsonl file, one json object per line, so a crash never loses earlier work

import json
import csv
import time
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()

# config in one place so it is easy to change later
MODEL = "claude-sonnet-4-6"
RUNS_PER_QUERY = 1
MAX_TOKENS = 600
INPUT_CSV = "queries.csv"
OUTPUT_FILE = "responses.jsonl"

# read the queries from the csv into a list of dicts
queries = []
with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        queries.append(row)

total_planned = len(queries) * RUNS_PER_QUERY
print(f"loaded {len(queries)} queries, running each {RUNS_PER_QUERY} times")
print(f"that is {total_planned} total calls")

# open in append mode so re running the script adds to the file instead of wiping it
calls_done = 0
with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
    for q in queries:
        qid = q["query_id"]
        query_text = q["query_text"]
        intent = q["intent_type"]
        for run in range(1, RUNS_PER_QUERY + 1):
            try:
                msg = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    messages=[{"role": "user", "content": query_text}]
                )
                response_text = msg.content[0].text
                # build one record per call with everything we will need later
                record = {
                    "query_id": qid,
                    "query": query_text,
                    "intent_type": intent,
                    "run": run,
                    "timestamp": datetime.now().isoformat(),
                    "model": MODEL,
                    "response": response_text
                }
                
                out.write(json.dumps(record) + "\n")
                out.flush()
                calls_done += 1
                print(f"[{calls_done}/{total_planned}] {intent} | run {run} | {query_text[:45]}")
            except Exception as e:
                # log the failure and keep going, never let one bad call kill the whole run
                print(f"ERROR on '{query_text}' run {run}: {e}")
            # small pause between calls to be gentle on the api
            time.sleep(0.5)

print(f"done. {calls_done} responses saved to {OUTPUT_FILE}")