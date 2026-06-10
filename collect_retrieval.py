# retrieval collection script: same queries as the memory run, but with web search turned on
# for each call we capture the answer, the urls search retrieved, the urls actually cited, and usage for cost

import json
import csv
import time
from datetime import datetime
from anthropic import Anthropic

client = Anthropic()

# config in one place
MODEL = "claude-sonnet-4-6"
RUNS_PER_QUERY = 1
MAX_TOKENS = 1024
MAX_SEARCHES = 3
INPUT_CSV = "queries.csv"
OUTPUT_FILE = "responses_retrieval.jsonl"

# the web search tool definition, capped so one call cannot run up unlimited searches
SEARCH_TOOL = [{
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": MAX_SEARCHES
}]

# pull the answer text, retrieved urls, cited urls, and search count out of one response
def parse_response(msg):
    answer_parts = []
    retrieved = []
    cited = []
    for block in msg.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            answer_parts.append(getattr(block, "text", ""))
            # citations attached to this text block are the sources the answer actually used
            for c in getattr(block, "citations", None) or []:
                url = getattr(c, "url", None)
                if url:
                    cited.append({"url": url, "title": getattr(c, "title", None)})
        elif btype == "web_search_tool_result":
            # these are everything the search returned, used or not
            results = getattr(block, "content", None)
            if isinstance(results, list):
                for r in results:
                    url = getattr(r, "url", None)
                    if url:
                        retrieved.append({"url": url, "title": getattr(r, "title", None)})
    answer_text = "\n".join(p for p in answer_parts if p)
    return answer_text, retrieved, cited

# read the queries, utf-8-sig strips any excel bom
queries = []
with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        queries.append(row)

total_planned = len(queries) * RUNS_PER_QUERY
print(f"loaded {len(queries)} queries, running each {RUNS_PER_QUERY} times with web search")
print(f"that is {total_planned} total calls")

# running totals so we can print a rough cost estimate at the end
calls_done = 0
total_searches = 0
total_input = 0
total_output = 0

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
                    messages=[{"role": "user", "content": query_text}],
                    tools=SEARCH_TOOL
                )
                answer_text, retrieved, cited = parse_response(msg)

                # the authoritative search count and token usage for cost tracking
                usage = msg.usage
                server_use = getattr(usage, "server_tool_use", None)
                searches = getattr(server_use, "web_search_requests", 0) or 0
                in_tok = getattr(usage, "input_tokens", 0) or 0
                out_tok = getattr(usage, "output_tokens", 0) or 0

                total_searches += searches
                total_input += in_tok
                total_output += out_tok

                record = {
                    "query_id": qid,
                    "query": query_text,
                    "intent_type": intent,
                    "run": run,
                    "timestamp": datetime.now().isoformat(),
                    "model": MODEL,
                    "mode": "retrieval",
                    "response": answer_text,
                    "retrieved_urls": retrieved,
                    "cited_urls": cited,
                    "search_requests": searches,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
                calls_done += 1
                print(f"[{calls_done}/{total_planned}] {intent} | {searches} searches | {len(retrieved)} found | {len(cited)} cited | {query_text[:35]}")
            except Exception as e:
                # log and keep going, never let one bad call kill the run
                print(f"ERROR on '{query_text}' run {run}: {e}")
            # pause between calls, search calls are heavier so give it a moment
            time.sleep(1.0)

# rough cost estimate
search_cost = total_searches * 0.01
token_cost = (total_input / 1_000_000) * 3 + (total_output / 1_000_000) * 15
print(f"\ndone. {calls_done} responses saved to {OUTPUT_FILE}")
print(f"total searches: {total_searches}  input tokens: {total_input}  output tokens: {total_output}")
print(f"rough cost: ${search_cost:.2f} search + ${token_cost:.2f} tokens = ${search_cost + token_cost:.2f}")
print("check the Anthropic console for the exact figure before deciding on a second run")