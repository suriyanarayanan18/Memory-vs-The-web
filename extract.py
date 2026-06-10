# extraction script: turns the raw answers into countable structured data
# haiku reads each answer and returns the brands mentioned


import json
import time
from urllib.parse import urlparse
from anthropic import Anthropic

client = Anthropic()

MODEL = "claude-haiku-4-5-20251001"
INPUT_FILES = ["responses.jsonl", "responses_retrieval.jsonl"]
OUTPUT_FILE = "structured.jsonl"

# the prompt asks haiku to return only a json array of brand names
EXTRACT_PROMPT = """You are reading an AI assistant's answer about running shoes.
List every running shoe BRAND mentioned as a recommendation or option in the text.
Use normalized brand names. Common ones: Nike, Adidas, Hoka, Brooks, ASICS, New Balance, Saucony, On, Mizuno, Altra, Topo, Salomon, Puma, Reebok, Kiprun, Merrell.
If a brand is clearly a running shoe brand but not in that list, include it with its proper name.
Count a brand once even if several of its models appear.
Return ONLY a JSON array of brand name strings and nothing else. Example: ["Nike", "Hoka", "ASICS"]

Answer text:
"""

# ask haiku for the brands in one answer, return a clean unique list
def extract_brands(text):
    if not text:
        return []
    msg = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": EXTRACT_PROMPT + text}]
    )
    raw = msg.content[0].text.strip()
    # strip code fences if haiku wraps the json
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        brands = json.loads(raw)
        if isinstance(brands, list):
            return sorted(set(str(b).strip() for b in brands if str(b).strip()))
    except Exception:
        pass
    return []

# pull a clean domain out of a url, drop the leading www
def domain_of(url):
    try:
        net = urlparse(url).netloc.lower()
        if net.startswith("www."):
            net = net[4:]
        return net or None
    except Exception:
        return None

# turn a list of url dicts into a sorted unique list of domains
def domains_from(url_list):
    doms = []
    for item in url_list or []:
        d = domain_of(item.get("url", ""))
        if d:
            doms.append(d)
    return sorted(set(doms))

records_out = 0
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    for path in INPUT_FILES:
        try:
            f = open(path, "r", encoding="utf-8")
        except FileNotFoundError:
            print(f"skipping missing file: {path}")
            continue
        with f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                brands = extract_brands(rec.get("response", ""))
                structured = {
                    "query_id": rec.get("query_id"),
                    "query": rec.get("query"),
                    "intent_type": rec.get("intent_type"),
                    "mode": rec.get("mode", "memory"),
                    "run": rec.get("run", 1),
                    "brands": brands,
                    "cited_domains": domains_from(rec.get("cited_urls")),
                    "retrieved_domains": domains_from(rec.get("retrieved_urls"))
                }
                out.write(json.dumps(structured) + "\n")
                out.flush()
                records_out += 1
                print(f"[{records_out}] {structured['mode']} | {structured['query_id']} | {len(brands)} brands | {len(structured['cited_domains'])} cited domains")
                time.sleep(0.3)

print(f"\ndone. {records_out} structured records saved to {OUTPUT_FILE}")